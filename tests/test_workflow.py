"""End-to-end tests for the three routing paths."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from docgen.checks.rules import validate_draft
from docgen.llm.mock import MockAdapter
from docgen.pipeline import build_pipeline
from docgen.state import STATUS_NEEDS_REVIEW, STATUS_PASSED, RunState
from docgen.tools.fs import InputSandbox
from docgen.trace import Trace

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "examples" / "todo_cli"


class WorkflowTest(unittest.TestCase):
    def run_scenario(self, scenario: str):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        output = Path(temp.name)
        state = RunState(
            run_id=f"test-{scenario}",
            input_dir=str(SAMPLE),
            output_dir=str(output),
            model=f"mock:{scenario}",
            max_revisions=1,
        )
        adapter = MockAdapter(scenario)
        trace = Trace(output / "trace.jsonl", state.run_id)
        self.addCleanup(trace.close)
        pipeline = build_pipeline(
            state=state,
            sandbox=InputSandbox(SAMPLE),
            adapter=adapter,
            trace=trace,
        )
        pipeline.run()
        return state, adapter, output

    def test_pass_path(self) -> None:
        state, adapter, output = self.run_scenario("pass")
        self.assertEqual(state.status, STATUS_PASSED)
        self.assertEqual(state.revision_count, 0)
        self.assertEqual(state.draft_version, 1)
        self.assertEqual(adapter.calls["analyst"], 5)
        self.assertEqual(adapter.calls["writer"], 1)
        self.assertEqual(adapter.calls["reviewer"], 2)
        self.assertEqual(len(state.facts), 14)
        self.assertEqual(validate_draft(state), [])

        generated = output / "README.generated.md"
        self.assertTrue(generated.exists())
        text = generated.read_text(encoding="utf-8")
        self.assertIn("# todo-cli", text)
        self.assertIn("## 项目用途", text)
        self.assertIn("[F1]", text)
        for name in ("analysis.json", "review.json", "state.json", "trace.jsonl"):
            self.assertTrue((output / name).exists(), name)

        trace = [
            json.loads(line)
            for line in (output / "trace.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        routes = [event["summary"] for event in trace if event["event"] == "route"]
        self.assertIn("finalize_pass", routes)
        self.assertGreaterEqual(
            sum(1 for event in trace if event["event"] == "tool_call"),
            5,
        )

    def test_rework_path(self) -> None:
        state, adapter, output = self.run_scenario("rework")
        self.assertEqual(state.status, STATUS_PASSED)
        self.assertEqual(state.revision_count, 1)
        self.assertEqual(state.draft_version, 2)
        self.assertEqual(adapter.calls["writer"], 2)
        self.assertEqual(adapter.calls["reviewer"], 4)
        stages = [(round_["stage"], round_.get("verdict")) for round_ in state.rounds]
        self.assertEqual(
            stages,
            [
                ("review", "revise"),
                ("rules", None),
                ("review", "pass"),
                ("rules", None),
            ],
        )
        text = (output / "README.generated.md").read_text(encoding="utf-8")
        self.assertIn("Python 3.11", text)
        self.assertIn("## 已知限制", text)
        self.assertTrue((output / "drafts" / "draft-v1.md").exists())
        self.assertTrue((output / "drafts" / "draft-v2.md").exists())

    def test_fail_path(self) -> None:
        state, adapter, output = self.run_scenario("fail")
        self.assertEqual(state.status, STATUS_NEEDS_REVIEW)
        self.assertEqual(state.revision_count, 1)
        self.assertEqual(adapter.calls["writer"], 2)
        self.assertEqual(adapter.calls["reviewer"], 4)
        self.assertFalse((output / "README.generated.md").exists())
        rejected = output / "README.rejected.md"
        self.assertTrue(rejected.exists())
        self.assertIn("pip install todo-cli", rejected.read_text(encoding="utf-8"))

        review = json.loads((output / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(review["verdict"], "revise")
        self.assertTrue(
            any("pip install" in issue["claim"] for issue in review["issues"])
        )
        rounds = [item.get("verdict") for item in review["rounds"] if item["stage"] == "review"]
        self.assertEqual(rounds, ["revise", "revise"])


if __name__ == "__main__":
    unittest.main()
