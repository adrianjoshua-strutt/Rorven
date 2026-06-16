from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch
import unittest

from rorven.adapters.model.openrouter import OpenRouterModelGateway
from rorven.adapters.model.profiles import ModelProfileConfig, ProfileConfig
from rorven.application.modeling import ModelMessage, ModelRequest
from rorven.domain import ModelProfile


class _FakeHttpResponse:
    def __enter__(self) -> _FakeHttpResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(
            {
                "choices": [{"message": {"role": "assistant", "content": "real model output"}}],
                "model": "openrouter/test-model",
                "usage": {"total_tokens": 42},
            }
        ).encode("utf-8")


class OpenRouterModelGatewayTests(unittest.TestCase):
    def test_chat_completion_request_uses_profile_and_redacts_secret_from_response(self) -> None:
        profiles = ModelProfileConfig(
            provider_adapter="openrouter",
            profiles={
                ModelProfile.UTILITY: ProfileConfig("openrouter/test-model", (), 30),
                ModelProfile.BALANCED: ProfileConfig(None, (), 30),
                ModelProfile.REASONING: ProfileConfig(None, (), 30),
                ModelProfile.FRONTIER: ProfileConfig(None, (), 30),
            },
            source=Path("test-profiles.yaml"),
        )
        captured: dict[str, object] = {}

        def fake_urlopen(request: object, timeout: int) -> _FakeHttpResponse:
            captured["timeout"] = timeout
            captured["request"] = request
            return _FakeHttpResponse()

        gateway = OpenRouterModelGateway(api_key="secret-key", profiles=profiles)
        with patch("rorven.adapters.model.openrouter.urlopen", fake_urlopen):
            response = gateway.complete(
                ModelRequest(
                    profile=ModelProfile.UTILITY,
                    session_id="run:agent",
                    messages=(ModelMessage("user", "hello"),),
                )
            )

        request = captured["request"]
        payload = json.loads(request.data.decode("utf-8"))

        self.assertEqual("real model output", response.content)
        self.assertEqual("openrouter/test-model", response.model)
        self.assertEqual(42, response.usage["total_tokens"])
        self.assertEqual("openrouter/test-model", payload["model"])
        self.assertEqual("run:agent", payload["session_id"])
        self.assertEqual(30, captured["timeout"])
        self.assertNotIn("secret-key", response.content)


if __name__ == "__main__":
    unittest.main()
