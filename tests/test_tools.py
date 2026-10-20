"""Tests for the sandbox, AST index and deterministic rules."""

from __future__ import annotations

import unittest
from pathlib import Path

from docgen.agents.analyst import make_analyst_validator
from docgen.agents.reviewer import make_review_validator, validate_review
from docgen.checks.rules import validate_draft, validate_facts
from docgen.state import RunState
from docgen.tools.ast_index import build_ast_index
from docgen.tools.fs import InputSandbox, ToolError

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "examples" / "todo_cli"


class SandboxTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sandbox = InputSandbox(SAMPLE)

    def test_manifest_contains_sample_files(self) -> None:
        paths = {entry["path"] for entry in self.sandbox.scan()}
        self.assertIn("pyproject.toml", paths)
        self.assertIn("todo_cli/cli.py", paths)
        self.assertIn("todo_cli/storage.py", paths)
        self.assertEqual(len(paths), 6)

    def test_read_file_range(self) -> None:
        result = self.sandbox.read_file("todo_cli/cli.py", 29, 38)
        self.assertEqual(result["start"], 29)
        self.assertEqual(result["end"], 38)
        self.assertIn("add_parser", result["text"])
        self.assertIn("delete", result["text"])

    def test_read_file_clamps_long_range(self) -> None:
        result = self.sandbox.read_file("todo_cli/cli.py", 1, 9999)
        self.assertEqual(result["end"], 95)
        self.assertFalse(result["truncated"])

    def test_search(self) -> None:
        result = self.sandbox.search("add_parser")
        self.assertTrue(result["matches"])
        self.assertTrue(
            any(match["file"] == "todo_cli/cli.py" for match in result["matches"])
        )

    def test_path_traversal_is_rejected(self) -> None:
        with self.assertRaises(ToolError):
            self.sandbox.read_file("../../secret.txt")
        with self.assertRaises(ToolError):
            self.sandbox.read_file(str(Path("C:/Windows/win.ini")))

    def test_check_lines(self) -> None:
        self.assertIsNone(self.sandbox.check_lines("todo_cli/cli.py", 1, 95))
        self.assertIsNotNone(self.sandbox.check_lines("todo_cli/cli.py", 1, 999))
        self.assertIsNotNone(self.sandbox.check_lines("todo_cli/cli.py", 0, 2))
        self.assertIsNotNone(self.sandbox.check_lines("missing.py", 1, 2))


class AstIndexTest(unittest.TestCase):
    def test_cli_structure(self) -> None:
        sandbox = InputSandbox(SAMPLE)
        index = build_ast_index(sandbox, sandbox.scan())
        cli = index["python_files"]["todo_cli/cli.py"]
        commands = {item["name"] for item in cli["argparse"]["subcommands"]}
        self.assertEqual(commands, {"add", "list", "done", "delete"})
        options = {item["option"] for item in cli["argparse"]["options"]}
        self.assertIn("--data", options)
        self.assertTrue(index["python_files"]["todo_cli/__main__.py"]["main_guard"])
        self.assertEqual(index["pyproject"]["project"]["requires-python"], ">=3.11")
        self.assertEqual(index["pyproject"]["project"]["dependencies"], [])


class RulesTest(unittest.TestCase):
    def make_state(self) -> RunState:
        sandbox = InputSandbox(SAMPLE)
        state = RunState(
            run_id="rules",
            input_dir=str(SAMPLE),
            output_dir="unused",
            model="test",
        )
        state.manifest = sandbox.scan()
        state.facts = [
            {
                "id": "F1",
                "kind": "entrypoint",
                "statement": "通过 python -m todo_cli 启动。",
                "evidence": [{"file": "todo_cli/__main__.py", "lines": [1, 6]}],
            },
            {
                "id": "F2",
                "kind": "command",
                "statement": "提供 add/list/done/delete 四个命令。",
                "evidence": [{"file": "todo_cli/cli.py", "lines": [29, 38]}],
            },
            {
                "id": "F3",
                "kind": "module",
                "statement": "models.py 定义 Task 数据类。",
                "evidence": [{"file": "todo_cli/models.py", "lines": [9, 30]}],
            },
        ]
        state.review_verdict = "pass"
        state.draft = "\n".join(
            [
                "# todo-cli",
                "## 项目用途",
                "用途说明。[F1]",
                "## 安装",
                "说明。[F2]",
                "## 使用方法",
                "说明。[F2]",
                "## 主要模块",
                "说明。[F3]",
                "## 已知限制",
                "说明。[F1]",
                "x" * 400,
            ]
        )
        return state

    def test_valid_state_has_no_rule_issues(self) -> None:
        state = self.make_state()
        self.assertEqual(validate_facts(state), [])
        self.assertEqual(validate_draft(state), [])

    def test_unknown_citation_is_reported(self) -> None:
        state = self.make_state()
        state.draft += "\n错误引用 [F99]"
        problems = [issue["problem"] for issue in validate_draft(state)]
        self.assertTrue(any("不存在的事实编号" in problem for problem in problems))

    def test_bad_evidence_is_reported(self) -> None:
        state = self.make_state()
        state.facts[0]["evidence"] = [{"file": "nope.py", "lines": [1, 2]}]
        problems = [issue["problem"] for issue in validate_facts(state)]
        self.assertTrue(any("清单之外" in problem for problem in problems))

    def test_missing_heading_is_reported(self) -> None:
        state = self.make_state()
        state.draft = state.draft.replace("## 安装\n", "")
        problems = [issue["problem"] for issue in validate_draft(state)]
        self.assertTrue(any("缺少必需章节" in problem for problem in problems))


class AgentValidatorTest(unittest.TestCase):
    def test_analyst_rejects_out_of_manifest_evidence(self) -> None:
        sandbox = InputSandbox(SAMPLE)
        validate = make_analyst_validator(sandbox)
        final = {
            "facts": [
                {
                    "id": "F1",
                    "kind": "feature",
                    "statement": "一个有效陈述",
                    "evidence": [{"file": "does/not/exist.py", "lines": [1, 2]}],
                }
            ],
            "unknowns": [],
        }
        self.assertIsNotNone(validate(final))

    def test_reviewer_rejects_pass_with_issues(self) -> None:
        error = validate_review(
            {
                "verdict": "pass",
                "issues": [
                    {
                        "severity": "high",
                        "claim": "x",
                        "problem": "y",
                        "evidence": "z",
                        "suggestion": "w",
                    }
                ],
            }
        )
        self.assertIsNotNone(error)

    def test_reviewer_accepts_consistent_review(self) -> None:
        self.assertIsNone(validate_review({"verdict": "pass", "issues": []}))

    def test_reviewer_requires_grounded_evidence(self) -> None:
        sandbox = InputSandbox(SAMPLE)
        validate = make_review_validator(sandbox)
        issue = {
            "severity": "high",
            "claim": "示例结论",
            "problem": "具体问题",
            "evidence": "源码里看起来不对",
            "suggestion": "修正",
        }
        self.assertIsNotNone(validate({"verdict": "revise", "issues": [issue]}))
        issue["evidence"] = "todo_cli/cli.py:57"
        self.assertIsNone(validate({"verdict": "revise", "issues": [issue]}))


if __name__ == "__main__":
    unittest.main()
