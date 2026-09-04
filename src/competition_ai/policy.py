from __future__ import annotations

import re
from dataclasses import dataclass

try:
    from langdetect import detect as _langdetect
except Exception:  # pragma: no cover - deterministic fallback remains available
    _langdetect = None


SUPPORTED_PROGRAMS = ("AIT", "DSBA", "IT", "IT_INTER")

DOMAIN_HINTS = (
    "หลักสูตร", "หน่วยกิต", "รายวิชา", "วิชา", "สาขา", "คณะเทคโนโลยีสารสนเทศ",
    "สจล", "kmitl", "ait", "dsba", "it inter", "bit international",
    "business information technology", "information technology",
    "data science", "artificial intelligence", "เทคโนโลยีสารสนเทศ",
    "วิทยาการข้อมูล", "ปัญญาประดิษฐ์", "อาชีพ", "โครงสร้างหลักสูตร",
    "เปิดสอน", "สหกิจ", "ค่าเทอม", "ค่าธรรมเนียม", "学分", "课程", "专业",
    "信息技术学院", "人工智能技术", "数据科学", "开课", "招生",
)

GREETING_PATTERNS = (
    r"^\s*(สวัสดี|หวัดดี|ดีครับ|ดีค่ะ|hello|hi|hey|你好|您好|哈喽)\b",
    r"^\s*good\s+(morning|afternoon|evening)\b",
)

INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+the\s+instructions",
    r"system\s+prompt", r"developer\s+message",
    r"reveal\s+.*instructions", r"show\s+.*prompt", r"jailbreak",
    r"\bdan\b.*(mode|jailbreak|anything)",
    r"ลืมคำสั่งเดิม", r"ไม่ต้องทำตามคำสั่ง", r"บอก.*คำสั่ง.*ระบบ",
    r"เปิดเผย.*prompt", r"เปิดเผย.*system", r"คำสั่งที่ซ่อน",
    r"(print|show|dump|export|reveal).*(context|knowledge\s*base|database|documents?|evidence)",
    r"(แสดง|พิมพ์|ส่ง|เปิดเผย).*(context|knowledge\s*base|ฐานความรู้|เอกสารทั้งหมด|ข้อมูลทั้งหมด)",
)

UNSAFE_MIXED_PATTERNS = (
    r"brute[\s-]*force", r"password\s*(crack|guess|attack)",
    r"ขโมยรหัส", r"เดารหัสผ่าน", r"เจาะรหัสผ่าน",
)

OTHER_UNIVERSITY_PATTERNS = (
    r"จุฬา", r"chulalongkorn", r"มหิดล", r"mahidol",
    r"ธรรมศาสตร์", r"thammasat", r"เกษตรศาสตร์", r"kasetsart",
    r"เชียงใหม่", r"chiang mai university",
)

GENERAL_OOS_PATTERNS = (
    r"ต้มยำ", r"สูตรอาหาร", r"พยากรณ์อากาศ", r"อากาศ.*กรุงเทพ",
    r"weather", r"ฟุตบอล", r"พรีเมียร์ลีก", r"หวย", r"bitcoin",
    r"หุ้น", r"ลดน้ำหนัก", r"1\s*\+\s*1",
)

NOT_FOUND_PATTERNS = (
    r"(ค่าเทอม|ค่าธรรมเนียมการศึกษา).*(ต่อภาค|ต่อเทอม|ราคาจริง)",
    r"(tuition|semester fee|term fee)", r"(学费|每学期费用)",
)

SUBJECTIVE_EXTERNAL_COMPARE_PATTERNS = (
    r"(ชื่อเสียง|ดังกว่า|ดีกว่า|เหนือกว่า).*(มหิดล|จุฬา|ธรรมศาสตร์|เกษตรศาสตร์)",
    r"(mahidol|chulalongkorn|thammasat|kasetsart).*(better|more famous|reputation)",
)


@dataclass(frozen=True)
class PolicyDecision:
    language: str
    kind: str
    reason: str


def detect_language(text: str) -> str:
    """Return an ISO-like language tag from the actual question text.

    Deterministic script checks protect the competition's Thai/Chinese cases.
    langdetect expands coverage to English, Japanese, Korean, Arabic, Russian,
    Spanish, French and other languages so answer-language policy is not tied
    to the TH/EN UI toggle.
    """
    text = (text or "").strip()
    if not text:
        return "th"

    thai = len(re.findall(r"[\u0E00-\u0E7F]", text))
    han = len(re.findall(r"[\u4E00-\u9FFF]", text))
    kana = len(re.findall(r"[\u3040-\u30FF]", text))
    hangul = len(re.findall(r"[\uAC00-\uD7AF]", text))
    arabic = len(re.findall(r"[\u0600-\u06FF]", text))
    cyrillic = len(re.findall(r"[\u0400-\u04FF]", text))

    if thai >= 2:
        return "th"
    if kana >= 2:
        return "ja"
    if hangul >= 2:
        return "ko"
    if han >= 2:
        return "zh"
    if arabic >= 2:
        return "ar"
    if cyrillic >= 2 and _langdetect is None:
        return "ru"

    if _langdetect is not None and len(text) >= 4:
        try:
            lang = (_langdetect(text) or "en").casefold()
            if lang.startswith("zh"):
                return "zh"
            return lang
        except Exception:
            pass

    return "en" if re.search(r"[A-Za-z]", text) else "th"


def has_domain_hint(text: str) -> bool:
    q = (text or "").casefold()
    return any(h.casefold() in q for h in DOMAIN_HINTS)


def is_greeting(text: str) -> bool:
    return any(re.search(p, text or "", flags=re.I) for p in GREETING_PATTERNS)


def is_prompt_injection(text: str) -> bool:
    return any(re.search(p, text or "", flags=re.I | re.S) for p in INJECTION_PATTERNS)


def has_unsafe_mixed_intent(text: str) -> bool:
    q = text or ""
    return has_domain_hint(q) and any(re.search(p, q, flags=re.I | re.S) for p in UNSAFE_MIXED_PATTERNS)


def mentions_other_university(text: str) -> bool:
    return any(re.search(p, text or "", flags=re.I) for p in OTHER_UNIVERSITY_PATTERNS)


def is_general_out_of_scope(text: str) -> bool:
    q = text or ""
    if any(re.search(p, q, flags=re.I) for p in GENERAL_OOS_PATTERNS):
        return True
    return not has_domain_hint(q)


def is_known_not_found_request(text: str) -> bool:
    return any(re.search(p, text or "", flags=re.I) for p in NOT_FOUND_PATTERNS)


def is_subjective_external_compare(text: str) -> bool:
    q = text or ""
    return has_domain_hint(q) and any(re.search(p, q, flags=re.I) for p in SUBJECTIVE_EXTERNAL_COMPARE_PATTERNS)


_TEXTS = {
    "th": {
        "empty": "กรุณาพิมพ์คำถาม",
        "blocked": "คำขอนี้พยายามเปลี่ยน เปิดเผย หรือดึงข้อมูลภายในของระบบ จึงไม่ดำเนินการต่อ คุณสามารถถามข้อมูลหลักสูตร AIT, DSBA, IT และ IT International ของคณะเทคโนโลยีสารสนเทศ สจล. ได้",
        "partial_blocked": "ช่วยได้เฉพาะส่วนที่เกี่ยวกับหลักสูตร AIT, DSBA, IT และ IT International ส่วนคำขอที่เกี่ยวกับการเจาะหรือเดารหัสผ่านจะไม่ดำเนินการ กรุณาระบุหัวข้อหลักสูตรที่ต้องการ เช่น หน่วยกิต รายวิชา หรืออาชีพ",
        "oos": "คำถามนี้อยู่นอกขอบเขตของ IT KMITL Curriculum Chatbot ระบบนี้ตอบข้อมูลหลักสูตร AIT, DSBA, IT และ IT International ของคณะเทคโนโลยีสารสนเทศ สจล. จากชุดข้อมูลที่ผู้จัดกำหนด",
        "greeting": "สวัสดีครับ พร้อมช่วยตอบข้อมูลหลักสูตรของคณะเทคโนโลยีสารสนเทศ สจล. ได้แก่ AIT, DSBA, IT และ IT International ถามเรื่องหน่วยกิต รายวิชา โครงสร้างหลักสูตร ทักษะ หรืออาชีพได้เลย",
        "not_found": "คำถามนี้เกี่ยวข้องกับคณะเทคโนโลยีสารสนเทศ สจล. แต่ไม่พบหลักฐานที่เพียงพอในชุดข้อมูลที่ผู้จัดกำหนด จึงไม่ควรเดาหรือใช้ข้อมูลภายนอก",
        "external_compare": "จากชุดข้อมูลที่กำหนด ระบบสามารถอธิบายข้อมูลของหลักสูตร IT KMITL ได้ แต่ไม่สามารถตัดสินชื่อเสียงหรือเปรียบเทียบกับมหาวิทยาลัยอื่นได้อย่างน่าเชื่อถือ เพราะไม่มีข้อมูลและเกณฑ์ของอีกมหาวิทยาลัยในชุดข้อมูล",
        "needs_context": "กรุณาระบุหลักสูตรที่ต้องการ เช่น AIT, DSBA, IT หรือ IT International เพื่อป้องกันการตอบข้ามหลักสูตร",
    },
    "en": {
        "empty": "Please enter a question.",
        "blocked": "This request attempts to override, reveal, or extract internal system information, so it has been blocked. You can ask about the AIT, DSBA, IT, and IT International curricula at KMITL School of Information Technology.",
        "partial_blocked": "I can help only with the curriculum-related part of your request. I will not assist with password cracking or brute-force activity. Ask a specific curriculum question such as credits, courses, structure, or careers.",
        "oos": "This question is outside the scope of the IT KMITL Curriculum Chatbot. I can answer questions about AIT, DSBA, IT, and IT International using the organizer-provided curriculum dataset.",
        "greeting": "Hello. I can help with KMITL School of Information Technology curricula: AIT, DSBA, IT, and IT International. You can ask about credits, courses, curriculum structure, skills, or careers.",
        "not_found": "This question is related to KMITL School of Information Technology, but the organizer-provided dataset does not contain enough evidence to answer it reliably. I will not guess or use external facts.",
        "external_compare": "The supplied dataset lets me describe the IT KMITL curriculum, but it does not provide enough evidence or a common metric to judge reputation against another university.",
        "needs_context": "Please specify AIT, DSBA, IT, or IT International so I do not mix evidence across programs.",
    },
    "zh": {
        "empty": "请输入问题。",
        "blocked": "该请求试图覆盖、泄露或提取系统内部信息，因此已被拦截。你可以询问 KMITL 信息技术学院的 AIT、DSBA、IT 和 IT International 课程信息。",
        "partial_blocked": "我只能处理与课程相关的部分，不会协助破解密码或暴力枚举。你可以具体询问学分、课程、课程结构或职业方向。",
        "oos": "这个问题不属于 IT KMITL Curriculum Chatbot 的范围。本系统依据主办方提供的数据回答 KMITL 信息技术学院 AIT、DSBA、IT 和 IT International 课程相关问题。",
        "greeting": "你好！我可以帮助回答 KMITL 信息技术学院 AIT、DSBA、IT 和 IT International 的课程问题，例如学分、课程结构、科目、技能和职业方向。",
        "not_found": "这个问题与 KMITL 信息技术学院有关，但主办方提供的数据中没有足够证据可以可靠回答，因此系统不会猜测或使用外部资料。",
        "external_compare": "现有数据可以说明 IT KMITL 的课程信息，但没有另一所大学的数据和统一评价标准，因此无法可靠判断哪一所大学在 AI 方面更有名。",
        "needs_context": "请明确指定 AIT、DSBA、IT 或 IT International，以避免混用不同课程的证据。",
    },
}


def message(language: str, key: str) -> str:
    return _TEXTS.get(language, _TEXTS["en"])[key]


def classify_pre_route(question: str) -> PolicyDecision | None:
    lang = detect_language(question)
    if not (question or "").strip():
        return PolicyDecision(lang, "EMPTY", "empty input")
    if is_prompt_injection(question):
        return PolicyDecision(lang, "BLOCKED", "prompt injection or knowledge extraction")
    if has_unsafe_mixed_intent(question):
        return PolicyDecision(lang, "PARTIAL_BLOCKED", "curriculum plus unsafe unrelated intent")
    if is_greeting(question) and not has_domain_hint(question):
        return PolicyDecision(lang, "GREETING", "social greeting")
    if is_known_not_found_request(question):
        return PolicyDecision(lang, "NOT_FOUND", "known unsupported dataset field")
    if is_subjective_external_compare(question):
        return PolicyDecision(lang, "PARTIALLY_SUPPORTED", "subjective external comparison")
    if mentions_other_university(question) and not has_domain_hint(question):
        return PolicyDecision(lang, "OUT_OF_SCOPE", "other university")
    if is_general_out_of_scope(question):
        return PolicyDecision(lang, "OUT_OF_SCOPE", "general knowledge outside curriculum scope")
    return None
