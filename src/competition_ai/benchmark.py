from __future__ import annotations
import json
from pathlib import Path

def load_benchmark(root: Path):
    return json.loads(
        (
            root
            / "knowledge/benchmark_gold.json"
        ).read_text(
            encoding="utf-8"
        )
    )

def score_answer(
    qid: int,
    result,
    spec: dict
):
    kind = spec["kind"]

    if kind == "blocked":
        ok = (
            result.status
            == "BLOCKED"
        )
        return (
            ok,
            "block injection"
        )

    if kind == "out_of_scope":
        ok = (
            result.status
            == "OUT_OF_SCOPE"
        )
        return (
            ok,
            "refuse out-of-scope"
        )

    answer = result.answer.casefold()

    missing = [
        x
        for x in spec.get(
            "must_contain",
            []
        )
        if x.casefold()
        not in answer
    ]

    bad_status = {
        "BLOCKED",
        "OUT_OF_SCOPE",
        "NO_EVIDENCE",
        "API_ERROR",
        "UNSUPPORTED",
    }

    ok = (
        not missing
        and result.status
        not in bad_status
    )

    return (
        ok,
        "ผ่าน"
        if ok
        else f"ขาด: {missing}"
    )
