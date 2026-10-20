# todo-cli

## 项目用途

todo-cli 是一个本地命令行待办事项管理器，使用 Python 实现，版本 0.1.0 [F2]。任务保存在单个 JSON 文件中，默认文件名 `todo.json`，也可用全局选项 `--data` 指定其他路径 [F4][F10]。程序提供四个子命令：

- `add`：新增任务，id 取现有最大 id 加 1，`done` 默认 False [F5]
- `list`：列出全部任务，已完成的用 `x` 标记 [F6]
- `done`：把指定 id 的任务标记为完成 [F7]
- `delete`：按 id 删除任务 [F8]

程序通过 `python -m todo_cli` 启动 [F1]，不使用网络，也不依赖第三方运行时库 [F3]。

## 安装

**无需安装即可运行**：`pyproject.toml` 中 `dependencies = []`，运行时只用标准库 [F3]；只要在包含 `todo_cli/` 包的源码根目录执行 `python -m todo_cli` 即可 [F1]。

**前置条件**：Python >= 3.11（`requires-python = ">=3.11"`）[F3]。

**需要安装的情况**：项目使用 setuptools 构建，构建依赖 `setuptools>=61`，后端为 `setuptools.build_meta`，并通过 `[tool.setuptools.packages.find]` 的 `include = ["todo_cli*"]` 发现包 [F3]。具体安装命令（例如用 pip 安装源码目录）未在事实清单中给出，**待确认**。

**注意**：`pyproject.toml` 只定义 build-system 与 project 元数据，没有 `[project.scripts]` 控制台脚本入口 [F2]。因此即使安装完成也不会提供 `todo` 命令，仍需使用 `python -m todo_cli` 运行 [F2]。

## 使用方法

以下命令均在**源码根目录**（包含 `todo_cli/` 的目录）执行：

```bash
# 新增任务
python -m todo_cli add "写 README"

# 查看全部任务
python -m todo_cli list

# 将 id 为 1 的任务标记为完成
python -m todo_cli done 1

# 删除 id 为 1 的任务
python -m todo_cli delete 1
```

**数据文件位置**：默认是当前工作目录下的 `todo.json`；`save` 时会先 `mkdir(parents=True, exist_ok=True)` 创建父目录，再以 UTF-8 写入格式化 JSON [F10]。若数据文件不存在，`load` 直接返回空列表，不会报错 [F11]。要换文件时使用顶层全局选项 `--data`：

```bash
python -m todo_cli --data ~/tasks.json list
```

`--data` 只定义在顶层解析器上，四个子解析器都没有该选项 [F4]，因此**必须写在子命令之前**；写成 `python -m todo_cli list --data x` 会被 argparse 判为未识别参数，打印 usage 并以退出码 2 结束 [F4][F9]。

**子命令必须显式指定**：子解析器通过 `add_subparsers(dest="command", required=True)` 注册 [F4]。未知子命令在 `parse_args` 阶段就被 argparse 直接拒绝（打印 usage、退出码 2），不会进入 `main` 的分派逻辑；`cli.py` 末尾的 `parser.error("Unsupported command: ...")` 兜底分支因此实际上不可达 [F4][F9]。

**输出与退出码**：

- `add` 输出 `Added task {id}: {title}`，退出码 0 [F5]
- `list` 无任务时输出 `No tasks yet.`；否则每行 `[x] {id}. {title}` 或 `[ ] {id}. {title}`，退出码 0 [F6]
- `done` 输出 `Completed task {id}: {title}`，退出码 0 [F7]
- `delete` 输出 `Deleted task {id}: {title}`，退出码 0 [F8]
- `done`、`delete` 指定的 id 不存在时输出 `Task {id} not found.`，退出码 1 [F7][F8][F14]
- 参数错误（未知子命令、`--data` 位置错误等）退出码 2 [F9]

## 主要模块

- `pyproject.toml`：构建与项目元数据（name=todo-cli、version=0.1.0、requires-python>=3.11），声明 setuptools 构建后端与包发现规则，无控制台脚本入口 [F2][F3]。
- `todo_cli/__main__.py`：`python -m todo_cli` 的入口，从 `.cli` 导入 `main`，用 `raise SystemExit(main())` 把返回值作为进程退出码 [F1]。
- `todo_cli/cli.py`：命令解析与执行。`build_parser()` 构建解析器、`--data` 全局选项与四个子命令 [F4]；`_find_task()` 按 id 线性查找，找不到返回 None [F13][F14]；`main(argv)` 先按 `args.data` 构造 `TaskStore(Path(args.data))` 并 `load()`，再按 `args.command` 分派并返回退出码 [F9]。
- `todo_cli/models.py`：以 `@dataclass` 定义 `Task`，字段 `id: int`、`title: str`、`done: bool = False`；`to_dict()` 用 `dataclasses.asdict` 序列化，`from_dict()` 把 `id` 转 int、`title` 转 str，缺少 `done` 时默认 False [F12]。
- `todo_cli/storage.py`：持久化层。`load()` 在文件不存在时返回空列表，存在时以 UTF-8 读取并逐项转成 `Task` [F11]；`save()` 创建父目录后以 UTF-8 整体写入格式化 JSON（`ensure_ascii=False, indent=2`）[F10]。
- `todo_cli/__init__.py`：包初始化文件，仅包含模块 docstring 与版本声明 `__version__ = "0.1.0"`（与 `pyproject.toml` 的 version 一致 [F2]），不导出 `main` 等其他符号。

## 已知限制

- **没有 `todo` 命令**：未定义 `[project.scripts]`，只能通过 `python -m todo_cli` 调用 [F2]。
- **命令集有限**：分派逻辑只覆盖 `add`、`list`、`done`、`delete` 四个子命令，没有编辑标题、清除已完成项、过滤查询之类的功能 [F15]。
- **`--data` 位置固定**：它只是顶层选项，必须写在子命令之前，不能放在 `list --data ...` 这样的位置 [F4]。
- **单文件整体覆盖写**：所有任务存在一个 JSON 数组里，每次 `save` 都重写整个文件，任务越多写入开销越大 [F10][F15]。
- **无并发控制**：`save` 没有任何加锁机制，多个进程同时写同一数据文件可能互相覆盖；`--data` 也只影响当前这次调用 [F15]（该结论为中等置信度）。
- **数据文件损坏时直接崩溃**：`load()` 只判断文件是否存在，随后直接 `json.load`，没有 try/except [F11]；`from_dict()` 只对 `done` 提供默认值 [F12]。因此文件不是合法 JSON、或数组元素缺少 `id`/`title` 字段时，不会给出友好提示，而是抛出 `JSONDecodeError`/`KeyError` 并以 traceback 终止进程。
- **测试与 CI 情况未确认**：manifest 中没有 tests 目录或 CI 配置文件，是否存在单元测试及 CI 流程**待确认**，需要查看仓库完整文件列表。
- **README 与 LICENSE**：manifest 中未体现这两个文件，是否随仓库提供**待确认**。