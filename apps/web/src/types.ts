import { AgentRun } from "./api";

export type LoadState = "idle" | "loading" | "error";

export type ChatMessage = {
  id: string;
  side: "user" | "orchestrator";
  title: string;
  body: string;
  time: string;
  status?: string;
};

export type SelectedScope = "root" | "project" | "settings";

export type InspectedAgent =
  | { scope: "project"; id: string }
  | { scope: "root"; id: string };

export type RootAgentActivity = {
  id: string;
  name: string;
  modelProfile: string;
  status: string;
  createdAt: string;
  summary: string;
};

export type ActivityCard = {
  id: string;
  title: string;
  subtitle: string;
  status: string;
};

export type NewProjectDraft = {
  name: string;
  allowed_root: string;
  workspace_root: string;
};

export type AgentWorkEntry = {
  side: "system" | "agent";
  title: string;
  body: string;
};

export type ProjectAgentRun = AgentRun;
