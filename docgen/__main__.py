"""Command-line entry point for the documentation workflow."""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

from .config import PROJECT_ROOT, ModelConfig, load_dotenv
from .llm.base import ModelAdapter
from .llm.mock import MockAdapter
from .llm.openai_compat import OpenAICompatibleAdapter
from .pipeline import build_pipeline, write_artifacts
from .state import (
    STATUS_FAILED,
    STATUS_PASSED,
    RunState,
    utc_now,
)
from .tools.fs import InputSandbox
from .trace import Trace


def _configure_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _new_run_id(output: Path | None) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if output is not None:
        return stamp
    candidate = PROJECT_ROOT / "runs" / stamp
    suffix = 2
    while candidate.exists():
        candidate = PROJECT_ROOT / "runs" / f"{stamp}-{suffix}"
        suffix += 1
    return candidate.name


def _build_adapter(args: argparse.Namespace) -> tuple[ModelAdapter, str]:
    if args.model == "mock":
        return MockAdapter(args.scenario), f"mock:{args.scenario}"
    config = ModelConfig.from_env()
    return OpenAICompatibleAdapter(config), config.model


def cmd_run(args: argparse.Namespace) -> int:
    load_dotenv()
    input_dir = Path(args.input).resolve()
    if not input_dir.is_dir():
        print(f"输入目录不存在: {input_dir}", file=sys.stderr)
        return 2

    run_id = _new_run_id(Path(args.out) if args.out else None)
    output_dir = (
        Path(args.out).resolve()
        if args.out
        else PROJECT_ROOT / "runs" / run_id
    )
    if (output_dir / "trace.jsonl").exists():
        print(f"输出目录已有运行记录，请换一个 --out: {output_dir}", file=sys.stderr)
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        adapter, model_label = _build_adapter(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    state = RunState(
        run_id=run_id,
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        model=model_label,
        max_revisions=args.max_revisions,
    )
    trace = Trace(output_dir / "trace.jsonl", run_id)

    try:
        sandbox = InputSandbox(input_dir)
        trace.emit(
            "run_start",
            summary=f"model={model_label}",
            input_dir=str(input_dir),
            max_revisions=args.max_revisions,
        )
        state.add_event("run_start", summary=f"model={model_label}")
        pipeline = build_pipeline(
            state=state,
            sandbox=sandbox,
            adapter=adapter,
            trace=trace,
        )
        pipeline.run()
        if state.status not in {STATUS_PASSED, "needs_manual_review"}:
            raise RuntimeError(f"工作流结束但状态未确定: {state.status}")

        trace.emit(
            "run_end",
            summary=state.status,
            facts=len(state.facts),
            revisions=state.revision_count,
        )
        state.add_event(
            "run_end",
            summary=state.status,
            facts=len(state.facts),
            revisions=state.revision_count,
        )
        (output_dir / "state.json").write_text(
            json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:  # fail the run with a readable, saved state
        state.status = STATUS_FAILED
        state.errors.append(f"{type(exc).__name__}: {exc}")
        state.finished_at = utc_now()
        state.add_event("error", summary=str(exc))
        trace.emit(
            "run_end",
            summary=STATUS_FAILED,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        try:
            write_artifacts(state, "README.rejected.md")
        except Exception:  # artifact writing must not hide the original error
            pass
        print(f"\n运行失败: {exc}", file=sys.stderr)
        print(f"状态与日志已保存到: {output_dir}", file=sys.stderr)
        return 3
    finally:
        trace.close()

    print("\n运行完成")
    print(f"  状态: {state.status}")
    print(f"  模型: {state.model}")
    print(f"  事实: {len(state.facts)} 条，审核返工: {state.revision_count} 次")
    print(f"  草稿版本: {state.draft_version}")
    print(f"  输出目录: {output_dir}")
    for name in (
        "README.generated.md",
        "README.rejected.md",
        "analysis.json",
        "review.json",
        "state.json",
        "trace.jsonl",
    ):
        if (output_dir / name).exists():
            print(f"    - {name}")

    if state.status == STATUS_PASSED:
        print(f"\n生成文档: {output_dir / 'README.generated.md'}")
        return 0
    print("\n文档未通过审核，请查看 README.rejected.md 与 review.json。")
    return 1


def cmd_check_api(_: argparse.Namespace) -> int:
    load_dotenv()
    try:
        config = ModelConfig.from_env()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    adapter = OpenAICompatibleAdapter(config)
    print(f"base_url: {config.base_url}")
    print(f"model:    {config.model}")
    started = time.monotonic()
    try:
        text = adapter.complete(
            [
                {"role": "system", "content": "你是一个连通性测试助手。"},
                {"role": "user", "content": '只返回 JSON：{"ok": true}'},
            ],
            agent="check-api",
            temperature=0.0,
            max_tokens=50,
        )
    except Exception as exc:
        print(f"调用失败: {exc}", file=sys.stderr)
        return 2
    elapsed = int((time.monotonic() - started) * 1000)
    print(f"耗时:     {elapsed} ms")
    print(f"usage:    {adapter.last_usage}")
    print(f"响应:     {text.strip()[:500]}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docgen",
        description="2–3 个 Agent 协作的 Python 项目文档生成工作流。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="运行一次文档生成工作流")
    run.add_argument("--input", required=True, help="只读的 Python 项目目录")
    run.add_argument("--out", default=None, help="运行产物目录")
    run.add_argument(
        "--model",
        choices=["api", "mock"],
        default="api",
        help="api 调用真实模型；mock 使用内置脚本化响应",
    )
    run.add_argument(
        "--scenario",
        choices=["pass", "rework", "fail"],
        default="pass",
        help="仅 mock 模式使用：一次通过 / 返工后通过 / 返工后失败",
    )
    run.add_argument(
        "--max-revisions",
        type=int,
        default=1,
        help="最多返工次数（默认 1）",
    )
    run.set_defaults(func=cmd_run)

    check = subparsers.add_parser("check-api", help="验证模型最小调用")
    check.set_defaults(func=cmd_check_api)
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_stdout()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
