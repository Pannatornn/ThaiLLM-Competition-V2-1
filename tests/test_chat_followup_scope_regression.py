from pathlib import Path

from competition_ai.knowledge import load_catalog
from competition_ai.policy import classify_pre_route
from competition_ai.router import route_question
from render_chat_app import _contextual_retry_question, _program_context_question


ROOT = Path(__file__).resolve().parents[1]
CATALOG = load_catalog(ROOT)


def test_it_2565_specialization_english_is_in_scope():
    q = "What specialization areas are in the IT 2565 curriculum?"
    decision = classify_pre_route(q)
    assert decision is None
    route = route_question(q, CATALOG)
    assert route.programs == ["IT"]


def test_it2565_compact_english_is_in_scope():
    q = "What are the specializations in IT2565?"
    decision = classify_pre_route(q)
    assert decision is None
    route = route_question(q, CATALOG)
    assert route.programs == ["IT"]


def test_thai_check_it_retry_reuses_previous_user_question_only():
    previous = "What specialization areas are in the IT 2565 curriculum?"
    history = [
        {"role": "user", "content": previous},
        {"role": "assistant", "content": "This question is outside the scope."},
    ]
    q = _contextual_retry_question("เช็คดูดิ", history)
    assert q is not None
    assert q.startswith("โปรดตรวจสอบคำถามก่อนหน้านี้อีกครั้ง")
    assert previous in q
    assert "outside the scope" not in q
    assert classify_pre_route(q) is None
    assert route_question(q, CATALOG).programs == ["IT"]


def test_short_followup_gets_program_context_before_policy():
    q = _program_context_question("แล้วเรียนกี่ปี?", "AIT")
    assert classify_pre_route(q) is None
    assert route_question(q, CATALOG).programs == ["AIT"]
