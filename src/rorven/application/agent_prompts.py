"""Prompt text for the first worker execution slice."""

from __future__ import annotations

from typing import Sequence

from rorven.application.tools import agent_tool_contract
from rorven.domain import AgentRun, ConversationEntry, ConversationRole, Project, Run


def agent_system_prompt(agent_name: str) -> str:
    if agent_name == "reviewer":
        return (
            "You are the reviewer subagent in Rorven. Inspect the user's request from a "
            "review and risk perspective. Produce concrete findings, questions, and "
            "verification ideas. Use brokered workspace tools when file evidence is needed. "
            "Do not claim shell, git, browser, or network access."
        )
    if agent_name == "implementer":
        return (
            "You are the implementer subagent in Rorven. Produce a concrete implementation "
            "approach, inspect relevant files through brokered workspace tools, and propose "
            "text-file changes when appropriate. Do not claim applied edits; proposals require "
            "human approval before they mutate files."
        )
    return (
        "You are the project orchestrator in Rorven. Synthesize subagent outputs into a "
        "clear user-facing response. Be direct about what is done versus still pending."
    )


def agent_task_prompt(
    project: Project,
    run: Run,
    agent_run: AgentRun,
    assignment: str | None = None,
    conversation_history: Sequence[ConversationEntry] = (),
) -> str:
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
        f"{_conversation_history_section(conversation_history)}\n\n"
        f"{agent_tool_contract()}\n\n"
        "Return useful work product for the project orchestrator. Keep it structured and "
        "specific. Use the project conversation history to resolve references such as "
        "'the file', 'that folder', or 'what I told you'. All workspace tool paths are "
        "relative to the workspace root above unless the user gave a path inside that "
        "root. Separate proven tool observations from recommendations."
    )


def orchestrator_summary_prompt(
    project: Project,
    run: Run,
    child_outputs: Sequence[str],
    conversation_history: Sequence[ConversationEntry] = (),
) -> str:
    return (
        f"Project: {project.name}\n"
        f"Workspace: {project.workspace.workspace_root}\n"
        f"User request: {run.command}\n\n"
        f"{_conversation_history_section(conversation_history)}\n\n"
        "Summarize the completed subagent work into a concise project orchestrator "
        "response. Treat the child outputs below as returned subagent messages. Use "
        "the project conversation history to resolve missing-looking details before "
        "asking the user again. Mention concrete next steps and avoid claiming tools "
        "were used if the child output did not prove it.\n\n"
        + "\n\n".join(child_outputs)
    )


def _conversation_history_section(entries: Sequence[ConversationEntry]) -> str:
    lines = [
        "Project conversation history:",
    ]
    if not entries:
        lines.append("- No prior project chat turns are available.")
        return "\n".join(lines)
    for entry in entries:
        speaker = "User" if entry.role == ConversationRole.USER else "Project orchestrator"
        lines.append(f"{speaker}: {entry.body.strip()}")
    return "\n".join(lines)
