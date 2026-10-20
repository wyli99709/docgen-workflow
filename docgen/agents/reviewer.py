"""The review agent: independently verify a draft against source evidence."""

from __future__ import annotations

from typing import Any

from ..llm.base import ModelAdapter
from ..tools.fs import InputSandbox
from ..trace import Trace
from .base import ToolLoopAgent, load_prompt

ISSUE_FIELDS = ("severity", "claim", "problem", "evidence", "suggestion")


def validate_review(final: dict[str, Any]) -> str | None:
    """Ensure a review verdict is internally consistent and actionable."""

    verdict = final.get("verdict")
    issues = final.get("issues")
    if verdict not in {"pass", "revise"}:
        return 'verdict 必须是 "pass" 或 "revise"'
    if not isinstance(issues, list):
        return '"issues" 必须是数组'
    if verdict == "pass" and issues:
        return 'verdict 为 "pass" 时 issues 必须为空'
    if verdict == "revise" and not issues:
        return 'verdict 为 "revise" 时必须列出具体问题'
    for index, issue in enumerate(issues, start=1):
        if not isinstance(issue, dict):
            return f"第 {index} 条问题是对象"
        missing = [field for field in ISSUE_FIELDS if not issue.get(field)]
        if missing:
            return f"第 {index} 条问题缺少字段: {', '.join(missing)}"
        if issue.get("severity") not in {"high", "medium", "low"}:
            return f"第 {index} 条问题的 severity 无效"
    return None


def build_reviewer(
    adapter: ModelAdapter,
    sandbox: InputSandbox,
    trace: Trace,
) -> ToolLoopAgent:
    """Create the reviewer with the same read-only tools as the analyst."""

    tools = {
        "list_files": sandbox.list_files,
        "read_file": sandbox.read_file,
        "search": sandbox.search,
    }
    return ToolLoopAgent(
        name="reviewer",
        adapter=adapter,
        system_prompt=load_prompt("reviewer.md"),
        tools=tools,
        trace=trace,
        validator=validate_review,
        max_turns=12,
        required_tool="read_file",
    )
