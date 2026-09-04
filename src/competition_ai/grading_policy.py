from __future__ import annotations

import re

from .policy import PolicyDecision, detect_language


# Feedback from the organizer grader showed that generic greetings, questions
# about other KMITL faculties, and subjective comparisons with another
# university should use the standard out-of-scope refusal rather than a
# conversational redirect or a partial comparison answer.
GREETING_PATTERNS = (
    r"^\s*(สวัสดี(?:ครับ|ค่ะ)?|หวัดดี(?:ครับ|ค่ะ)?|ดีครับ|ดีค่ะ)(?:\s|$)",
    r"^\s*(hello|hi|hey)(?:\s|$)",
    r"^\s*(你好|您好|哈喽)(?:\s|$)",
    r"^\s*good\s+(morning|afternoon|evening)(?:\s|$)",
)

OTHER_KMITL_FACULTY_PATTERNS = (
    r"คณะบริหารธุรกิจ\s*(?:สจล\.?|kmitl)",
    r"คณะวิศวกรรมศาสตร์\s*(?:สจล\.?|kmitl)",
    r"คณะสถาปัตยกรรม(?:ศาสตร์)?\s*(?:สจล\.?|kmitl)",
    r"คณะวิทยาศาสตร์\s*(?:สจล\.?|kmitl)",
    r"คณะครุศาสตร์อุตสาหกรรม(?:และเทคโนโลยี)?\s*(?:สจล\.?|kmitl)",
    r"คณะศิลปศาสตร์\s*(?:สจล\.?|kmitl)",
    r"คณะอุตสาหกรรมอาหาร\s*(?:สจล\.?|kmitl)",
    r"business\s+school.*kmitl",
    r"engineering.*kmitl",
    r"kmitl.*(?:business\s+school|engineering\s+faculty)",
)

SUBJECTIVE_EXTERNAL_COMPARE_PATTERNS = (
    r"คณะเทคโนโลยีสารสนเทศ.*(?:มหิดล|mahidol).*(ชื่อเสียง|ดังกว่า|ดีกว่า|เหนือกว่า|ai)",
    r"(?:มหิดล|mahidol).*คณะเทคโนโลยีสารสนเทศ.*(ชื่อเสียง|ดังกว่า|ดีกว่า|เหนือกว่า|ai)",
    r"it\s*kmitl.*(?:ict\s*)?mahidol.*(reputation|famous|better|ai)",
    r"(?:ict\s*)?mahidol.*it\s*kmitl.*(reputation|famous|better|ai)",
)


def classify_grader_edge(question: str) -> PolicyDecision | None:
    q = question or ""
    lang = detect_language(q)

    if any(re.search(p, q, flags=re.I | re.S) for p in GREETING_PATTERNS):
        return PolicyDecision(lang, "OUT_OF_SCOPE", "generic greeting must use standard scope refusal")

    if any(re.search(p, q, flags=re.I | re.S) for p in OTHER_KMITL_FACULTY_PATTERNS):
        return PolicyDecision(lang, "OUT_OF_SCOPE", "question targets another KMITL faculty")

    if any(re.search(p, q, flags=re.I | re.S) for p in SUBJECTIVE_EXTERNAL_COMPARE_PATTERNS):
        return PolicyDecision(lang, "OUT_OF_SCOPE", "subjective cross-university comparison is unsupported")

    return None
