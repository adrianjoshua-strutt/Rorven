from __future__ import annotations

import importlib
import os
from pathlib import Path
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


class ApiSettingsTests(unittest.TestCase):
    def test_settings_report_key_presence_without_raw_secret(self) -> None:
        data_dir = Path("test-output") / "tests" / f"settings-{uuid4()}"
        data_dir.mkdir(parents=True, exist_ok=True)
        previous_data_dir = os.environ.get("RORVEN_DATA_DIR")
        previous_key = os.environ.get("RORVEN_OPENROUTER_API_KEY")
        self.addCleanup(_restore_env, "RORVEN_DATA_DIR", previous_data_dir)
        self.addCleanup(_restore_env, "RORVEN_OPENROUTER_API_KEY", previous_key)
        os.environ["RORVEN_DATA_DIR"] = str(data_dir.resolve())
        os.environ["RORVEN_OPENROUTER_API_KEY"] = "test-secret-that-must-not-leak"

        module = importlib.import_module("rorven_api.main")
        client = TestClient(module.create_app())

        response = client.get("/settings")
        self.assertEqual(200, response.status_code)
        payload_text = response.text
        payload = response.json()["settings"]

        self.assertNotIn("test-secret-that-must-not-leak", payload_text)
        self.assertEqual("langgraph", payload["runtime"]["active_runtime_adapter"])
        self.assertTrue(payload["credentials"][0]["configured"])
        self.assertFalse(payload["credentials"][0]["raw_value_visible"])
        self.assertEqual("openrouter", payload["runtime"]["active_model_gateway"])
        self.assertEqual(
            {"utility", "balanced", "reasoning", "frontier"},
            {profile["name"] for profile in payload["model_profiles"]},
        )


if __name__ == "__main__":
    unittest.main()
