# todo-cli

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