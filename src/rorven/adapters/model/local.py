"""Local model gateway used when no external credential is configured."""

from __future__ import annotations

from rorven.application.modeling import ModelRequest, ModelResponse


class LocalModelGateway:
    provider = "local"

    def complete(self, request: ModelRequest) -> ModelResponse:
        user_message = next(
            (message.content for message in reversed(request.messages) if message.role == "user"),
            "",
        )
        return ModelResponse(
            content=(
                "Local model gateway is active because no OpenRouter API key is configured.\n\n"
                "The durable worker path ran, persisted this artifact, and received the "
                f"following task input:\n\n{user_message}"
            ),
            provider=self.provider,
            model="local-deterministic",
            usage={},
        )
