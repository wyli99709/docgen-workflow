"""Tolerant JSON extraction for model responses."""

from __future__ import annotations

import json
import re
from typing import Any


def _first_balanced_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse the first JSON object found in ``text``.

    Models sometimes wrap JSON in Markdown fences or add a short explanation;
    this accepts both without silently turning malformed output into data.
    """

    if not isinstance(text, str) or not text.strip():
        raise ValueError("模型返回为空")

    candidates: list[str] = []
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
    candidates.extend(block.strip() for block in fenced)
    candidates.append(text.strip())

    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            balanced = _first_balanced_object(candidate)
            if balanced is None:
                continue
            try:
                value = json.loads(balanced)
            except json.JSONDecodeError:
                continue
        if isinstance(value, dict):
            return value

    raise ValueError("未找到合法的 JSON 对象")


def truncate(text: str, limit: int) -> str:
    """Shorten long text while making the truncation explicit."""

    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[已截断，原长度 {len(text)} 字符]"
