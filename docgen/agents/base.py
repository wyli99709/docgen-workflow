"""Shared agent machinery: tool loops, JSON protocol and tracing."""

from __future__ import annotations

import inspect
import json
import time
from pathlib import Path
from typing import Any, Callable

from ..llm.base import LLMError, ModelAdapter
from ..trace import Trace
from ..utils.jsonx import extract_json_object, truncate

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROMPT_DIR = PROJECT_ROOT / "prompts"

Validator = Callable[[dict[str, Any]], str | None]
Tool = Callable[..., Any]


class AgentError(RuntimeError):
    """An agent could not produce a valid final result."""


def load_prompt(name: str) -> str:
    """Read one prompt file from ``prompts/``."""

    path = PROMPT_DIR / name
    if not path.exists():
        raise AgentError(f"提示词文件不存在: {path}")
    return path.read_text(encoding="utf-8")


class ToolLoopAgent:
    """A model-driven loop that may call read-only tools before answering."""

    def __init__(
        self,
        *,
        name: str,
        adapter: ModelAdapter,
        system_prompt: str,
        tools: dict[str, Tool],
        trace: Trace,
        validator: Validator | None = None,
        max_turns: int = 8,
        required_tool: str | None = None,
    ) -> None:
        self.name = name
        self.adapter = adapter
        self.system_prompt = system_prompt
        self.tools = tools
        self.trace = trace
        self.validator = validator
        self.max_turns = max_turns
        self.required_tool = required_tool

    def _protocol(self) -> str:
        tool_lines = []
        for tool_name, tool in self.tools.items():
            try:
                signature = str(inspect.signature(tool))
            except (TypeError, ValueError):
                signature = "(...)"
            doc = (tool.__doc__ or "").strip().splitlines()
            tool_lines.append(
                f"- {tool_name}{signature}: {doc[0] if doc else '无说明'}"
            )
        return (
            "\n\n## 回复协议\n"
            "每次回复必须是**单个 JSON 对象**，不要输出 Markdown 代码块以外的解释。\n"
            '调用工具：{"thought": "为什么调用", "tool": "工具名", "args": {...}}\n'
            '给出最终结果：{"thought": "简要结论", "final": {...}}\n'
            "可用工具：\n"
            + "\n".join(tool_lines)
            + "\n只能读取输入目录内的文件，不要尝试修改或执行目标代码。"
        )

    def run(self, task: dict[str, Any]) -> dict[str, Any]:
        """Run the tool loop until the model returns a validated final object."""

        messages = [
            {"role": "system", "content": self.system_prompt + self._protocol()},
            {
                "role": "user",
                "content": "任务输入：\n"
                + json.dumps(task, ensure_ascii=False, indent=2),
            },
        ]
        parse_failures = 0
        validation_failures = 0
        llm_failures = 0
        successful_tool_calls: dict[str, int] = {}

        for turn in range(1, self.max_turns + 1):
            started = time.monotonic()
            try:
                raw = self.adapter.complete(
                    messages, agent=self.name, json_mode=True
                )
            except LLMError as exc:
                llm_failures += 1
                self.trace.emit(
                    "llm_error",
                    node=self.name,
                    summary=truncate(str(exc), 500),
                )
                if llm_failures > 3:
                    raise AgentError(
                        f"{self.name} 多次模型调用失败: {exc}"
                    ) from exc
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "上一次模型调用没有返回可用正文。请直接返回一个 JSON 对象"
                            '（"tool" 或 "final"），不要输出空内容。'
                        ),
                    }
                )
                continue
            duration_ms = int((time.monotonic() - started) * 1000)
            self.trace.emit(
                "llm_call",
                node=self.name,
                summary=f"turn {turn}",
                duration_ms=duration_ms,
                chars=len(raw),
                usage=self.adapter.last_usage,
            )

            try:
                parsed = extract_json_object(raw)
            except ValueError as exc:
                parse_failures += 1
                self.trace.emit(
                    "agent_protocol_error",
                    node=self.name,
                    summary=str(exc),
                    raw_preview=truncate(raw, 800),
                )
                if parse_failures > 3:
                    raise AgentError(f"{self.name} 多次返回非法 JSON: {exc}") from exc
                messages.extend(
                    [
                        {"role": "assistant", "content": raw},
                        {
                            "role": "user",
                            "content": (
                                f"无法解析为 JSON：{exc}。请只返回一个 JSON 对象，"
                                '包含 "thought" 和 "tool"/"final" 字段。'
                            ),
                        },
                    ]
                )
                continue

            if "final" in parsed:
                final = parsed["final"]
                if not isinstance(final, dict):
                    validation_failures += 1
                    messages.extend(
                        [
                            {"role": "assistant", "content": raw},
                            {
                                "role": "user",
                                "content": '"final" 必须是 JSON 对象，请修正后重新返回。',
                            },
                        ]
                    )
                    continue
                error = self.validator(final) if self.validator else None
                if (
                    error is None
                    and self.required_tool
                    and successful_tool_calls.get(self.required_tool, 0) == 0
                ):
                    error = (
                        f"必须先成功调用至少一次 `{self.required_tool}`，"
                        "再给出最终结果；不能只依赖输入摘要。"
                    )
                if error:
                    validation_failures += 1
                    self.trace.emit(
                        "agent_validation_error",
                        node=self.name,
                        summary=error,
                    )
                    if validation_failures > 2:
                        raise AgentError(f"{self.name} 最终结果未通过校验: {error}")
                    messages.extend(
                        [
                            {"role": "assistant", "content": raw},
                            {
                                "role": "user",
                                "content": f"最终结果未通过校验：{error}。请修正后重新返回。",
                            },
                        ]
                    )
                    continue
                self.trace.emit(
                    "agent_final",
                    node=self.name,
                    summary=f"turn {turn} 完成",
                    keys=sorted(final.keys()),
                )
                return final

            tool_name = parsed.get("tool")
            args = parsed.get("args", {})
            if not isinstance(tool_name, str) or tool_name not in self.tools:
                messages.extend(
                    [
                        {"role": "assistant", "content": raw},
                        {
                            "role": "user",
                            "content": (
                                f'未知工具 {tool_name!r}。可用工具：'
                                + ", ".join(self.tools)
                                + "；或返回 final。"
                            ),
                        },
                    ]
                )
                continue
            if not isinstance(args, dict):
                messages.extend(
                    [
                        {"role": "assistant", "content": raw},
                        {
                            "role": "user",
                            "content": '"args" 必须是 JSON 对象。',
                        },
                    ]
                )
                continue

            tool_started = time.monotonic()
            try:
                result = self.tools[tool_name](**args)
            except Exception as exc:  # tool failures are observations, not crashes
                result = {"error": str(exc)}
            tool_ms = int((time.monotonic() - tool_started) * 1000)
            if not (isinstance(result, dict) and "error" in result):
                successful_tool_calls[tool_name] = (
                    successful_tool_calls.get(tool_name, 0) + 1
                )
            result_json = json.dumps(result, ensure_ascii=False)
            self.trace.emit(
                "tool_call",
                node=self.name,
                summary=tool_name,
                duration_ms=tool_ms,
                args=args,
                result_chars=len(result_json),
                error="error" in result if isinstance(result, dict) else False,
            )
            messages.extend(
                [
                    {"role": "assistant", "content": raw},
                    {
                        "role": "user",
                        "content": (
                            f"工具 {tool_name} 的返回：\n"
                            + truncate(result_json, 12000)
                        ),
                    },
                ]
            )

        raise AgentError(f"{self.name} 在 {self.max_turns} 轮内没有给出最终结果")


class WriterAgent:
    """Single-shot Markdown writer with one retry for an empty answer."""

    name = "writer"

    def __init__(
        self,
        *,
        adapter: ModelAdapter,
        system_prompt: str,
        trace: Trace,
    ) -> None:
        self.adapter = adapter
        self.system_prompt = system_prompt
        self.trace = trace

    def run(self, task: dict[str, Any]) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": "写作输入：\n"
                + json.dumps(task, ensure_ascii=False, indent=2),
            },
        ]
        for attempt in range(1, 3):
            started = time.monotonic()
            try:
                raw = self.adapter.complete(messages, agent=self.name)
            except LLMError as exc:
                self.trace.emit(
                    "llm_error",
                    node=self.name,
                    summary=truncate(str(exc), 500),
                )
                if attempt >= 2:
                    raise AgentError(f"文档 Agent 模型调用失败: {exc}") from exc
                continue
            duration_ms = int((time.monotonic() - started) * 1000)
            draft = _strip_code_fence(raw).strip()
            self.trace.emit(
                "llm_call",
                node=self.name,
                summary=f"attempt {attempt}",
                duration_ms=duration_ms,
                chars=len(raw),
                draft_chars=len(draft),
                usage=self.adapter.last_usage,
            )
            if len(draft) >= 200:
                return draft
            messages.extend(
                [
                    {"role": "assistant", "content": raw},
                    {
                        "role": "user",
                        "content": "草稿过短。请输出完整的 Markdown 文档，不要只写说明。",
                    },
                ]
            )
        raise AgentError("文档 Agent 没有返回有效草稿")


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) >= 2:
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
    return "\n".join(lines)
