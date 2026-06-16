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
  const finished = subagents.filter((agent) => isDone(agent.status)).length;
  const running = subagents.length - finished;
  const summary =
    finished === subagents.length && subagents.length > 0
      ? root?.result_artifact_id
        ? (run.artifacts.find((artifact) => artifact.id === root.result_artifact_id)?.content ??
          `All ${subagents.length} subagents finished.`)
        : `All ${subagents.length} subagents finished. I am preparing the final summary.`
      : subagents.length
        ? `I started ${subagents.length} subagents. ${running} still running, ${finished} finished.`
        : "I am preparing the work plan.";

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
      body: summary,
      time: root?.created_at ?? run.created_at,
      status: root?.status ?? run.status,
    },
  ];
}

export function buildAgentWork(agent: AgentRun, run: RunState | null): AgentWorkEntry[] {
  const task = run?.tasks.find((candidate) => candidate.agent_run_id === agent.id);
  const resultArtifact = run?.artifacts.find((artifact) => artifact.id === agent.result_artifact_id);
  const entries: AgentWorkEntry[] = [
    {
      side: "system",
      title: "Assignment",
      body: `${agent.definition.name} was started by the project orchestrator for the current request.`,
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
