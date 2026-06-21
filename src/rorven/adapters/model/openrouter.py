"""OpenRouter model gateway adapter."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from rorven.adapters.model.profiles import ModelProfileConfig
from rorven.application.modeling import ModelRequest, ModelResponse


OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


class OpenRouterModelGateway:
    provider = "openrouter"

    def __init__(
        self,
        api_key: str,
        profiles: ModelProfileConfig,
        endpoint: str = OPENROUTER_CHAT_COMPLETIONS_URL,
    ) -> None:
        if not api_key.strip():
            raise ValueError("OpenRouter API key is required")
        self._api_key = api_key
        self._profiles = profiles
        self._endpoint = endpoint

    def complete(self, request: ModelRequest) -> ModelResponse:
        profile = self._profiles.profile(request.profile)
        payload: dict[str, Any] = {
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "temperature": request.temperature,
            "max_completion_tokens": request.max_output_tokens,
            "session_id": request.session_id,
            "metadata": {
                "app": "rorven",
                "model_profile": request.profile.value,
            },
        }
        if profile.model_id:
            payload["model"] = profile.model_id
        if profile.fallback_model_ids:
            payload["models"] = [
                *([profile.model_id] if profile.model_id else []),
                *profile.fallback_model_ids,
            ]

        response = self._post_json(payload, timeout=profile.request_timeout_seconds)
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("OpenRouter response did not include choices")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise RuntimeError("OpenRouter response did not include a message")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("OpenRouter response did not include text content")
        usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
        model = response.get("model") if isinstance(response.get("model"), str) else profile.model_id
        return ModelResponse(content=content, provider=self.provider, model=model, usage=usage)

    def _post_json(self, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            self._endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "X-OpenRouter-Metadata": "enabled",
                "X-Title": "Rorven",
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(_sanitize_error(f"OpenRouter HTTP {exc.code}: {detail}", self._api_key)) from exc
        except URLError as exc:
            raise RuntimeError(_sanitize_error(f"OpenRouter request failed: {exc}", self._api_key)) from exc

        decoded = json.loads(raw)
        if not isinstance(decoded, dict):
            raise RuntimeError("OpenRouter response was not a JSON object")
        return decoded


def _sanitize_error(message: str, api_key: str) -> str:
    return message.replace(api_key, "[redacted]")


def list_openrouter_models(api_key: str | None = None, timeout: int = 20) -> list[dict[str, Any]]:
    headers = {
        "Content-Type": "application/json",
        "X-Title": "Rorven",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(OPENROUTER_MODELS_URL, method="GET", headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        safe_detail = _sanitize_error(detail, api_key) if api_key else detail
        raise RuntimeError(f"OpenRouter models HTTP {exc.code}: {safe_detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"OpenRouter models request failed: {exc}") from exc

    decoded = json.loads(raw)
    data = decoded.get("data") if isinstance(decoded, dict) else None
    if not isinstance(data, list):
        raise RuntimeError("OpenRouter models response did not include data")
    models: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        model_id = item.get("id")
        if not isinstance(model_id, str) or not model_id.strip():
            continue
        models.append(
            {
                "id": model_id,
                "name": item.get("name") if isinstance(item.get("name"), str) else model_id,
                "context_length": item.get("context_length") if isinstance(item.get("context_length"), int) else None,
            }
        )
    return models
