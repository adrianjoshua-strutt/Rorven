"""Prompt text for the first worker execution slice."""

from __future__ import annotations

from typing import Sequence

from rorven.domain import AgentRun, Project, Run


def agent_system_prompt(agent_name: str) -> str:
    if agent_name == "reviewer":
        return (
            "You are the reviewer subagent in Rorven. Inspect the user's request from a "
            "review and risk perspective. Produce concrete findings, questions, and "
            "verification ideas. Do not claim filesystem or shell access."
        )
    if agent_name == "implementer":
        return (
            "You are the implementer subagent in Rorven. Produce a concrete implementation "
            "approach, files likely affected, and validation steps. Do not claim you edited "
            "files or ran tools."
        )
    return (
        "You are the project orchestrator in Rorven. Synthesize subagent outputs into a "
        "clear user-facing response. Be direct about what is done versus still pending."
    )


def agent_task_prompt(project: Project, run: Run, agent_run: AgentRun, assignment: str | None = None) -> str:
    task_text = assignment or run.command
    return (
        f"Project: {project.name}\n"
        f"Workspace root: {project.workspace.workspace_root}\n"
        f"Allowed root: {project.workspace.allowed_root}\n"
        f"Run id: {run.id}\n"
        f"Agent: {agent_run.definition.name}@{agent_run.definition.version}\n"
        f"Model profile: {agent_run.definition.model_profile.value}\n\n"
        f"User request:\n{run.command}\n\n"
        f"Assigned task:\n{task_text}\n\n"
        "Return useful work product for the project orchestrator. Keep it structured and "
        "specific. If execution tools are required, state exactly what should be run next."
    )


def orchestrator_summary_prompt(project: Project, run: Run, child_outputs: Sequence[str]) -> str:
    return (
        f"Project: {project.name}\n"
        f"Workspace: {project.workspace.workspace_root}\n"
        f"User request: {run.command}\n\n"
        "Summarize the completed subagent work into a concise project orchestrator "
        "response. Mention concrete next steps and avoid claiming tools were used if "
        "the child output did not prove it.\n\n"
        + "\n\n".join(child_outputs)
    )
