import { AgentRun, Project, RunState } from "../api";
import { AgentWorkEntry, ChatMessage, SubagentWorkSummary } from "../types";
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
  const runs = [...(project.runs ?? [])].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );
  if (runs.length > 0) {
    const messages: ChatMessage[] = [];
    for (const projectRun of runs) {
      const entriesForRun = rootTranscript.filter((entry) => entry.run_id === projectRun.id);
      const userEntry = entriesForRun.find((entry) => entry.role === "user" && entry.title === "You");
      messages.push({
        id: userEntry?.id ?? `${projectRun.id}-user`,
        side: "user",
        title: "You",
        body: cleanChatBody(userEntry?.body ?? projectRun.command),
        time: userEntry?.created_at ?? projectRun.created_at,
      });
      for (const entry of entriesForRun.filter((candidate) => candidate.role === "assistant")) {
        messages.push({
          id: entry.id,
          side: "orchestrator",
          title: entry.title,
          body: cleanChatBody(entry.body),
          time: entry.created_at,
        });
      }
    }
    appendSelectedRunPlaceholder(messages, run, subagents, rootTranscript);
    return messages;
  }
  const messages = rootTranscript.map((entry): ChatMessage => ({
    id: entry.id,
    side: entry.role === "user" ? "user" : "orchestrator",
    title: entry.role === "user" ? "You" : entry.title,
    body: cleanChatBody(entry.body),
    time: entry.created_at,
  }));
  appendSelectedRunPlaceholder(messages, run, subagents, rootTranscript);
  return messages;
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
  rootTranscript: { run_id: string; role: string }[],
): void {
  if (!run) return;
  const root = run.agent_runs.find((agentRun) => agentRun.parent_agent_run_id === null);
  const rootHasAssistantEntry = rootTranscript.some(
    (entry) => entry.run_id === run.id && entry.role === "assistant",
  );
  if (rootHasAssistantEntry) return;

  let orchestratorBody: string;
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
    time: root?.created_at ?? run.created_at,
    status: root?.status ?? run.status,
  });
}

export function buildSubagentSummaries(run: RunState | null, subagents: AgentRun[]): SubagentWorkSummary[] {
  if (!run || !subagents.length) return [];
  return subagents.map((agent) => {
    const entries = buildAgentWork(agent, run);
    const usefulEntry =
      [...entries].reverse().find((entry) => entry.side === "agent" && entry.body.trim()) ??
      [...entries].reverse().find((entry) => entry.side === "tool" && entry.body.trim()) ??
      entries[entries.length - 1];
    const approvals = run.approvals.filter((approval) => approval.agent_run_id === agent.id);
    return {
      id: agent.id,
      title: agent.definition.name,
      status: agent.status,
      summary: compactSummary(usefulEntry?.body ?? "No subagent output recorded yet."),
      detailCount: entries.length,
      approvalCount: approvals.length,
    };
  });
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
  const withoutModelPrefix = trimmed.replace(/^Model:\s+[^\n]+(?:\n\s*\n)?/, "").trim();
  const withoutMarkdownDecoration = withoutModelPrefix
    .replace(/\*\*/g, "")
    .replace(/__/g, "")
    .replace(/`/g, "")
    .replace(/^#{1,6}\s+/gm, "");
  return withoutMarkdownDecoration.trim() || trimmed;
}

function compactSummary(body: string): string {
  const cleaned = cleanChatBody(body).replace(/\s+/g, " ").trim();
  if (cleaned.length <= 260) return cleaned;
  return `${cleaned.slice(0, 257).trimEnd()}...`;
}
