from pathlib import Path
from competition_ai.router import load_catalog, route_question

ROOT = Path(__file__).resolve().parents[1]
CAT = load_catalog(ROOT/"knowledge/program_catalog.json")

def test_ait_route():
    assert route_question("AIT เรียนกี่หน่วยกิต", CAT).programs == ["AIT"]

def test_it_inter_not_plain_it():
    r = route_question("IT Inter เรียนภาษาอะไร", CAT)
    assert r.programs == ["IT_INTER"]

def test_ambiguous_short_query():
    assert route_question("เรียนกี่หน่วยกิต", CAT).ambiguous is True

def test_compare_two():
    r = route_question("เปรียบเทียบ AIT กับ DSBA", CAT)
    assert set(r.programs) == {"AIT","DSBA"}


def test_compare_ait_it():
    r = route_question("เปรียบเทียบจำนวนหน่วยกิต AIT กับ IT", CAT)
    assert set(r.programs) == {"AIT","IT"}
