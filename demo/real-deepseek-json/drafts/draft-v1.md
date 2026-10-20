# todo-cli

## 项目用途

`todo-cli` 是一个极简的本地命令行待办管理工具，项目描述为 “A minimal local command-line todo manager.”，当前版本 `0.1.0` [F2]。它通过命令行添加、查看、完成和删除任务，并将任务持久化到单个 JSON 文件中 [F6][F13]。项目要求 Python `>=3.11`，无第三方运行依赖 [F3]。

## 安装

**无需安装直接运行**：项目无第三方运行依赖 [F3]，要求 Python `>=3.11` [F3]。在可导入 `todo_cli` 包的项目根目录下，可直接通过模块方式启动 [F1]：

- `python -m todo_cli list` [F1][F8]

**需要安装时**：`pyproject.toml` 使用 setuptools 作为构建系统（`setuptools>=61`、`setuptools.build_meta`），并在 `.` 下按 `todo_cli*` 收集包 [F4]。但当前事实未给出具体安装命令，也未确认安装后是否提供 `todo` 可执行命令（console_scripts），因此安装步骤及安装后的命令名待确认 [F4]。

## 使用方法

以下命令在可导入 `todo_cli` 的项目根目录执行 [F1]。默认数据文件为 `todo.json` [F5][F13]；可通过全局选项 `--data` 指定其他 JSON 数据文件路径 [F5]。

- 添加任务：`python -m todo_cli add "写周报"`  
  新任务 id 按现有最大 id 加 1 生成，成功时打印 `Added task {id}: {title}` 并返回退出码 0 [F7]。

- 查看任务：`python -m todo_cli list`  
  无任务时打印 `No tasks yet.`；有任务时逐条打印 `[{x|空格}] {id}. {title}`，已完成任务显示为 `x`，返回退出码 0 [F8]。

- 完成任务：`python -m todo_cli done 1`  
  成功时将该任务标记为完成，打印 `Completed task {id}: {title}` 并返回 0 [F9]。

- 删除任务：`python -m todo_cli delete 1`  
  成功时移除该任务，打印 `Deleted task {id}: {title}` 并返回 0 [F10]。

- 使用自定义数据文件：`python -m todo_cli --data my-todo.json list`  
  `--data` 为全局选项，用于指定 JSON 数据文件路径 [F5]。

`done` 或 `delete` 找不到指定 id 时，会打印 `Task {task_id} not found.` 并返回退出码 1 [F11]。若传入未支持的命令，`main` 会调用 `parser.error(...)`，以退出码 2 终止 [F12]。

## 主要模块

- `pyproject.toml`：定义项目名 `todo-cli`、版本 `0.1.0`、Python `>=3.11`、无第三方运行依赖，以及 setuptools 构建配置 [F2][F3][F4]。
- `todo_cli/__init__.py`：定义包版本 `__version__ = "0.1.0"` [F2]。
- `todo_cli/__main__.py`：模块入口，从 `.cli` 导入 `main`，并以 `raise SystemExit(main())` 启动 [F1]。
- `todo_cli/cli.py`：创建 argparse 解析器，注册全局选项 `--data` 和 `add`、`list`、`done`、`delete` 子命令，处理输出及退出码 [F5][F6][F7][F8][F9][F10][F11][F12]。
- `todo_cli/models.py`：定义 `Task` dataclass，字段为 `id`、`title`、`done`，并提供 `to_dict()` 与 `from_dict()` [F15]。
- `todo_cli/storage.py`：负责 JSON 数据文件的读取与保存；文件不存在时返回空列表，保存时创建父目录并覆盖写入 [F13][F14]。

## 已知限制

- 仅提供 `add`、`list`、`done`、`delete` 四个子命令，未确认存在编辑、搜索、清空等其他命令 [F6]。
- 数据保存在单个 JSON 文件中，默认路径为 `todo.json` [F13]；保存时会整文件覆盖写入 [F14]。
- 多进程并发写同一数据文件的行为待确认；当前保存实现为整文件覆盖 [F14]。
- 损坏或非法 JSON 文件的容错行为待确认；`load()` 会直接使用 `json.load` 解析 [F13]。
- `list` 的排序规则待确认；当前实现按存储顺序遍历，未显式排序 [F8]。
- 安装后是否提供 `todo` 可执行命令待确认；当前仅确认了 setuptools 构建配置，未确认 console_scripts 声明 [F4]。