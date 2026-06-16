from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_IMPORTS = {
    "fastapi",
    "langchain",
    "langgraph",
    "openai",
    "openrouter",
    "psycopg",
    "psycopg2",
    "sqlalchemy",
    "docker",
    "react",
}


def imports_in(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", maxsplit=1)[0])
    return imports


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_domain_and_application_do_not_import_providers_or_frameworks(self) -> None:
        protected_roots = [
            ROOT / "src" / "rorven" / "domain",
            ROOT / "src" / "rorven" / "application",
        ]
        violations: list[str] = []

        for root in protected_roots:
            for path in root.rglob("*.py"):
                forbidden = imports_in(path) & FORBIDDEN_IMPORTS
                if forbidden:
                    violations.append(f"{path.relative_to(ROOT)} imports {sorted(forbidden)}")

        self.assertEqual([], violations)

    def test_domain_and_application_do_not_branch_on_historical_schema(self) -> None:
        protected_roots = [
            ROOT / "src" / "rorven" / "domain",
            ROOT / "src" / "rorven" / "application",
        ]
        banned_terms = ["schema_version", "legacy", "old_schema", "previous_schema"]
        violations: list[str] = []

        for root in protected_roots:
            for path in root.rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                found = [term for term in banned_terms if term in text]
                if found:
                    violations.append(f"{path.relative_to(ROOT)} contains {found}")

        self.assertEqual([], violations)

