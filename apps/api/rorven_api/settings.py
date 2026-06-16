"""Settings metadata for the local API adapter."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from rorven.adapters.model import MODEL_PROFILE_NAMES, OPENROUTER_KEY_ENV, load_model_profile_config


def read_settings(data_dir: Path) -> dict[str, Any]:
    model_config = load_model_profile_config()
    api_key_configured = bool(os.environ.get(OPENROUTER_KEY_ENV))
    gateway_mode = os.environ.get("RORVEN_MODEL_GATEWAY", "auto").strip().lower()
    active_model_gateway = "openrouter" if api_key_configured and gateway_mode != "local" else "local"

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
                "model_id": model_config.profile_name(name).model_id or "provider-default",
                "model_id_configured": model_config.profile_name(name).model_id is not None,
                "request_timeout_seconds": model_config.profile_name(name).request_timeout_seconds,
                "source": str(model_config.source),
            }
            for name in MODEL_PROFILE_NAMES
        ],
        "runtime": {
            "active_runtime_adapter": "local-deterministic",
            "planned_runtime_adapter": "langgraph",
            "active_model_gateway": active_model_gateway,
            "system_of_record": "local-file-walking-skeleton",
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
