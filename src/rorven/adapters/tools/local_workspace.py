"""Local read-only workspace tool broker."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rorven.application.tools import (
    MAX_LIST_ENTRIES,
    MAX_READ_BYTES,
    ToolExecutionResult,
    ToolRequest,
)
from rorven.domain import AgentRun, Project


SKIPPED_DIRS = {".git", ".venv", "node_modules", "dist", "__pycache__", "test-output"}
SENSITIVE_MARKERS = (
    ".env",
    ".git",
    "secret",
    "secrets",
    "token",
    "tokens",
    "credential",
    "credentials",
    "private_key",
    "id_rsa",
    ".pem",
    ".pfx",
    ".p12",
)


class LocalWorkspaceToolBroker:
    def execute(
        self,
        project: Project,
        agent_run: AgentRun,
        request: ToolRequest,
    ) -> ToolExecutionResult:
        if request.name == "workspace.list_files":
            return self._list_files(project, request)
        if request.name == "workspace.read_text_file":
            return self._read_text_file(project, request)
        raise ValueError(f"unsupported tool: {request.name}")

    def _list_files(self, project: Project, request: ToolRequest) -> ToolExecutionResult:
        root = _workspace_root(project)
        target = _resolve_inside(root, _input_path(request))
        if _is_sensitive(target.relative_to(root)):
            raise ValueError("path is blocked by secret-safety policy")
        if not target.exists():
            raise FileNotFoundError(f"path not found: {_display_path(root, target)}")
        if not target.is_dir():
            raise ValueError("workspace.list_files requires a directory path")
        max_entries = _bounded_int(request.input.get("max_entries"), MAX_LIST_ENTRIES)
        entries: list[dict[str, Any]] = []
        for path in sorted(target.rglob("*")):
            relative = path.relative_to(root)
            if _skip_path(relative) or _is_sensitive(relative):
                continue
            entries.append(
                {
                    "path": relative.as_posix(),
                    "type": "dir" if path.is_dir() else "file",
                    "bytes": path.stat().st_size if path.is_file() else None,
                }
            )
            if len(entries) >= max_entries:
                break
        content = json.dumps({"entries": entries, "truncated": len(entries) >= max_entries}, indent=2)
        return ToolExecutionResult(
            content=content,
            metadata={"tool": request.name, "path": _display_path(root, target), "entries": len(entries)},
        )

    def _read_text_file(self, project: Project, request: ToolRequest) -> ToolExecutionResult:
        root = _workspace_root(project)
        target = _resolve_inside(root, _input_path(request))
        relative = target.relative_to(root)
        if _is_sensitive(relative):
            raise ValueError("path is blocked by secret-safety policy")
        if not target.exists():
            raise FileNotFoundError(f"path not found: {relative.as_posix()}")
        if not target.is_file():
            raise ValueError("workspace.read_text_file requires a file path")
        max_bytes = _bounded_int(request.input.get("max_bytes"), MAX_READ_BYTES)
        data = target.read_bytes()
        truncated = len(data) > max_bytes
        content = data[:max_bytes].decode("utf-8", errors="replace")
        return ToolExecutionResult(
            content=content,
            metadata={
                "tool": request.name,
                "path": relative.as_posix(),
                "bytes_read": min(len(data), max_bytes),
                "bytes_total": len(data),
                "truncated": truncated,
            },
        )


def _workspace_root(project: Project) -> Path:
    root = Path(project.workspace.workspace_root).resolve()
    if not root.exists():
        raise FileNotFoundError(f"workspace root not found: {root}")
    if not root.is_dir():
        raise ValueError(f"workspace root is not a directory: {root}")
    return root


def _input_path(request: ToolRequest) -> str:
    value = request.input.get("path", ".")
    if not isinstance(value, str) or not value.strip():
        return "."
    return value


def _resolve_inside(root: Path, requested: str) -> Path:
    target = (root / requested).resolve()
    if target != root and not target.is_relative_to(root):
        raise ValueError("tool path must stay inside the project workspace")
    return target


def _bounded_int(value: object, fallback: int) -> int:
    if isinstance(value, int) and value > 0:
        return min(value, fallback)
    return fallback


def _skip_path(path: Path) -> bool:
    return any(part in SKIPPED_DIRS for part in path.parts)


def _is_sensitive(path: Path) -> bool:
    return any(
        any(marker in part.lower() for marker in SENSITIVE_MARKERS)
        for part in path.parts
    )


def _display_path(root: Path, target: Path) -> str:
    return "." if target == root else target.relative_to(root).as_posix()
