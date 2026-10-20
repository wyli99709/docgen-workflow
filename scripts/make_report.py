"""Render a static HTML report from one workflow run directory.

This is a viewer for the artifacts, not part of the agent workflow.
Usage:
    python scripts/make_report.py --run demo/real-deepseek --out demo/real-deepseek/report.html
"""

from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _read_trace(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _badge(severity: str) -> str:
    return f'<span class="badge { _esc(severity) }">{ _esc(severity) }</span>'


def _issue_card(issue: dict[str, Any]) -> str:
    severity = str(issue.get("severity", "low"))
    return f"""
    <div class="issue { _esc(severity) }">
      <div class="issue-head">{_badge(severity)}<strong>{_esc(issue.get("claim"))}</strong></div>
      <p><b>问题：</b>{_esc(issue.get("problem"))}</p>
      <p><b>证据：</b><code>{_esc(issue.get("evidence"))}</code></p>
      <p><b>建议：</b>{_esc(issue.get("suggestion"))}</p>
    </div>
    """


def build_report(run_dir: Path) -> str:
    state = _read_json(run_dir / "state.json", {})
    analysis = _read_json(run_dir / "analysis.json", {})
    review = _read_json(run_dir / "review.json", {})
    trace = _read_trace(run_dir / "trace.jsonl")

    status = str(state.get("status", "unknown"))
    status_class = "passed" if status == "passed" else "failed"
    facts = analysis.get("facts", [])
    rounds = review.get("rounds", [])
    llm_calls = [event for event in trace if event.get("event") == "llm_call"]
    tool_calls = [event for event in trace if event.get("event") == "tool_call"]
    node_sequence = [
        event.get("node")
        for event in state.get("events", [])
        if event.get("event") == "node_start"
    ]
    by_agent = Counter(event.get("node") for event in tool_calls)
    tokens = sum(
        (event.get("details", {}).get("usage") or {}).get("total_tokens", 0)
        for event in llm_calls
    )

    flow_chips = []
    for index, node in enumerate(node_sequence, start=1):
        cls = "node revise" if node == "revise" else "node"
        label = {
            "scan": "扫描/AST",
            "analyze": "分析 Agent",
            "write": "文档 Agent",
            "review": "审核 Agent",
            "rules": "规则校验",
            "revise": "返工",
            "finalize_pass": "发布",
            "finalize_fail": "失败保存",
        }.get(str(node), str(node))
        flow_chips.append(f'<span class="{cls}">{index}. {_esc(label)}</span>')
        if index < len(node_sequence):
            flow_chips.append('<span class="arrow">→</span>')

    round_html = []
    for round_item in rounds:
        stage = str(round_item.get("stage"))
        verdict = round_item.get("verdict")
        issues = round_item.get("issues", [])
        title = f"{stage} · draft v{round_item.get('draft_version', '?')}"
        if verdict:
            title += f" · {verdict}"
        cards = "".join(_issue_card(issue) for issue in issues)
        if not cards:
            cards = '<p class="muted">无问题。</p>'
        round_html.append(
            f'<div class="round"><h3>{_esc(title)}</h3>{cards}</div>'
        )

    fact_rows = []
    for fact in facts:
        evidence = "<br>".join(
            f"<code>{_esc(item.get('file'))}:{_esc(item.get('lines'))}</code>"
            for item in fact.get("evidence", [])
        )
        fact_rows.append(
            f"<tr><td><b>{_esc(fact.get('id'))}</b></td>"
            f"<td>{_esc(fact.get('kind'))}</td>"
            f"<td>{_esc(fact.get('statement'))}</td>"
            f"<td>{evidence}</td>"
            f"<td>{_esc(fact.get('confidence', ''))}</td></tr>"
        )

    tool_rows = []
    for event in tool_calls:
        details = event.get("details", {})
        tool_rows.append(
            f"<tr><td>{_esc(event.get('node'))}</td>"
            f"<td>{_esc(event.get('summary'))}</td>"
            f"<td><code>{_esc(json.dumps(details.get('args', {}), ensure_ascii=False))}</code></td>"
            f"<td>{_esc(details.get('result_chars'))}</td>"
            f"<td>{_esc(details.get('duration_ms'))} ms</td>"
            f"<td>{_esc(details.get('error'))}</td></tr>"
        )

    llm_rows = []
    for event in llm_calls:
        details = event.get("details", {})
        usage = details.get("usage") or {}
        llm_rows.append(
            f"<tr><td>{_esc(event.get('node'))}</td>"
            f"<td>{_esc(event.get('summary'))}</td>"
            f"<td>{_esc(event.get('duration_ms'))} ms</td>"
            f"<td>{_esc(details.get('chars'))}</td>"
            f"<td>{_esc(usage.get('total_tokens', ''))}</td></tr>"
        )

    artifacts = [
        ("README.generated.md", "README.generated.md"),
        ("README.rejected.md", "README.rejected.md"),
        ("analysis.json", "analysis.json"),
        ("review.json", "review.json"),
        ("state.json", "state.json"),
        ("trace.jsonl", "trace.jsonl"),
        ("manifest.json", "manifest.json"),
    ]
    artifact_links = [
        f'<a href="{name}">{label}</a>'
        for name, label in artifacts
        if (run_dir / name).exists()
    ]
    for draft in sorted((run_dir / "drafts").glob("*.md")):
        artifact_links.append(
            f'<a href="drafts/{_esc(draft.name)}">{_esc(draft.name)}</a>'
        )

    css = """
    :root { color-scheme: light; --bg:#f6f7fb; --card:#fff; --text:#18202f;
            --muted:#667085; --line:#e4e7ec; --green:#067647; --red:#b42318;
            --amber:#b54708; --blue:#175cd3; }
    * { box-sizing: border-box; }
    body { margin:0; padding:32px; background:var(--bg); color:var(--text);
           font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif; }
    .wrap { max-width:1180px; margin:0 auto; }
    h1 { margin:0 0 4px; font-size:26px; }
    h2 { margin:30px 0 12px; font-size:19px; }
    h3 { margin:0 0 10px; font-size:15px; }
    .muted { color:var(--muted); }
    .card, .round, .issue { background:var(--card); border:1px solid var(--line); border-radius:10px; }
    .card { padding:18px 20px; }
    .stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin-top:18px; }
    .stat { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }
    .stat b { display:block; font-size:22px; }
    .status { display:inline-block; padding:3px 10px; border-radius:999px; font-weight:600; }
    .status.passed { background:#ecfdf3; color:var(--green); }
    .status.failed { background:#fef3f2; color:var(--red); }
    .flow { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-top:10px; }
    .node { background:#eff8ff; color:var(--blue); border:1px solid #b2ddff; border-radius:8px; padding:6px 10px; }
    .node.revise { background:#fffaeb; color:var(--amber); border-color:#fedf89; }
    .arrow { color:var(--muted); }
    table { width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line); border-radius:10px; overflow:hidden; }
    th, td { text-align:left; vertical-align:top; padding:9px 11px; border-bottom:1px solid var(--line); }
    th { background:#f9fafb; font-size:12px; text-transform:uppercase; letter-spacing:.03em; color:var(--muted); }
    tr:last-child td { border-bottom:0; }
    code { background:#f2f4f7; padding:1px 5px; border-radius:4px; font-size:12px; }
    .round { padding:16px 18px; margin-bottom:12px; }
    .issue { padding:12px 14px; margin-top:10px; border-left:4px solid var(--line); }
    .issue.high { border-left-color:var(--red); }
    .issue.medium { border-left-color:var(--amber); }
    .issue.low { border-left-color:var(--blue); }
    .issue p { margin:6px 0; }
    .badge { display:inline-block; min-width:54px; text-align:center; padding:1px 7px; margin-right:8px;
             border-radius:999px; font-size:11px; font-weight:700; text-transform:uppercase; }
    .badge.high { background:#fef3f2; color:var(--red); }
    .badge.medium { background:#fffaeb; color:var(--amber); }
    .badge.low { background:#eff8ff; color:var(--blue); }
    .links a { display:inline-block; margin:0 14px 8px 0; color:var(--blue); }
    .note { margin-top:10px; color:var(--muted); font-size:12px; }
    """

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DocGen Workflow — {_esc(state.get('run_id'))}</title>
<style>{css}</style>
</head>
<body>
<div class="wrap">
  <h1>文档生成 Workflow · 运行报告</h1>
  <p class="muted">run_id: {_esc(state.get('run_id'))} · 模型: {_esc(state.get('model'))}</p>
  <p><span class="status {status_class}">{_esc(status)}</span>
     <span class="muted"> · 输入: {_esc(state.get('input_dir'))}</span></p>

  <div class="stats">
    <div class="stat"><span class="muted">事实</span><b>{len(facts)}</b></div>
    <div class="stat"><span class="muted">草稿版本</span><b>{_esc(state.get('draft_version'))}</b></div>
    <div class="stat"><span class="muted">返工次数</span><b>{_esc(state.get('revision_count'))}</b></div>
    <div class="stat"><span class="muted">模型调用</span><b>{len(llm_calls)}</b></div>
    <div class="stat"><span class="muted">工具调用</span><b>{len(tool_calls)}</b></div>
    <div class="stat"><span class="muted">总 token</span><b>{tokens or '—'}</b></div>
  </div>

  <h2>执行路径</h2>
  <div class="flow">{''.join(flow_chips) or '<span class="muted">无节点事件</span>'}</div>

  <h2>审核与返工</h2>
  {''.join(round_html) or '<p class="muted">无记录</p>'}

  <h2>事实清单（带源码证据）</h2>
  <table>
    <thead><tr><th>ID</th><th>类型</th><th>陈述</th><th>证据</th><th>置信度</th></tr></thead>
    <tbody>{''.join(fact_rows) or '<tr><td colspan="5" class="muted">无事实</td></tr>'}</tbody>
  </table>

  <h2>工具调用</h2>
  <table>
    <thead><tr><th>Agent</th><th>工具</th><th>参数</th><th>结果字符</th><th>耗时</th><th>错误</th></tr></thead>
    <tbody>{''.join(tool_rows) or '<tr><td colspan="6" class="muted">无工具调用</td></tr>'}</tbody>
  </table>

  <h2>模型调用</h2>
  <table>
    <thead><tr><th>Agent</th><th>轮次</th><th>耗时</th><th>字符</th><th>token</th></tr></thead>
    <tbody>{''.join(llm_rows) or '<tr><td colspan="5" class="muted">无模型调用</td></tr>'}</tbody>
  </table>

  <h2>原始产物</h2>
  <p class="links">{''.join(artifact_links) or '无产物'}</p>
  <p class="note">这是从运行产物生成的静态查看页，不是工作流的一部分；工作流本身没有网页界面。
  通过状态以 <code>README.generated.md</code> 为准，失败状态以 <code>README.rejected.md</code> 和 <code>review.json</code> 为准。</p>
</div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a static HTML report")
    parser.add_argument("--run", required=True, help="run directory")
    parser.add_argument("--out", default=None, help="output HTML path")
    args = parser.parse_args()
    run_dir = Path(args.run).resolve()
    if not (run_dir / "state.json").exists():
        print(f"不是有效的运行目录: {run_dir}")
        return 1
    output = Path(args.out).resolve() if args.out else run_dir / "report.html"
    output.write_text(build_report(run_dir), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
