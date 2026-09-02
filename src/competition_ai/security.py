from __future__ import annotations
import re

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+the\s+instructions",
    r"system\s+prompt",
    r"developer\s+message",
    r"reveal\s+.*instructions",
    r"show\s+.*prompt",
    r"jailbreak",
    r"ลืมคำสั่งเดิม",
    r"ไม่ต้องทำตามคำสั่ง",
    r"บอก.*คำสั่ง.*ระบบ",
    r"เปิดเผย.*prompt",
    r"เปิดเผย.*system",
    r"คำสั่งที่ซ่อน",
]

OUT_OF_SCOPE_PATTERNS = [
    r"ต้มยำ", r"สูตรอาหาร", r"พยากรณ์อากาศ", r"อากาศวันนี้",
    r"ฟุตบอล", r"พรีเมียร์ลีก", r"หวย", r"bitcoin", r"หุ้นวันนี้",
    r"จุฬา", r"มหิดล", r"ธรรมศาสตร์", r"เกษตรศาสตร์",
]

DOMAIN_HINTS = [
    "หลักสูตร", "หน่วยกิต", "วิชา", "เรียน", "สาขา", "คณะ",
    "สจล", "kmitl", "ait", "dsba", "it", "it inter", "bit",
    "business information", "data science", "artificial intelligence",
    "เทคโนโลยีสารสนเทศ", "วิทยาการข้อมูล", "ปัญญาประดิษฐ์",
    "อาชีพ", "กลุ่มวิชา", "โครงสร้างหลักสูตร", "เปิดสอน"
]

def is_prompt_injection(question: str) -> bool:
    q = question.lower()
    return any(re.search(p, q, flags=re.I) for p in INJECTION_PATTERNS)

def looks_out_of_scope(question: str) -> bool:
    q = question.lower()
    if any(re.search(p, q, flags=re.I) for p in OUT_OF_SCOPE_PATTERNS):
        return True
    return not any(h.lower() in q for h in DOMAIN_HINTS)
