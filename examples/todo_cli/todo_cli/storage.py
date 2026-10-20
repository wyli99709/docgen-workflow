"""JSON-file persistence for tasks."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Task


class TaskStore:
    """Load and save tasks in a single JSON file."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def load(self) -> list[Task]:
        """Read tasks from disk; a missing file means an empty list."""

        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        return [Task.from_dict(item) for item in raw]

    def save(self, tasks: list[Task]) -> None:
        """Write all tasks to disk, creating parent directories if needed."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(
                [task.to_dict() for task in tasks],
                handle,
                ensure_ascii=False,
                indent=2,
            )
