# todo-cli

## 项目用途

`todo-cli` 是一个极简的本地命令行待办事项管理器，项目描述为 “A minimal local command-line todo manager.”，当前版本 `0.1.0` [F2][F4]。所有任务保存在一个本地 JSON 文件中，默认文件名为 `todo.json` [F5][F15][F16]。

命令行提供四个子命令：`add`、`list`、`done`、`delete` [F6]，覆盖新增任务、查看列表、标记完成和删除任务。任务模型包含 `id`、`title`、`done` 三个字段 [F13]。

## 安装

**无需安装，直接运行**

- 要求 Python `>=3.11` [F3]。
- 项目没有第三方运行时依赖（`dependencies = []`），只用标准库 [F3]。
- 在包含 `todo_cli` 包的仓库根目录下，可直接用 `python -m todo_cli` 启动：`__main__.py` 从 `.cli` 导入 `main`，并在 `__main__` 保护下执行 `raise SystemExit(main())` [F1]。

**需要安装为包时**

- `pyproject.toml` 声明构建使用 `setuptools>=61` 与 `setuptools.build_meta` 后端 [F3]，包发现范围为 `where = ["."]`、`include = ["todo_cli*"]` [F2]，因此可按常规 setuptools 流程构建（例如在仓库根目录执行 `pip install .`）。该命令本身未在项目文件中显式给出，属于基于构建后端的常规做法，可用性待确认。
- 项目**未声明 `console_scripts` 入口**，因此安装后是否会出现 `todo` 可执行命令待确认；在此之前请统一使用 `python -m todo_cli` 调用（解析器的 `prog` 仅为 `todo`，作用于帮助信息显示）[F3][F5]。

## 使用方法

以下命令均在仓库根目录执行；默认数据文件为当前工作目录下的 `todo.json`（`--data` 的默认值）[F1][F5]。

新增一条任务：

```bash
python -m todo_cli add "写 README"
```

输出 `Added task {id}: {title}`，退出码 0；新任务 id 由现有任务最大 id 加 1 得到（无任务时为 1）[F7]。

查看全部任务：

```bash
python -m todo_cli list
```

无任务时输出 `No tasks yet.`；否则每条输出 `[x] {id}. {title}`，已完成为 `x`，未完成为空格 [F8]。

标记完成与删除（参数为整型 id）：

```bash
python -m todo_cli done 1
python -m todo_cli delete 1
```

分别输出 `Completed task {id}: {title}` 和 `Deleted task {id}: {title}`，退出码 0 [F9][F10]。若 id 不存在，输出 `Task {id} not found.` 并返回退出码 1 [F11]。

指定其他数据文件（`--data` 是顶层解析器的全局选项 [F5]）：

```bash
python -m todo_cli --data /tmp/my-todo.json list
```

以上示例把 `--data` 放在子命令之前；放在子命令之后是否被接受，源码中未说明，待确认。

## 主要模块

- `pyproject.toml`：项目元数据（名称 `todo-cli`、版本 `0.1.0`、描述）、包发现配置 [F2]，以及 Python 版本要求与 setuptools 构建后端 [F3]。
- `todo_cli/__init__.py`：定义 `__version__ = "0.1.0"` [F4]。
- `todo_cli/__main__.py`：模块入口，导入 `main` 并以 `SystemExit` 返回其退出码，支持 `python -m todo_cli` [F1]。
- `todo_cli/cli.py`：argparse 解析器构建（`prog="todo"`、全局 `--data`、四个必需子命令）[F5][F6]，各子命令处理逻辑 [F7][F8][F9][F10]，以及 `main()` 中的加载、任务查找与未找到任务的错误返回 [F11]。
- `todo_cli/models.py`：`Task` dataclass（`id: int`、`title: str`、`done: bool = False`）与 `to_dict()` 序列化 [F13]；`from_dict()` 强制转换 `id`/`title` 类型，`done` 缺省为 `False` [F14]。
- `todo_cli/storage.py`：`TaskStore.load()` 以 UTF-8 读取 JSON，文件缺失返回空列表 [F15]；`TaskStore.save()` 创建父目录后以 UTF-8 写出带缩进的 JSON [F16]。

## 已知限制

- 数据存储为单个 JSON 文件的**全量覆盖写入**，每次保存都会重写整个文件 [F16]；任务规模变大时无增量写入机制。
- 源码中没有文件锁或原子写，多进程/多次同时写入时的行为（是否丢数据）待确认。
- 读取到损坏的或非数组的 JSON 时没有显式处理逻辑，实际表现待确认。
- 命令行只有 `add`、`list`、`done`、`delete` 四个子命令 [F6]，没有编辑、搜索、清除已完成等命令；如需这些功能需自行扩展。
- 任务 id 取自当前最大 id 加 1 [F7]，删除任务后 id 是否被复用未在源码中说明，待确认。
- `main()` 末尾的 `Unsupported command` 分支因 `add_subparsers(required=True)` 且四个分支均已返回，实际不可达 [F12]。
- argparse 对非法参数或非整型 `task_id` 的具体退出码未在源码中显式定义，待确认。
- 仓库清单中未包含测试文件或 CI 配置，是否有测试/持续集成待确认。
- 未声明 `console_scripts` 入口，安装后是否提供 `todo` 命令以及是否计划发布到 PyPI 均待确认 [F3]。