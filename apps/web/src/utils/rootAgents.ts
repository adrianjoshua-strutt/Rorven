import { RootAgentActivity } from "../types";

export function chooseRootSubagents(command: string, createdAt: string): RootAgentActivity[] {
  const lower = command.toLowerCase();
  const agents: RootAgentActivity[] = [];

  if (lower.includes("create") || lower.includes("new project") || lower.includes("workspace")) {
    agents.push({
      id: `root-create-${crypto.randomUUID()}`,
      name: "project-creator",
      modelProfile: "balanced",
      status: "started",
      createdAt,
      summary: "Create or register a workspace-scoped project through the root project.",
    });
  }

  if (lower.includes("search") || lower.includes("find") || lower.includes("list")) {
    agents.push({
      id: `root-search-${crypto.randomUUID()}`,
      name: "project-searcher",
      modelProfile: "utility",
      status: "started",
      createdAt,
      summary: "Search local projects, runs, artifacts, and project metadata.",
    });
  }

  if (lower.includes("stat") || lower.includes("summary") || lower.includes("report")) {
    agents.push({
      id: `root-stats-${crypto.randomUUID()}`,
      name: "project-analyst",
      modelProfile: "utility",
      status: "started",
      createdAt,
      summary: "Summarize root-level project activity, run counts, and operational status.",
    });
  }

  if (agents.length === 0) {
    agents.push({
      id: `root-router-${crypto.randomUUID()}`,
      name: "root-router",
      modelProfile: "utility",
      status: "started",
      createdAt,
      summary: "Classify the request and decide which root-level project operation should run.",
    });
  }

  return agents;
}
