from __future__ import annotations
import requests
from .config import Settings

def api_health(settings: Settings) -> tuple[bool, str]:
    if not settings.api_key:
        return False, "ยังไม่ได้ตั้ง API key"

    try:
        r = requests.get(
            "http://thaillm.or.th/api/v1/models",
            headers={
                "Authorization":
                    "Bearer "
                    + settings.api_key
            },
            timeout=15
        )

        if r.status_code == 200:
            return True, "ThaiLLM API พร้อม"

        return (
            False,
            f"HTTP {r.status_code}"
        )

    except Exception as exc:
        return False, str(exc)
