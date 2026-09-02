from __future__ import annotations

import os
import re
import sys
import time
from collections import defaultdict, deque
from dataclasses import replace
from pathlib import Path
from typing import Any

import requests
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from competition_ai.config import SETTINGS
from competition_ai.knowledge import load_catalog, load_evidence
from competition_ai.pipeline import (
    CompetitionPipeline,
    balance_evidence_by_program,
    render_evidence,
)
from competition_ai.retrieval import infer_topics, retrieve
from competition_ai.benchmark import load_benchmark, score_answer

from render_ui import INDEX_HTML

CATALOG = load_catalog(ROOT)
EVIDENCE = load_evidence(ROOT, CATALOG)
PIPE: CompetitionPipeline | None = None
BENCH_PIPE: CompetitionPipeline | None = None

LABELS = {
    "AIT": "AIT — เทคโนโลยีปัญญาประดิษฐ์",
    "DSBA": "DSBA — วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ",
    "IT": "IT — เทคโนโลยีสารสนเทศ",
    "IT_INTER": "IT Inter — เทคโนโลยีสารสนเทศทางธุรกิจ (นานาชาติ)",
}

RATE = max(1, int(os.getenv("PUBLIC_RATE_LIMIT_PER_MINUTE", "30")))
BENCHMARK_COOLDOWN = max(0, int(os.getenv("BENCHMARK_COOLDOWN_SECONDS", "60")))
REQ: dict[tuple[str, str], deque[float]] = defaultdict(deque)
BENCHMARK_CACHE: dict[str, Any] | None = None
BENCHMARK_CACHE_AT = 0.0


def pipe() -> CompetitionPipeline:
    global PIPE
    if PIPE is None:
        PIPE = CompetitionPipeline(SETTINGS, CATALOG, EVIDENCE)
    return PIPE


def bench_pipe() -> CompetitionPipeline:
    """Benchmark path: one ThaiLLM generation per curriculum case, no planner/rerank/verifier fan-out."""
    global BENCH_PIPE
    if BENCH_PIPE is None:
        fast = replace(
            SETTINGS,
            use_query_planner=False,
            use_rerank=False,
            verify_answers=False,
            answer_repair=False,
            retries=0,
            timeout=min(SETTINGS.timeout, 75),
        )
        BENCH_PIPE = CompetitionPipeline(fast, CATALOG, EVIDENCE)
    return BENCH_PIPE


def ip(req: Request) -> str:
    return (
        req.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (req.client.host if req.client else "unknown")
    )


def limited(req: Request, bucket: str, limit: int | None = None):
    now = time.monotonic()
    q = REQ[(ip(req), bucket)]
    window = 60
    while q and now - q[0] > window:
        q.popleft()
    allowed = limit or RATE
    if len(q) >= allowed:
        retry = max(1, int(window - (now - q[0])))
        return JSONResponse(
            {
                "error": "Too many requests. Please retry shortly.",
                "type": "RATE_LIMIT",
                "retryAfterSeconds": retry,
            },
            status_code=429,
            headers={"Retry-After": str(retry)},
        )
    q.append(now)
    return None


def has_thai(s: str) -> bool:
    return bool(re.search(r"[\u0E00-\u0E7F]", s or ""))


def clean_error(exc: Exception | str) -> str:
    s = str(exc).strip()
    s = re.sub(r"Bearer\s+[A-Za-z0-9._\-]+", "Bearer [redacted]", s, flags=re.I)
    return (s[:380] + "…") if len(s) > 380 else (s or "Unknown error")


def transient_upstream(exc: Exception | str) -> bool:
    s = str(exc).casefold()
    return any(
        x in s
        for x in (
            "http 502",
            "http 503",
            "http 504",
            "bad gateway",
            "service unavailable",
            "gateway timeout",
            "timed out",
            "timeout",
            "connection reset",
            "remote disconnected",
        )
    )


def localize(p: CompetitionPipeline, question: str, result: Any, lang: str):
    lang = lang.upper()
    static = {
        "BLOCKED": {
            "TH": "คำขอนี้พยายามเปลี่ยนหรือเปิดเผยคำสั่งภายในระบบ จึงถูกบล็อก",
            "EN": "This request attempts to override or reveal internal instructions, so it was blocked.",
        },
        "OUT_OF_SCOPE": {
            "TH": "คำถามนี้อยู่นอกขอบเขตชุดข้อมูลที่ผู้จัดกำหนด",
            "EN": "This question is outside the organizer-provided curriculum dataset.",
        },
        "NEEDS_CONTEXT": {
            "TH": "กรุณาระบุ AIT, DSBA, IT หรือ IT Inter",
            "EN": "Please specify AIT, DSBA, IT, or IT Inter.",
        },
        "EMPTY": {"TH": "กรุณาพิมพ์คำถาม", "EN": "Please enter a question."},
    }
    if result.status in static:
        result.answer = static[result.status][lang]
        return result
    if not result.evidence or result.status == "API_ERROR":
        return result
    if has_thai(result.answer) == (lang == "TH"):
        return result

    target = "Thai" if lang == "TH" else "English"
    try:
        result.answer = p.llm.generate(
            (
                f"Rewrite ANSWER in {target} only. Preserve every fact, number, "
                "course name and [E#] citation. Do not add facts. Return only "
                "the rewritten answer."
            ),
            (
                f"QUESTION:\n{question}\n\nANSWER:\n{result.answer}\n\n"
                f"EVIDENCE:\n{render_evidence(result.evidence)}"
            ),
        )
    except Exception:
        pass
    return result


def response(question: str, result: Any) -> dict[str, Any]:
    conf = (
        float(result.verification.confidence)
        if result.verification
        else (1.0 if result.status in {"BLOCKED", "OUT_OF_SCOPE"} else 0.0)
    )
    evs = [
        {
            "id": e.id,
            "sourceDoc": e.source,
            "sourceDocTitle": LABELS.get(e.program, e.program),
            "page": f"หน้า {e.page}" if e.page else "ไม่ระบุหน้า",
            "pageNumber": int(e.page or 0),
            "programCode": e.program,
            "quoteTh": e.text,
            "quoteEn": e.text,
            "confidence": conf,
        }
        for e in result.evidence
    ]
    points = list(result.verification.supported_claims)[:4] if result.verification else []
    if not points:
        points = [
            re.sub(r"^[\-•*\d.\s]+", "", x).strip()
            for x in (result.answer or "").splitlines()
            if len(x.strip()) > 12
        ][:4]
    return {
        "question": question,
        "status": result.status,
        "answerTh": result.answer,
        "answerEn": result.answer,
        "programDetected": (
            " / ".join(LABELS.get(x, x) for x in result.programs)
            if result.programs
            else None
        ),
        "confidence": max(0.0, min(1.0, conf)),
        "supportedByEvidence": bool(result.evidence)
        and result.status in {"SUPPORTED", "PARTIALLY_SUPPORTED", "CHECK_REQUIRED"},
        "securityVerdict": (
            "PROMPT_INJECTION_BLOCKED"
            if result.status == "BLOCKED"
            else ("OUT_OF_SCOPE" if result.status == "OUT_OF_SCOPE" else "CLEAN")
        ),
        "summaryKeyPoints": points,
        "evidenceList": evs,
        "latencyMs": int(result.latency_ms or 0),
        "cacheHit": bool(getattr(result, "cache_hit", False)),
    }


def by_topic(code: str, topic: str, limit: int = 2):
    return [
        re.sub(r"\s+", " ", str(f.get("text", ""))).strip()
        for f in CATALOG.get(code, {}).get("facts", [])
        if str(f.get("topic", "")) == topic
    ][:limit]


def matrix(left: str, right: str, focus: str):
    q = focus.casefold()
    specs = [("ภาพรวมหลักสูตร", ["basic", "duration"])]
    checks = [
        (("หน่วยกิต", "โครงสร้าง", "credit", "structure"), "โครงสร้าง/หน่วยกิต", ["structure", "basic"]),
        (("สาย", "กลุ่ม", "track", "เฉพาะ"), "กลุ่มวิชา/ความเชี่ยวชาญ", ["tracks"]),
        (("วิชา", "course", "ai", "machine", "deep", "nlp"), "รายวิชาสำคัญ", ["courses"]),
        (("ทักษะ", "skill"), "ทักษะและผลลัพธ์การเรียนรู้", ["skills"]),
        (("อาชีพ", "career", "งาน"), "แนวทางอาชีพ", ["career"]),
        (("ภาษา", "language", "english"), "ภาษาที่ใช้ในการเรียน", ["language"]),
    ]
    for words, label, topics in checks:
        if any(w in q for w in words):
            specs.append((label, topics))
    if len(specs) == 1:
        specs += [
            ("โครงสร้าง/หน่วยกิต", ["structure", "basic"]),
            ("กลุ่มวิชา/ความเชี่ยวชาญ", ["tracks"]),
            ("รายวิชาสำคัญ", ["courses"]),
            ("ทักษะและผลลัพธ์การเรียนรู้", ["skills"]),
            ("แนวทางอาชีพ", ["career"]),
        ]

    rows = []
    for label, topics in specs:
        def items(code: str):
            out = []
            for t in topics:
                for x in by_topic(code, t, 2):
                    if x not in out:
                        out.append(x)
                    if len(out) >= 2:
                        return out
            return out

        a, b = items(left), items(right)
        if a or b:
            rows.append({"label": label, "left": a, "right": b})

    return {
        "left": {"code": left, "display": CATALOG[left].get("display", left)},
        "right": {"code": right, "display": CATALOG[right].get("display", right)},
        "focus": focus,
        "rows": rows,
    }


def fallback_evidence(programs: list[str], focus: str, limit: int = 8):
    topics = infer_topics(focus)
    if not topics:
        topics = {"basic", "structure", "tracks", "courses", "skills", "career"}

    selected = []
    seen = set()
    for code in programs:
        for e in EVIDENCE:
            if e.program != code or e.kind != "canonical":
                continue
            topic = str(e.metadata.get("topic", "")).casefold()
            if topic in topics or topic == "basic":
                if e.id not in seen:
                    selected.append(e)
                    seen.add(e.id)
                    break

    for e in EVIDENCE:
        if len(selected) >= limit:
            break
        if e.program not in programs or e.kind != "canonical" or e.id in seen:
            continue
        topic = str(e.metadata.get("topic", "")).casefold()
        if topic in topics or topic in {"basic", "structure"}:
            selected.append(e)
            seen.add(e.id)
    return selected[:limit]


def evidence_payload(items: list[Any], confidence: float = 1.0):
    return [
        {
            "id": e.id,
            "sourceDoc": e.source,
            "sourceDocTitle": LABELS.get(e.program, e.program),
            "page": f"หน้า {e.page}" if e.page else "ไม่ระบุหน้า",
            "pageNumber": int(e.page or 0),
            "programCode": e.program,
            "quoteTh": e.text,
            "quoteEn": e.text,
            "confidence": confidence,
        }
        for e in items
    ]


def fallback_compare_payload(left: str, right: str, focus: str, lang: str, exc: Exception | str):
    sc = matrix(left, right, focus)
    ev = fallback_evidence([left, right], focus)
    if lang == "EN":
        answer = (
            "ThaiLLM is temporarily unavailable, so the comparison table below is being "
            "shown directly from canonical curriculum facts. No external facts were added."
        )
    else:
        answer = (
            "ThaiLLM ตอบกลับไม่สำเร็จชั่วคราว ระบบจึงแสดงตารางเปรียบเทียบจาก canonical facts "
            "ของหลักสูตรโดยตรง โดยไม่เติมข้อมูลภายนอก"
        )
    return {
        "question": f"compare {left} {right}",
        "status": "DEGRADED_CANONICAL",
        "answerTh": answer,
        "answerEn": answer,
        "programDetected": f"{LABELS[left]} / {LABELS[right]}",
        "confidence": 1.0,
        "supportedByEvidence": bool(ev),
        "securityVerdict": "CLEAN",
        "summaryKeyPoints": [answer],
        "evidenceList": evidence_payload(ev),
        "latencyMs": 0,
        "cacheHit": False,
        "left": left,
        "right": right,
        "focus": focus,
        "language": lang,
        "structuredComparison": sc,
        "degraded": True,
        "degradedReason": "ThaiLLM upstream temporarily unavailable",
        "upstreamError": clean_error(exc),
    }


async def root(_: Request):
    return HTMLResponse(
        INDEX_HTML,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


async def favicon(_: Request):
    return Response(status_code=204)


async def healthz(_: Request):
    return JSONResponse({"ok": True, "programs": len(CATALOG), "evidenceUnits": len(EVIDENCE)})


async def api_health(_: Request):
    ok = False
    detail = "THAILLM_API_KEY is not configured"
    if SETTINGS.api_key:
        try:
            r = requests.get(
                "https://thaillm.or.th/api/v1/models",
                headers={"Authorization": "Bearer " + SETTINGS.api_key},
                timeout=12,
            )
            ok = r.status_code == 200
            detail = "ThaiLLM API ready" if ok else f"HTTP {r.status_code}"
        except Exception as e:
            detail = clean_error(e)
    return JSONResponse(
        {
            "status": "online" if ok else "degraded",
            "apiConnected": ok,
            "detail": detail,
            "model": SETTINGS.model,
            "programs": len(CATALOG),
            "evidenceUnits": len(EVIDENCE),
        }
    )


async def api_programs(_: Request):
    return JSONResponse(
        {
            "programs": [
                {"code": c, "display": CATALOG[c].get("display", c)}
                for c in ["AIT", "DSBA", "IT", "IT_INTER"]
                if c in CATALOG
            ]
        }
    )


async def api_ask(req: Request):
    if x := limited(req, "ask"):
        return x
    try:
        b = await req.json()
        q = str(b.get("question", "")).strip()
        lang = str(b.get("language", "TH")).upper()
        if not q:
            return JSONResponse({"error": "question is required"}, status_code=400)
        forced = b.get("program")
        forced = forced if forced in {"AIT", "DSBA", "IT", "IT_INTER"} else None
        p = pipe()
        r = p.ask(q, forced_program=forced)
        r = localize(p, q, r, "EN" if lang == "EN" else "TH")
        out = response(q, r)
        out["language"] = lang
        if r.status == "API_ERROR":
            out["degraded"] = True
            out["degradedReason"] = "ThaiLLM upstream temporarily unavailable"
        return JSONResponse(out)
    except Exception as e:
        return JSONResponse(
            {
                "error": "ระบบวิเคราะห์คำถามขัดข้องชั่วคราว",
                "detail": clean_error(e),
                "type": e.__class__.__name__,
            },
            status_code=503 if transient_upstream(e) else 500,
        )


async def api_compare(req: Request):
    if x := limited(req, "compare"):
        return x
    b: dict[str, Any] = {}
    try:
        b = await req.json()
        left = str(b.get("left", ""))
        right = str(b.get("right", ""))
        focus = str(b.get("focus", "")).strip()
        lang = str(b.get("language", "TH")).upper()
        if left not in LABELS or right not in LABELS or left == right:
            return JSONResponse({"error": "select two different valid programs"}, status_code=400)
        if not focus:
            focus = (
                "program overview, courses, skills, and careers"
                if lang == "EN"
                else "ภาพรวมหลักสูตร รายวิชา ทักษะ และอาชีพ"
            )
        q = (
            f"Compare {left} and {right}: {focus}"
            if lang == "EN"
            else f"เปรียบเทียบ {left} กับ {right}: {focus}"
        )

        sc = matrix(left, right, focus)
        try:
            p = pipe()
            r = p.compare(q, [left, right], focus)
            r = localize(p, q, r, "EN" if lang == "EN" else "TH")
            out = response(q, r)
            out.update(
                {
                    "left": left,
                    "right": right,
                    "focus": focus,
                    "language": lang,
                    "structuredComparison": sc,
                    "degraded": False,
                }
            )
            return JSONResponse(out)
        except Exception as upstream:
            return JSONResponse(fallback_compare_payload(left, right, focus, lang, upstream))
    except Exception as e:
        left = str(b.get("left", ""))
        right = str(b.get("right", ""))
        focus = str(b.get("focus", "")).strip() or "ภาพรวมหลักสูตร"
        lang = str(b.get("language", "TH")).upper()
        if left in LABELS and right in LABELS and left != right:
            return JSONResponse(fallback_compare_payload(left, right, focus, lang, e))
        return JSONResponse(
            {"error": "ไม่สามารถสร้าง Comparison Report ได้", "detail": clean_error(e)},
            status_code=500,
        )


async def api_benchmark(req: Request):
    global BENCHMARK_CACHE, BENCHMARK_CACHE_AT
    if x := limited(req, "benchmark", limit=max(2, RATE // 3)):
        return x

    now = time.monotonic()
    if BENCHMARK_CACHE is not None and now - BENCHMARK_CACHE_AT < BENCHMARK_COOLDOWN:
        cached = dict(BENCHMARK_CACHE)
        cached["cacheHit"] = True
        cached["cacheAgeSeconds"] = int(now - BENCHMARK_CACHE_AT)
        return JSONResponse(cached)

    try:
        bench = load_benchmark(ROOT)
        try:
            p = bench_pipe()
        except Exception:
            p = None

        rows = []
        passed = sec_t = sec_p = scope_t = scope_p = ground_t = ground_e = 0
        errors = 0

        for item in bench["questions"]:
            spec = bench["gold"][str(item["id"])]
            kind = spec["kind"]
            started = time.perf_counter()
            try:
                if p is None:
                    raise RuntimeError("ThaiLLM pipeline is unavailable")
                r = p.ask(item["question"])
                good, note = score_answer(item["id"], r, spec)
                if r.status == "API_ERROR":
                    good = False
                    note = "ThaiLLM upstream unavailable"
                latency = int(r.latency_ms or ((time.perf_counter() - started) * 1000))
                status = r.status
                has_evidence = bool(r.evidence)
            except Exception as one:
                good = False
                note = clean_error(one)
                latency = int((time.perf_counter() - started) * 1000)
                status = "ERROR"
                has_evidence = False
                errors += 1

            passed += int(good)
            if kind == "blocked":
                sec_t += 1
                sec_p += int(good)
                cat = "Prompt Injection"
            elif kind == "out_of_scope":
                scope_t += 1
                scope_p += int(good)
                cat = "Out-of-scope Detection"
            else:
                ground_t += 1
                ground_e += int(has_evidence)
                cat = "Curriculum QA"

            rows.append(
                {
                    "id": str(item["id"]),
                    "category": cat,
                    "question": item["question"],
                    "groundTruth": ", ".join(spec.get("must_contain", [])) or kind,
                    "expectedBehavior": kind,
                    "score": 100 if good else 0,
                    "latencyMs": latency,
                    "passed": bool(good),
                    "status": status,
                    "note": note,
                }
            )

        total = len(rows)
        payload = {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "passRate": passed / total if total else 0,
            "evidenceCoverage": ground_e / ground_t if ground_t else 0,
            "scopeHandling": scope_p / scope_t if scope_t else 0,
            "injectionBlock": sec_p / sec_t if sec_t else 0,
            "rows": rows,
            "errors": errors,
            "degraded": errors > 0,
            "cacheHit": False,
        }
        BENCHMARK_CACHE = payload
        BENCHMARK_CACHE_AT = time.monotonic()
        return JSONResponse(payload)
    except Exception as e:
        return JSONResponse(
            {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "passRate": 0,
                "evidenceCoverage": 0,
                "scopeHandling": 0,
                "injectionBlock": 0,
                "rows": [],
                "errors": 1,
                "degraded": True,
                "error": "Benchmark service is temporarily degraded",
                "detail": clean_error(e),
            },
            status_code=200,
        )


routes = [
    Route("/", root),
    Route("/favicon.ico", favicon),
    Route("/healthz", healthz),
    Route("/api/health", api_health),
    Route("/api/programs", api_programs),
    Route("/api/ask", api_ask, methods=["POST"]),
    Route("/api/compare", api_compare, methods=["POST"]),
    Route("/api/benchmark", api_benchmark, methods=["POST"]),
]
app = Starlette(routes=routes, debug=False)
