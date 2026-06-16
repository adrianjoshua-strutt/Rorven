from __future__ import annotations

import unittest

from rorven.application.dispatching import parse_orchestrator_decision


class OrchestratorDispatchTests(unittest.TestCase):
    def test_parses_direct_answer(self) -> None:
        decision = parse_orchestrator_decision(
            '{"action":"answer","content":"Use the worker command."}'
        )

        self.assertFalse(decision.dispatches_children)
        self.assertEqual("Use the worker command.", decision.answer)

    def test_parses_child_dispatches(self) -> None:
        decision = parse_orchestrator_decision(
            """
            {
              "action": "dispatch",
              "subagents": [
                {"name": "reviewer", "task": "Find risks."},
                {"name": "implementer", "task": "Plan the code changes."}
              ]
            }
            """
        )

        self.assertTrue(decision.dispatches_children)
        self.assertEqual(["reviewer", "implementer"], [item.definition.name for item in decision.child_agents])
        self.assertEqual(["balanced", "reasoning"], [item.definition.model_profile.value for item in decision.child_agents])

    def test_rejects_unknown_subagent(self) -> None:
        with self.assertRaises(ValueError):
            parse_orchestrator_decision(
                '{"action":"dispatch","subagents":[{"name":"filesystem","task":"Edit files."}]}'
            )


if __name__ == "__main__":
    unittest.main()
