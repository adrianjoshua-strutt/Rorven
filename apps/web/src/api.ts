export type Project = {
  id: string;
  name: string;
  workspace: {
    allowed_root: string;
    workspace_root: string;
  };
  created_at: string;
  runs?: RunSummary[];
};

export type RunSummary = {
  id: string;
  project_id: string;
  status: string;
  command: string;
  created_at: string;
  completed_at: string | null;
};

export type AgentRun = {
  id: string;
  run_id: string;
  project_id: string;
  parent_agent_run_id: string | null;
  definition: {
    name: string;
    version: string;
    model_profile: string;
  };
  status: string;
  input_artifact_id: string | null;
  result_artifact_id: string | null;
  created_at: string;
};

export type Task = {
  id: string;
  agent_run_id: string;
  status: string;
  lease_owner: string | null;
  lease_expires_at: string | null;
  created_at: string;
};

export type EventRecord = {
  id: string;
  project_id: string;
  run_id: string | null;
  type: string;
  payload: Record<string, unknown>;
  occurred_at: string;
};

export type ArtifactRecord = {
  id: string;
  project_id: string;
  run_id: string;
  kind: string;
  uri: string;
  content: string;
  created_at: string;
};

export type RunState = RunSummary & {
  agent_runs: AgentRun[];
  tasks: Task[];
  events: EventRecord[];
  artifacts: ArtifactRecord[];
};

export type SettingsSnapshot = {
  credentials: {
    id: string;
    label: string;
    adapter: string;
    environment_variable: string;
    configured: boolean;
    raw_value_visible: boolean;
    notes: string;
  }[];
  model_profiles: {
    name: string;
    adapter: string;
    model_id: string;
    model_id_configured: boolean;
    request_timeout_seconds: number | null;
    source: string;
  }[];
  runtime: {
    active_runtime_adapter: string;
    planned_runtime_adapter: string;
    active_model_gateway: string;
    system_of_record: string;
    planned_system_of_record: string;
    data_dir: string;
  };
  policy: {
    destructive_actions: string;
    secret_exposure: string;
    default_tool_access: string;
  };
  project_defaults: {
    workspace_root_source: string;
    memory_backend: string;
    sandbox: string;
  };
};

export type RootActivity = {
  id: string;
  name: string;
  modelProfile: string;
  status: string;
  createdAt: string;
  summary: string;
};

export type RootDashboard = {
  messages: {
    id: string;
    side: "user" | "orchestrator";
    title: string;
    body: string;
    time: string;
    status?: string;
  }[];
  activities: RootActivity[];
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "content-type": "application/json",
      ...init?.headers,
    },
    ...init,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function listProjects(): Promise<Project[]> {
  const payload = await request<{ projects: Project[] }>("/projects");
  return payload.projects;
}

export async function getSettings(): Promise<SettingsSnapshot> {
  const payload = await request<{ settings: SettingsSnapshot }>("/settings");
  return payload.settings;
}

export async function getRootDashboard(): Promise<RootDashboard> {
  const payload = await request<{ root: RootDashboard }>("/root");
  return payload.root;
}

export async function submitRootMessage(message: string): Promise<RootDashboard> {
  const payload = await request<{ root: RootDashboard }>("/root/messages", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
  return payload.root;
}

export async function createProject(input: {
  name: string;
  allowed_root: string;
  workspace_root: string;
}): Promise<Project> {
  const payload = await request<{ project: Project }>("/projects", {
    method: "POST",
    body: JSON.stringify(input),
  });
  return payload.project;
}

export async function getProject(projectId: string): Promise<Project> {
  const payload = await request<{ project: Project }>(`/projects/${projectId}`);
  return payload.project;
}

export async function submitRun(projectId: string, command: string): Promise<RunState> {
  const payload = await request<{ run: RunState }>(`/projects/${projectId}/runs`, {
    method: "POST",
    body: JSON.stringify({ command }),
  });
  return payload.run;
}

export async function getRun(projectId: string, runId: string): Promise<RunState> {
  const payload = await request<{ run: RunState }>(`/projects/${projectId}/runs/${runId}`);
  return payload.run;
}

export async function workOnce(): Promise<Task[]> {
  const payload = await request<{ completed_tasks: Task[] }>("/worker/work-once", {
    method: "POST",
    body: JSON.stringify({ worker_id: "web-console", limit: 2 }),
  });
  return payload.completed_tasks;
}
