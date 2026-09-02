from __future__ import annotations
import json
import re
from pathlib import Path
from .models import RouteResult

def load_catalog(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def _alias_hit(question: str, alias: str) -> bool:
    q = question.casefold()
    a = alias.casefold()
    if a in {"it", "ait", "dsba", "bit"}:
        return bool(re.search(
            rf"(?<![A-Za-z0-9_]){re.escape(a)}(?![A-Za-z0-9_])",
            q
        ))
    return a in q

def route_question(
    question: str,
    catalog: dict,
    forced_program: str | None = None,
    available_programs: list[str] | None = None,
) -> RouteResult:
    if forced_program and forced_program != "AUTO":
        return RouteResult(
            [forced_program],
            reason="ผู้ใช้กำหนดบริบทหลักสูตร"
        )

    order = ["IT_INTER", "AIT", "DSBA", "IT"]
    hits = []

    for code in order:
        if any(
            _alias_hit(question, alias)
            for alias in catalog[code]["aliases"]
        ):
            hits.append(code)

    if "IT_INTER" in hits and "IT" in hits:
        hits.remove("IT")

    comparison_words = [
        "เปรียบเทียบ", "ต่างกัน", "แตกต่าง", "เทียบ", "กับ",
        "มากกว่า", "น้อยกว่า", "หลักสูตรไหน", "which",
        "vs", "versus"
    ]
    comparison = any(
        w.casefold() in question.casefold()
        for w in comparison_words
    )

    if hits:
        return RouteResult(
            programs=hits,
            comparison=(comparison or len(hits) > 1),
            reason="ตรวจพบชื่อหรือ alias ของหลักสูตร"
        )

    available = available_programs or list(catalog.keys())

    if len(available) == 1:
        return RouteResult(
            available,
            reason="มีหลักสูตรเดียวในบริบท"
        )

    if comparison:
        return RouteResult(
            available,
            comparison=True,
            reason="คำถามเปรียบเทียบโดยไม่ระบุชื่อหลักสูตร"
        )

    return RouteResult(
        [],
        ambiguous=True,
        reason="ไม่สามารถระบุหลักสูตรจากคำถามได้"
    )
