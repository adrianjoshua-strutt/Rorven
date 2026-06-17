import { AgentRun, Project, RunState } from "../api";
import { AgentWorkEntry, ChatMessage } from "../types";
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
  const rootTranscript = persisted.filter((entry) => {
    if (entry.role === "user") return true;
    if (entry.title === "Project orchestrator" || entry.title === "orchestrator") return true;
    if (entry.agent_run_id === null) return true;
    const entryRun = entry.run_id === run?.id ? run : null;
    const agent = entryRun?.agent_runs.find((candidate) => candidate.id === entry.agent_run_id);
    return agent?.parent_agent_run_id === null;
  });
  const messages = rootTranscript.map((entry): ChatMessage => ({
    id: entry.id,
    side: entry.role === "user" ? "user" : "orchestrator",
    title: entry.role === "user" ? "You" : entry.title,
    body: entry.body,
    time: entry.created_at,
  }));
  const runs = [...(project.runs ?? [])].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );
  for (const projectRun of runs) {
    const hasUserEntry = rootTranscript.some(
      (entry) => entry.role === "user" && entry.run_id === projectRun.id,
    );
    if (!hasUserEntry) {
      messages.push({
        id: `${projectRun.id}-user`,
        side: "user",
        title: "You",
        body: projectRun.command,
        time: projectRun.created_at,
      });
    }
  }
  messages.sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());
  if (!run) return messages;
  const root = run.agent_runs.find((agentRun) => agentRun.parent_agent_run_id === null);
  const rootHasAssistantEntry = rootTranscript.some(
    (entry) => entry.run_id === run.id && entry.role === "assistant",
  );

  let orchestratorBody: string;
  if (root?.result_artifact_id) {
    orchestratorBody =
      run.artifacts.find((a) => a.id === root.result_artifact_id)?.content ??
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

  if (!rootHasAssistantEntry) {
    messages.push({
      id: `${run.id}-orchestrator`,
      side: "orchestrator",
      title: root?.definition.name ?? "Project orchestrator",
      body: orchestratorBody,
      time: root?.created_at ?? run.created_at,
      status: root?.status ?? run.status,
    });
  }
  return messages;
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
      body: entry.body,
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
        assignmentArtifact?.content ??
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
      body: resultArtifact?.content ?? `Result artifact: ${agent.result_artifact_id.slice(0, 8)}.`,
    });
  }
  return entries;
}
