"""Provider-neutral model request and response objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from rorven.domain import ModelProfile


ModelRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True, slots=True)
class ModelMessage:
    role: ModelRole
    content: str


@dataclass(frozen=True, slots=True)
class ModelRequest:
    profile: ModelProfile
    messages: tuple[ModelMessage, ...]
    session_id: str
    temperature: float = 0.2
    max_output_tokens: int = 900


@dataclass(frozen=True, slots=True)
class ModelResponse:
    content: str
    provider: str
    model: str | None
    usage: dict[str, Any] = field(default_factory=dict)
