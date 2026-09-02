from __future__ import annotations
import json, hashlib
from pathlib import Path
from .models import Evidence

def load_catalog(root: Path) -> dict:
    return json.loads((root/"knowledge/program_catalog.json").read_text(encoding="utf-8"))

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
            out.append(Evidence(
                id=f"FACT-{code}-{i}",
                source=item["file"],
                page=fact.get("page"),
                text=fact["text"],
                program=code,
                kind="canonical",
                metadata={"topic": fact.get("topic","")}
            ))

    # Preprocessed source pages.
    with (root/"knowledge/pages.jsonl").open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            code = _program_for_file(catalog, row["source"])
            out.append(Evidence(
                id=hashlib.sha1(f'{row["source"]}|{row["page"]}'.encode()).hexdigest()[:12],
                source=row["source"],
                page=row["page"],
                text=row["text"],
                program=code,
                kind="page",
            ))
    return out
