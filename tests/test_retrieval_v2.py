from pathlib import Path
from competition_ai.knowledge import (
    load_catalog,
    load_evidence
)
from competition_ai.retrieval import retrieve

ROOT = Path(__file__).resolve().parents[1]

cat = load_catalog(ROOT)
ev = load_evidence(ROOT, cat)

def test_no_cross_program_contamination():
    hits = retrieve(
        "AIT เรียนกี่หน่วยกิต",
        ev,
        ["AIT"],
        8
    )
    assert hits
    assert all(
        x.program == "AIT"
        for x in hits
    )

def test_ait_credit_top():
    hits = retrieve(
        "AIT เรียนกี่หน่วยกิต และกี่ปี",
        ev,
        ["AIT"],
        8
    )
    assert "120" in hits[0].text

def test_comparison_representation():
    hits = retrieve(
        "เปรียบเทียบจำนวนหน่วยกิต AIT กับ IT",
        ev,
        ["AIT","IT"],
        8
    )
    programs = {x.program for x in hits[:4]}
    assert "AIT" in programs
    assert "IT" in programs
