from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import Evidence


def load_catalog(root: Path) -> dict:
    catalog = json.loads(
        (root / "knowledge/program_catalog.json").read_text(encoding="utf-8")
    )

    # Supplemental canonical facts are kept in a small reviewable file rather
    # than hard-coding individual benchmark answers in the router/pipeline.
    extra_path = root / "knowledge/hard_facts.json"
    if extra_path.exists():
        extra = json.loads(extra_path.read_text(encoding="utf-8"))
        for code, facts in extra.items():
            if code not in catalog:
                continue
            existing = {
                (str(f.get("topic", "")), str(f.get("text", "")))
                for f in catalog[code].get("facts", [])
            }
            for fact in facts:
                key = (str(fact.get("topic", "")), str(fact.get("text", "")))
                if key not in existing:
                    catalog[code].setdefault("facts", []).append(fact)
                    existing.add(key)

    return catalog


def _program_for_file(catalog: dict, filename: str) -> str:
    for code, item in catalog.items():
        if item["file"] == filename:
            return code
    return "UNKNOWN"


def load_evidence(root: Path, catalog: dict) -> list[Evidence]:
    out: list[Evidence] = []

    # Canonical clean evidence first.
    for code, item in catalog.items():
        for i, fact in enumerate(item["facts"]):
            out.append(
                Evidence(
                    id=f"FACT-{code}-{i}",
                    source=item["file"],
                    page=fact.get("page"),
                    text=fact["text"],
                    program=code,
                    kind="canonical",
                    metadata={"topic": fact.get("topic", "")},
                )
            )

    # Preprocessed source pages.
    with (root / "knowledge/pages.jsonl").open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            code = _program_for_file(catalog, row["source"])
            out.append(
                Evidence(
                    id=hashlib.sha1(
                        f'{row["source"]}|{row["page"]}'.encode()
                    ).hexdigest()[:12],
                    source=row["source"],
                    page=row["page"],
                    text=row["text"],
                    program=code,
                    kind="page",
                )
            )
    return out
