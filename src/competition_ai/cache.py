from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path

class DiskCache:
    def __init__(self, root: Path, ttl: int):
        self.dir = root / "runtime" / "cache"
        self.dir.mkdir(
            parents=True,
            exist_ok=True
        )
        self.ttl = ttl

    def _path(self, key: str) -> Path:
        h = hashlib.sha256(
            key.encode("utf-8")
        ).hexdigest()
        return self.dir / f"{h}.json"

    def get(self, key: str):
        p = self._path(key)

        if not p.exists():
            return None

        try:
            data = json.loads(
                p.read_text(
                    encoding="utf-8"
                )
            )

            if (
                time.time()
                - data["time"]
                > self.ttl
            ):
                p.unlink(missing_ok=True)
                return None

            return data["value"]

        except Exception:
            return None

    def set(self, key: str, value):
        p = self._path(key)
        p.write_text(
            json.dumps(
                {
                    "time": time.time(),
                    "value": value
                },
                ensure_ascii=False
            ),
            encoding="utf-8"
        )
