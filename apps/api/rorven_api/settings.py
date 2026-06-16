"""Settings metadata for the local API adapter."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


MODEL_PROFILE_NAMES = ("utility", "balanced", "reasoning", "frontier")
OPENROUTER_KEY_ENV = "RORVEN_OPENROUTER_API_KEY"


def read_settings(data_dir: Path) -> dict[str, Any]:
    model_config_path = Path(
        os.environ.get("RORVEN_MODEL_PROFILES_PATH", "config/model-profiles/profiles.example.yaml")
    )
    model_config = _read_model_config(model_config_path)
    api_key_configured = bool(os.environ.get(OPENROUTER_KEY_ENV))

    return {
        "credentials": [
            {
                "id": "model-provider-api-key",
                "label": "Model provider API key",
                "adapter": model_config["provider_adapter"],
                "environment_variable": OPENROUTER_KEY_ENV,
                "configured": api_key_configured,
                "raw_value_visible": False,
                "notes": "Stored outside Rorven state; agents only receive brokered tool authority.",
            }
        ],
        "model_profiles": [
            {
                "name": name,
                "adapter": model_config["provider_adapter"],
                "model_id": model_config["profiles"].get(name, {}).get("model_id", "replace-me"),
                "model_id_configured": _is_configured_model_id(
                    model_config["profiles"].get(name, {}).get("model_id")
                ),
                "request_timeout_seconds": model_config["profiles"]
                .get(name, {})
                .get("request_timeout_seconds"),
                "source": str(model_config_path),
            }
            for name in MODEL_PROFILE_NAMES
        ],
        "runtime": {
            "active_runtime_adapter": "local-deterministic",
            "planned_runtime_adapter": "langgraph",
            "system_of_record": "local-file-walking-skeleton",
            "planned_system_of_record": "postgresql",
            "data_dir": str(data_dir),
        },
        "frontend": {
            "framework": "React + Vite",
            "design_system": "custom CSS tokens",
            "icon_system": "lucide-react",
            "needs_design_system_migration": True,
        },
    }


def _read_model_config(path: Path) -> dict[str, Any]:
    config: dict[str, Any] = {
        "provider_adapter": "openrouter",
        "profiles": {name: {"model_id": "replace-me"} for name in MODEL_PROFILE_NAMES},
    }
    if not path.exists():
        return config

    current_profile: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("provider_adapter:"):
            config["provider_adapter"] = stripped.split(":", maxsplit=1)[1].strip()
            continue
        if raw_line.startswith("  ") and not raw_line.startswith("    ") and stripped.endswith(":"):
            candidate = stripped[:-1]
            current_profile = candidate if candidate in MODEL_PROFILE_NAMES else None
            continue
        if current_profile and raw_line.startswith("    ") and ":" in stripped:
            key, value = stripped.split(":", maxsplit=1)
            config["profiles"].setdefault(current_profile, {})[key.strip()] = _coerce_scalar(
                value.strip()
            )
    return config


def _coerce_scalar(value: str) -> str | int | list[str]:
    if value == "[]":
        return []
    if value.isdigit():
        return int(value)
    return value


def _is_configured_model_id(value: object) -> bool:
    return isinstance(value, str) and value.strip() not in {"", "replace-me"}
