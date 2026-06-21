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
            "runtime evidence is needed. Do not claim git writes, browser, or network "
            "access. You are part of an async project run: if another subagent is waiting "
            "on approval, continue with the evidence available to you and report what "
            "remains blocked."
        )
    if agent_name == "implementer":
        return (
            "You are the implementer subagent in Rorven. Produce a concrete implementation "
            "approach, inspect relevant files through brokered workspace tools, and propose "
            "text-file changes when appropriate. Do not claim applied edits; proposals require "
            "approval before they mutate files unless a standing approval policy applies. "
            "When you propose a write, stop and let the approval flow resolve instead of "
            "pretending the file already changed. Use the brokered shell command tool for "
            "safe read/test/build commands when runtime evidence is needed. Do not claim "
            "git writes, browser, or network access."
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
        "Return useful work product for the project orchestrator. Keep it structured and "
        "specific. Use the project conversation history to resolve references such as "
        "'the file', 'that folder', or 'what I told you'. All workspace tool paths are "
        "relative to the workspace root above unless the user gave a path inside that "
        "root. Separate proven tool observations from recommendations. If a write proposal "
        "needs approval, say exactly what was proposed and then wait for the approval "
        "system instead of asking the user to repeat information already present in history."
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
        "asking the user again. If an approval was applied, report the concrete applied "
        "result. If an approval was rejected, report that no change was made. Mention "
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
