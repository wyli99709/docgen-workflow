"""Append-only JSONL execution trace."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Trace:
    """Write one JSON object per line so a run can be inspected after the fact."""

    def __init__(self, path: Path, run_id: str) -> None:
        self.path = Path(path)
        self.run_id = run_id
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8")

    def emit(
        self,
        event: str,
        *,
        node: str | None = None,
        summary: str = "",
        duration_ms: int | None = None,
        **details: Any,
    ) -> None:
        record: dict[str, Any] = {
            "ts": _now(),
            "run_id": self.run_id,
            "event": event,
            "node": node,
            "summary": summary,
        }
        if duration_ms is not None:
            record["duration_ms"] = duration_ms
        if details:
            record["details"] = details
        self._handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._handle.flush()

    def close(self) -> None:
        if not self._handle.closed:
            self._handle.close()

    def __enter__(self) -> "Trace":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
