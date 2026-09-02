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
    ],
    "กี่ปี": [
        "ระยะเวลา",
        "ระยะเวลาการศึกษา",
        "หลักสูตรปริญญาตรี",
        "ปริญญาตรี 4 ปี",
        "4 ปี",
        "duration",
    ],
    "เรียนกี่ปี": [
        "ระยะเวลาการศึกษา",
        "หลักสูตรปริญญาตรี",
        "4 ปี",
    ],
    "จบกี่ปี": [
        "ระยะเวลาการศึกษา",
        "หลักสูตรปริญญาตรี",
        "4 ปี",
    ],
    "เปิดสอน": [
        "กำหนดเปิดสอน",
        "สถานภาพของหลักสูตร",
    ],
    "สาย": [
        "กลุ่มวิชา",
        "ความเชี่ยวชาญ",
        "วิชาชีพเฉพาะด้าน",
    ],
    "อาชีพ": [
        "ประกอบอาชีพ",
        "ตำแหน่งงาน",
    ],
    "ภาษา": [
        "ภาษาที่ใช้",
        "จัดการศึกษาเป็นภาษา",
    ],
    "machine learning": [
        "machine learning",
        "การเรียนรู้ของเครื่อง",
    ],
    "deep learning": [
        "deep learning",
        "การเรียนรู้เชิงลึก",
    ],
    "nlp": [
        "natural language processing",
        "การประมวลผลภาษาธรรมชาติ",
    ],
}


def _thai_ngrams(seq: str) -> list[str]:
    out = [seq]

    for n in (3, 4, 5, 6, 7, 8):
        if len(seq) >= n:
            out.extend(
                seq[i:i + n]
                for i in range(len(seq) - n + 1)
            )

    return out


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []

    for part in TOKEN_RE.findall(text):
        part = part.casefold()

        if re.fullmatch(r"[\u0E00-\u0E7F]+", part):
            tokens.extend(_thai_ngrams(part))
        else:
            tokens.append(part)

    return [
        token
        for token in tokens
        if token.strip()
    ]


def expand_query(
    question: str,
    planner_keywords: list[str] | None = None,
) -> str:
    parts = [question]
    q = question.casefold()

    for key, values in EXPANSIONS.items():
        if key.casefold() in q:
            parts.extend(values)

    if planner_keywords:
        parts.extend(
            str(x)
            for x in planner_keywords
            if str(x).strip()
        )

    return " ".join(parts)


def infer_topics(question: str) -> set[str]:
    q = question.casefold()
    topics: set[str] = set()

    if (
        "หน่วยกิต" in q
        or "credit" in q
        or "credits" in q
        or "学分" in q
    ):
        topics |= {"basic", "structure"}

    if any(
        phrase in q
        for phrase in (
            "กี่ปี",
            "เรียนกี่ปี",
            "จบกี่ปี",
            "ใช้เวลากี่ปี",
            "ระยะเวลา",
            "ระยะเวลาการศึกษา",
            "duration",
            "学制",
        )
    ):
        # "basic" is intentional: AIT and IT_INTER keep duration together
        # with other basic facts in program_catalog.json.
        topics |= {"basic", "duration"}

    if (
        "เปิดสอน" in q
        or "เปิดเมื่อ" in q
        or "招生" in q
        or "开课" in q
    ):
        topics.add("opening")

    if (
        "สาย" in q
        or "กลุ่มวิชา" in q
        or "เฉพาะด้าน" in q
        or "track" in q
        or "tracks" in q
    ):
        topics.add("tracks")

    if (
        "อาชีพ" in q
        or "career" in q
        or "งานอะไร" in q
        or "ทำงานอะไร" in q
    ):
        topics.add("career")

    if (
        "ภาษา" in q
        or "language" in q
        or "english" in q
        or "อังกฤษ" in q
    ):
        topics.add("language")

    if "โครงสร้าง" in q:
        topics.add("structure")

    if (
        "รายวิชา" in q
        or "วิชา" in q
        or "course" in q
        or "courses" in q
    ):
        topics.add("courses")

    if (
        "ทักษะ" in q
        or "skill" in q
        or "skills" in q
    ):
        topics.add("skills")

    return topics


def _rank(
    query: str,
    pool: list[Evidence],
) -> list[Evidence]:
    if not pool:
        return []

    qt = Counter(tokenize(query))

    tokenized = [
        tokenize(e.text)
        for e in pool
    ]

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

            idf = math.log(
                (n + 1)
                / (df[term] + 1)
            ) + 1.0

            score += (
                (1 + math.log(tf))
                * idf
                * min(qtf, 2)
            )

        scored.append(
            Evidence(
                **{
                    **e.__dict__,
                    "score": float(score),
                }
            )
        )

    scored.sort(
        key=lambda x: x.score,
        reverse=True,
    )

    return scored


def retrieve(
    question: str,
    evidence: list[Evidence],
    programs: list[str],
    top_k: int = 16,
    planner_keywords: list[str] | None = None,
) -> list[Evidence]:
    """
    Hybrid deterministic retriever.

    1. Restrict evidence to routed program(s).
    2. Infer topic from the user's question.
    3. Protect canonical facts whose topic matches the inferred topic
       by assigning score=10000.
    4. Rank source pages lexically.
    5. Return canonical facts first, then ranked source pages.

    pipeline.py protects high-score canonical evidence from being dropped
    by the LLM reranker.
    """
    pool = [
        e
        for e in evidence
        if (
            not programs
            or e.program in programs
        )
    ]

    if not pool:
        return []

    query = expand_query(
        question,
        planner_keywords=planner_keywords,
    )

    topics = infer_topics(question)

    canonical = [
        e
        for e in pool
        if e.kind == "canonical"
    ]

    pages = [
        e
        for e in pool
        if e.kind != "canonical"
    ]

    matched_facts: list[Evidence] = []

    for e in canonical:
        topic = str(
            e.metadata.get(
                "topic",
                "",
            )
        ).casefold()

        if topics and topic in topics:
            matched_facts.append(
                Evidence(
                    **{
                        **e.__dict__,
                        "score": 10000.0,
                    }
                )
            )

    # Preserve every selected program in comparison queries.
    if len(programs) > 1 and matched_facts:
        matched_facts.sort(
            key=lambda x: (
                programs.index(x.program)
                if x.program in programs
                else 999,
                x.page
                if x.page is not None
                else 999,
            )
        )

    ranked_pages = _rank(
        query,
        pages,
    )

    positive_pages = [
        x
        for x in ranked_pages
        if x.score > 0
    ]

    if positive_pages:
        ranked_pages = positive_pages

    # If no topic-based canonical fact matched, fall back to lexical ranking
    # over canonical facts rather than returning no canonical evidence.
    if not matched_facts:
        ranked_facts = _rank(
            query,
            canonical,
        )

        matched_facts = [
            x
            for x in ranked_facts
            if x.score > 0
        ][:4]

    out: list[Evidence] = []
    seen = set()

    for item in matched_facts + ranked_pages:
        key = (
            item.source,
            item.page,
            item.text,
        )

        if key in seen:
            continue

        seen.add(key)
        out.append(item)

        if len(out) >= top_k:
            break

    return out
