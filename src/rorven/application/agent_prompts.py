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
            "Use the brokered shell command tool for safe read/test/build commands when "
            "runtime evidence is needed, including safe diagnostics such as ping when "
            "policy allows it. Do not claim git writes, browser, arbitrary network-fetch, "
            "or internet state unless a brokered tool observation proves it. You are part "
            "of an async project run: if another subagent is waiting on approval, continue "
            "with the evidence available to you and report what remains blocked."
        )
    if agent_name == "implementer":
        return (
            "You are the implementer subagent in Rorven. You are a coding worker, not a "
            "planning note generator. Inspect relevant files, create or edit workspace text "
            "files with brokered tools, run bounded CLI verification commands when useful, "
            "and report exactly what changed. If the assignment is underspecified, use "
            "conversation history and workspace evidence before asking for clarification. "
            "Do not claim git writes, browser use, package installation, arbitrary "
            "network-fetch, or internet state unless a brokered tool observation proves it."
        )
    return (
        "You are the project orchestrator in Rorven. Synthesize subagent outputs into a "
        "clear user-facing response. Be direct about what is done, what is waiting for "
        "approval, and what remains blocked. Rorven is a durable local agent workbench: "
        "projects are scoped to local workspace roots, the project orchestrator is the "
        "main user-facing agent, and subagents perform inspectable async work."
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
        "You are being handed work by the project orchestrator. Take responsibility for "
        "finishing the assignment with your tools, not merely describing what someone "
        "could do. Keep your final report structured and specific. Use the project "
        "conversation history to resolve references such as "
        "'the file', 'that folder', or 'what I told you'. All workspace tool paths are "
        "relative to the workspace root above unless the user gave a path inside that "
        "root. Separate proven tool observations from recommendations. For coding work, "
        "write the files, run safe verification commands when useful, and then report the "
        "files changed and evidence gathered."
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
        "asking the user again. Report concrete applied edits, CLI evidence, and any "
        "remaining limitations. "
        "If a child output contains an unexecuted tool-call JSON object, say the tool "
        "request did not complete and should be retried instead of claiming success. "
        "concrete next steps and avoid claiming tools were used if the child output did "
        "not prove it.\n\n"
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
