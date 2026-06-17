"""Settings metadata for the local API adapter."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from rorven.adapters.model import MODEL_PROFILE_NAMES, OPENROUTER_KEY_ENV, load_model_profile_config


def read_settings(data_dir: Path) -> dict[str, Any]:
    persisted_profile_ids = _read_persisted_model_profile_ids(data_dir)
    model_config = load_model_profile_config(profile_overrides=persisted_profile_ids)
    api_key_configured = bool(os.environ.get(OPENROUTER_KEY_ENV))
    active_model_gateway = "openrouter" if api_key_configured else "unconfigured"

    return {
        "credentials": [
            {
                "id": "model-provider-api-key",
                "label": "Model provider API key",
                "adapter": model_config.provider_adapter,
                "environment_variable": OPENROUTER_KEY_ENV,
                "configured": api_key_configured,
                "raw_value_visible": False,
                "notes": "Stored outside Rorven state; agents only receive brokered tool authority.",
            }
        ],
        "model_profiles": [
            {
                "name": name,
                "adapter": model_config.provider_adapter,
                "model_id": model_config.profile_name(name).model_id,
                "model_id_configured": model_config.profile_name(name).model_id is not None,
                "request_timeout_seconds": model_config.profile_name(name).request_timeout_seconds,
                "source": "state.json" if name in persisted_profile_ids else str(model_config.source),
            }
            for name in MODEL_PROFILE_NAMES
        ],
        "runtime": {
            "active_runtime_adapter": "langgraph",
            "planned_runtime_adapter": "langgraph",
            "active_model_gateway": active_model_gateway,
            "system_of_record": "local-file-json",
            "planned_system_of_record": "postgresql",
            "data_dir": str(data_dir),
        },
        "policy": {
            "destructive_actions": "approval-required",
            "secret_exposure": "presence-only",
            "default_tool_access": "deny",
        },
        "project_defaults": {
            "workspace_root_source": "user-selected",
            "memory_backend": "deferred",
            "sandbox": "deferred",
        },
    }


def _read_persisted_model_profile_ids(data_dir: Path) -> dict[str, str]:
    state_path = data_dir / "state.json"
    if not state_path.exists():
        return {}

    try:
        import json

        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    settings = state.get("settings")
    if not isinstance(settings, dict):
        return {}
    profiles = settings.get("model_profiles")
    if not isinstance(profiles, dict):
        return {}

    result: dict[str, str] = {}
    for name in MODEL_PROFILE_NAMES:
        value = profiles.get(name)
        if isinstance(value, str) and value.strip() and value.strip() != "replace-me":
            result[name] = value.strip()
    return result
