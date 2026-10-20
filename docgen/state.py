"""Shared state for one documentation workflow run."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

STATUS_RUNNING = "running"
STATUS_PASSED = "passed"
STATUS_NEEDS_REVIEW = "needs_manual_review"
STATUS_FAILED = "failed"


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class RunState:
    """Everything the workflow nodes share.

    Agents never mutate this object directly; each node returns updates by
    assigning fields, and every assignment is visible in ``state.json``.
    """

    run_id: str
    input_dir: str
    output_dir: str
    model: str
    status: str = STATUS_RUNNING
    source_digest: str = ""
    manifest: list[dict[str, Any]] = field(default_factory=list)
    ast_index: dict[str, Any] = field(default_factory=dict)
    facts: list[dict[str, Any]] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    draft: str = ""
    draft_version: int = 0
    review_verdict: str = ""
    review_issues: list[dict[str, Any]] = field(default_factory=list)
    rule_issues: list[dict[str, Any]] = field(default_factory=list)
    revision_feedback: list[dict[str, Any]] = field(default_factory=list)
    revision_count: int = 0
    max_revisions: int = 1
    rounds: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=utc_now)
    finished_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable snapshot."""

        return asdict(self)

    def add_event(
        self,
        event: str,
        node: str | None = None,
        summary: str = "",
        **extra: Any,
    ) -> None:
        """Append one compact event to the state history."""

        record: dict[str, Any] = {
            "ts": utc_now(),
            "event": event,
            "node": node,
            "summary": summary,
        }
        record.update(extra)
        self.events.append(record)

    @property
    def all_issues(self) -> list[dict[str, Any]]:
        """Return reviewer issues followed by deterministic rule issues."""

        return [*self.review_issues, *self.rule_issues]
