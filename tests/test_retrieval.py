from pathlib import Path
from competition_ai.knowledge import load_catalog, load_evidence
from competition_ai.retrieval import retrieve

ROOT = Path(__file__).resolve().parents[1]
cat = load_catalog(ROOT)
ev = load_evidence(ROOT, cat)

def test_ait_credit_evidence():
    hits = retrieve("AIT เรียนกี่หน่วยกิต", ev, ["AIT"], 5)
    text = " ".join(x.text for x in hits)
    assert "120" in text

def test_dsba_tracks():
    hits = retrieve("DSBA มีสายอะไรบ้าง", ev, ["DSBA"], 6)
    text = " ".join(x.text for x in hits)
    assert "วิทยาการข้อมูล" in text


def test_ait_credit_is_top_clean_evidence():
    hits = retrieve("AIT เรียนกี่หน่วยกิต และกี่ปี", ev, ["AIT"], 5)
    assert hits[0].kind == "canonical"
    assert "120" in hits[0].text

def test_dsba_tracks_is_top_clean_evidence():
    hits = retrieve("DSBA มีสายอะไรบ้าง", ev, ["DSBA"], 5)
    assert hits[0].metadata.get("topic") == "tracks"
