from __future__ import annotations

import base64
import re

from .policy import PolicyDecision, detect_language


ALL_PROGRAM_PATTERNS = (
    r"แต่ละหลักสูตร",
    r"ทุกหลักสูตร",
    r"ทั้ง\s*4\s*หลักสูตร",
    r"ทั้งสี่หลักสูตร",
    r"4\s*หลักสูตร.*คณะ.*IT",
    r"all\s+(four|4)\s+(programs|curricula)",
    r"each\s+(program|curriculum)",
    r"四个专业",
    r"四个课程",
    r"全部四个专业",
)

HARD_OOS_PATTERNS = (
    # Curriculum documents list Calculus 1, but a request for a full-semester
    # tutoring summary is outside the curriculum-information scope.
    r"แคลคูลัส\s*1.*(ทั้งเทอม|แบบละเอียด)",
    r"สรุป.*แคลคูลัส\s*1.*(ทั้งเทอม|แบบละเอียด)",
    r"calculus\s*1.*(full semester|in detail|detailed notes)",
)

HARD_NOT_FOUND_PATTERNS = (
    r"ผลงานตีพิมพ์.*(ล่าสุด|ปีนี้)",
    r"อาจารย์.*ผลงานตีพิมพ์.*(ล่าสุด|ปีนี้)",
    r"(latest|this year).*(publication|paper).*(faculty|lecturer|professor)",
    r"(publication|paper).*(latest|this year)",
    r"ค่าใช้จ่ายทั้งหมดตลอด.*(4\s*ปี|สี่ปี).*(หอพัก|ค่าครองชีพ)",
    r"(หอพัก|ค่าครองชีพ).*(ค่าใช้จ่ายทั้งหมด|ตลอด\s*4\s*ปี)",
    r"(total|overall).*(4\s*years|four\s*years).*(housing|dorm|living cost)",
)

HARD_INJECTION_PATTERNS = (
    r"ข้อความซ่อน.*(เปิดเผย|ข้อมูลทั้งหมด|ทำตาม)",
    r"ระบบ\s*:.*(เปิดเผย|ข้อมูลทั้งหมด|คลังความรู้)",
    r"(ลืม|เพิกเฉย).*(กฎ|ข้อจำกัด).*(ความปลอดภัย|ระบบ)",
    r"(forget|ignore).*(safety|security).*(rules|policy)",
    r"(รวม|คัดลอก|แสดง|พิมพ์).*(เนื้อหาทั้งหมด|ข้อมูลทั้งหมด).*(pdf|เอกสาร|คลังความรู้)",
)

BASE64_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{24,}={0,2}(?![A-Za-z0-9+/])")
DECODED_INJECTION_PATTERNS = (
    r"system\s+prompt",
    r"developer\s+message",
    r"ignore\s+all\s+(rules|instructions)",
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"reveal\s+.*(prompt|instructions|context|knowledge)",
    r"dump\s+.*(context|knowledge|documents)",
)


def is_all_program_question(question: str) -> bool:
    q = question or ""
    return any(re.search(p, q, flags=re.I) for p in ALL_PROGRAM_PATTERNS)


def _decoded_base64_payloads(question: str) -> list[str]:
    decoded: list[str] = []
    for token in BASE64_TOKEN_RE.findall(question or ""):
        try:
            padded = token + "=" * ((4 - len(token) % 4) % 4)
            raw = base64.b64decode(padded, validate=True)
            text = raw.decode("utf-8")
        except Exception:
            continue
        if text and sum(ch.isprintable() for ch in text) / max(1, len(text)) >= 0.9:
            decoded.append(text)
    return decoded


def contains_encoded_injection(question: str) -> bool:
    for payload in _decoded_base64_payloads(question):
        if any(re.search(p, payload, flags=re.I | re.S) for p in DECODED_INJECTION_PATTERNS):
            return True
    return False


def classify_hard_edge(question: str) -> PolicyDecision | None:
    lang = detect_language(question)
    q = question or ""

    if contains_encoded_injection(q):
        return PolicyDecision(lang, "BLOCKED", "encoded prompt injection")
    if any(re.search(p, q, flags=re.I | re.S) for p in HARD_INJECTION_PATTERNS):
        return PolicyDecision(lang, "BLOCKED", "document/context extraction or instruction override")
    if any(re.search(p, q, flags=re.I | re.S) for p in HARD_NOT_FOUND_PATTERNS):
        return PolicyDecision(lang, "NOT_FOUND", "requested current/financial detail is not in organizer dataset")
    if any(re.search(p, q, flags=re.I | re.S) for p in HARD_OOS_PATTERNS):
        return PolicyDecision(lang, "OUT_OF_SCOPE", "request is tutoring/general content rather than curriculum information")
    return None
