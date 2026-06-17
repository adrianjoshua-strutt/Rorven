"""Local workspace provisioning adapter."""

from __future__ import annotations

from pathlib import Path


class LocalWorkspaceProvisioner:
    def __init__(self, default_base_root: Path | None = None) -> None:
        self._default_base_root = (default_base_root or Path.cwd()).resolve()

    def default_workspace_base_root(self) -> str:
        return str(self._default_base_root)

    def ensure_directory(self, workspace_root: str) -> None:
        Path(workspace_root).resolve().mkdir(parents=True, exist_ok=True)
