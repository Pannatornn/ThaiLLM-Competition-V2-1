from __future__ import annotations

import math
import re
from collections import Counter

from .models import Evidence


TOKEN_RE = re.compile(
    r"[A-Za-z0-9_./%-]+|[\u0E00-\u0E7F]+|[\u4E00-\u9FFF]+"
)


EXPANSIONS = {
    "หน่วยกิต": [
        "จำนวนหน่วยกิต",
        "หน่วยกิตตลอดหลักสูตร",
        "จำนวนหน่วยกิตที่เรียนตลอดหลักสูตร",
        "credits",
        "学分",
    ],
    "กี่ปี": [
        "ระยะเวลา", "ระยะเวลาการศึกษา", "หลักสูตรปริญญาตรี",
        "ปริญญาตรี 4 ปี", "4 ปี", "duration", "学制",
    ],
    "เรียนกี่ปี": ["ระยะเวลาการศึกษา", "หลักสูตรปริญญาตรี", "4 ปี"],
    "จบกี่ปี": ["ระยะเวลาการศึกษา", "หลักสูตรปริญญาตรี", "4 ปี"],
    "เปิดสอน": ["กำหนดเปิดสอน", "สถานภาพของหลักสูตร"],
    "ภาคการศึกษา": [
        "ระบบทวิภาค", "ภาคการศึกษาที่ 1", "ภาคการศึกษาที่ 2",
        "ภาคฤดูร้อน", "semester", "academic calendar", "学期",
    ],
    "学期": [
        "ภาคการศึกษา", "ระบบทวิภาค", "semester", "academic year",
        "第一学期", "第二学期", "暑期",
    ],
    "สาย": ["กลุ่มวิชา", "ความเชี่ยวชาญ", "วิชาชีพเฉพาะด้าน", "track"],
    "专业方向": ["ความเชี่ยวชาญเฉพาะทาง", "กลุ่มวิชา", "track", "tracks"],
    "อาชีพ": ["ประกอบอาชีพ", "ตำแหน่งงาน", "career", "职业"],
    "职业": ["อาชีพ", "ประกอบอาชีพ", "career"],
    "สหกิจ": ["สหกิจศึกษา", "cooperative education", "合作教育", "实习", "6 หน่วยกิต"],
    "合作教育": ["สหกิจศึกษา", "cooperative education", "6 学分"],
    "ภาษา": ["ภาษาที่ใช้", "จัดการศึกษาเป็นภาษา"],
    "machine learning": ["machine learning", "การเรียนรู้ของเครื่อง"],
    "deep learning": ["deep learning", "การเรียนรู้เชิงลึก"],
    "nlp": ["natural language processing", "การประมวลผลภาษาธรรมชาติ"],
}


def _thai_ngrams(seq: str) -> list[str]:
    out = [seq]
    for n in (3, 4, 5, 6, 7, 8):
        if len(seq) >= n:
            out.extend(seq[i:i + n] for i in range(len(seq) - n + 1))
    return out


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for part in TOKEN_RE.findall(text):
        part = part.casefold()
        if re.fullmatch(r"[\u0E00-\u0E7F]+", part):
            tokens.extend(_thai_ngrams(part))
        else:
            tokens.append(part)
    return [token for token in tokens if token.strip()]


def expand_query(question: str, planner_keywords: list[str] | None = None) -> str:
    parts = [question]
    q = question.casefold()
    for key, values in EXPANSIONS.items():
        if key.casefold() in q:
            parts.extend(values)
    if planner_keywords:
        parts.extend(str(x) for x in planner_keywords if str(x).strip())
    return " ".join(parts)


def infer_topics(question: str) -> set[str]:
    q = question.casefold()
    topics: set[str] = set()

    if any(x in q for x in ("หน่วยกิต", "credit", "credits", "学分")):
        topics |= {"basic", "structure"}

    if any(
        phrase in q
        for phrase in (
            "กี่ปี", "เรียนกี่ปี", "จบกี่ปี", "ใช้เวลากี่ปี",
            "ระยะเวลา", "ระยะเวลาการศึกษา", "duration", "学制",
        )
    ):
        topics |= {"basic", "duration"}

    if any(x in q for x in ("เปิดสอน", "เปิดเมื่อ", "招生", "开课")):
        topics.add("opening")

    if any(
        x in q
        for x in (
            "ภาคการศึกษา", "semester", "academic year", "academic calendar",
            "学期", "学年", "第一学期", "第二学期", "暑期",
        )
    ):
        topics.add("academic_calendar")

    if any(
        x in q
        for x in (
            "สาย", "กลุ่มวิชา", "เฉพาะด้าน", "ความเชี่ยวชาญ",
            "track", "tracks", "专业方向", "专业方向有哪", "方向",
        )
    ):
        topics.add("tracks")

    if any(x in q for x in ("อาชีพ", "career", "งานอะไร", "ทำงานอะไร", "职业", "从事哪些职业")):
        topics.add("career")

    if any(x in q for x in ("สหกิจ", "cooperative education", "合作教育", "实习")):
        topics.add("coop")

    if any(x in q for x in ("ภาษา", "language", "english", "อังกฤษ")):
        topics.add("language")

    if "โครงสร้าง" in q or "专业课程类" in q:
        topics.add("structure")

    if any(x in q for x in ("รายวิชา", "วิชา", "course", "courses", "课程")):
        topics.add("courses")

    if any(x in q for x in ("ทักษะ", "skill", "skills", "技能")):
        topics.add("skills")

    return topics


def _rank(query: str, pool: list[Evidence]) -> list[Evidence]:
    if not pool:
        return []

    qt = Counter(tokenize(query))
    tokenized = [tokenize(e.text) for e in pool]
    df = Counter()
    for toks in tokenized:
        df.update(set(toks))

    n = max(1, len(pool))
    scored: list[Evidence] = []
    for e, toks in zip(pool, tokenized):
        counts = Counter(toks)
        score = 0.0
        for term, qtf in qt.items():
            tf = counts.get(term, 0)
            if not tf:
                continue
            idf = math.log((n + 1) / (df[term] + 1)) + 1.0
            score += (1 + math.log(tf)) * idf * min(qtf, 2)
        scored.append(Evidence(**{**e.__dict__, "score": float(score)}))

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored


def retrieve(
    question: str,
    evidence: list[Evidence],
    programs: list[str],
    top_k: int = 16,
    planner_keywords: list[str] | None = None,
) -> list[Evidence]:
    """Hybrid deterministic retriever with protected canonical facts."""
    pool = [e for e in evidence if (not programs or e.program in programs)]
    if not pool:
        return []

    query = expand_query(question, planner_keywords=planner_keywords)
    topics = infer_topics(question)
    canonical = [e for e in pool if e.kind == "canonical"]
    pages = [e for e in pool if e.kind != "canonical"]

    matched_facts: list[Evidence] = []
    for e in canonical:
        topic = str(e.metadata.get("topic", "")).casefold()
        if topics and topic in topics:
            matched_facts.append(Evidence(**{**e.__dict__, "score": 10000.0}))

    if len(programs) > 1 and matched_facts:
        matched_facts.sort(
            key=lambda x: (
                programs.index(x.program) if x.program in programs else 999,
                x.page if x.page is not None else 999,
            )
        )

    ranked_pages = _rank(query, pages)
    positive_pages = [x for x in ranked_pages if x.score > 0]
    if positive_pages:
        ranked_pages = positive_pages

    if not matched_facts:
        ranked_facts = _rank(query, canonical)
        matched_facts = [x for x in ranked_facts if x.score > 0][:4]

    out: list[Evidence] = []
    seen = set()
    for item in matched_facts + ranked_pages:
        key = (item.source, item.page, item.text)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= top_k:
            break

    return out
