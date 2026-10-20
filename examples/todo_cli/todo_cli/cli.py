"""Command-line interface for the todo manager."""

from __future__ import annotations

import argparse
from pathlib import Path

from .models import Task
from .storage import TaskStore

DEFAULT_DATA_FILE = "todo.json"


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser and all subcommands."""

    parser = argparse.ArgumentParser(
        prog="todo",
        description="A minimal local command-line todo manager.",
    )
    parser.add_argument(
        "--data",
        default=DEFAULT_DATA_FILE,
        help="Path to the JSON data file (default: todo.json).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a new task.")
    add_parser.add_argument("title", help="Title of the new task.")

    subparsers.add_parser("list", help="List all tasks.")

    done_parser = subparsers.add_parser("done", help="Mark a task as completed.")
    done_parser.add_argument("task_id", type=int, help="ID of the task to complete.")

    delete_parser = subparsers.add_parser("delete", help="Delete a task.")
    delete_parser.add_argument("task_id", type=int, help="ID of the task to delete.")

    return parser


def _find_task(tasks: list[Task], task_id: int) -> Task | None:
    """Return the task with ``task_id``, or ``None`` when absent."""

    for task in tasks:
        if task.id == task_id:
            return task
    return None


def main(argv: list[str] | None = None) -> int:
    """Run one command and return a process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)
    store = TaskStore(Path(args.data))
    tasks = store.load()

    if args.command == "add":
        next_id = max((task.id for task in tasks), default=0) + 1
        task = Task(id=next_id, title=args.title)
        tasks.append(task)
        store.save(tasks)
        print(f"Added task {task.id}: {task.title}")
        return 0

    if args.command == "list":
        if not tasks:
            print("No tasks yet.")
            return 0
        for task in tasks:
            marker = "x" if task.done else " "
            print(f"[{marker}] {task.id}. {task.title}")
        return 0

    task = _find_task(tasks, args.task_id)
    if task is None:
        print(f"Task {args.task_id} not found.")
        return 1

    if args.command == "done":
        task.done = True
        store.save(tasks)
        print(f"Completed task {task.id}: {task.title}")
        return 0

    if args.command == "delete":
        tasks.remove(task)
        store.save(tasks)
        print(f"Deleted task {task.id}: {task.title}")
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2
