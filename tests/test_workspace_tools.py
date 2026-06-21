from __future__ import annotations

from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
from uuid import uuid4

from rorven.adapters.tools import LocalWorkspaceToolBroker
from rorven.application.tools import ToolRequest, WorkspaceReadPolicy, parse_agent_tool_instruction
from rorven.domain import AgentDefinitionRef, AgentRun, ModelProfile, Project, WorkspaceBinding


class WorkspaceToolTests(unittest.TestCase):
    def test_policy_denies_root_agent_and_sensitive_paths(self) -> None:
        project, child, root = _project_and_agents()
        policy = WorkspaceReadPolicy()

        root_decision = policy.evaluate(project, root, ToolRequest("workspace.list_files", {"path": "."}))
        secret_decision = policy.evaluate(
            project,
            child,
            ToolRequest("workspace.read_text_file", {"path": ".env"}),
        )

        self.assertFalse(root_decision.allowed)
        self.assertFalse(secret_decision.allowed)

        write_decision = policy.evaluate(
            project,
            child,
            ToolRequest("workspace.write_text_file", {"path": "README.md", "content": "ok"}),
        )
        self.assertTrue(write_decision.allowed)

    def test_policy_allows_safe_command_and_blocks_destructive_command(self) -> None:
        project, child, _root = _project_and_agents()
        policy = WorkspaceReadPolicy()

        safe = policy.evaluate(
            project,
            child,
            ToolRequest("workspace.run_shell_command", {"command": "python --version"}),
        )
        diagnostic = policy.evaluate(
            project,
            child,
            ToolRequest("workspace.run_shell_command", {"command": "ping www.google.de"}),
        )
        network_fetch = policy.evaluate(
            project,
            child,
            ToolRequest("workspace.run_shell_command", {"command": "curl https://example.com"}),
        )
        destructive = policy.evaluate(
            project,
            child,
            ToolRequest("workspace.run_shell_command", {"command": "Remove-Item README.md"}),
        )

        self.assertTrue(safe.allowed)
        self.assertTrue(diagnostic.allowed)
        self.assertFalse(network_fetch.allowed)
        self.assertFalse(destructive.allowed)

    def test_agent_final_protocol_handles_model_wrappers(self) -> None:
        instruction = parse_agent_tool_instruction(
            '<think>I should answer cleanly.</think>\n{"action":"final","content":"Ping completed."}'
        )

        self.assertFalse(instruction.requests_tools)
        self.assertEqual("Ping completed.", instruction.final_content)

    def test_local_workspace_broker_reads_text_inside_workspace(self) -> None:
        project, child, _root = _project_and_agents()
        workspace = Path(project.workspace.workspace_root)
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "README.md").write_text("Rorven workspace notes", encoding="utf-8")

        result = LocalWorkspaceToolBroker().execute(
            project,
            child,
            ToolRequest("workspace.read_text_file", {"path": "README.md"}),
        )

        self.assertIn("Rorven workspace notes", result.content)
        self.assertEqual("README.md", result.metadata["path"])

    def test_local_workspace_broker_rejects_path_escape(self) -> None:
        project, child, _root = _project_and_agents()
        workspace = Path(project.workspace.workspace_root)
        workspace.mkdir(parents=True, exist_ok=True)
        outside = workspace.parent / "outside.txt"
        outside.write_text("outside", encoding="utf-8")

        with self.assertRaises(ValueError):
            LocalWorkspaceToolBroker().execute(
                project,
                child,
                ToolRequest("workspace.read_text_file", {"path": "../outside.txt"}),
            )

    def test_local_workspace_broker_writes_text_file_inside_workspace(self) -> None:
        project, child, _root = _project_and_agents()
        workspace = Path(project.workspace.workspace_root)
        workspace.mkdir(parents=True, exist_ok=True)
        readme = workspace / "README.md"
        readme.write_text("Before\n", encoding="utf-8")

        result = LocalWorkspaceToolBroker().execute(
            project,
            child,
            ToolRequest(
                "workspace.write_text_file",
                {"path": "README.md", "content": "After\n"},
            ),
        )

        self.assertTrue(result.metadata["applied"])
        self.assertEqual("workspace.write_text_file", result.metadata["tool"])
        self.assertEqual("README.md", result.metadata["path"])
        self.assertEqual("After\n", readme.read_text(encoding="utf-8"))

    def test_local_workspace_broker_runs_shell_command_in_workspace(self) -> None:
        project, child, _root = _project_and_agents()
        workspace = Path(project.workspace.workspace_root)
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "README.md").write_text("hello", encoding="utf-8")

        result = LocalWorkspaceToolBroker().execute(
            project,
            child,
            ToolRequest(
                "workspace.run_shell_command",
                {"command": "Get-ChildItem README.md | Select-Object -ExpandProperty Name"},
            ),
        )

        self.assertIn("README.md", result.content)
        self.assertEqual(".", result.metadata["cwd"])
        self.assertEqual(False, result.metadata["timed_out"])

    def test_shell_command_handles_missing_output_streams(self) -> None:
        project, child, _root = _project_and_agents()
        Path(project.workspace.workspace_root).mkdir(parents=True, exist_ok=True)

        with patch(
            "rorven.adapters.tools.local_workspace.subprocess.run",
            return_value=subprocess.CompletedProcess(args=["shell"], returncode=0, stdout=None, stderr=None),
        ):
            result = LocalWorkspaceToolBroker().execute(
                project,
                child,
                ToolRequest("workspace.run_shell_command", {"command": "ping google.com"}),
            )

        self.assertIn("Return code: 0", result.content)
        self.assertEqual(0, result.metadata["stdout_bytes"])
        self.assertEqual(0, result.metadata["stderr_bytes"])


def _project_and_agents() -> tuple[Project, AgentRun, AgentRun]:
    root = Path("test-output") / "tests" / f"workspace-tools-{uuid4()}"
    workspace = root / "workspace"
    project = Project.create(
        "Example",
        WorkspaceBinding(str(root.resolve()), str(workspace.resolve())),
    )
    root_agent = AgentRun.create(
        run_id="11111111-1111-4111-8111-111111111111",
        project_id=project.id,
        definition=AgentDefinitionRef("orchestrator", "0001", ModelProfile.REASONING),
    )
    child = AgentRun.create(
        run_id=root_agent.run_id,
        project_id=project.id,
        definition=AgentDefinitionRef("reviewer", "0001", ModelProfile.BALANCED),
        parent_agent_run_id=root_agent.id,
    )
    return project, child, root_agent
