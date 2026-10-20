# todo-cli

## 项目用途

todo-cli 是一个极简的本地命令行待办事项管理器，项目元数据中的描述即为 “A minimal local command-line todo manager.” [F16]。它把任务保存在一个本地 JSON 文件中，默认文件名为 `todo.json` [F4]，并提供添加、列出、完成、删除四类操作 [F3]。

任务模型是 `Task` 数据类，包含 `id: int`、`title: str`、`done: bool = False` 三个字段 [F11]，在 JSON 中同样以这三个键存取 [F12]。

## 安装

**无需安装直接运行**：项目没有第三方运行时依赖，`pyproject.toml` 的 `dependencies` 为空列表 [F15]，只要求 Python `>=3.11` [F15]。在项目根目录下直接以模块方式启动即可 [F1]：

```bash
python -m todo_cli --help
```

**需要安装的情况**：仓库提供了 `pyproject.toml`，构建后端为 `setuptools.build_meta`，构建依赖为 `setuptools>=61`，包名 `todo-cli`、版本 `0.1.0`，包发现范围包含 `todo_cli*` [F15][F16]。但 `pyproject.toml` 未声明 `[project.scripts]`，因此安装后不会生成 `todo` 之类的命令行入口，仍然只能用 `python -m todo_cli` 启动 [F18]。具体安装命令待确认（事实清单未给出安装步骤），如需安装请确认要使用的构建/安装方式。

## 使用方法

所有命令在项目根目录（即包含 `todo_cli/` 的目录）执行，这样 `python -m todo_cli` 才能找到包 [F1]。数据文件默认为当前目录下的 `todo.json`，可通过全局选项 `--data` 指定其他路径 [F4]。

添加任务（位置参数 `title`，新 ID 为现有最大 ID + 1，空列表时为 1，成功后打印 `Added task {id}: {title}` 并返回 0）[F5]：

```bash
python -m todo_cli add "Buy milk"
```

列出任务（无任务时打印 `No tasks yet.`；否则逐条打印 `[x] id. title` 或 `[ ] id. title`，返回 0）[F6]：

```bash
python -m todo_cli list
```

标记完成（位置参数为整型 `task_id`，打印 `Completed task {id}: {title}`，返回 0）[F7]：

```bash
python -m todo_cli done 1
```

删除任务（位置参数为整型 `task_id`，打印 `Deleted task {id}: {title}`，返回 0）[F8]：

```bash
python -m todo_cli delete 2
```

指定自定义数据文件（`--data` 是顶层解析器上的全局选项，需写在子命令之前）[F4]：

```bash
python -m todo_cli --data tasks.json list
```

`done` 与 `delete` 会先按 ID 查找任务，找不到时打印 `Task {task_id} not found.` 并返回退出码 1 [F9]。子命令由 argparse 的必填 subparsers 提供，未提供子命令时由 argparse 报错 [F3]。

## 主要模块

- `pyproject.toml`：项目元数据与构建配置；声明 Python `>=3.11`、空依赖列表、setuptools 构建后端、包发现范围 `["todo_cli*"]`，未声明命令行入口 [F15][F16][F18]。
- `todo_cli/__init__.py`：包初始化，声明 `__version__ = "0.1.0"`，与 pyproject 版本一致 [F17]。
- `todo_cli/__main__.py`：模块入口，从 `.cli` 导入 `main`，在 `if __name__ == "__main__"` 中执行 `raise SystemExit(main())` [F1]。
- `todo_cli/cli.py`：命令行主体，包含 `build_parser`（prog 为 `todo`、注册 add/list/done/delete 四个子命令、`--data` 选项）[F3][F4]、`main`（解析参数、构造 `TaskStore(Path(args.data))` 并加载、按 `args.command` 分派、返回退出码）[F2]，以及 `_find_task` 查找逻辑 [F9]。
- `todo_cli/models.py`：定义 `Task` 数据类 [F11]，提供 `to_dict`（`asdict`）与 `from_dict`（读取 `id`、`title`，`done` 用 `data.get("done", False)` 兜底）[F12]。
- `todo_cli/storage.py`：`TaskStore` 负责读写；`load` 在文件不存在时返回空列表，否则以 UTF-8 读取顶层为数组的 JSON 并逐项转成 `Task` [F13]；`save` 先递归创建父目录，再以 UTF-8 写入 JSON，`ensure_ascii=False`、`indent=2` [F14]。

## 已知限制

- 安装后没有 `todo` 等命令行入口，只能通过 `python -m todo_cli` 启动 [F18]。
- 数据以单个 JSON 文件整文件写入的方式保存 [F14]，并发写入同一文件的行为待确认（事实清单未确认是否存在锁机制），需要确认多人/多进程同时使用是否安全。
- `add` 是否校验空标题或重复标题待确认，需要确认空字符串是否会被接受。
- 数据文件 JSON 损坏或顶层不是数组时的错误处理行为待确认，需要确认此时是否会抛出未捕获异常 [F13]。
- 未匹配到任何子命令时会调用 `parser.error("Unsupported command: ...")` 并返回 2 [F10]，但正常使用中 argparse 的必填子命令 [F3] 已限制该分支的触发条件，其实际触发场景待确认。
- 新任务 ID 取现有最大 ID + 1 [F5]，因此删除最大 ID 的任务后新增任务可能复用该 ID，任务标识不保证长期唯一（据 F5 推导）。
- 是否有测试目录或 CI 配置待确认，当前文件清单中未见相关文件。