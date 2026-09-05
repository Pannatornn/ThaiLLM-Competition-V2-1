from __future__ import annotations

import os
import re

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

import render_app_v2 as legacy
import render_server as core
from chat_ui import render_chat_ui
from chat_ui_finish_patch import inject_final_ui_patch
from chat_ui_patch import inject_chat_runtime_patch
from competition_ai.router import route_question


FOLLOWUP_COMPARE_RE = re.compile(
    r"เปรียบ|เทียบ|ต่าง|อันไหน|มากกว่า|น้อยกว่า|compare|difference|which|better|more|less|比较|区别|哪个|更多|更少",
    re.I,
)


def chat_config() -> dict[str, object]:
    url = os.getenv("SUPABASE_URL", "").strip()
    anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip()
    return {
        "supabaseUrl": url,
        "supabaseAnonKey": anon_key,
        "authConfigured": bool(url and anon_key),
        "modelDisplay": core.MODEL_DISPLAY,
    }


def _recent_user_programs(history: list[dict]) -> list[str]:
    """Recover explicit program context from recent user turns only.

    Assistant answers can mention many curricula, so they are intentionally not
    used for routing context. The nearest user turn that names a program wins.
    """
    for item in reversed(history[-10:]):
        if str(item.get("role", "")).casefold() != "user":
            continue
        text = str(item.get("content", "")).strip()
        if not text:
            continue
        routed = route_question(text, core.CATALOG)
        if routed.programs:
            return list(dict.fromkeys(routed.programs))
    return []


async def root(_: Request):
    html = inject_chat_runtime_patch(render_chat_ui(chat_config()))
    html = inject_final_ui_patch(html)
    return HTMLResponse(
        html,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "same-origin",
        },
    )


async def api_chat_config(_: Request):
    # Supabase anon keys are intentionally public browser credentials. Row-level
    # security in supabase/schema.sql is what protects each user's chat data.
    return JSONResponse(chat_config())


async def api_chat(req: Request):
    if x := core.limited(req, "chat"):
        return x

    try:
        body = await req.json()
        question = str(body.get("question", "")).strip()
        if not question:
            return JSONResponse({"error": "question is required"}, status_code=400)

        history = body.get("history", [])
        if not isinstance(history, list):
            history = []
        history = [x for x in history[-10:] if isinstance(x, dict)]

        pipeline = legacy.resilient_pipe(req)
        current_route = route_question(question, core.CATALOG)
        contextualized = False

        if current_route.programs or not current_route.ambiguous:
            result = pipeline.ask(question)
        else:
            recent_programs = _recent_user_programs(history)
            if len(recent_programs) == 1:
                # Example: "AIT เรียนอะไรบ้าง" -> "แล้วเรียนกี่ปี?"
                result = pipeline.ask(question, forced_program=recent_programs[0])
                contextualized = True
            elif len(recent_programs) >= 2 and FOLLOWUP_COMPARE_RE.search(question):
                # Example: "AIT กับ DSBA ต่างกันยังไง" -> "แล้วอันไหนหน่วยกิตมากกว่า?"
                programs = recent_programs[:2]
                result = pipeline.compare(question, programs, question)
                result = pipeline._ensure_answer_language(question, result)
                contextualized = True
            else:
                result = pipeline.ask(question)

        payload = core.response_payload(question, result)
        payload["contextualized"] = contextualized
        return JSONResponse(payload)
    except Exception as exc:
        # Keep the conversational surface non-empty even during transient
        # upstream failures, matching the competition batch invariant.
        fallback = legacy.nonempty_error_result(
            str(locals().get("question", "") or "คำถามนี้"),
            core.clean_error(exc),
        )
        payload = core.response_payload(str(locals().get("question", "")), fallback)
        payload["degraded"] = True
        payload["contextualized"] = False
        return JSONResponse(payload, status_code=200)


routes = [
    Route("/", root),
    Route("/favicon.ico", core.favicon),
    Route("/healthz", core.healthz),
    Route("/api/chat-config", api_chat_config),
    Route("/api/health", core.api_health),
    Route("/api/programs", core.api_programs),
    Route("/api/chat", api_chat, methods=["POST"]),
    Route("/api/ask", legacy.api_ask, methods=["POST"]),
    Route("/api/compare", core.api_compare, methods=["POST"]),
    Route("/api/import-questions", core.api_import_questions, methods=["POST"]),
    Route("/api/run-batch", legacy.api_run_batch, methods=["POST"]),
    Route("/api/benchmark", core.api_benchmark, methods=["POST"]),
]

app = Starlette(routes=routes, debug=False)
