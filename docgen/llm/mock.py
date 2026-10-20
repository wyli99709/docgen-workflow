"""Deterministic model responses for tests and offline demos.

The mock is intentionally transparent: it exercises the same message protocol
as a real model and is always labelled as mock in the run output.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from .base import ModelAdapter

PASS_DRAFT = """# todo-cli

## 项目用途

`todo_cli` 是一个本地命令行待办事项工具，任务保存在 JSON 文件中，支持添加、查看、完成和删除任务。[F1][F2][F9]

## 安装

- 需要 Python 3.11 或更新版本（`pyproject.toml` 声明 `requires-python = ">=3.11"`）。[F8]
- 运行时仅使用 Python 标准库，不需要安装第三方依赖。[F8]
- 在 `examples/todo_cli` 目录下可以直接运行，无需打包安装。[F1]

## 使用方法

在项目根目录执行：

```bash
python -m todo_cli --help
python -m todo_cli add "写作业"
python -m todo_cli list
python -m todo_cli done 1
python -m todo_cli delete 1
```

- `add <title>`：创建新任务，ID 为当前最大 ID 加 1。[F3]
- `list`：列出任务，`[ ]` 表示未完成，`[x]` 表示已完成。[F4]
- `done <task_id>`：把指定任务标记为完成。[F5]
- `delete <task_id>`：删除指定任务。[F6]
- 使用 `--data <path>` 可以指定数据文件，默认是当前目录下的 `todo.json`。[F7]

任务 ID 不存在时，`done` 和 `delete` 会打印提示并返回退出码 1。[F5][F6]

## 主要模块

- `todo_cli/cli.py`：解析命令行参数、分发子命令并输出结果。[F10]
- `todo_cli/storage.py`：负责从 JSON 文件加载任务和保存任务。[F10]
- `todo_cli/models.py`：定义 `Task` 数据类，字段为 `id`、`title`、`done`。[F10][F12]

## 已知限制

- 任务保存在单个 JSON 文件中，加载和保存都会操作整个文件，没有并发控制；多个进程同时写入时可能互相覆盖。[F9][F11]
- 当前只提供 `add`、`list`、`done`、`delete` 四个命令，不支持编辑标题或调整顺序。[F2][F14]
- 列表输出没有排序、筛选或关键字搜索选项。[F4]
"""

DRAFT_WITHOUT_VERSION = PASS_DRAFT.replace(
    '- 需要 Python 3.11 或更新版本（`pyproject.toml` 声明 `requires-python = ">=3.11"`）。[F8]\n',
    "",
)

DRAFT_FAILED_REVISION = PASS_DRAFT.replace(
    "- 在 `examples/todo_cli` 目录下可以直接运行，无需打包安装。[F1]",
    "- 在 `examples/todo_cli` 目录下可以直接运行，无需打包安装。[F1]\n"
    "- 也可以执行 `pip install todo-cli` 安装命令行工具。",
)

FACTS: list[dict[str, Any]] = [
    {
        "id": "F1",
        "kind": "entrypoint",
        "statement": "通过 `python -m todo_cli` 启动，`__main__.py` 调用 `cli.main()` 并把返回值作为退出码。",
        "evidence": [{"file": "todo_cli/__main__.py", "lines": [1, 6]}],
        "confidence": "high",
    },
    {
        "id": "F2",
        "kind": "command",
        "statement": "通过 argparse 子解析器提供 add、list、done、delete 四个子命令。",
        "evidence": [{"file": "todo_cli/cli.py", "lines": [29, 38]}],
        "confidence": "high",
    },
    {
        "id": "F3",
        "kind": "command",
        "statement": "`add <title>` 使用当前最大任务 ID 加 1 创建新任务，并立即写入数据文件。",
        "evidence": [{"file": "todo_cli/cli.py", "lines": [60, 66]}],
        "confidence": "high",
    },
    {
        "id": "F4",
        "kind": "command",
        "statement": "`list` 按保存顺序输出任务，未完成任务标记为 `[ ]`，已完成标记为 `[x]`。",
        "evidence": [{"file": "todo_cli/cli.py", "lines": [68, 75]}],
        "confidence": "high",
    },
    {
        "id": "F5",
        "kind": "command",
        "statement": "`done <task_id>` 将指定任务标记为已完成；ID 不存在时打印提示并返回退出码 1。",
        "evidence": [
            {"file": "todo_cli/cli.py", "lines": [43, 49]},
            {"file": "todo_cli/cli.py", "lines": [77, 86]},
        ],
        "confidence": "high",
    },
    {
        "id": "F6",
        "kind": "command",
        "statement": "`delete <task_id>` 删除指定任务；ID 不存在时打印提示并返回退出码 1。",
        "evidence": [
            {"file": "todo_cli/cli.py", "lines": [77, 80]},
            {"file": "todo_cli/cli.py", "lines": [88, 92]},
        ],
        "confidence": "high",
    },
    {
        "id": "F7",
        "kind": "configuration",
        "statement": "全局选项 `--data` 指定 JSON 数据文件，默认值为 `todo.json`。",
        "evidence": [
            {"file": "todo_cli/cli.py", "lines": [11, 11]},
            {"file": "todo_cli/cli.py", "lines": [21, 25]},
        ],
        "confidence": "high",
    },
    {
        "id": "F8",
        "kind": "dependency",
        "statement": "运行时只使用 Python 标准库，依赖列表为空；要求 Python 3.11 或更新版本。",
        "evidence": [{"file": "pyproject.toml", "lines": [9, 10]}],
        "confidence": "high",
    },
    {
        "id": "F9",
        "kind": "data",
        "statement": "任务保存在单个 JSON 文件中，加载时读取整个文件，保存时重写整个文件。",
        "evidence": [{"file": "todo_cli/storage.py", "lines": [17, 36]}],
        "confidence": "high",
    },
    {
        "id": "F10",
        "kind": "module",
        "statement": "`cli.py` 负责参数解析、命令分发和输出，`storage.py` 负责 JSON 读写，`models.py` 定义 Task 数据类。",
        "evidence": [
            {"file": "todo_cli/cli.py", "lines": [14, 40]},
            {"file": "todo_cli/storage.py", "lines": [11, 36]},
            {"file": "todo_cli/models.py", "lines": [9, 30]},
        ],
        "confidence": "high",
    },
    {
        "id": "F11",
        "kind": "limitation",
        "statement": "存储层没有加锁或合并逻辑，多个进程同时写入时可能互相覆盖。",
        "evidence": [{"file": "todo_cli/storage.py", "lines": [26, 36]}],
        "confidence": "medium",
    },
    {
        "id": "F12",
        "kind": "feature",
        "statement": "Task 数据类包含整数 id、字符串 title 和布尔 done，done 默认为 False。",
        "evidence": [{"file": "todo_cli/models.py", "lines": [9, 15]}],
        "confidence": "high",
    },
    {
        "id": "F13",
        "kind": "data",
        "statement": "任务以 JSON 数组形式保存，每个元素包含 id、title、done 字段。",
        "evidence": [{"file": "todo_cli/storage.py", "lines": [22, 36]}],
        "confidence": "high",
    },
    {
        "id": "F14",
        "kind": "limitation",
        "statement": "当前只注册了 add、list、done、delete 四个命令，没有编辑或排序命令。",
        "evidence": [{"file": "todo_cli/cli.py", "lines": [29, 38]}],
        "confidence": "high",
    },
]

UNKNOWNS = [
    "未确认是否计划支持多用户或并发访问。",
    "未确认是否存在 Windows 之外的路径兼容性要求。",
]

REVIEW_ISSUE_MISSING_VERSION = {
    "severity": "medium",
    "claim": "安装章节缺少 Python 版本要求",
    "problem": "pyproject.toml 声明 requires-python >= 3.11，但草稿的安装章节只说明无需第三方依赖，没有告诉用户最低 Python 版本。",
    "evidence": 'pyproject.toml:9 声明 requires-python = ">=3.11"',
    "suggestion": "在安装章节补充“需要 Python 3.11 或更新版本”，并引用事实 F8。",
}

REVIEW_ISSUE_FAKE_INSTALL = {
    "severity": "high",
    "claim": "安装章节的 pip install todo-cli 命令",
    "problem": "事实清单和 pyproject.toml 都没有提供 pip 安装命令或发布包信息；该命令没有源码证据。",
    "evidence": "pyproject.toml 只声明项目元数据，未提供 scripts 或发布配置",
    "suggestion": "删除该安装命令，或先在事实清单中补充可核验的安装方式。",
}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


class MockAdapter(ModelAdapter):
    """Scripted responses keyed by agent name and call count."""

    def __init__(self, scenario: str = "pass") -> None:
        if scenario not in {"pass", "rework", "fail"}:
            raise ValueError(f"未知 mock 场景: {scenario}")
        self.scenario = scenario
        self.calls: Counter[str] = Counter()
        self._last_usage: dict[str, Any] | None = None

    @property
    def last_usage(self) -> dict[str, Any] | None:
        return self._last_usage

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        agent: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        index = self.calls[agent]
        self.calls[agent] += 1
        self._last_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        if agent == "analyst":
            return self._analyst(index)
        if agent == "writer":
            return self._writer(index)
        if agent == "reviewer":
            return self._reviewer(index)
        raise ValueError(f"MockAdapter 不认识 agent: {agent!r}")

    def _analyst(self, index: int) -> str:
        if index == 0:
            return _json(
                {
                    "thought": "先查看文件清单，确定需要读取哪些源码。",
                    "tool": "list_files",
                    "args": {},
                }
            )
        if index == 1:
            return _json(
                {
                    "thought": "读取命令行入口，确认所有子命令和参数。",
                    "tool": "read_file",
                    "args": {"path": "todo_cli/cli.py", "start": 1, "end": 95},
                }
            )
        if index == 2:
            return _json(
                {
                    "thought": "读取存储实现，确认数据文件格式和写入方式。",
                    "tool": "read_file",
                    "args": {"path": "todo_cli/storage.py"},
                }
            )
        if index == 3:
            return _json(
                {
                    "thought": "读取数据模型，确认任务字段。",
                    "tool": "read_file",
                    "args": {"path": "todo_cli/models.py"},
                }
            )
        return _json(
            {
                "thought": "已核对入口、四个子命令、存储实现和依赖声明。",
                "final": {"facts": FACTS, "unknowns": UNKNOWNS},
            }
        )

    def _writer(self, index: int) -> str:
        if self.scenario == "pass":
            return PASS_DRAFT
        if index == 0:
            return DRAFT_WITHOUT_VERSION
        if self.scenario == "fail":
            return DRAFT_FAILED_REVISION
        return PASS_DRAFT

    def _reviewer(self, index: int) -> str:
        if index == 0:
            return _json(
                {
                    "thought": "读取命令行入口，核对草稿中的命令和参数。",
                    "tool": "read_file",
                    "args": {"path": "todo_cli/cli.py", "start": 1, "end": 95},
                }
            )
        if self.scenario == "pass":
            return _json(
                {
                    "thought": "入口、四个子命令、默认数据文件和存储方式均与源码一致。",
                    "final": {"verdict": "pass", "issues": []},
                }
            )
        if index == 1:
            return _json(
                {
                    "thought": "安装章节遗漏了源码声明的 Python 版本要求。",
                    "final": {
                        "verdict": "revise",
                        "issues": [REVIEW_ISSUE_MISSING_VERSION],
                    },
                }
            )
        if index == 2:
            return _json(
                {
                    "thought": "再次检查安装章节和命令示例。",
                    "tool": "read_file",
                    "args": {"path": "pyproject.toml"},
                }
            )
        if self.scenario == "rework":
            return _json(
                {
                    "thought": "修订版补充了 Python 版本要求，未发现其他影响正确性的问题。",
                    "final": {"verdict": "pass", "issues": []},
                }
            )
        return _json(
            {
                "thought": "修订版引入了没有源码依据的 pip 安装命令。",
                "final": {
                    "verdict": "revise",
                    "issues": [REVIEW_ISSUE_FAKE_INSTALL],
                },
            }
        )
