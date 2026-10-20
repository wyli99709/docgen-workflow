"""Read-only, sandboxed access to the input project."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

ALLOWED_SUFFIXES = {".py", ".toml", ".txt", ".md", ".cfg", ".ini"}
IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    ".idea",
    ".vscode",
}
MAX_FILES = 50
MAX_FILE_BYTES = 200_000
MAX_READ_LINES = 250
MAX_SEARCH_HITS = 40


class ToolError(RuntimeError):
    """A tool call that cannot be satisfied within the read-only sandbox."""


class InputSandbox:
    """Expose only files under ``root`` and never write to them."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise ToolError(f"输入目录不存在: {self.root}")
        self._manifest: list[dict[str, Any]] | None = None
        self._line_cache: dict[str, list[str]] = {}

    def scan(self) -> list[dict[str, Any]]:
        """Return a deterministic manifest of supported files."""

        if self._manifest is not None:
            return self._manifest

        files: list[dict[str, Any]] = []
        for path in sorted(self.root.rglob("*")):
            try:
                relative = path.relative_to(self.root)
            except ValueError:
                continue
            if any(part in IGNORED_DIRS for part in relative.parts):
                continue
            if not path.is_file() or path.suffix.lower() not in ALLOWED_SUFFIXES:
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > MAX_FILE_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            files.append(
                {
                    "path": relative.as_posix(),
                    "size_bytes": size,
                    "lines": len(text.splitlines()),
                    "sha256": hashlib.sha256(
                        text.encode("utf-8", errors="replace")
                    ).hexdigest(),
                }
            )

        if len(files) > MAX_FILES:
            raise ToolError(
                f"输入包含 {len(files)} 个受支持文件，超过上限 {MAX_FILES}；"
                "请缩小演示项目范围。"
            )
        if not files:
            raise ToolError("输入目录中没有可读取的源码或配置文件。")

        self._manifest = files
        return files

    def source_digest(self) -> str:
        """Hash the manifest so a run is tied to an exact input snapshot."""

        digest = hashlib.sha256()
        for entry in self.scan():
            digest.update(entry["path"].encode("utf-8"))
            digest.update(entry["sha256"].encode("ascii"))
        return digest.hexdigest()

    def _resolve(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ToolError("path 必须是非空字符串")
        candidate = Path(relative_path)
        resolved = (
            candidate.resolve()
            if candidate.is_absolute()
            else (self.root / candidate).resolve()
        )
        if resolved != self.root and self.root not in resolved.parents:
            raise ToolError(f"拒绝访问输入目录之外的路径: {relative_path}")
        if not resolved.is_file():
            raise ToolError(f"文件不存在: {relative_path}")
        if resolved.suffix.lower() not in ALLOWED_SUFFIXES:
            raise ToolError(f"不支持的文件类型: {relative_path}")
        if resolved.stat().st_size > MAX_FILE_BYTES:
            raise ToolError(f"文件过大，拒绝读取: {relative_path}")
        return resolved

    def read_text(self, relative_path: str) -> str:
        """Read a whole file for internal indexing (never exposed to tools)."""

        return self._resolve(relative_path).read_text(encoding="utf-8", errors="replace")

    def _lines(self, relative_path: str) -> list[str]:
        if relative_path not in self._line_cache:
            self._line_cache[relative_path] = self.read_text(relative_path).splitlines()
        return self._line_cache[relative_path]

    def line_count(self, relative_path: str) -> int:
        """Return the number of lines in a file inside the sandbox."""

        return len(self._lines(Path(relative_path).as_posix()))

    # ---- tools exposed to agents -------------------------------------

    def list_files(self) -> dict[str, Any]:
        """List supported project files with size and line count."""

        return {
            "files": [
                {
                    "path": entry["path"],
                    "size_bytes": entry["size_bytes"],
                    "lines": entry["lines"],
                }
                for entry in self.scan()
            ]
        }

    def read_file(
        self,
        path: str,
        start: int | None = None,
        end: int | None = None,
    ) -> dict[str, Any]:
        """Read a line range (1-based, inclusive) from one project file."""

        lines = self._lines(Path(path).as_posix())
        total = len(lines)
        if total == 0:
            return {"path": path, "start": 0, "end": 0, "total_lines": 0, "text": ""}

        first = 1 if start is None else int(start)
        if first < 1:
            raise ToolError("start 必须 >= 1")
        if first > total:
            raise ToolError(f"start={first} 超出文件行数 {total}")
        last = first + MAX_READ_LINES - 1 if end is None else int(end)
        if last < first:
            raise ToolError("end 必须 >= start")
        last = min(last, total)
        if last - first + 1 > MAX_READ_LINES:
            last = first + MAX_READ_LINES - 1
        return {
            "path": path,
            "start": first,
            "end": last,
            "total_lines": total,
            "truncated": last < total,
            "numbered_text": "\n".join(
                f"{number:4d} | {lines[number - 1]}"
                for number in range(first, last + 1)
            ),
            "text": "\n".join(lines[first - 1 : last]),
        }

    def search(self, query: str, regex: bool = False) -> dict[str, Any]:
        """Search supported files for a literal string or regular expression."""

        if not isinstance(query, str) or not query.strip():
            raise ToolError("query 必须是非空字符串")
        if len(query) > 200:
            raise ToolError("query 过长（上限 200 字符）")
        try:
            pattern = re.compile(query if regex else re.escape(query), re.IGNORECASE)
        except re.error as exc:
            raise ToolError(f"正则表达式无效: {exc}") from exc

        matches: list[dict[str, Any]] = []
        for entry in self.scan():
            path = entry["path"]
            for number, line in enumerate(self._lines(path), start=1):
                if pattern.search(line):
                    matches.append(
                        {
                            "file": path,
                            "line": number,
                            "text": line.strip()[:300],
                        }
                    )
                    if len(matches) >= MAX_SEARCH_HITS:
                        return {
                            "query": query,
                            "matches": matches,
                            "truncated": True,
                        }
        return {"query": query, "matches": matches, "truncated": False}

    def check_lines(self, path: str, start: int, end: int) -> str | None:
        """Return an error message when an evidence range is invalid."""

        try:
            total = self.line_count(path)
        except ToolError as exc:
            return str(exc)
        if not isinstance(start, int) or not isinstance(end, int):
            return "行号必须是整数"
        if start < 1 or end < start:
            return f"行号范围无效: {start}-{end}"
        if end > total:
            return f"{path} 只有 {total} 行，证据引用了 {end} 行"
        return None
