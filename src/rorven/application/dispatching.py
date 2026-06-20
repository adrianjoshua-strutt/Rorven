"""Provider-neutral orchestrator dispatch contract."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from rorven.domain import AgentDefinitionRef, ModelProfile


MAX_DISPATCHED_AGENTS = 4

AGENT_DEFINITIONS: dict[str, AgentDefinitionRef] = {
    "reviewer": AgentDefinitionRef(
        name="reviewer",
        version="0001",
        model_profile=ModelProfile.BALANCED,
    ),
    "implementer": AgentDefinitionRef(
        name="implementer",
        version="0001",
        model_profile=ModelProfile.REASONING,
    ),
}


@dataclass(frozen=True, slots=True)
class ChildAgentDispatch:
    definition: AgentDefinitionRef
    task: str


@dataclass(frozen=True, slots=True)
class OrchestratorDecision:
    answer: str | None
    child_agents: tuple[ChildAgentDispatch, ...]
    raw_content: str

    @property
    def dispatches_children(self) -> bool:
        return len(self.child_agents) > 0


def orchestrator_dispatch_contract() -> str:
    allowed = ", ".join(sorted(AGENT_DEFINITIONS))
    return (
        "You are the project orchestrator in Rorven. Decide whether the request "
        "can be answered directly or should be split into subagent work.\n\n"
        "Return exactly one JSON object and no prose outside the JSON.\n"
        "Direct answer shape:\n"
        '{"action":"answer","content":"short answer for the user"}\n'
        "Dispatch shape:\n"
        '{"action":"dispatch","subagents":[{"name":"reviewer","task":"specific assignment"},'
        '{"name":"implementer","task":"specific assignment"}]}\n\n'
        f"Allowed subagent names: {allowed}.\n"
        "Each request is framed as project context, an explicit prior project conversation "
        "history section, and then the current user message. Treat the prior conversation "
        "section as the real project chat history available to you for this request.\n"
        "If the user asks about previous messages, answer from the provided prior "
        "conversation. Use that history to resolve follow-up references such as "
        "'that file', 'the folder', 'what about now', or 'what I told you'.\n"
        "Use a direct answer only for conversation, explanation, or questions that do "
        "not require workspace evidence or file-change proposals.\n"
        "If the request requires listing files, reading files, checking workspace state, "
        "or proposing a file change, dispatch an appropriate subagent instead of claiming "
        "the work is already done.\n"
        "Subagents can use brokered workspace.list_files, workspace.read_text_file, "
        "and workspace.propose_text_file_write tools. The write tool creates an approval "
        "proposal only; it does not apply edits. Subagents still have no shell, git, "
        "browser, network, or sandbox execution."
    )


def parse_orchestrator_decision(content: str) -> OrchestratorDecision:
    payload = _loads_json_object(content)
    action = _required_string(payload, "action").lower()
    if action == "answer":
        return OrchestratorDecision(
            answer=_required_string(payload, "content"),
            child_agents=(),
            raw_content=content,
        )
    if action != "dispatch":
        raise ValueError(f"unsupported orchestrator action: {action}")

    subagents = payload.get("subagents")
    if not isinstance(subagents, list) or not subagents:
        raise ValueError("dispatch action requires at least one subagent")
    if len(subagents) > MAX_DISPATCHED_AGENTS:
        raise ValueError(f"dispatch may create at most {MAX_DISPATCHED_AGENTS} subagents")

    child_agents: list[ChildAgentDispatch] = []
    seen_names: set[str] = set()
    for item in subagents:
        if not isinstance(item, dict):
            raise ValueError("each subagent dispatch must be an object")
        name = _required_string(item, "name").lower()
        task = _required_string(item, "task")
        try:
            definition = AGENT_DEFINITIONS[name]
        except KeyError as exc:
            raise ValueError(f"unsupported subagent: {name}") from exc
        if name in seen_names:
            raise ValueError(f"duplicate subagent dispatch: {name}")
        seen_names.add(name)
        child_agents.append(ChildAgentDispatch(definition=definition, task=task))

    return OrchestratorDecision(
        answer=None,
        child_agents=tuple(child_agents),
        raw_content=content,
    )


def _loads_json_object(content: str) -> dict[str, Any]:
    trimmed = content.strip()
    if trimmed.startswith("```"):
        lines = trimmed.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        trimmed = "\n".join(lines).strip()
    try:
        payload = json.loads(trimmed)
    except json.JSONDecodeError as exc:
        raise ValueError("orchestrator response was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("orchestrator response must be a JSON object")
    return payload


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()
