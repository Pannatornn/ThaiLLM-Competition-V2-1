from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

class Telemetry:
    def __init__(self, root: Path):
        self.dir = root / "runtime" / "logs"
        self.dir.mkdir(
            parents=True,
            exist_ok=True
        )

    def log(self, event: dict):
        event = {
            "timestamp":
                datetime.now().isoformat(
                    timespec="seconds"
                ),
            **event
        }

        with (
            self.dir / "events.jsonl"
        ).open(
            "a",
            encoding="utf-8"
        ) as f:
            f.write(
                json.dumps(
                    event,
                    ensure_ascii=False
                ) + "\n"
            )
