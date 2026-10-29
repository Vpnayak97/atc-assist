from __future__ import annotations

import json
import logging
import time
from collections import deque
from pathlib import Path

log = logging.getLogger("atc.audit")


class AuditService:
    """Append-only JSONL log of every controller action."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.recent: deque = deque(maxlen=100)

    def log(self, kind: str, payload: dict, now: float | None = None) -> None:
        rec = {"t": now if now is not None else time.time(), "kind": kind, **payload}
        self.recent.appendleft(rec)
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, default=str) + "\n")
        except OSError:
            log.exception("audit write failed")