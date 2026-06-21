from __future__ import annotations

import json
from pathlib import Path
import unittest
from uuid import uuid4

from rorven.adapters.model import DEFAULT_MODEL_IDS
from rorven.adapters.persistence import LocalFilePlatformStore
from rorven.adapters.runtime.langgraph import LangGraphAgentRuntime
from rorven.adapters.tools import LocalWorkspaceToolBroker
from rorven.application.modeling import ModelRequest, ModelResponse
from rorven.application.services import ProjectService, WorkerService
from rorven.application.tools import WorkspaceReadPolicy


class TestModelGateway:
    def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            content='{"action":"answer","content":"test model result"}',
            provider="test",
            model="test/model",
            usage={"total_tokens": 1},
        )


class ScriptedModelGateway:
    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self.requests: list[ModelRequest] = []

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        try:
            content = self._responses.pop(0)
        except IndexError as exc:
            raise AssertionError("unexpected model request") from exc
        return ModelResponse(
            content=content,
            provider="test",
            model="test/model",
            usage={"total_tokens": 1},
        )


class LocalFileStoreTests(unittest.TestCase):
    def test_project_run_and_worker_state_survive_store_reopen(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-{uuid4()}"
        root.mkdir(parents=True, exist_ok=True)
        store = LocalFilePlatformStore(root)
        projects = ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=LangGraphAgentRuntime(store),
            artifacts=store,
            approvals=store,
            conversations=store,
        )
        worker = WorkerService(
            runs=store,
            tasks=store,
            artifacts=store,
            events=store,
            model_gateway=TestModelGateway(),
            approvals=store,
            conversations=store,
        )

        project = projects.create_project("Example", "D:/workspaces", "D:/workspaces/example")
        run_state = projects.submit_task(project.id, "Build backend and frontend")
        worker.work_once("test-worker")

        reopened = LocalFilePlatformStore(root)
        reopened_projects = ProjectService(
            runs=reopened,
            events=reopened,
            tasks=reopened,
            runtime=LangGraphAgentRuntime(reopened),
            artifacts=reopened,
            approvals=reopened,
            conversations=reopened,
        )
        reopened_state = reopened_projects.get_run_state(project.id, run_state.run.id)

        self.assertEqual("completed", reopened_state.run.status.value)
        self.assertEqual(1, len(reopened_state.agent_runs))
        self.assertEqual({"completed"}, {item.status.value for item in reopened_state.tasks})
        self.assertEqual(1, len(reopened_state.artifacts))
        self.assertEqual(
            ["You", "Project orchestrator"],
            [entry.title for entry in reopened_state.conversation_entries],
        )
        self.assertTrue((root / "state.json").exists())

    def test_worker_dispatches_child_agents_and_joins_results(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-dispatch-{uuid4()}"
        root.mkdir(parents=True, exist_ok=True)
        store = LocalFilePlatformStore(root)
        projects = ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=LangGraphAgentRuntime(store),
            artifacts=store,
            approvals=store,
            conversations=store,
        )
        gateway = ScriptedModelGateway(
            [
                (
                    '{"action":"dispatch","subagents":['
                    '{"name":"reviewer","task":"Review the request for risks."},'
                    '{"name":"implementer","task":"Plan the implementation."}'
                    "]} "
                ),
                "reviewer result",
                "implementer result",
                "summary result",
            ]
        )
        worker = WorkerService(
            runs=store,
            tasks=store,
            artifacts=store,
            events=store,
            model_gateway=gateway,
            approvals=store,
            conversations=store,
        )

        project = projects.create_project("Example", "D:/workspaces", "D:/workspaces/example")
        run_state = projects.submit_task(project.id, "Build backend and frontend")

        self.assertEqual(1, len(worker.work_once("test-worker", limit=1)))
        waiting_state = projects.get_run_state(project.id, run_state.run.id)
        self.assertEqual("waiting", waiting_state.run.status.value)
        self.assertEqual(3, len(waiting_state.agent_runs))
        self.assertEqual(3, len(waiting_state.tasks))
        self.assertEqual(
            ["orchestrator", "reviewer", "implementer"],
            [agent.definition.name for agent in waiting_state.agent_runs],
        )

        self.assertEqual(2, len(worker.work_once("test-worker", limit=2)))
        finished_state = projects.get_run_state(project.id, run_state.run.id)
        self.assertEqual("completed", finished_state.run.status.value)
        self.assertEqual({"completed"}, {task.status.value for task in finished_state.tasks})
        self.assertEqual({"completed"}, {agent.status.value for agent in finished_state.agent_runs})
        artifact_text = "\n".join(finished_state.artifact_contents.values())
        self.assertIn("Review the request for risks.", artifact_text)
        self.assertIn("reviewer result", artifact_text)
        self.assertIn("implementer result", artifact_text)
        self.assertIn("summary result", artifact_text)
        transcript = "\n".join(entry.body for entry in finished_state.conversation_entries)
        self.assertIn("Build backend and frontend", transcript)
        self.assertIn("Review the request for risks.", transcript)
        self.assertIn("reviewer result", transcript)
        self.assertIn("implementer result", transcript)

    def test_malformed_orchestrator_dispatch_fails_run(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-dispatch-fail-{uuid4()}"
        root.mkdir(parents=True, exist_ok=True)
        store = LocalFilePlatformStore(root)
        projects = ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=LangGraphAgentRuntime(store),
            artifacts=store,
            approvals=store,
            conversations=store,
        )
        worker = WorkerService(
            runs=store,
            tasks=store,
            artifacts=store,
            events=store,
            model_gateway=ScriptedModelGateway(["not-json"]),
            approvals=store,
            conversations=store,
        )

        project = projects.create_project("Example", "D:/workspaces", "D:/workspaces/example")
        run_state = projects.submit_task(project.id, "Build backend and frontend")

        self.assertEqual(0, len(worker.work_once("test-worker", limit=1)))
        failed_state = projects.get_run_state(project.id, run_state.run.id)
        self.assertEqual("failed", failed_state.run.status.value)
        self.assertEqual({"failed"}, {task.status.value for task in failed_state.tasks})
        self.assertEqual({"failed"}, {agent.status.value for agent in failed_state.agent_runs})
        artifact_text = "\n".join(failed_state.artifact_contents.values())
        self.assertIn("orchestrator response was not valid JSON", artifact_text)

    def test_orchestrator_receives_project_history_as_model_messages(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-history-{uuid4()}"
        root.mkdir(parents=True, exist_ok=True)
        store = LocalFilePlatformStore(root)
        projects = ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=LangGraphAgentRuntime(store),
            artifacts=store,
            approvals=store,
            conversations=store,
        )
        gateway = ScriptedModelGateway(
            [
                '{"action":"answer","content":"I can propose README.md with test after approval."}',
                '{"action":"answer","content":"I remember the requested README.md content."}',
            ]
        )
        worker = WorkerService(
            runs=store,
            tasks=store,
            artifacts=store,
            events=store,
            model_gateway=gateway,
            approvals=store,
            conversations=store,
        )

        project = projects.create_project("Example", "D:/workspaces", "D:/workspaces/example")
        projects.submit_task(project.id, 'create README.md that says "test"')
        self.assertEqual(1, len(worker.work_once("test-worker", limit=1)))
        projects.submit_task(project.id, "just create the file I told you to")
        self.assertEqual(1, len(worker.work_once("test-worker", limit=1)))

        second_messages = gateway.requests[1].messages

        self.assertEqual("system", second_messages[0].role)
        self.assertEqual("user", second_messages[1].role)
        self.assertIn("Prior project chat turns available: 2", second_messages[1].content)
        self.assertEqual("system", second_messages[2].role)
        self.assertIn("Begin project conversation history", second_messages[2].content)
        self.assertEqual("user", second_messages[3].role)
        self.assertEqual('create README.md that says "test"', second_messages[3].content)
        self.assertEqual("assistant", second_messages[4].role)
        self.assertEqual("I can propose README.md with test after approval.", second_messages[4].content)
        self.assertEqual("system", second_messages[5].role)
        self.assertIn("End project conversation history", second_messages[5].content)
        self.assertEqual("system", second_messages[6].role)
        self.assertIn("Project work-log facts", second_messages[6].content)
        self.assertEqual("user", second_messages[7].role)
        self.assertEqual("just create the file I told you to", second_messages[7].content)

    def test_orchestrator_keeps_prior_assistant_turns_inside_explicit_history(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-history-boundary-{uuid4()}"
        root.mkdir(parents=True, exist_ok=True)
        store = LocalFilePlatformStore(root)
        projects = ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=LangGraphAgentRuntime(store),
            artifacts=store,
            approvals=store,
            conversations=store,
        )
        gateway = ScriptedModelGateway(
            [
                '{"action":"answer","content":"I do not have access to previous messages."}',
                '{"action":"answer","content":"You asked whether I had previous messages."}',
            ]
        )
        worker = WorkerService(
            runs=store,
            tasks=store,
            artifacts=store,
            events=store,
            model_gateway=gateway,
            approvals=store,
            conversations=store,
        )

        project = projects.create_project("Example", "D:/workspaces", "D:/workspaces/example")
        projects.submit_task(project.id, "what are the previous messages?")
        self.assertEqual(1, len(worker.work_once("test-worker", limit=1)))
        projects.submit_task(project.id, "what about now?")
        self.assertEqual(1, len(worker.work_once("test-worker", limit=1)))

        second_messages = gateway.requests[1].messages

        self.assertEqual("system", second_messages[2].role)
        self.assertIn("Begin project conversation history", second_messages[2].content)
        self.assertEqual("user", second_messages[3].role)
        self.assertEqual("what are the previous messages?", second_messages[3].content)
        self.assertEqual("assistant", second_messages[4].role)
        self.assertEqual("I do not have access to previous messages.", second_messages[4].content)
        self.assertEqual("system", second_messages[5].role)
        self.assertIn("answer from the transcript above", second_messages[5].content)
        self.assertEqual("system", second_messages[6].role)
        self.assertIn("Project work-log facts", second_messages[6].content)
        self.assertEqual("user", second_messages[7].role)
        self.assertEqual("what about now?", second_messages[7].content)

    def test_child_and_summary_requests_receive_project_conversation_history(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-child-history-{uuid4()}"
        workspace = root / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        store = LocalFilePlatformStore(root / "state")
        projects = ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=LangGraphAgentRuntime(store),
            artifacts=store,
            approvals=store,
            conversations=store,
        )
        gateway = ScriptedModelGateway(
            [
                '{"action":"answer","content":"I will remember README.md should say test."}',
                '{"action":"dispatch","subagents":[{"name":"implementer","task":"Create the requested file."}]}',
                '{"action":"final","content":"Proposed README.md with the remembered content."}',
                "Summary confirms README.md with test content.",
            ]
        )
        worker = WorkerService(
            runs=store,
            tasks=store,
            artifacts=store,
            events=store,
            model_gateway=gateway,
            approvals=store,
            conversations=store,
            tool_policy=WorkspaceReadPolicy(),
            tool_broker=LocalWorkspaceToolBroker(),
        )

        project = projects.create_project("Example", str(root.resolve()), str(workspace.resolve()))
        projects.submit_task(project.id, 'the file is README.md and it should say "test"')
        self.assertEqual(1, len(worker.work_once("test-worker", limit=1)))
        projects.submit_task(project.id, "create the file for me")
        self.assertEqual(1, len(worker.work_once("test-worker", limit=1)))
        self.assertEqual(1, len(worker.work_once("test-worker", limit=1)))

        child_prompt = gateway.requests[2].messages[1].content
        summary_prompt = gateway.requests[3].messages[1].content

        self.assertIn(f"Workspace root: {workspace.resolve()}", child_prompt)
        self.assertIn('User: the file is README.md and it should say "test"', child_prompt)
        self.assertIn('User: the file is README.md and it should say "test"', summary_prompt)
        self.assertIn("Subagent message from implementer", summary_prompt)
        project_state = projects.get_project_state(project.id)
        assignment_artifact = next(
            content
            for content in project_state.artifact_contents.values()
            if "Orchestrator assignment: Create the requested file." in content
        )
        self.assertIn("Recent user/orchestrator context:", assignment_artifact)
        self.assertIn('User: the file is README.md and it should say "test"', assignment_artifact)
        child_runs = [
            agent_run for agent_run in project_state.agent_runs
            if agent_run.parent_agent_run_id is not None
        ]
        self.assertEqual(1, len(child_runs))

    def test_child_agent_uses_brokered_read_only_workspace_tool(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-tools-{uuid4()}"
        workspace = root / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "README.md").write_text("Workspace fact: adapters stay modular.", encoding="utf-8")
        store = LocalFilePlatformStore(root / "state")
        projects = ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=LangGraphAgentRuntime(store),
            artifacts=store,
            approvals=store,
            conversations=store,
        )
        gateway = ScriptedModelGateway(
            [
                '{"action":"dispatch","subagents":[{"name":"reviewer","task":"Read README and review risks."}]}',
                (
                    '{"action":"tool_calls","tool_calls":['
                    '{"name":"workspace.read_text_file","input":{"path":"README.md","max_bytes":2000}}'
                    "]} "
                ),
                '{"action":"final","content":"Reviewer saw adapters stay modular."}',
                "Summary includes reviewer workspace findings.",
            ]
        )
        worker = WorkerService(
            runs=store,
            tasks=store,
            artifacts=store,
            events=store,
            model_gateway=gateway,
            approvals=store,
            conversations=store,
            tool_policy=WorkspaceReadPolicy(),
            tool_broker=LocalWorkspaceToolBroker(),
        )

        project = projects.create_project("Example", str(root.resolve()), str(workspace.resolve()))
        run_state = projects.submit_task(project.id, "Inspect project posture")

        self.assertEqual(1, len(worker.work_once("test-worker", limit=1)))
        self.assertEqual(1, len(worker.work_once("test-worker", limit=1)))
        finished_state = projects.get_run_state(project.id, run_state.run.id)
        artifact_text = "\n".join(finished_state.artifact_contents.values())
        event_types = [event.type.value for event in finished_state.events]

        self.assertEqual("completed", finished_state.run.status.value)
        self.assertIn("Workspace fact: adapters stay modular.", artifact_text)
        self.assertIn("Reviewer saw adapters stay modular.", artifact_text)
        self.assertIn("tool.requested", event_types)
        self.assertIn("tool.completed", event_types)

    def test_child_agent_can_write_file_directly(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-direct-write-{uuid4()}"
        workspace = root / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        readme = workspace / "README.md"
        readme.write_text("Before\n", encoding="utf-8")
        store = LocalFilePlatformStore(root / "state")
        projects = ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=LangGraphAgentRuntime(store),
            artifacts=store,
            approvals=store,
            conversations=store,
        )
        gateway = ScriptedModelGateway(
            [
                '{"action":"dispatch","subagents":[{"name":"implementer","task":"Propose README update."}]}',
                (
                    '{"action":"tool_calls","tool_calls":['
                    '{"name":"workspace.write_text_file",'
                    '"input":{"path":"README.md","content":"After\\n"}}'
                    "]} "
                ),
                '{"action":"final","content":"Wrote README.md with the requested content."}',
                "Summary includes applied README change.",
            ]
        )
        worker = WorkerService(
            runs=store,
            tasks=store,
            artifacts=store,
            events=store,
            model_gateway=gateway,
            approvals=store,
            conversations=store,
            tool_policy=WorkspaceReadPolicy(),
            tool_broker=LocalWorkspaceToolBroker(),
        )

        project = projects.create_project("Example", str(root.resolve()), str(workspace.resolve()))
        run_state = projects.submit_task(project.id, "Prepare README change")

        self.assertEqual(1, len(worker.work_once("test-worker", limit=1)))
        self.assertEqual(1, len(worker.work_once("test-worker", limit=1)))
        finished_state = projects.get_run_state(project.id, run_state.run.id)
        artifact_text = "\n".join(finished_state.artifact_contents.values())

        self.assertEqual("completed", finished_state.run.status.value)
        child_statuses = {
            agent.definition.name: agent.status.value for agent in finished_state.agent_runs
        }
        self.assertEqual("completed", child_statuses["implementer"])
        self.assertEqual("After\n", readme.read_text(encoding="utf-8"))
        self.assertEqual([], list(finished_state.approvals))
        self.assertIn("workspace.write_text_file", artifact_text)
        self.assertIn('"applied": true', artifact_text)

    def test_child_agent_can_read_then_write_across_tool_rounds(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-tool-loop-{uuid4()}"
        workspace = root / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        readme = workspace / "README.md"
        readme.write_text("Before\n", encoding="utf-8")
        store = LocalFilePlatformStore(root / "state")
        projects = ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=LangGraphAgentRuntime(store),
            artifacts=store,
            approvals=store,
            conversations=store,
        )
        gateway = ScriptedModelGateway(
            [
                '{"action":"dispatch","subagents":[{"name":"implementer","task":"Inspect README, then write the update."}]}',
                (
                    '{"action":"tool_calls","tool_calls":['
                    '{"name":"workspace.read_text_file","input":{"path":"README.md","max_bytes":2000}}'
                    "]} "
                ),
                (
                    '{"action":"tool_calls","tool_calls":['
                    '{"name":"workspace.write_text_file",'
                    '"input":{"path":"README.md","content":"Before\\nAfter\\n"}}'
                    "]} "
                ),
                '{"action":"final","content":"Updated README.md after reading the existing content."}',
                "Summary includes the applied README change.",
            ]
        )
        worker = WorkerService(
            runs=store,
            tasks=store,
            artifacts=store,
            events=store,
            model_gateway=gateway,
            approvals=store,
            conversations=store,
            tool_policy=WorkspaceReadPolicy(),
            tool_broker=LocalWorkspaceToolBroker(),
        )

        project = projects.create_project("Example", str(root.resolve()), str(workspace.resolve()))
        run_state = projects.submit_task(project.id, "Update the README")

        self.assertEqual(1, len(worker.work_once("test-worker", limit=1)))
        self.assertEqual(1, len(worker.work_once("test-worker", limit=1)))
        finished_state = projects.get_run_state(project.id, run_state.run.id)
        artifact_text = "\n".join(finished_state.artifact_contents.values())
        event_types = [event.type.value for event in finished_state.events]

        self.assertEqual("completed", finished_state.run.status.value)
        self.assertEqual("Before\nAfter\n", readme.read_text(encoding="utf-8"))
        self.assertEqual([], list(finished_state.approvals))
        self.assertGreaterEqual(event_types.count("tool.completed"), 2)
        self.assertIn("Before", artifact_text)
        self.assertIn("workspace.write_text_file", artifact_text)

    def test_direct_write_completes_with_applied_summary_not_raw_tool_json(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-write-{uuid4()}"
        workspace = root / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        todo = workspace / "todo.html"
        store = LocalFilePlatformStore(root / "state")
        projects = ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=LangGraphAgentRuntime(store),
            artifacts=store,
            approvals=store,
            conversations=store,
        )
        gateway = ScriptedModelGateway(
            [
                '{"action":"dispatch","subagents":[{"name":"implementer","task":"Create todo.html with localStorage."}]}',
                (
                    '{"action":"tool_calls","tool_calls":['
                    '{"name":"workspace.write_text_file",'
                    '"input":{"path":"todo.html","content":"<html><body><script>localStorage.setItem(\\\"ok\\\",\\\"1\\\")</script></body></html>\\n"}}'
                    "]} "
                ),
                '{"action":"final","content":"Applied todo.html with localStorage support."}',
                "The todo.html file was applied and is ready to test.",
            ]
        )
        worker = WorkerService(
            runs=store,
            tasks=store,
            artifacts=store,
            events=store,
            model_gateway=gateway,
            approvals=store,
            conversations=store,
            tool_policy=WorkspaceReadPolicy(),
            tool_broker=LocalWorkspaceToolBroker(),
        )

        project = projects.create_project("Example", str(root.resolve()), str(workspace.resolve()))
        run_state = projects.submit_task(project.id, "Create a localStorage todo app")

        self.assertEqual(1, len(worker.work_once("test-worker", limit=1)))
        self.assertEqual(1, len(worker.work_once("test-worker", limit=1)))
        finished_state = projects.get_run_state(project.id, run_state.run.id)
        assistant_entries = [
            entry.body
            for entry in finished_state.conversation_entries
            if entry.role.value == "assistant"
        ]

        self.assertEqual("completed", finished_state.run.status.value)
        self.assertTrue(todo.exists())
        self.assertEqual([], list(finished_state.approvals))
        self.assertIn("Applied todo.html with localStorage support.", assistant_entries)
        self.assertFalse(any('"action":"tool_calls"' in body for body in assistant_entries))

    def test_projects_are_listed_newest_first_after_reopen(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-order-{uuid4()}"
        root.mkdir(parents=True, exist_ok=True)
        store = LocalFilePlatformStore(root)
        projects = ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=LangGraphAgentRuntime(store),
            artifacts=store,
            approvals=store,
            conversations=store,
        )

        first = projects.create_project("First", "D:/workspaces", "D:/workspaces/first")
        second = projects.create_project("Second", "D:/workspaces", "D:/workspaces/second")

        reopened = LocalFilePlatformStore(root)
        reopened_projects = ProjectService(
            runs=reopened,
            events=reopened,
            tasks=reopened,
            runtime=LangGraphAgentRuntime(reopened),
            artifacts=reopened,
            approvals=reopened,
            conversations=reopened,
        )

        self.assertEqual(
            [second.id, first.id],
            [project.id for project in reopened_projects.list_projects()],
        )

    def test_duplicate_workspace_roots_are_rejected(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-duplicates-{uuid4()}"
        root.mkdir(parents=True, exist_ok=True)
        store = LocalFilePlatformStore(root)
        projects = ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=LangGraphAgentRuntime(store),
            artifacts=store,
            approvals=store,
            conversations=store,
        )

        projects.create_project("Example", "D:/workspaces", "D:/workspaces/example")

        with self.assertRaises(ValueError):
            projects.create_project("Duplicate", "D:/workspaces", "D:/workspaces/example/")

    def test_store_adds_missing_artifacts_bucket_on_reopen(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-migration-{uuid4()}"
        root.mkdir(parents=True, exist_ok=True)
        state_path = root / "state.json"
        state_path.write_text(
            json.dumps(
                {
                    "projects": {},
                    "runs": {},
                    "agent_runs": {},
                    "tasks": {},
                    "events": {},
                }
            ),
            encoding="utf-8",
        )

        LocalFilePlatformStore(root)

        migrated = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual({}, migrated["artifacts"])
        self.assertEqual({}, migrated["approvals"])
        self.assertEqual(DEFAULT_MODEL_IDS, migrated["settings"]["model_profiles"])


if __name__ == "__main__":
    unittest.main()
