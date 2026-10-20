"""The analysis agent: turn source evidence into verifiable facts."""

from __future__ import annotations

import re
from typing import Any

from ..llm.base import ModelAdapter
from ..tools.fs import InputSandbox
from ..trace import Trace
from .base import ToolLoopAgent, load_prompt

ALLOWED_KINDS = {
    "entrypoint",
    "command",
    "dependency",
    "module",
    "feature",
    "data",
    "limitation",
    "configuration",
    "metadata",
    "unknown",
}
FACT_ID = re.compile(r"^F[1-9][0-9]*$")


def make_analyst_validator(sandbox: InputSandbox):
    """Build a validator that rejects facts without usable source evidence."""

    allowed_files = {entry["path"] for entry in sandbox.scan()}

    def validate(final: dict[str, Any]) -> str | None:
        facts = final.get("facts")
        unknowns = final.get("unknowns", [])
        if not isinstance(facts, list) or not facts:
            return '"facts" 必须是非空数组'
        if not isinstance(unknowns, list) or not all(
            isinstance(item, str) for item in unknowns
        ):
            return '"unknowns" 必须是字符串数组'
        if len(facts) > 25:
            return "事实数量超过 25 条，请聚焦主要事实"

        seen_ids: set[str] = set()
        for index, fact in enumerate(facts, start=1):
            if not isinstance(fact, dict):
                return f"第 {index} 条事实必须是 JSON 对象"
            fact_id = fact.get("id")
            if not isinstance(fact_id, str) or not FACT_ID.match(fact_id):
                return f'第 {index} 条事实的 id 必须形如 "F1"'
            if fact_id in seen_ids:
                return f"事实 id 重复: {fact_id}"
            seen_ids.add(fact_id)
            if fact.get("kind") not in ALLOWED_KINDS:
                return f"{fact_id} 的 kind 不在允许列表: {fact.get('kind')!r}"
            statement = fact.get("statement")
            if not isinstance(statement, str) or len(statement.strip()) < 5:
                return f"{fact_id} 的 statement 过短"
            evidence = fact.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                return f"{fact_id} 缺少 evidence"
            for evidence_index, item in enumerate(evidence, start=1):
                if not isinstance(item, dict):
                    return f"{fact_id} 的第 {evidence_index} 条证据必须是对象"
                path = item.get("file")
                lines = item.get("lines")
                if not isinstance(path, str) or path not in allowed_files:
                    return f"{fact_id} 引用了清单之外的文件: {path!r}"
                if (
                    not isinstance(lines, list)
                    or len(lines) != 2
                    or not all(isinstance(value, int) for value in lines)
                ):
                    return f"{fact_id} 的 evidence.lines 必须是 [start, end]"
                error = sandbox.check_lines(path, lines[0], lines[1])
                if error:
                    return f"{fact_id} 证据无效: {error}"
        return None

    return validate


def build_analyst(
    adapter: ModelAdapter,
    sandbox: InputSandbox,
    trace: Trace,
) -> ToolLoopAgent:
    """Create the analyst with its read-only tool surface."""

    tools = {
        "list_files": sandbox.list_files,
        "read_file": sandbox.read_file,
        "search": sandbox.search,
    }
    return ToolLoopAgent(
        name="analyst",
        adapter=adapter,
        system_prompt=load_prompt("analyst.md"),
        tools=tools,
        trace=trace,
        validator=make_analyst_validator(sandbox),
        max_turns=12,
        required_tool="read_file",
    )
