import { AgentRun, Project, RunState } from "../api";
import { AgentWorkEntry, ChatMessage } from "../types";
import { isDone } from "./status";

export function buildProjectChat(
  project: Project | null,
  run: RunState | null,
  subagents: AgentRun[],
): ChatMessage[] {
  if (!project || !run) return [];
  const root = run.agent_runs.find((agentRun) => agentRun.parent_agent_run_id === null);

  // Show the real result artifact content if available, otherwise the live run status.
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
      ? "Working…"
      : root?.status === "completed"
        ? "Done."
        : "Queued.";
  }

  return [
    {
      id: `${run.id}-user`,
      side: "user",
      title: "You",
      body: run.command,
      time: run.created_at,
    },
    {
      id: `${run.id}-orchestrator`,
      side: "orchestrator",
      title: root?.definition.name ?? "Project orchestrator",
      body: orchestratorBody,
      time: root?.created_at ?? run.created_at,
      status: root?.status ?? run.status,
    },
  ];
}

export function buildAgentWork(agent: AgentRun, run: RunState | null): AgentWorkEntry[] {
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
