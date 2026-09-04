from __future__ import annotations

import time

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

import render_app as ui
import render_server as core
from competition_ai.batch_fallback import nonempty_error_result
from competition_ai.policy import detect_language
from competition_ai.resilient_pipeline import ResilientCompetitionPipeline


def resilient_pipe(req: Request) -> ResilientCompetitionPipeline:
    return ResilientCompetitionPipeline(
        core.request_settings(req),
        core.CATALOG,
        core.EVIDENCE,
    )


async def root(_: Request):
    return HTMLResponse(
        ui.enhanced_ui(),
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Content-Type-Options": "nosniff",
        },
    )


async def api_ask(req: Request):
    if x := core.limited(req, "ask"):
        return x

    question = ""
    try:
        body = await req.json()
        question = str(body.get("question", "")).strip()
        if not question:
            return JSONResponse({"error": "question is required"}, status_code=400)

        forced = body.get("program")
        forced = forced if forced in {"AIT", "DSBA", "IT", "IT_INTER"} else None
        result = resilient_pipe(req).ask(question, forced_program=forced)
        return JSONResponse(core.response_payload(question, result))

    except Exception as exc:
        # Competition invariant: never return a blank answer for a valid row.
        if question:
            fallback = nonempty_error_result(question, core.clean_error(exc))
            payload = core.response_payload(question, fallback)
            payload["degraded"] = True
            payload["degradedReason"] = "temporary processing failure; rerun recommended"
            return JSONResponse(payload, status_code=200)
        return JSONResponse(
            {"error": "ระบบวิเคราะห์คำถามขัดข้องชั่วคราว", "detail": core.clean_error(exc)},
            status_code=500,
        )


async def api_run_batch(req: Request):
    if x := core.limited(req, "batch", limit=max(2, core.RATE // 4)):
        return x

    try:
        body = await req.json()
        questions = [
            str(q).strip()
            for q in body.get("questions", [])
            if str(q).strip()
        ]
        if not questions:
            return JSONResponse({"error": "questions is required"}, status_code=400)
        if len(questions) > 100:
            return JSONResponse({"error": "batch is limited to 100 questions"}, status_code=400)

        pipeline = resilient_pipe(req)
        rows = []
        batch_started = time.perf_counter()

        for idx, question in enumerate(questions, 1):
            started = time.perf_counter()
            try:
                result = pipeline.ask(question)
            except Exception as exc:
                result = nonempty_error_result(question, core.clean_error(exc))

            payload = core.response_payload(question, result)
            answer = str(result.answer or "").strip()
            if not answer:
                result = nonempty_error_result(question, "empty answer guard")
                payload = core.response_payload(question, result)
                answer = result.answer

            rows.append({
                "id": idx,
                "question": question,
                "answer": answer,
                "status": result.status,
                "language": payload["language"] or detect_language(question),
                "confidence": payload["confidence"],
                "program": payload["programDetected"] or "",
                "latencyMs": int(
                    getattr(result, "latency_ms", 0)
                    or ((time.perf_counter() - started) * 1000)
                ),
            })

        return JSONResponse({
            "total": len(rows),
            "rows": rows,
            "latencyMs": int((time.perf_counter() - batch_started) * 1000),
            "modelDisplay": core.MODEL_DISPLAY,
            "blankAnswers": sum(1 for row in rows if not str(row["answer"]).strip()),
        })

    except Exception as exc:
        return JSONResponse(
            {"error": "batch runner failed", "detail": core.clean_error(exc)},
            status_code=500,
        )


routes = [
    Route("/", root),
    Route("/favicon.ico", core.favicon),
    Route("/healthz", core.healthz),
    Route("/api/health", core.api_health),
    Route("/api/programs", core.api_programs),
    Route("/api/ask", api_ask, methods=["POST"]),
    Route("/api/compare", core.api_compare, methods=["POST"]),
    Route("/api/import-questions", core.api_import_questions, methods=["POST"]),
    Route("/api/run-batch", api_run_batch, methods=["POST"]),
    Route("/api/benchmark", core.api_benchmark, methods=["POST"]),
]

app = Starlette(routes=routes, debug=False)
