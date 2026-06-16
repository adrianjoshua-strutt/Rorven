import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  Boxes,
  CheckCircle2,
  FolderPlus,
  GitBranch,
  Play,
  RefreshCw,
  Server,
  TerminalSquare,
} from "lucide-react";
import {
  AgentRun,
  Project,
  RunState,
  createProject,
  getProject,
  getRun,
  listProjects,
  submitRun,
  workOnce,
} from "./api";
import "./styles.css";

type LoadState = "idle" | "loading" | "error";

function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<RunState | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [newProject, setNewProject] = useState({
    name: "Rorven Local",
    allowed_root: "D:/Cloud/Dropbox/GitHub",
    workspace_root: "D:/Cloud/Dropbox/GitHub/rorven",
  });
  const [command, setCommand] = useState("Build the next durable platform slice.");

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  );

  async function loadProjects() {
    setLoadState("loading");
    setError(null);
    try {
      const nextProjects = await listProjects();
      setProjects(nextProjects);
      if (!selectedProjectId && nextProjects[0]) {
        setSelectedProjectId(nextProjects[0].id);
      }
      setLoadState("idle");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load projects");
      setLoadState("error");
    }
  }

  async function refreshSelectedProject(projectId = selectedProjectId) {
    if (!projectId) return;
    const project = await getProject(projectId);
    setProjects((current) => [
      project,
      ...current.filter((candidate) => candidate.id !== project.id),
    ]);
    if (!selectedRun && project.runs?.[0]) {
      setSelectedRun(await getRun(project.id, project.runs[0].id));
    }
  }

  async function handleCreateProject(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const project = await createProject(newProject);
      setProjects((current) => [project, ...current]);
      setSelectedProjectId(project.id);
      setSelectedRun(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to create project");
    }
  }

  async function handleSubmitRun(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedProjectId) return;
    setError(null);
    try {
      const run = await submitRun(selectedProjectId, command);
      setSelectedRun(run);
      await refreshSelectedProject(selectedProjectId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to submit run");
    }
  }

  async function handleWorkOnce() {
    if (!selectedProjectId || !selectedRun) return;
    setError(null);
    try {
      await workOnce();
      setSelectedRun(await getRun(selectedProjectId, selectedRun.id));
      await refreshSelectedProject(selectedProjectId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to run worker");
    }
  }

  useEffect(() => {
    void loadProjects();
  }, []);

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Boxes size={22} aria-hidden="true" />
          </div>
          <div>
            <strong>Rorven</strong>
            <span>Console</span>
          </div>
        </div>

        <form className="panel compact-form" onSubmit={handleCreateProject}>
          <div className="panel-title">
            <FolderPlus size={16} aria-hidden="true" />
            <span>Project</span>
          </div>
          <label>
            <span>Name</span>
            <input
              value={newProject.name}
              onChange={(event) => setNewProject({ ...newProject, name: event.target.value })}
            />
          </label>
          <label>
            <span>Allowed root</span>
            <input
              value={newProject.allowed_root}
              onChange={(event) =>
                setNewProject({ ...newProject, allowed_root: event.target.value })
              }
            />
          </label>
          <label>
            <span>Workspace</span>
            <input
              value={newProject.workspace_root}
              onChange={(event) =>
                setNewProject({ ...newProject, workspace_root: event.target.value })
              }
            />
          </label>
          <button className="primary" type="submit">
            <FolderPlus size={16} aria-hidden="true" />
            Create project
          </button>
        </form>

        <section className="project-list" aria-label="Projects">
          {projects.map((project) => (
            <button
              key={project.id}
              className={project.id === selectedProjectId ? "project selected" : "project"}
              onClick={async () => {
                setSelectedProjectId(project.id);
                setSelectedRun(null);
                await refreshSelectedProject(project.id);
              }}
              type="button"
            >
              <strong>{project.name}</strong>
              <span>{project.workspace.workspace_root}</span>
            </button>
          ))}
        </section>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Durable workbench</p>
            <h1>{selectedProject?.name ?? "No project selected"}</h1>
          </div>
          <div className="topbar-actions">
            <button className="ghost" onClick={() => void loadProjects()} type="button">
              <RefreshCw size={16} aria-hidden="true" />
              Refresh
            </button>
            <button
              className="primary"
              disabled={!selectedRun}
              onClick={() => void handleWorkOnce()}
              type="button"
            >
              <Play size={16} aria-hidden="true" />
              Work once
            </button>
          </div>
        </header>

        {error ? <div className="error">{error}</div> : null}
        {loadState === "loading" ? <div className="muted-row">Loading state...</div> : null}

        <div className="content-grid">
          <section className="panel run-command">
            <div className="panel-title">
              <TerminalSquare size={16} aria-hidden="true" />
              <span>Run command</span>
            </div>
            <form onSubmit={handleSubmitRun}>
              <textarea
                value={command}
                onChange={(event) => setCommand(event.target.value)}
                rows={4}
              />
              <button className="primary" disabled={!selectedProjectId} type="submit">
                <Play size={16} aria-hidden="true" />
                Submit run
              </button>
            </form>
          </section>

          <section className="panel status-panel">
            <div className="panel-title">
              <Server size={16} aria-hidden="true" />
              <span>Project runs</span>
            </div>
            <div className="run-list">
              {selectedProject?.runs?.map((run) => (
                <button
                  className={selectedRun?.id === run.id ? "run-row selected" : "run-row"}
                  key={run.id}
                  onClick={async () => {
                    if (!selectedProjectId) return;
                    setSelectedRun(await getRun(selectedProjectId, run.id));
                  }}
                  type="button"
                >
                  <span>{run.command}</span>
                  <StatusPill status={run.status} />
                </button>
              ))}
            </div>
          </section>
        </div>

        <section className="panel run-tree-panel">
          <div className="panel-title">
            <GitBranch size={16} aria-hidden="true" />
            <span>Run tree</span>
          </div>
          {selectedRun ? <RunTree run={selectedRun} /> : <EmptyRunTree />}
        </section>

        <div className="content-grid lower">
          <section className="panel">
            <div className="panel-title">
              <CheckCircle2 size={16} aria-hidden="true" />
              <span>Tasks</span>
            </div>
            <div className="task-table">
              {selectedRun?.tasks.map((task) => (
                <div className="task-row" key={task.id}>
                  <code>{task.id.slice(0, 8)}</code>
                  <span>{task.agent_run_id.slice(0, 8)}</span>
                  <StatusPill status={task.status} />
                </div>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="panel-title">
              <Activity size={16} aria-hidden="true" />
              <span>Events</span>
            </div>
            <div className="event-stream">
              {selectedRun?.events.slice(-10).map((event) => (
                <div className="event-row" key={event.id}>
                  <span>{event.type}</span>
                  <time>{new Date(event.occurred_at).toLocaleTimeString()}</time>
                </div>
              ))}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}

function RunTree({ run }: { run: RunState }) {
  const root = run.agent_runs.find((agentRun) => agentRun.parent_agent_run_id === null);
  const children = run.agent_runs.filter((agentRun) => agentRun.parent_agent_run_id !== null);
  return (
    <div className="run-tree">
      <div className="root-run">
        <AgentRunNode agentRun={root} fallbackLabel={run.command} />
      </div>
      <div className="branch-line" />
      <div className="child-runs">
        {children.map((agentRun) => (
          <AgentRunNode agentRun={agentRun} key={agentRun.id} />
        ))}
      </div>
    </div>
  );
}

function AgentRunNode({
  agentRun,
  fallbackLabel,
}: {
  agentRun?: AgentRun;
  fallbackLabel?: string;
}) {
  if (!agentRun) {
    return <div className="agent-node muted-node">{fallbackLabel ?? "Run pending"}</div>;
  }
  return (
    <div className="agent-node">
      <div>
        <strong>{agentRun.definition.name}</strong>
        <span>v{agentRun.definition.version}</span>
      </div>
      <StatusPill status={agentRun.status} />
      <code>{agentRun.definition.model_profile}</code>
    </div>
  );
}

function EmptyRunTree() {
  return <div className="empty-state">No run selected.</div>;
}

function StatusPill({ status }: { status: string }) {
  return <span className={`status ${status}`}>{status}</span>;
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

