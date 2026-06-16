from __future__ import annotations

from collections.abc import Sequence
import unittest

from rorven.adapters.runtime.local import LocalDeterministicRuntime
from rorven.domain import AgentRun, Event, Project, Run, Task, WorkspaceBinding


class CapturingRunRepository:
    def __init__(self) -> None:
        self.run: Run | None = None
        self.parent: AgentRun | None = None
        self.children: list[AgentRun] = []
        self.tasks: list[Task] = []
        self.events: list[Event] = []

    def add_project(self, project: Project, event: Event) -> None:
        raise NotImplementedError

    def add_run(self, run: Run, agent_run: AgentRun, events: Sequence[Event]) -> None:
        self.run = run
        self.parent = agent_run
        self.events.extend(events)

    def add_child_runs(
        self,
        parent_agent_run: AgentRun,
        child_agent_runs: Sequence[AgentRun],
        tasks: Sequence[Task],
        events: Sequence[Event],
    ) -> None:
        self.parent = parent_agent_run
        self.children.extend(child_agent_runs)
        self.tasks.extend(tasks)
        self.events.extend(events)

    def get_run_tree(self, project_id: str, run_id: str) -> Sequence[AgentRun]:
        if self.parent is None:
            return []
        return [self.parent, *self.children]


class LocalRuntimeContractTests(unittest.TestCase):
    def test_runtime_persists_parent_then_two_child_runs_with_parent_links(self) -> None:
        repository = CapturingRunRepository()
        runtime = LocalDeterministicRuntime(repository)
        project = Project.create(
            "Example",
            WorkspaceBinding("D:/workspaces", "D:/workspaces/example"),
        )

        run = runtime.start_parent_run(project, "Build a serious spine")
        self.assertIsNotNone(repository.parent)
        parent = repository.parent
        assert parent is not None

        children = runtime.plan_child_runs(run, parent)

        self.assertEqual(2, len(children))
        self.assertEqual(2, len(repository.tasks))
        self.assertEqual({parent.id}, {child.parent_agent_run_id for child in children})
        self.assertEqual({"reviewer", "implementer"}, {child.definition.name for child in children})
        self.assertEqual({"balanced", "reasoning"}, {child.definition.model_profile.value for child in children})


if __name__ == "__main__":
    unittest.main()

