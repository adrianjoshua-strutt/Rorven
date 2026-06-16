from __future__ import annotations

import os
from pathlib import Path
import unittest

from rorven.composition import _default_data_dir


class CompositionTests(unittest.TestCase):
    def test_default_data_dir_is_repo_local(self) -> None:
        previous = os.environ.pop("RORVEN_DATA_DIR", None)
        self.addCleanup(_restore_env, "RORVEN_DATA_DIR", previous)
        self.assertEqual(Path(".rorven").resolve(), _default_data_dir())


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


if __name__ == "__main__":
    unittest.main()
