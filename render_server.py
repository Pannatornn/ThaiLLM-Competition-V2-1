from __future__ import annotations

import os, re, sys, time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import requests
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from competition_ai.config import SETTINGS
from competition_ai.knowledge import load_catalog, load_evidence
from competition_ai.pipeline import CompetitionPipeline, render_evidence
from competition_ai.benchmark import load_benchmark, score_answer
from render_ui import INDEX_HTML

CATALOG = load_catalog(ROOT)
EVIDENCE = load_evidence(ROOT, CATALOG)
PIPE: CompetitionPipeline | None = None
LABELS = {
    "AIT": "AIT — เทคโนโลยีปัญญาประดิษฐ์",
    "DSBA": "DSBA — วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ",
    "IT": "IT — เทคโนโลยีสารสนเทศ",
    "IT_INTER": "IT Inter — เทคโนโลยีสารสนเทศทางธุรกิจ (นานาชาติ)",
}
RATE = max(1, int(os.getenv("PUBLIC_RATE_LIMIT_PER_MINUTE", "30")))
REQ: dict[tuple[str, str], deque[float]] = defaultdict(deque)


def pipe() -> CompetitionPipeline:
    global PIPE
    if PIPE is None:
        PIPE = CompetitionPipeline(SETTINGS, CATALOG, EVIDENCE)
    return PIPE


def ip(req: Request) -> str:
    return req.headers.get("x-forwarded-for", "").split(",")[0].strip() or (req.client.host if req.client else "unknown")


def limited(req: Request, bucket: str):
    now = time.monotonic(); q = REQ[(ip(req), bucket)]
    while q and now - q[0] > 60: q.popleft()
    if len(q) >= RATE:
        return JSONResponse({"error": "Too many requests. Please retry shortly."}, status_code=429)
    q.append(now); return None


def has_thai(s: str) -> bool:
    return bool(re.search(r"[\u0E00-\u0E7F]", s or ""))


def localize(p: CompetitionPipeline, question: str, result: Any, lang: str):
    lang = lang.upper()
    static = {
        "BLOCKED": {"TH": "คำขอนี้พยายามเปลี่ยนหรือเปิดเผยคำสั่งภายในระบบ จึงถูกบล็อก", "EN": "This request attempts to override or reveal internal instructions, so it was blocked."},
        "OUT_OF_SCOPE": {"TH": "คำถามนี้อยู่นอกขอบเขตชุดข้อมูลที่ผู้จัดกำหนด", "EN": "This question is outside the organizer-provided curriculum dataset."},
        "NEEDS_CONTEXT": {"TH": "กรุณาระบุ AIT, DSBA, IT หรือ IT Inter", "EN": "Please specify AIT, DSBA, IT, or IT Inter."},
    }
    if result.status in static:
        result.answer = static[result.status][lang]; return result
    if not result.evidence or result.status == "API_ERROR": return result
    if has_thai(result.answer) == (lang == "TH"): return result
    target = "Thai" if lang == "TH" else "English"
    result.answer = p.llm.generate(
        f"Rewrite ANSWER in {target} only. Preserve every fact, number, course name and [E#] citation. Do not add facts. Return only the rewritten answer.",
        f"QUESTION:\n{question}\n\nANSWER:\n{result.answer}\n\nEVIDENCE:\n{render_evidence(result.evidence)}",
    )
    return result


def response(question: str, result: Any) -> dict[str, Any]:
    conf = float(result.verification.confidence) if result.verification else (1.0 if result.status == "BLOCKED" else 0.0)
    evs = [{
        "id": e.id, "sourceDoc": e.source, "sourceDocTitle": LABELS.get(e.program, e.program),
        "page": f"หน้า {e.page}" if e.page else "ไม่ระบุหน้า", "pageNumber": int(e.page or 0),
        "programCode": e.program, "quoteTh": e.text, "quoteEn": e.text, "confidence": conf,
    } for e in result.evidence]
    points = list(result.verification.supported_claims)[:4] if result.verification else []
    if not points:
        points = [re.sub(r"^[\-•*\d.\s]+", "", x).strip() for x in (result.answer or "").splitlines() if len(x.strip()) > 12][:4]
    return {
        "question": question, "status": result.status, "answerTh": result.answer, "answerEn": result.answer,
        "programDetected": " / ".join(LABELS.get(x, x) for x in result.programs) if result.programs else None,
        "confidence": max(0.0, min(1.0, conf)), "supportedByEvidence": bool(result.evidence) and result.status in {"SUPPORTED", "PARTIALLY_SUPPORTED"},
        "securityVerdict": "PROMPT_INJECTION_BLOCKED" if result.status == "BLOCKED" else ("OUT_OF_SCOPE" if result.status == "OUT_OF_SCOPE" else "CLEAN"),
        "summaryKeyPoints": points, "evidenceList": evs, "latencyMs": int(result.latency_ms or 0), "cacheHit": bool(getattr(result, "cache_hit", False)),
    }


def by_topic(code: str, topic: str, limit=2):
    return [re.sub(r"\s+", " ", str(f.get("text", ""))).strip() for f in CATALOG.get(code, {}).get("facts", []) if str(f.get("topic", "")) == topic][:limit]


def matrix(left: str, right: str, focus: str):
    q = focus.casefold(); specs = [("ภาพรวมหลักสูตร", ["basic", "duration"])]
    checks = [
        (("หน่วยกิต", "โครงสร้าง", "credit", "structure"), "โครงสร้าง/หน่วยกิต", ["structure", "basic"]),
        (("สาย", "กลุ่ม", "track", "เฉพาะ"), "กลุ่มวิชา/ความเชี่ยวชาญ", ["tracks"]),
        (("วิชา", "course", "ai", "machine", "deep", "nlp"), "รายวิชาสำคัญ", ["courses"]),
        (("ทักษะ", "skill"), "ทักษะและผลลัพธ์การเรียนรู้", ["skills"]),
        (("อาชีพ", "career", "งาน"), "แนวทางอาชีพ", ["career"]),
        (("ภาษา", "language", "english"), "ภาษาที่ใช้ในการเรียน", ["language"]),
    ]
    for words, label, topics in checks:
        if any(w in q for w in words): specs.append((label, topics))
    if len(specs) == 1:
        specs += [("โครงสร้าง/หน่วยกิต", ["structure", "basic"]), ("กลุ่มวิชา/ความเชี่ยวชาญ", ["tracks"]), ("รายวิชาสำคัญ", ["courses"]), ("ทักษะและผลลัพธ์การเรียนรู้", ["skills"]), ("แนวทางอาชีพ", ["career"])]
    rows=[]
    for label, topics in specs:
        def items(code):
            out=[]
            for t in topics:
                for x in by_topic(code, t, 2):
                    if x not in out: out.append(x)
                    if len(out) >= 2: return out
            return out
        a,b=items(left),items(right)
        if a or b: rows.append({"label": label, "left": a, "right": b})
    return {"left": {"code": left, "display": CATALOG[left].get("display", left)}, "right": {"code": right, "display": CATALOG[right].get("display", right)}, "focus": focus, "rows": rows}


async def root(_: Request):
    return HTMLResponse(INDEX_HTML, headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

async def healthz(_: Request):
    return JSONResponse({"ok": True, "programs": len(CATALOG), "evidenceUnits": len(EVIDENCE)})

async def api_health(_: Request):
    ok=False; detail="THAILLM_API_KEY is not configured"
    if SETTINGS.api_key:
        try:
            r=requests.get("https://thaillm.or.th/api/v1/models", headers={"Authorization": "Bearer "+SETTINGS.api_key}, timeout=12)
            ok=r.status_code==200; detail="ThaiLLM API ready" if ok else f"HTTP {r.status_code}"
        except Exception as e: detail=str(e)[:300]
    return JSONResponse({"status": "online" if ok else "degraded", "apiConnected": ok, "detail": detail, "model": SETTINGS.model, "programs": len(CATALOG), "evidenceUnits": len(EVIDENCE)})

async def api_programs(_: Request):
    return JSONResponse({"programs": [{"code": c, "display": CATALOG[c].get("display", c)} for c in ["AIT","DSBA","IT","IT_INTER"] if c in CATALOG]})

async def api_ask(req: Request):
    if x:=limited(req,"ask"): return x
    try:
        b=await req.json(); q=str(b.get("question","")).strip(); lang=str(b.get("language","TH")).upper()
        if not q: return JSONResponse({"error":"question is required"},status_code=400)
        forced=b.get("program"); forced=forced if forced in {"AIT","DSBA","IT","IT_INTER"} else None
        p=pipe(); r=p.ask(q, forced_program=forced); r=localize(p,q,r,"EN" if lang=="EN" else "TH")
        out=response(q,r); out["language"]=lang; return JSONResponse(out)
    except Exception as e: return JSONResponse({"error":str(e)[:500],"type":e.__class__.__name__},status_code=500)

async def api_compare(req: Request):
    if x:=limited(req,"compare"): return x
    try:
        b=await req.json(); left=str(b.get("left","")); right=str(b.get("right","")); focus=str(b.get("focus","")).strip(); lang=str(b.get("language","TH")).upper()
        if left not in LABELS or right not in LABELS or left==right: return JSONResponse({"error":"select two different valid programs"},status_code=400)
        if not focus: focus="ภาพรวมหลักสูตร รายวิชา ทักษะ และอาชีพ" if lang!="EN" else "program overview, courses, skills, and careers"
        q=f"Compare {left} and {right}: {focus}" if lang=="EN" else f"เปรียบเทียบ {left} กับ {right}: {focus}"
        p=pipe(); r=p.compare(q,[left,right],focus); r=localize(p,q,r,"EN" if lang=="EN" else "TH")
        out=response(q,r); out.update({"left":left,"right":right,"focus":focus,"language":lang,"structuredComparison":matrix(left,right,focus)}); return JSONResponse(out)
    except Exception as e: return JSONResponse({"error":str(e)[:500],"type":e.__class__.__name__},status_code=500)

async def api_benchmark(req: Request):
    if x:=limited(req,"benchmark"): return x
    try:
        bench=load_benchmark(ROOT); p=pipe(); rows=[]; passed=sec_t=sec_p=scope_t=scope_p=ground_t=ground_e=0
        for item in bench["questions"]:
            r=p.ask(item["question"]); spec=bench["gold"][str(item["id"])]; good,note=score_answer(item["id"],r,spec); passed+=int(good); kind=spec["kind"]
            if kind=="blocked": sec_t+=1; sec_p+=int(good); cat="Prompt Injection"
            elif kind=="out_of_scope": scope_t+=1; scope_p+=int(good); cat="Out-of-scope Detection"
            else: ground_t+=1; ground_e+=int(bool(r.evidence)); cat="Curriculum QA"
            rows.append({"id":str(item["id"]),"category":cat,"question":item["question"],"groundTruth":", ".join(spec.get("must_contain",[])) or kind,"score":100 if good else 0,"latencyMs":int(r.latency_ms or 0),"passed":bool(good),"status":r.status,"note":note})
        total=len(rows); return JSONResponse({"total":total,"passed":passed,"failed":total-passed,"passRate":passed/total if total else 0,"evidenceCoverage":ground_e/ground_t if ground_t else 0,"scopeHandling":scope_p/scope_t if scope_t else 0,"injectionBlock":sec_p/sec_t if sec_t else 0,"rows":rows})
    except Exception as e: return JSONResponse({"error":str(e)[:500],"type":e.__class__.__name__},status_code=500)

routes=[Route("/",root),Route("/healthz",healthz),Route("/api/health",api_health),Route("/api/programs",api_programs),Route("/api/ask",api_ask,methods=["POST"]),Route("/api/compare",api_compare,methods=["POST"]),Route("/api/benchmark",api_benchmark,methods=["POST"])]
app=Starlette(routes=routes,debug=False)
