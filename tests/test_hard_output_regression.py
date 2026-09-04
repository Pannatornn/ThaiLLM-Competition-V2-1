from pathlib import Path

from competition_ai.batch_fallback import (
    deterministic_ait_dsba_compare,
    deterministic_structure_ranking,
    nonempty_error_result,
)
from competition_ai.knowledge import load_catalog, load_evidence


ROOT = Path(__file__).resolve().parents[1]
CAT = load_catalog(ROOT)
EVIDENCE = load_evidence(ROOT, CAT)
ALL = ["AIT", "DSBA", "IT", "IT_INTER"]


def test_hard_all_program_credit_ranking_is_deterministic_thai():
    q = "หมวดวิชาเฉพาะของแต่ละหลักสูตรในคณะเทคโนโลยีสารสนเทศ สจล. มีกี่หน่วยกิต เรียงลำดับจากมากไปน้อย"
    r = deterministic_structure_ranking(q, EVIDENCE, ALL)
    assert r is not None
    assert r.status == "SUPPORTED"
    assert "DSBA 96" in r.answer
    assert "IT 93" in r.answer
    assert "AIT 90" in r.answer
    assert "IT_INTER 90" in r.answer or "IT International" in r.answer
    assert len(r.evidence) == 4


def test_hard_all_program_credit_ranking_is_deterministic_chinese():
    q = "这四个专业的专业课程类学分从高到低如何排列?"
    r = deterministic_structure_ranking(q, EVIDENCE, ALL)
    assert r is not None
    assert "DSBA 96 学分" in r.answer
    assert "IT 93 学分" in r.answer
    assert "90 学分" in r.answer


def test_hard_ait_dsba_compare_has_nonempty_grounded_fallback():
    q = "หากสนใจสายงานด้าน AI และ Data โดยเฉพาะ ควรเลือกเรียนหลักสูตรใดระหว่าง AIT กับ DSBA และทั้งสองหลักสูตรต่างกันอย่างไร"
    r = deterministic_ait_dsba_compare(q, EVIDENCE, ["AIT", "DSBA"])
    assert r is not None
    assert r.answer.strip()
    assert r.status == "SUPPORTED"
    assert {e.program for e in r.evidence} == {"AIT", "DSBA"}
    assert "AIT" in r.answer
    assert "DSBA" in r.answer


def test_error_guard_never_returns_blank_answer():
    for q in (
        "ค่าใช้จ่ายทั้งหมดตลอด 4 ปีของหลักสูตร IT2565 รวมหอพักและค่าครองชีพประมาณเท่าไหร่",
        "这四个专业的专业课程类学分从高到低如何排列?",
        "How many credits does AIT require?",
    ):
        r = nonempty_error_result(q, "simulated upstream failure")
        assert r.answer.strip()
        assert r.status == "RETRY_REQUIRED"
