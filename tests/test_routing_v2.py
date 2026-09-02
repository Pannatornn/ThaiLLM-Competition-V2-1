from pathlib import Path
from competition_ai.router import (
    load_catalog,
    route_question
)

ROOT = Path(__file__).resolve().parents[1]
CAT = load_catalog(
    ROOT/"knowledge/program_catalog.json"
)

def test_ambiguous_short_question():
    assert route_question(
        "เรียนกี่หน่วยกิต",
        CAT
    ).ambiguous

def test_it_inter_routes_only_inter():
    assert route_question(
        "IT Inter เรียนภาษาอะไร",
        CAT
    ).programs == ["IT_INTER"]

def test_ait_it_comparison():
    r = route_question(
        "เปรียบเทียบ AIT กับ IT",
        CAT
    )
    assert set(r.programs) == {
        "AIT","IT"
    }
