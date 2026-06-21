"""Provider-neutral tool-call contracts and policy decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any

from rorven.domain import AgentRun, Project


MAX_TOOL_CALLS = 3
MAX_TOOL_ROUNDS = 3
MAX_READ_BYTES = 20_000
MAX_LIST_ENTRIES = 200
MAX_PROPOSED_TEXT_BYTES = 40_000
MAX_COMMAND_CHARS = 500
MAX_COMMAND_TIMEOUT_SECONDS = 30
READ_ONLY_TOOLS = {"workspace.list_files", "workspace.read_text_file"}
PROPOSAL_TOOLS = {"workspace.propose_text_file_write"}
COMMAND_TOOLS = {"workspace.run_shell_command"}
SUPPORTED_TOOLS = READ_ONLY_TOOLS | PROPOSAL_TOOLS | COMMAND_TOOLS
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
DENIED_COMMAND_PATTERNS = (
    r"\brm\b",
    r"\brmdir\b",
    r"\bdel\b",
    r"\berase\b",
    r"\bRemove-Item\b",
    r"\bmove\b",
    r"\bmv\b",
    r"\bcopy\b",
    r"\bcp\b",
    r"\bgit\s+push\b",
    r"\bgit\s+reset\b",
    r"\bgit\s+clean\b",
    r"\bgit\s+checkout\b",
    r"\bcurl\b",
    r"\bwget\b",
    r"\bInvoke-WebRequest\b",
    r"\bInvoke-RestMethod\b",
    r"\bnpm\s+(install|i|add)\b",
    r"\bpnpm\s+(install|add)\b",
    r"\byarn\s+(add|install)\b",
    r"\bpip\s+install\b",
    r"\buv\s+(add|pip\s+install|sync)\b",
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
        if request.name == "workspace.run_shell_command":
            command = request.input.get("command")
            if not isinstance(command, str) or not command.strip():
                return ToolPolicyDecision(False, "command must be a non-empty string")
            if len(command) > MAX_COMMAND_CHARS:
                return ToolPolicyDecision(False, f"command must be at most {MAX_COMMAND_CHARS} characters")
            timeout = request.input.get("timeout_seconds", MAX_COMMAND_TIMEOUT_SECONDS)
            if (
                not isinstance(timeout, int)
                or timeout < 1
                or timeout > MAX_COMMAND_TIMEOUT_SECONDS
            ):
                return ToolPolicyDecision(
                    False,
                    f"timeout_seconds must be between 1 and {MAX_COMMAND_TIMEOUT_SECONDS}",
                )
            if _has_sensitive_path_marker(command.lower()):
                return ToolPolicyDecision(False, "command references a blocked secret-sensitive path")
            for pattern in DENIED_COMMAND_PATTERNS:
                if re.search(pattern, command, flags=re.IGNORECASE):
                    return ToolPolicyDecision(False, f"command is blocked by policy pattern: {pattern}")
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
        "You may either produce a final answer or request brokered workspace tools. "
        f"You may request up to {MAX_TOOL_ROUNDS} tool rounds, with at most "
        f"{MAX_TOOL_CALLS} tool calls in one round.\n\n"
        "For a final answer, return useful prose normally or JSON in this shape:\n"
        '{"action":"final","content":"your final work product"}\n\n'
        "To request tools, return exactly one JSON object and no prose outside it:\n"
        '{"action":"tool_calls","tool_calls":[{"name":"workspace.list_files",'
        '"input":{"path":".","max_entries":80}},{"name":"workspace.read_text_file",'
        '"input":{"path":"README.md","max_bytes":6000}},'
        '{"name":"workspace.propose_text_file_write","input":{"path":"README.md",'
        '"content":"complete proposed file content"}},'
        '{"name":"workspace.run_shell_command","input":{"command":"python -m pytest",'
        '"cwd":".","timeout_seconds":30}}]}\n\n'
        "Allowed tools are workspace.list_files, workspace.read_text_file, and "
        "workspace.propose_text_file_write, and workspace.run_shell_command. The write "
        "tool only creates a persisted diff proposal; it does not modify files. The "
        "shell command tool runs inside the project workspace with captured output and "
        "a short timeout, and policy blocks obvious destructive, package-install, "
        "network-fetch, and secret-sensitive commands. Safe diagnostic commands such "
        "as version checks or ping may be used when policy accepts them. Tools are policy checked, audited, "
        "and cannot access obvious secret paths such as .env, .git, key, token, or "
        "credential files. Only claim workspace inspection, shell results, or proposed "
        "edits when the tool results prove them."
    )


def tool_results_prompt(results: list[dict[str, Any]], remaining_tool_rounds: int = 0) -> str:
    if remaining_tool_rounds > 0:
        instruction = (
            "Brokered tool results are below. Produce the final work product now, "
            f"or request another tool round if required. Remaining tool rounds: {remaining_tool_rounds}."
        )
    else:
        instruction = (
            "Brokered tool results are below. Produce the final work product now. "
            "Do not request more tools in this run."
        )
    return instruction + "\n\n" + json.dumps(results, indent=2, sort_keys=True)


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
    trimmed = _strip_common_model_wrappers(content)
    try:
        payload = json.loads(trimmed)
    except json.JSONDecodeError:
        payload = _loads_embedded_json_object(trimmed)
        if payload is None:
            return None
    if not isinstance(payload, dict):
        return None
    return payload


def _strip_common_model_wrappers(content: str) -> str:
    trimmed = content.strip()
    if trimmed.startswith("```"):
        lines = trimmed.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        trimmed = "\n".join(lines).strip()
    return re.sub(r"<think>.*?</think>", "", trimmed, flags=re.IGNORECASE | re.DOTALL).strip()


def _loads_embedded_json_object(content: str) -> dict[str, Any] | None:
    start = content.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(content)):
            char = content[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    try:
                        payload = json.loads(content[start : index + 1])
                    except json.JSONDecodeError:
                        break
                    if isinstance(payload, dict) and payload.get("action") in {"final", "tool_calls"}:
                        return payload
                    break
        start = content.find("{", start + 1)
    return None


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()
