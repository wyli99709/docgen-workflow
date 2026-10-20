"""Deterministic AST and metadata indexing for Python projects."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path
from typing import Any

from .fs import InputSandbox


def _literal(node: ast.AST | None) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    return None


def _argument_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _function_info(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    return {
        "name": node.name,
        "lineno": node.lineno,
        "end_lineno": getattr(node, "end_lineno", node.lineno),
        "args": [arg.arg for arg in node.args.args],
        "docstring": ast.get_docstring(node),
    }


def _class_info(node: ast.ClassDef) -> dict[str, Any]:
    return {
        "name": node.name,
        "lineno": node.lineno,
        "end_lineno": getattr(node, "end_lineno", node.lineno),
        "docstring": ast.get_docstring(node),
        "methods": [
            _function_info(child)
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        ],
    }


def _has_main_guard(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
            and any(
                isinstance(comparator, ast.Constant)
                and comparator.value == "__main__"
                for comparator in test.comparators
            )
        ):
            return True
    return False


def _argparse_calls(tree: ast.Module) -> dict[str, Any]:
    options: list[dict[str, Any]] = []
    subcommands: list[dict[str, Any]] = []
    parsers: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _argument_name(node.func)
        if name == "ArgumentParser":
            parsers.append(
                {
                    "lineno": node.lineno,
                    "prog": _literal(next((kw.value for kw in node.keywords if kw.arg == "prog"), None)),
                    "description": _literal(
                        next((kw.value for kw in node.keywords if kw.arg == "description"), None)
                    ),
                }
            )
        elif name == "add_parser":
            if node.args and isinstance(_literal(node.args[0]), str):
                subcommands.append(
                    {
                        "name": _literal(node.args[0]),
                        "lineno": node.lineno,
                        "help": _literal(
                            next((kw.value for kw in node.keywords if kw.arg == "help"), None)
                        ),
                    }
                )
        elif name == "add_argument":
            if not node.args or not isinstance(_literal(node.args[0]), str):
                continue
            option = _literal(node.args[0])
            keywords = {kw.arg: kw.value for kw in node.keywords if kw.arg}
            options.append(
                {
                    "option": option,
                    "lineno": node.lineno,
                    "dest": _literal(keywords.get("dest")),
                    "help": _literal(keywords.get("help")),
                    "default": _literal(keywords.get("default")),
                    "type": _argument_name(keywords.get("type")),
                    "action": _literal(keywords.get("action")),
                }
            )

    return {
        "parsers": parsers,
        "subcommands": subcommands,
        "options": options,
    }


def _summarise_module(tree: ast.Module) -> dict[str, Any]:
    imports: list[dict[str, Any]] = []
    from_imports: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []
    classes: list[dict[str, Any]] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(_function_info(node))
        elif isinstance(node, ast.ClassDef):
            classes.append(_class_info(node))
        elif isinstance(node, ast.Import):
            imports.extend(
                {"module": alias.name, "asname": alias.asname} for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            from_imports.append(
                {
                    "module": node.module or "",
                    "names": [alias.name for alias in node.names],
                    "level": node.level,
                }
            )

    return {
        "docstring": ast.get_docstring(tree),
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "from_imports": from_imports,
        "main_guard": _has_main_guard(tree),
        "argparse": _argparse_calls(tree),
    }


def _parse_pyproject(sandbox: InputSandbox, path: str) -> dict[str, Any] | None:
    try:
        data = tomllib.loads(sandbox.read_text(path))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        return {"path": path, "error": f"无法解析: {exc}"}

    project = data.get("project", {})
    if not isinstance(project, dict):
        project = {}
    keep = (
        "name",
        "version",
        "description",
        "requires-python",
        "dependencies",
        "optional-dependencies",
        "scripts",
    )
    return {
        "path": path,
        "project": {key: project[key] for key in keep if key in project},
        "build_system": data.get("build-system"),
    }


def _parse_requirements(sandbox: InputSandbox, path: str) -> dict[str, Any]:
    dependencies = [
        line.strip()
        for line in sandbox.read_text(path).splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    return {"path": path, "dependencies": dependencies}


def build_ast_index(
    sandbox: InputSandbox,
    manifest: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a compact, model-readable index of structure and CLI metadata."""

    index: dict[str, Any] = {
        "python_files": {},
        "pyproject": None,
        "requirements": None,
    }

    for entry in manifest:
        path = entry["path"]
        suffix = Path(path).suffix.lower()
        if suffix == ".py":
            try:
                tree = ast.parse(sandbox.read_text(path))
            except SyntaxError as exc:
                index["python_files"][path] = {
                    "syntax_error": f"第 {exc.lineno} 行: {exc.msg}"
                }
                continue
            index["python_files"][path] = _summarise_module(tree)
        elif Path(path).name == "pyproject.toml" and index["pyproject"] is None:
            index["pyproject"] = _parse_pyproject(sandbox, path)
        elif Path(path).name == "requirements.txt" and index["requirements"] is None:
            index["requirements"] = _parse_requirements(sandbox, path)

    return index
