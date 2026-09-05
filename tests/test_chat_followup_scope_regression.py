from competition_ai.policy import classify_pre_route
from competition_ai.router import route_question
from competition_ai.knowledge import load_catalog
from pathlib import Path

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
