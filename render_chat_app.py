from __future__ import annotations

import os

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

import render_app_v2 as legacy
import render_server as core
from chat_ui import render_chat_ui


def chat_config() -> dict[str, object]:
    url = os.getenv("SUPABASE_URL", "").strip()
    anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip()
    return {
        "supabaseUrl": url,
        "supabaseAnonKey": anon_key,
        "authConfigured": bool(url and anon_key),
        "modelDisplay": core.MODEL_DISPLAY,
    }


async def root(_: Request):
    return HTMLResponse(
        render_chat_ui(chat_config()),
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


routes = [
    Route("/", root),
    Route("/favicon.ico", core.favicon),
    Route("/healthz", core.healthz),
    Route("/api/chat-config", api_chat_config),
    Route("/api/health", core.api_health),
    Route("/api/programs", core.api_programs),
    Route("/api/ask", legacy.api_ask, methods=["POST"]),
    Route("/api/compare", core.api_compare, methods=["POST"]),
    Route("/api/import-questions", core.api_import_questions, methods=["POST"]),
    Route("/api/run-batch", legacy.api_run_batch, methods=["POST"]),
    Route("/api/benchmark", core.api_benchmark, methods=["POST"]),
]

app = Starlette(routes=routes, debug=False)
