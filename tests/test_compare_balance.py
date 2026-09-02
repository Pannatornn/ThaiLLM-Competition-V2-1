from pathlib import Path
from competition_ai.knowledge import load_catalog, load_evidence
from competition_ai.retrieval import retrieve
from competition_ai.pipeline import balance_evidence_by_program

ROOT = Path(__file__).resolve().parents[1]
cat = load_catalog(ROOT)
ev = load_evidence(ROOT, cat)

def test_it_course_evidence_exists():
    hits = retrieve(
        "รายวิชาและทักษะ",
        ev,
        ["IT"],
        8
    )
    text = " ".join(x.text for x in hits)
    assert "SOFTWARE" in text.upper() or "ซอฟต์แวร์" in text

def test_it_inter_course_evidence_exists():
    hits = retrieve(
        "รายวิชาและทักษะ",
        ev,
        ["IT_INTER"],
        8
    )
    text = " ".join(x.text for x in hits)
    assert "BUSINESS" in text.upper() or "ธุรกิจ" in text

def test_balancer_keeps_both_programs():
    hits = retrieve(
        "เปรียบเทียบรายวิชาและทักษะ IT กับ IT Inter",
        ev,
        ["IT","IT_INTER"],
        16
    )
    # Simulate biased reranker by putting IT_INTER first.
    biased = sorted(hits, key=lambda x: x.program == "IT_INTER", reverse=True)
    balanced = balance_evidence_by_program(
        biased,
        ["IT","IT_INTER"],
        6
    )
    programs = [x.program for x in balanced]
    assert "IT" in programs
    assert "IT_INTER" in programs
    assert programs.count("IT") >= 2
    assert programs.count("IT_INTER") >= 2

def test_course_skill_topics_are_top():
    hits = retrieve(
        "รายวิชาและทักษะ",
        ev,
        ["IT","IT_INTER"],
        10
    )
    topics = {x.metadata.get("topic") for x in hits[:6] if x.kind == "canonical"}
    assert "courses" in topics
    assert "skills" in topics
