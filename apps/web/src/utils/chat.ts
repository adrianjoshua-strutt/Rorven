import { AgentRun, ApprovalRecord, ArtifactRecord, Project, RunState } from "../api";
import { AgentWorkEntry, ChatMessage } from "../types";
import { normalizeDisplayPath } from "./projects";
import { isDone } from "./status";

export function buildProjectChat(
  project: Project | null,
  run: RunState | null,
  subagents: AgentRun[],
): ChatMessage[] {
  if (!project) return [];
  const persisted = [...(project.conversation_entries ?? [])].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );
  const rootTranscript = persisted.filter(isRootChatEntry);
  const messages = rootTranscript.map((entry): ChatMessage => ({
    id: entry.id,
    side: entry.role === "user" ? "user" : "orchestrator",
    title: entry.role === "user" ? "You" : entry.title,
    body: cleanChatBody(entry.body),
    time: entry.created_at,
  }));

  if (!messages.length) {
    for (const projectRun of [...(project.runs ?? [])]) {
      messages.push({
        id: `${projectRun.id}-user`,
        side: "user",
        title: "You",
        body: cleanChatBody(projectRun.command),
        time: projectRun.created_at,
      });
    }
  }

  const projectApprovals = project.approvals ?? [];
  const projectArtifacts = project.artifacts ?? [];
  messages.push(...buildSubagentTimeline(persisted, subagents, projectApprovals));
  messages.push(...buildApprovalTimeline(projectApprovals, projectArtifacts, subagents));
  const selectedRunSubagents = run
    ? subagents.filter((agent) => agent.run_id === run.id)
    : [];
  appendSelectedRunPlaceholder(messages, run, selectedRunSubagents, rootTranscript);
  return messages.sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());
}

function isRootChatEntry(entry: { role: string; title: string }): boolean {
  if (entry.role === "user") return entry.title === "You";
  if (entry.role === "assistant") {
    return entry.title === "Project orchestrator" || entry.title === "orchestrator";
  }
  return false;
}

function appendSelectedRunPlaceholder(
  messages: ChatMessage[],
  run: RunState | null,
  subagents: AgentRun[],
  rootTranscript: { run_id: string; role: string; created_at: string }[],
): void {
  if (!run) return;
  const root = run.agent_runs.find((agentRun) => agentRun.parent_agent_run_id === null);
  if (!isDone(run.status)) return;
  const rootHasAssistantEntry = rootTranscript.some(
    (entry) => entry.run_id === run.id && entry.role === "assistant",
  );
  if (rootHasAssistantEntry) return;

  let orchestratorBody: string;
  const currentUserEntry = rootTranscript.find((entry) => entry.run_id === run.id && entry.role === "user");
  const placeholderTime = currentUserEntry
    ? new Date(new Date(currentUserEntry.created_at).getTime() + 1).toISOString()
    : root?.created_at ?? run.created_at;
  if (root?.result_artifact_id) {
    orchestratorBody =
      cleanChatBody(run.artifacts.find((a) => a.id === root.result_artifact_id)?.content ?? "") ||
      "Work completed.";
  } else if (subagents.length > 0) {
    const finished = subagents.filter((a) => isDone(a.status)).length;
    const running = subagents.length - finished;
    orchestratorBody =
      finished === subagents.length
        ? `All ${subagents.length} subagents finished.`
        : `${running} subagent${running !== 1 ? "s" : ""} running, ${finished} finished.`;
  } else {
    orchestratorBody = root?.status === "queued" || root?.status === "started"
      ? "Working..."
      : root?.status === "completed"
        ? "Done."
        : "Queued.";
  }

  messages.push({
    id: `${run.id}-orchestrator`,
    side: "orchestrator",
    title: root?.definition.name ?? "Project orchestrator",
    body: cleanChatBody(orchestratorBody),
    time: placeholderTime,
    status: root?.status ?? run.status,
  });
}

function buildSubagentTimeline(
  projectEntries: { agent_run_id: string | null; role: string; title: string; body: string; created_at: string }[],
  subagents: AgentRun[],
  approvals: ApprovalRecord[] = [],
): ChatMessage[] {
  if (!subagents.length) return [];
  const messages: ChatMessage[] = [];
  for (const agent of subagents) {
    const entries = projectEntries
      .filter((entry) => entry.agent_run_id === agent.id)
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
    const assignment = entries.find((entry) => entry.role === "user");
    const pendingApproval = approvals.find(
      (approval) => approval.agent_run_id === agent.id && approval.status === "pending",
    );
    const statusTitle =
      pendingApproval ? `${agent.definition.name} waiting for approval`
      : agent.status === "queued" ? `${agent.definition.name} queued`
      : agent.status === "waiting" ? `${agent.definition.name} waiting`
      : isDone(agent.status) ? `${agent.definition.name} completed`
      : `${agent.definition.name} running`;
    messages.push({
      id: `${agent.id}-started`,
      side: "orchestrator",
      title: statusTitle,
      body: subagentTimelineSummary(
        agent.definition.name,
        assignment?.body,
      ),
      time: assignment?.created_at ?? agent.created_at,
      status: agent.status,
      kind: "subagent",
      agentId: agent.id,
      actionLabel: "Open work log",
    });

    if (!isDone(agent.status) || pendingApproval) {
      continue;
    }

    const usefulEntry =
      [...entries].reverse().find((entry) => entry.role === "assistant" && entry.body.trim()) ??
      [...entries].reverse().find((entry) => entry.role === "tool" && entry.body.trim()) ??
      entries[entries.length - 1];
    messages.push({
      id: `${agent.id}-finished`,
      side: "orchestrator",
      title: `${agent.definition.name} finished`,
      body: compactSummary(usefulEntry?.body ?? `${agent.definition.name} finished without recorded output.`),
      time: usefulEntry?.created_at ?? assignment?.created_at ?? agent.created_at,
      status: agent.status,
      kind: "subagent",
      agentId: agent.id,
      actionLabel: "Review output",
    });
  }
  return messages;
}

function buildApprovalTimeline(
  approvals: ApprovalRecord[],
  artifacts: ArtifactRecord[],
  subagents: AgentRun[],
): ChatMessage[] {
  return approvals.map((approval) => {
    const artifact = artifacts.find((candidate) => candidate.id === approval.artifact_id);
    const agent = subagents.find((candidate) => candidate.id === approval.agent_run_id);
    const proposal = summarizeApprovalProposal(approval, artifact);
    return {
      id: `${approval.id}-${approval.status}`,
      side: "orchestrator",
      title: approvalTitle(approval, agent?.definition.name),
      body: proposal,
      time: approval.decided_at ?? approval.created_at,
      status: approval.status,
      kind: "approval",
      agentId: approval.agent_run_id,
      approval,
      approvalArtifact: artifact,
      actionLabel: "Open subagent",
    };
  });
}

function approvalTitle(approval: ApprovalRecord, agentName?: string): string {
  const owner = agentName ?? "subagent";
  if (approval.status === "pending") return `${owner} needs approval`;
  if (approval.status === "applied") return `${owner} approval applied`;
  if (approval.status === "rejected") return `${owner} approval rejected`;
  if (approval.status === "failed") return `${owner} approval failed`;
  return `${owner} approval`;
}

function summarizeApprovalProposal(approval: ApprovalRecord, artifact?: ArtifactRecord): string {
  const fallback = `${approval.action} is ${approval.status}.`;
  if (!artifact?.content) return fallback;
  try {
    const payload = JSON.parse(artifact.content) as {
      request?: { input?: { path?: unknown } };
      result?: { content?: unknown; metadata?: { path?: unknown } };
    };
    const path = payload.result?.metadata?.path ?? payload.request?.input?.path;
    const proposal = typeof payload.result?.content === "string" ? payload.result.content : "";
    const pathLine = typeof path === "string" ? `Path: ${normalizeDisplayPath(path)}` : "Path: workspace file";
    const stateLine =
      approval.status === "pending"
        ? "This proposal is waiting for your approval."
        : approval.status === "applied"
          ? "This proposal was approved and applied."
          : approval.status === "rejected"
            ? "This proposal was rejected; no file was changed."
            : fallback;
    return compactSummary(`${stateLine}\n${pathLine}\n${proposal}`);
  } catch {
    return fallback;
  }
}

function subagentTimelineSummary(agentName: string, assignmentBody?: string): string {
  const assignment = extractHarnessValue(assignmentBody ?? "", "Orchestrator assignment");
  if (assignment) {
    return `${agentName} is working on: ${assignment}`;
  }
  return `${agentName} was started by the project orchestrator.`;
}

function extractHarnessValue(body: string, label: string): string | null {
  const line = body
    .split(/\r?\n/)
    .find((candidate) => candidate.trim().toLowerCase().startsWith(`${label.toLowerCase()}:`));
  if (!line) return null;
  const value = line.slice(line.indexOf(":") + 1).trim();
  return value || null;
}

export function buildAgentWork(agent: AgentRun, run: RunState | null): AgentWorkEntry[] {
  const transcript = [...(run?.conversation_entries ?? [])]
    .filter((entry) => entry.agent_run_id === agent.id)
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
  if (transcript.length) {
    return transcript.map((entry) => ({
      side:
        entry.role === "user"
          ? "system"
          : entry.role === "tool"
            ? "tool"
            : entry.role === "event"
              ? "event"
              : "agent",
      title: entry.title,
      body: cleanChatBody(entry.body),
      created_at: entry.created_at,
    }));
  }
  const task = run?.tasks.find((candidate) => candidate.agent_run_id === agent.id);
  const assignmentArtifact = run?.artifacts.find((artifact) => artifact.id === agent.input_artifact_id);
  const resultArtifact = run?.artifacts.find((artifact) => artifact.id === agent.result_artifact_id);
  const entries: AgentWorkEntry[] = [
    {
      side: "system",
      title: "Assignment",
      body:
        cleanChatBody(assignmentArtifact?.content ?? "") ||
        `${agent.definition.name} was started by the project orchestrator for the current request.`,
    },
  ];
  if (task) {
    entries.push({
      side: "agent",
      title: "Execution",
      body:
        task.status === "completed"
          ? "I completed the assigned work and recorded a result for the orchestrator."
          : task.status === "leased"
            ? `I am currently running${task.lease_owner ? ` on ${task.lease_owner}` : ""}.`
            : "I am waiting for an available worker slot.",
    });
  }
  if (agent.result_artifact_id) {
    entries.push({
      side: "agent",
      title: "Result",
      body: cleanChatBody(resultArtifact?.content ?? "") || `Result artifact: ${agent.result_artifact_id.slice(0, 8)}.`,
    });
  }
  return entries;
}

export function cleanChatBody(body: string): string {
  const trimmed = body.trim();
  const protocolContent = extractProtocolFinalContent(trimmed);
  if (protocolContent) {
    return cleanChatBody(protocolContent);
  }
  const withoutModelPrefix = trimmed.replace(/^Model:\s+[^\n]+(?:\n\s*\n)?/, "").trim();
  const withoutMarkdownDecoration = withoutModelPrefix
    .replace(/\*\*/g, "")
    .replace(/__/g, "")
    .replace(/`/g, "")
    .replace(/^#{1,6}\s+/gm, "");
  return withoutMarkdownDecoration.trim() || trimmed;
}

function extractProtocolFinalContent(body: string): string | null {
  const candidates = [body, stripFencedJson(body), stripThinkBlocks(body)];
  for (const candidate of candidates) {
    const parsed = parseProtocolJson(candidate);
    if (parsed) return parsed;
  }
  const embedded = extractEmbeddedProtocolJson(stripThinkBlocks(body));
  return embedded;
}

function stripFencedJson(body: string): string {
  const trimmed = body.trim();
  if (!trimmed.startsWith("```")) return trimmed;
  const lines = trimmed.split(/\r?\n/);
  if (lines[0]?.startsWith("```")) lines.shift();
  if (lines[lines.length - 1]?.startsWith("```")) lines.pop();
  return lines.join("\n").trim();
}

function stripThinkBlocks(body: string): string {
  return body.replace(/<think>[\s\S]*?<\/think>/gi, "").trim();
}

function parseProtocolJson(body: string): string | null {
  try {
    const payload = JSON.parse(body) as {
      action?: unknown;
      content?: unknown;
      tool_calls?: { name?: unknown; input?: { path?: unknown; command?: unknown } }[];
    };
    if (payload.action === "final" && typeof payload.content === "string") {
      return payload.content;
    }
    if (payload.action === "tool_calls" && Array.isArray(payload.tool_calls)) {
      const calls = payload.tool_calls
        .map((call) => {
          const name = typeof call.name === "string" ? call.name : "workspace tool";
          const path = typeof call.input?.path === "string" ? ` for ${normalizeDisplayPath(call.input.path)}` : "";
          const command = typeof call.input?.command === "string" ? `: ${call.input.command}` : "";
          return `${name}${path}${command}`;
        })
        .join(", ");
      return calls ? `Requested brokered tool work: ${calls}.` : "Requested brokered tool work.";
    }
    return null;
  } catch {
    return null;
  }
}

function extractEmbeddedProtocolJson(body: string): string | null {
  const start = body.indexOf("{");
  if (start < 0) return null;
  for (let index = body.length; index > start; index -= 1) {
    const parsed = parseProtocolJson(body.slice(start, index));
    if (parsed) return parsed;
  }
  return null;
}

function compactSummary(body: string): string {
  const cleaned = cleanChatBody(body).replace(/\s+/g, " ").trim();
  if (cleaned.length <= 260) return cleaned;
  return `${cleaned.slice(0, 257).trimEnd()}...`;
}
