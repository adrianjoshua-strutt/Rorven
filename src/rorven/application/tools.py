"""Provider-neutral tool-call contracts and policy decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any

from rorven.domain import AgentRun, Project


MAX_TOOL_CALLS = 3
MAX_READ_BYTES = 20_000
MAX_LIST_ENTRIES = 200
MAX_PROPOSED_TEXT_BYTES = 40_000
READ_ONLY_TOOLS = {"workspace.list_files", "workspace.read_text_file"}
PROPOSAL_TOOLS = {"workspace.propose_text_file_write"}
SUPPORTED_TOOLS = READ_ONLY_TOOLS | PROPOSAL_TOOLS
SENSITIVE_PATH_MARKERS = (
    ".env",
    ".git",
    "secret",
    "secrets",
    "token",
    "tokens",
    "credential",
    "credentials",
    "private_key",
    "id_rsa",
    ".pem",
    ".pfx",
    ".p12",
)


@dataclass(frozen=True, slots=True)
class ToolRequest:
    name: str
    input: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolPolicyDecision:
    allowed: bool
    reason: str
    approval_required: bool = False


@dataclass(frozen=True, slots=True)
class ToolExecutionResult:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AgentToolInstruction:
    final_content: str | None
    tool_requests: tuple[ToolRequest, ...]
    raw_content: str

    @property
    def requests_tools(self) -> bool:
        return bool(self.tool_requests)


class WorkspaceReadPolicy:
    """Deny-by-default policy for the first brokered workspace tools."""

    def evaluate(
        self,
        project: Project,
        agent_run: AgentRun,
        request: ToolRequest,
    ) -> ToolPolicyDecision:
        if agent_run.parent_agent_run_id is None:
            return ToolPolicyDecision(False, "root orchestrator cannot invoke workspace tools")
        if request.name not in SUPPORTED_TOOLS:
            return ToolPolicyDecision(False, f"unsupported tool: {request.name}")
        path = _tool_path(request)
        if _has_sensitive_path_marker(path):
            return ToolPolicyDecision(False, "path is blocked by secret-safety policy")
        if request.name == "workspace.read_text_file":
            max_bytes = request.input.get("max_bytes", MAX_READ_BYTES)
            if not isinstance(max_bytes, int) or max_bytes < 1 or max_bytes > MAX_READ_BYTES:
                return ToolPolicyDecision(False, f"max_bytes must be between 1 and {MAX_READ_BYTES}")
        if request.name == "workspace.list_files":
            max_entries = request.input.get("max_entries", MAX_LIST_ENTRIES)
            if not isinstance(max_entries, int) or max_entries < 1 or max_entries > MAX_LIST_ENTRIES:
                return ToolPolicyDecision(False, f"max_entries must be between 1 and {MAX_LIST_ENTRIES}")
        if request.name == "workspace.propose_text_file_write":
            content = request.input.get("content")
            if not isinstance(content, str):
                return ToolPolicyDecision(False, "content must be a string")
            if len(content.encode("utf-8")) > MAX_PROPOSED_TEXT_BYTES:
                return ToolPolicyDecision(
                    False,
                    f"content must be at most {MAX_PROPOSED_TEXT_BYTES} bytes",
                )
        return ToolPolicyDecision(True, "read-only workspace access allowed")


class DenyAllToolPolicy:
    def evaluate(
        self,
        project: Project,
        agent_run: AgentRun,
        request: ToolRequest,
    ) -> ToolPolicyDecision:
        return ToolPolicyDecision(False, "no tool policy configured")


def agent_tool_contract() -> str:
    return (
        "You may either produce a final answer or request one round of read-only "
        "workspace tools.\n\n"
        "For a final answer, return useful prose normally or JSON in this shape:\n"
        '{"action":"final","content":"your final work product"}\n\n'
        "To request tools, return exactly one JSON object and no prose outside it:\n"
        '{"action":"tool_calls","tool_calls":[{"name":"workspace.list_files",'
        '"input":{"path":".","max_entries":80}},{"name":"workspace.read_text_file",'
        '"input":{"path":"README.md","max_bytes":6000}},'
        '{"name":"workspace.propose_text_file_write","input":{"path":"README.md",'
        '"content":"complete proposed file content"}}]}\n\n'
        "Allowed tools are workspace.list_files, workspace.read_text_file, and "
        "workspace.propose_text_file_write. The write tool only creates a persisted "
        "diff proposal; it does not modify files. Tools are policy checked, audited, "
        "and cannot access obvious secret paths such as .env, .git, key, token, or "
        "credential files. Do not claim shell commands, git actions, browser access, "
        "or applied file edits."
    )


def tool_results_prompt(results: list[dict[str, Any]]) -> str:
    return (
        "Brokered tool results are below. Produce the final work product now. "
        "Do not request more tools in this run.\n\n"
        + json.dumps(results, indent=2, sort_keys=True)
    )


def parse_agent_tool_instruction(content: str) -> AgentToolInstruction:
    payload = _try_loads_json_object(content)
    if payload is None:
        return AgentToolInstruction(final_content=content, tool_requests=(), raw_content=content)
    action = _required_string(payload, "action").lower()
    if action == "final":
        return AgentToolInstruction(
            final_content=_required_string(payload, "content"),
            tool_requests=(),
            raw_content=content,
        )
    if action != "tool_calls":
        return AgentToolInstruction(final_content=content, tool_requests=(), raw_content=content)

    tool_calls = payload.get("tool_calls")
    if not isinstance(tool_calls, list) or not tool_calls:
        raise ValueError("tool_calls action requires at least one tool call")
    if len(tool_calls) > MAX_TOOL_CALLS:
        raise ValueError(f"at most {MAX_TOOL_CALLS} tool calls are allowed")

    requests: list[ToolRequest] = []
    for item in tool_calls:
        if not isinstance(item, dict):
            raise ValueError("each tool call must be an object")
        name = _required_string(item, "name")
        tool_input = item.get("input", {})
        if not isinstance(tool_input, dict):
            raise ValueError("tool input must be an object")
        requests.append(ToolRequest(name=name, input=dict(tool_input)))
    return AgentToolInstruction(final_content=None, tool_requests=tuple(requests), raw_content=content)


def tool_request_to_json(request: ToolRequest) -> dict[str, Any]:
    return {"name": request.name, "input": request.input}


def tool_decision_to_json(decision: ToolPolicyDecision) -> dict[str, Any]:
    return {
        "allowed": decision.allowed,
        "reason": decision.reason,
        "approval_required": decision.approval_required,
    }


def _tool_path(request: ToolRequest) -> str:
    value = request.input.get("path", ".")
    if not isinstance(value, str):
        return ""
    return value.replace("\\", "/").strip().lower()


def _has_sensitive_path_marker(path: str) -> bool:
    parts = [part for part in path.replace("\\", "/").split("/") if part]
    return any(any(marker in part for marker in SENSITIVE_PATH_MARKERS) for part in parts)


def _try_loads_json_object(content: str) -> dict[str, Any] | None:
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
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()
