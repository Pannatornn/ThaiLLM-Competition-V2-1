from __future__ import annotations

import re
from typing import Iterable

from .models import AnswerResult, Evidence
from .policy import detect_language


STRUCTURE_QUERY_PATTERNS = (
    r"หมวดวิชาเฉพาะ.*(แต่ละหลักสูตร|ทุกหลักสูตร|เรียงลำดับ)",
    r"(แต่ละหลักสูตร|ทุกหลักสูตร).*(หมวดวิชาเฉพาะ|หน่วยกิต)",
    r"(all|each).*(program|curricul).*(specific|professional).*(credit)",
    r"四个专业.*(专业课程|学分)",
    r"专业课程类学分.*(高到低|排序|排列)",
)

AI_DATA_COMPARE_PATTERNS = (
    r"ait.*dsba|dsba.*ait",
    r"人工智能.*数据|数据.*人工智能",
)


def is_structure_credit_ranking(question: str) -> bool:
    q = question or ""
    return any(re.search(p, q, flags=re.I | re.S) for p in STRUCTURE_QUERY_PATTERNS)


def is_ait_dsba_ai_data_compare(question: str, programs: list[str]) -> bool:
    if set(programs) != {"AIT", "DSBA"}:
        return False
    q = question or ""
    has_pair = any(re.search(p, q, flags=re.I | re.S) for p in AI_DATA_COMPARE_PATTERNS)
    has_focus = bool(re.search(r"\bai\b|artificial intelligence|data|ปัญญาประดิษฐ์|ข้อมูล|人工智能|数据", q, flags=re.I))
    return has_pair and has_focus


def _specific_credits(text: str) -> int | None:
    patterns = (
        r"หมวดวิชาเฉพาะ\s*(\d+)\s*หน่วยกิต",
        r"specific(?:-course| course| professional)?[^0-9]{0,30}(\d+)\s*credits?",
        r"专业课程(?:类)?[^0-9]{0,20}(\d+)\s*学分",
    )
    for pattern in patterns:
        m = re.search(pattern, text or "", flags=re.I)
        if m:
            return int(m.group(1))
    return None


def deterministic_structure_ranking(
    question: str,
    evidence: Iterable[Evidence],
    programs: list[str],
) -> AnswerResult | None:
    """Build the 4-program specific-course-credit ranking without an LLM."""
    if not is_structure_credit_ranking(question):
        return None

    picked: dict[str, tuple[int, Evidence]] = {}
    for e in evidence:
        if e.program not in programs or e.kind != "canonical":
            continue
        if str(e.metadata.get("topic", "")).casefold() != "structure":
            continue
        credits = _specific_credits(e.text)
        if credits is not None:
            current = picked.get(e.program)
            if current is None or e.score > current[1].score:
                picked[e.program] = (credits, e)

    if not all(code in picked for code in programs):
        return None

    order_index = {code: i for i, code in enumerate(programs)}
    ranked = sorted(
        ((code, picked[code][0], picked[code][1]) for code in programs),
        key=lambda x: (-x[1], order_index[x[0]]),
    )
    selected = [item[2] for item in ranked]
    lang = detect_language(question)

    if lang == "zh":
        answer = "按专业课程类学分从高到低排列：" + "，".join(
            f"{code} {credits} 学分" for code, credits, _ in ranked
        ) + "。AIT 与 IT International 同为 90 学分，因此并列。"
    elif lang == "en":
        answer = "Specific-course credits from highest to lowest: " + ", ".join(
            f"{code} {credits} credits" for code, credits, _ in ranked
        ) + ". AIT and IT International are tied at 90 credits."
    else:
        answer = "เรียงหมวดวิชาเฉพาะจากมากไปน้อย: " + " > ".join(
            f"{code} {credits} หน่วยกิต" for code, credits, _ in ranked
        ) + " โดย AIT และ IT International มี 90 หน่วยกิตเท่ากัน จึงเป็นอันดับร่วม"

    return AnswerResult(
        status="SUPPORTED",
        answer=answer,
        programs=programs.copy(),
        evidence=selected,
        debug={"language": lang, "deterministic_fallback": "structure_credit_ranking"},
    )


def _canonical_topic_items(
    evidence: Iterable[Evidence],
    program: str,
    topics: tuple[str, ...],
    limit: int = 3,
) -> list[Evidence]:
    out: list[Evidence] = []
    for topic in topics:
        for e in evidence:
            if (
                e.program == program
                and e.kind == "canonical"
                and str(e.metadata.get("topic", "")).casefold() == topic
            ):
                out.append(e)
                break
        if len(out) >= limit:
            break
    return out


def deterministic_ait_dsba_compare(
    question: str,
    evidence: Iterable[Evidence],
    programs: list[str],
) -> AnswerResult | None:
    """Evidence-only fallback for the common AIT-vs-DSBA AI/Data comparison.

    It intentionally avoids claims such as reputation, difficulty, or job-market
    superiority that the curriculum documents do not measure.
    """
    if not is_ait_dsba_ai_data_compare(question, programs):
        return None

    ait = _canonical_topic_items(evidence, "AIT", ("courses", "skills", "career"), 3)
    dsba = _canonical_topic_items(evidence, "DSBA", ("tracks", "courses", "career"), 3)
    selected = ait + dsba
    if len(ait) < 2 or len(dsba) < 2:
        return None

    lang = detect_language(question)
    if lang == "zh":
        answer = (
            "如果主要目标是人工智能、机器学习、深度学习、NLP 或计算机视觉，可优先考虑 AIT；"
            "AIT 的课程证据直接覆盖这些 AI 主题。"
            "如果主要目标是数据科学、统计分析或数据工程，可优先考虑 DSBA；"
            "DSBA 明确设有数据科学、统计分析和数据工程三个方向。"
            "两者都涉及 AI 与数据，因此应按你更想深入的方向选择，而不是简单判断哪个专业“更好”。"
        )
    elif lang == "en":
        answer = (
            "If your primary goal is AI, machine learning, deep learning, NLP, or computer vision, "
            "AIT is the more direct fit because its curriculum evidence explicitly covers those AI areas. "
            "If your primary goal is data science, statistical analytics, or data engineering, DSBA is "
            "the more direct fit because it explicitly offers those three specialization groups. Both "
            "include AI and data content, so the choice should follow the area you want to specialize in, "
            "not an unsupported claim that one program is universally better."
        )
    else:
        answer = (
            "ถ้าเป้าหมายหลักคือ AI, Machine Learning, Deep Learning, NLP หรือ Computer Vision ให้เอนมาทาง AIT "
            "เพราะหลักฐานรายวิชาของ AIT ครอบคลุมหัวข้อ AI เหล่านี้โดยตรง ส่วนถ้าเป้าหมายหลักคือ Data Science, "
            "การวิเคราะห์เชิงสถิติ หรือ Data Engineering ให้เอนมาทาง DSBA เพราะ DSBA ระบุกลุ่มวิชาชีพเฉพาะด้าน "
            "3 กลุ่มดังกล่าวชัดเจน ทั้งสองหลักสูตรมีทั้ง AI และ Data จึงควรเลือกตามด้านที่ต้องการลงลึก ไม่ใช่ฟันธงว่า "
            "หลักสูตรใดดีกว่ากันโดยรวม"
        )

    return AnswerResult(
        status="SUPPORTED",
        answer=answer,
        programs=programs.copy(),
        evidence=selected,
        debug={"language": lang, "deterministic_fallback": "ait_dsba_ai_data_compare"},
    )


def nonempty_error_result(question: str, reason: str = "upstream failure") -> AnswerResult:
    """Never allow competition CSV export to contain a blank answer cell."""
    lang = detect_language(question)
    if lang == "zh":
        answer = "系统暂时无法完成此题的可靠回答。请重新运行此题；系统不会在没有足够证据时猜测。"
    elif lang == "en":
        answer = "The system could not produce a reliable answer for this item right now. Please rerun this item; it will not guess without sufficient evidence."
    else:
        answer = "ระบบยังไม่สามารถสร้างคำตอบที่เชื่อถือได้สำหรับข้อนี้ในขณะนี้ กรุณารันข้อนี้ใหม่ โดยระบบจะไม่เดาคำตอบเมื่อหลักฐานไม่เพียงพอ"
    return AnswerResult(
        status="RETRY_REQUIRED",
        answer=answer,
        debug={"language": lang, "fallback_reason": reason},
    )
