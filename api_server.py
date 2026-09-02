from __future__ import annotations

from pathlib import Path
from typing import Any
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from competition_ai.config import SETTINGS
from competition_ai.knowledge import load_catalog, load_evidence
from competition_ai.pipeline import CompetitionPipeline
from competition_ai.benchmark import load_benchmark, score_answer
from competition_ai.health import api_health

DOCS_DIR = ROOT / "data" / "documents"
FRONTEND_DIR = ROOT / "frontend"

catalog = load_catalog(ROOT)
evidence = load_evidence(ROOT, catalog)
pipeline = CompetitionPipeline(SETTINGS, catalog, evidence)
benchmark_spec = load_benchmark(ROOT)

app = FastAPI(title="ThaiLLM Academic Intelligence API", version="2.1-integrated")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    program: str | None = None


class CompareRequest(BaseModel):
    left: str
    right: str
    focus: str = "รายวิชาและทักษะ"


def _verification_payload(v: Any) -> dict[str, Any] | None:
    if v is None:
        return None
    return {
        "status": v.status,
        "confidence": v.confidence,
        "rationale": v.rationale,
        "supported_claims": v.supported_claims,
        "unsupported_claims": v.unsupported_claims,
    }


def _result_payload(result: Any) -> dict[str, Any]:
    return {
        "status": result.status,
        "answer": result.answer,
        "programs": result.programs,
        "latency_ms": result.latency_ms,
        "cache_hit": result.cache_hit,
        "verification": _verification_payload(result.verification),
        "evidence": [
            {
                "id": item.id,
                "source": item.source,
                "page": item.page,
                "text": item.text,
                "program": item.program,
                "score": item.score,
                "kind": item.kind,
                "citation": item.citation,
            }
            for item in result.evidence
        ],
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    ok, detail = api_health(SETTINGS)
    return {
        "ok": ok,
        "detail": detail,
        "model": SETTINGS.model,
        "evidence_units": len(evidence),
        "programs": [
            {
                "code": code,
                "display": data.get("display", code),
                "file": data.get("file", ""),
            }
            for code, data in catalog.items()
        ],
    }


@app.post("/api/ask")
def ask(req: AskRequest) -> dict[str, Any]:
    forced_program = req.program
    if forced_program in {"", "AUTO", "auto", None}:
        forced_program = None
    return _result_payload(pipeline.ask(req.question, forced_program=forced_program))


@app.post("/api/compare")
def compare(req: CompareRequest) -> dict[str, Any]:
    allowed = set(catalog.keys())
    if req.left not in allowed or req.right not in allowed:
        raise HTTPException(status_code=400, detail="Unknown curriculum code")
    if req.left == req.right:
        raise HTTPException(status_code=400, detail="Choose two different programs")
    question = f"เปรียบเทียบ {req.left} กับ {req.right}: {req.focus}"
    return _result_payload(pipeline.compare(question, [req.left, req.right], req.focus))


@app.post("/api/benchmark")
def benchmark() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    passed = 0
    for item in benchmark_spec["questions"]:
        result = pipeline.ask(item["question"])
        spec = benchmark_spec["gold"][str(item["id"])]
        ok, note = score_answer(item["id"], result, spec)
        passed += int(ok)
        rows.append({
            "id": item["id"],
            "question": item["question"],
            "type": item.get("type", ""),
            "passed": ok,
            "status": result.status,
            "note": note,
            "latency_ms": result.latency_ms,
        })
    total = len(rows)
    return {"passed": passed, "total": total, "score": (passed / total) if total else 0.0, "rows": rows}


@app.get("/api/documents/{filename}")
def document(filename: str):
    safe_name = Path(filename).name
    path = DOCS_DIR / safe_name
    if not path.exists() or path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(path, media_type="application/pdf")


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="frontend-static")


@app.get("/")
def frontend_root():
    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=503, detail="Frontend missing")
    return FileResponse(index, media_type="text/html")


@app.get("/{path:path}")
def frontend_fallback(path: str):
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    candidate = FRONTEND_DIR / path
    if candidate.exists() and candidate.is_file():
        return FileResponse(candidate)
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index, media_type="text/html")
    raise HTTPException(status_code=404, detail="Frontend missing")
