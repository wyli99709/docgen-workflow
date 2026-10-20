"""Mechanical validation of facts and drafts."""

from __future__ import annotations

import re
from typing import Any

from ..state import RunState

REQUIRED_HEADINGS = (
    "## 项目用途",
    "## 安装",
    "## 使用方法",
    "## 主要模块",
    "## 已知限制",
)
CITATION_RE = re.compile(r"\[(F[1-9][0-9]*)\]")
MIN_DRAFT_CHARS = 300
MAX_DRAFT_CHARS = 20_000
MIN_DISTINCT_CITATIONS = 3


def _issue(
    problem: str,
    *,
    severity: str = "high",
    claim: str = "文档结构",
    evidence: str = "",
    suggestion: str,
) -> dict[str, Any]:
    return {
        "source": "rules",
        "severity": severity,
        "claim": claim,
        "problem": problem,
        "evidence": evidence,
        "suggestion": suggestion,
    }


def validate_facts(state: RunState) -> list[dict[str, Any]]:
    """Check that fact evidence points at real files and line ranges."""

    issues: list[dict[str, Any]] = []
    if not state.facts:
        issues.append(
            _issue(
                "分析结果为空，无法生成可核验文档。",
                claim="事实清单",
                suggestion="重新运行分析 Agent，确认它读取了源码。",
            )
        )
        return issues

    manifest = {entry["path"]: entry for entry in state.manifest}
    seen: set[str] = set()
    for fact in state.facts:
        fact_id = fact.get("id", "?")
        if fact_id in seen:
            issues.append(
                _issue(
                    f"事实编号重复: {fact_id}。",
                    claim="事实清单",
                    suggestion="为每条事实分配唯一编号。",
                )
            )
        seen.add(fact_id)
        evidence = fact.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            issues.append(
                _issue(
                    f"{fact_id} 没有源码证据。",
                    claim="事实清单",
                    suggestion="删除该事实或补充文件与行号证据。",
                )
            )
            continue
        for item in evidence:
            path = item.get("file") if isinstance(item, dict) else None
            lines = item.get("lines") if isinstance(item, dict) else None
            if path not in manifest:
                issues.append(
                    _issue(
                        f"{fact_id} 引用了清单之外的文件: {path!r}。",
                        claim="事实清单",
                        suggestion="只引用 manifest 中的文件。",
                    )
                )
                continue
            if (
                not isinstance(lines, list)
                or len(lines) != 2
                or not all(isinstance(value, int) for value in lines)
                or lines[0] < 1
                or lines[1] < lines[0]
                or lines[1] > manifest[path]["lines"]
            ):
                issues.append(
                    _issue(
                        f"{fact_id} 的行号范围无效: {lines!r}。",
                        claim="事实清单",
                        evidence=f"{path} 共 {manifest[path]['lines']} 行",
                        suggestion="修正证据行号。",
                    )
                )
    return issues


def validate_draft(state: RunState) -> list[dict[str, Any]]:
    """Check structure, citations and review consistency without a model."""

    issues: list[dict[str, Any]] = []
    draft = state.draft.strip()
    if not draft:
        return [
            _issue(
                "草稿为空。",
                claim="文档正文",
                suggestion="文档 Agent 需要输出完整 Markdown。",
            )
        ]
    if len(draft) < MIN_DRAFT_CHARS:
        issues.append(
            _issue(
                f"草稿只有 {len(draft)} 字，少于下限 {MIN_DRAFT_CHARS}。",
                claim="文档正文",
                suggestion="补充用途、安装、命令和限制等必要内容。",
            )
        )
    if len(draft) > MAX_DRAFT_CHARS:
        issues.append(
            _issue(
                f"草稿有 {len(draft)} 字，超过上限 {MAX_DRAFT_CHARS}。",
                claim="文档正文",
                suggestion="压缩重复内容，聚焦可核验事实。",
            )
        )

    heading_lines = {line.strip() for line in draft.splitlines()}
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in heading_lines]
    if missing:
        issues.append(
            _issue(
                "缺少必需章节: " + "、".join(missing),
                claim="文档结构",
                suggestion="按模板补全五个二级标题。",
            )
        )

    fact_ids = {
        fact.get("id")
        for fact in state.facts
        if isinstance(fact, dict) and isinstance(fact.get("id"), str)
    }
    citations = CITATION_RE.findall(draft)
    unknown = sorted({citation for citation in citations if citation not in fact_ids})
    if unknown:
        issues.append(
            _issue(
                "引用了不存在的事实编号: " + "、".join(unknown),
                claim="引用检查",
                suggestion="只引用分析结果中存在的 [F#]，或删除错误引用。",
            )
        )
    distinct = set(citations) & fact_ids
    if len(distinct) < MIN_DISTINCT_CITATIONS:
        issues.append(
            _issue(
                f"草稿只引用了 {len(distinct)} 条不同事实，少于 {MIN_DISTINCT_CITATIONS} 条。",
                claim="引用检查",
                suggestion="为主要功能和命令补充可核验的事实引用。",
            )
        )

    if state.review_verdict not in {"pass", "revise"}:
        issues.append(
            _issue(
                f"审核结论无效: {state.review_verdict!r}。",
                claim="审核结果",
                suggestion="审核 Agent 必须返回 pass 或 revise。",
            )
        )
    elif state.review_verdict == "pass" and state.review_issues:
        issues.append(
            _issue(
                "审核结论为 pass，但同时列出了问题。",
                claim="审核结果",
                suggestion="修正审核结论或问题列表。",
            )
        )
    elif state.review_verdict == "revise" and not state.review_issues:
        issues.append(
            _issue(
                "审核结论为 revise，但没有给出具体问题。",
                claim="审核结果",
                suggestion="列出可执行的修改意见。",
            )
        )

    return issues
