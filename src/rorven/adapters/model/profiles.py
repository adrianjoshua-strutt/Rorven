"""Model profile configuration for model-provider adapters."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from rorven.domain import ModelProfile


MODEL_PROFILE_NAMES = ("utility", "balanced", "reasoning", "frontier")
OPENROUTER_KEY_ENV = "RORVEN_OPENROUTER_API_KEY"
MODEL_PROFILE_ENV_PREFIX = "RORVEN_MODEL_PROFILE_"


@dataclass(frozen=True, slots=True)
class ProfileConfig:
    model_id: str | None
    fallback_model_ids: tuple[str, ...]
    request_timeout_seconds: int


@dataclass(frozen=True, slots=True)
class ModelProfileConfig:
    provider_adapter: str
    profiles: dict[ModelProfile, ProfileConfig]
    source: Path

    def profile(self, profile: ModelProfile) -> ProfileConfig:
        return self.profiles[profile]

    def profile_name(self, name: str) -> ProfileConfig:
        return self.profile(ModelProfile(name))


def load_model_profile_config(
    path: Path | None = None,
    profile_overrides: dict[str, str] | None = None,
) -> ModelProfileConfig:
    configured_path = Path(
        os.environ.get("RORVEN_MODEL_PROFILES_PATH", "config/model-profiles/profiles.example.yaml")
    )
    source = path or configured_path
    raw_config = _read_model_config(source)
    profiles = {
        ModelProfile(name): ProfileConfig(
            model_id=_configured_model_id((profile_overrides or {}).get(name))
            or _configured_model_id(raw_config["profiles"].get(name, {}).get("model_id")),
            fallback_model_ids=_configured_fallbacks(
                raw_config["profiles"].get(name, {}).get("fallback_model_ids")
            ),
            request_timeout_seconds=int(
                raw_config["profiles"].get(name, {}).get("request_timeout_seconds", 120)
            ),
        )
        for name in MODEL_PROFILE_NAMES
    }
    return ModelProfileConfig(
        provider_adapter=str(raw_config["provider_adapter"]),
        profiles=profiles,
        source=source,
    )


def _read_model_config(path: Path) -> dict[str, object]:
    config: dict[str, object] = {
        "provider_adapter": "openrouter",
        "profiles": {
            name: {
                "model_id": None,
                "fallback_model_ids": [],
                "request_timeout_seconds": 120,
            }
            for name in MODEL_PROFILE_NAMES
        },
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
            profiles = config["profiles"]
            assert isinstance(profiles, dict)
            profile = profiles.setdefault(current_profile, {})
            assert isinstance(profile, dict)
            profile[key.strip()] = _coerce_scalar(value.strip())
    return config


def _coerce_scalar(value: str) -> str | int | list[str] | None:
    if value in {"", "null", "~"}:
        return None
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip('"').strip("'") for item in inner.split(",")]
    if value.isdigit():
        return int(value)
    return value.strip('"').strip("'")


def _env_model_id(name: str) -> str | None:
    value = os.environ.get(f"{MODEL_PROFILE_ENV_PREFIX}{name.upper()}")
    return _configured_model_id(value)


def _configured_model_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped if stripped and stripped != "replace-me" else None


def _configured_fallbacks(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(item for item in value if isinstance(item, str) and item.strip())
    return ()
