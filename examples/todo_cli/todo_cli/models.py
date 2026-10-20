"""Data model for todo tasks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Task:
    """A single todo item."""

    id: int
    title: str
    done: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""

        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """Build a task from a decoded JSON object."""

        return cls(
            id=int(data["id"]),
            title=str(data["title"]),
            done=bool(data.get("done", False)),
        )
