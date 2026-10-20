"""Build and run the document-generation workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agents.analyst import build_analyst
from .agents.reviewer import build_reviewer
from .agents.writer import build_writer
from .checks.rules import REQUIRED_HEADINGS, validate_draft, validate_facts
from .llm.base import ModelAdapter
from .orchestrator import Workflow
from .state import (
    STATUS_NEEDS_REVIEW,
    STATUS_PASSED,
    RunState,
    utc_now,
)
from .tools.ast_index import build_ast_index
from .tools.fs import InputSandbox
from .trace import Trace


class PipelineError(RuntimeError):
    """A node could not produce the state required by the next node."""


def _manifest_view(state: RunState) -> list[dict[str, Any]]:
    return [
        {
            "path": entry["path"],
            "size_bytes": entry["size_bytes"],
            "lines": entry["lines"],
        }
        for entry in state.manifest
    ]


def write_artifacts(state: RunState, draft_name: str | None = None) -> None:
    """Persist the shared state and the evidence used by the final document."""

    output = Path(state.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    def dump(name: str, value: Any) -> None:
        (output / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    dump("manifest.json", state.manifest)
    dump(
        "analysis.json",
        {
            "source_digest": state.source_digest,
            "facts": state.facts,
            "unknowns": state.unknowns,
        },
    )
    dump(
        "review.json",
        {
            "verdict": state.review_verdict,
            "issues": state.review_issues,
            "rule_issues": state.rule_issues,
            "rounds": state.rounds,
        },
    )
    if draft_name and state.draft:
        (output / draft_name).write_text(state.draft, encoding="utf-8")
    dump("state.json", state.to_dict())


class Pipeline:
    """The concrete graph: scan → analyze → write → review → rules → route."""

    def __init__(
        self,
        *,
        state: RunState,
        sandbox: InputSandbox,
        adapter: ModelAdapter,
        trace: Trace,
    ) -> None:
        self.state = state
        self.sandbox = sandbox
        self.adapter = adapter
        self.trace = trace
        self.analyst = build_analyst(adapter, sandbox, trace)
        self.writer = build_writer(adapter, trace)
        self.reviewer = build_reviewer(adapter, sandbox, trace)
        self.workflow = self._build()

    def _build(self) -> Workflow:
        workflow = Workflow(self.trace)
        workflow.add_node("scan", self._scan)
        workflow.add_node("analyze", self._analyze)
        workflow.add_node("write", self._write)
        workflow.add_node("review", self._review)
        workflow.add_node("rules", self._rules)
        workflow.add_node("revise", self._revise)
        workflow.add_node("finalize_pass", self._finalize_pass)
        workflow.add_node("finalize_fail", self._finalize_fail)

        workflow.set_entry("scan")
        workflow.add_edge("scan", "analyze")
        workflow.add_edge("analyze", "write")
        workflow.add_edge("write", "review")
        workflow.add_edge("review", "rules")
        workflow.add_conditional("rules", self._route_after_rules)
        workflow.add_edge("revise", "write")
        workflow.add_edge("finalize_pass", None)
        workflow.add_edge("finalize_fail", None)
        return workflow

    def run(self) -> None:
        self.workflow.run(self.state)

    # ---- nodes -------------------------------------------------------

    def _scan(self, state: RunState) -> None:
        manifest = self.sandbox.scan()
        if not any(entry["path"].endswith(".py") for entry in manifest):
            raise PipelineError("输入目录中没有 Python 源码文件，无法生成项目文档。")
        state.manifest = manifest
        state.ast_index = build_ast_index(self.sandbox, manifest)
        state.source_digest = self.sandbox.source_digest()
        state.add_event(
            "scan",
            node="scan",
            summary=f"{len(manifest)} 个文件",
            digest=state.source_digest[:12],
        )

    def _analyze(self, state: RunState) -> None:
        final = self.analyst.run(
            {
                "goal": "为生成 README 建立可核验的事实清单",
                "manifest": _manifest_view(state),
                "ast_index": state.ast_index,
            }
        )
        facts = final.get("facts")
        if not isinstance(facts, list) or not facts:
            raise PipelineError("分析 Agent 没有返回事实清单。")
        state.facts = facts
        state.unknowns = final.get("unknowns", [])
        state.add_event(
            "analyze",
            node="analyze",
            summary=f"{len(state.facts)} 条事实",
            facts=[fact.get("id") for fact in state.facts],
        )

    def _write(self, state: RunState) -> None:
        feedback = state.revision_feedback
        pyproject = state.ast_index.get("pyproject") or {}
        project = pyproject.get("project") if isinstance(pyproject, dict) else None
        project_name = (
            project.get("name")
            if isinstance(project, dict) and project.get("name")
            else Path(state.input_dir).name
        )
        draft = self.writer.run(
            {
                "project_name": project_name,
                "manifest": _manifest_view(state),
                "facts": state.facts,
                "unknowns": state.unknowns,
                "required_headings": list(REQUIRED_HEADINGS),
                "previous_draft": state.draft if feedback else None,
                "review_feedback": feedback,
            }
        )
        state.draft = draft
        state.draft_version += 1
        drafts_dir = Path(state.output_dir) / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / f"draft-v{state.draft_version}.md").write_text(
            draft, encoding="utf-8"
        )
        state.revision_feedback = []
        state.add_event(
            "write",
            node="write",
            summary=f"第 {state.draft_version} 版草稿",
            chars=len(draft),
            feedback_items=len(feedback),
        )

    def _review(self, state: RunState) -> None:
        final = self.reviewer.run(
            {
                "draft": state.draft,
                "facts": state.facts,
                "unknowns": state.unknowns,
                "manifest": _manifest_view(state),
                "revision_count": state.revision_count,
            }
        )
        verdict = final.get("verdict")
        issues = final.get("issues", [])
        if verdict not in {"pass", "revise"} or not isinstance(issues, list):
            raise PipelineError("审核 Agent 返回了无效结论。")
        state.review_verdict = verdict
        state.review_issues = issues
        state.rounds.append(
            {
                "stage": "review",
                "draft_version": state.draft_version,
                "verdict": verdict,
                "issues": issues,
            }
        )
        state.add_event(
            "review",
            node="review",
            summary=f"{verdict}，{len(issues)} 条问题",
            draft_version=state.draft_version,
        )

    def _rules(self, state: RunState) -> None:
        issues = validate_facts(state) + validate_draft(state)
        state.rule_issues = issues
        state.rounds.append(
            {
                "stage": "rules",
                "draft_version": state.draft_version,
                "issues": issues,
            }
        )
        state.add_event(
            "rules",
            node="rules",
            summary=f"{len(issues)} 条机械校验问题",
            draft_version=state.draft_version,
        )

    def _revise(self, state: RunState) -> None:
        if state.revision_count >= state.max_revisions:
            raise PipelineError("返工次数已用尽，路由逻辑有误。")
        state.revision_count += 1
        state.revision_feedback = [*state.review_issues, *state.rule_issues]
        state.add_event(
            "revise",
            node="revise",
            summary=f"第 {state.revision_count} 次返工",
            feedback_items=len(state.revision_feedback),
        )
        state.review_verdict = ""
        state.review_issues = []
        state.rule_issues = []

    def _route_after_rules(self, state: RunState) -> str:
        if not state.all_issues:
            return "finalize_pass"
        if state.revision_count < state.max_revisions:
            return "revise"
        return "finalize_fail"

    def _finalize_pass(self, state: RunState) -> None:
        state.status = STATUS_PASSED
        state.finished_at = utc_now()
        state.add_event("finalize", node="finalize_pass", summary="通过")
        write_artifacts(state, "README.generated.md")

    def _finalize_fail(self, state: RunState) -> None:
        state.status = STATUS_NEEDS_REVIEW
        state.finished_at = utc_now()
        state.add_event(
            "finalize",
            node="finalize_fail",
            summary=f"{len(state.all_issues)} 条未解决问题",
        )
        write_artifacts(state, "README.rejected.md")


def build_pipeline(
    *,
    state: RunState,
    sandbox: InputSandbox,
    adapter: ModelAdapter,
    trace: Trace,
) -> Pipeline:
    return Pipeline(state=state, sandbox=sandbox, adapter=adapter, trace=trace)
