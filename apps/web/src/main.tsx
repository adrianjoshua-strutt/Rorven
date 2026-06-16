import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Bot,
  CircleDashed,
  ChevronLeft,
  FolderPlus,
  Menu,
  MessageSquare,
  Plus,
  Search,
  Send,
  Settings,
  Sparkles,
  User,
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
} from "./api";
import "./styles.css";

type LoadState = "idle" | "loading" | "error";
type ChatMessage = {
  id: string;
  side: "user" | "orchestrator";
  title: string;
  body: string;
  time: string;
  status?: string;
};
type SelectedScope = "root" | "project";

function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedScope, setSelectedScope] = useState<SelectedScope>("root");
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<RunState | null>(null);
  const [inspectedAgentId, setInspectedAgentId] = useState<string | null>(null);
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [newProject, setNewProject] = useState({
    name: "Rorven Local",
    allowed_root: "D:/Cloud/Dropbox/GitHub",
    workspace_root: "D:/Cloud/Dropbox/GitHub/rorven",
  });
  const [message, setMessage] = useState("Build the next durable platform slice.");

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  );

  const subagents = useMemo(
    () =>
      selectedRun?.agent_runs.filter((agentRun) => agentRun.parent_agent_run_id !== null) ?? [],
    [selectedRun],
  );

  const runningSubagents = subagents.filter((agent) => !isDone(agent.status));
  const finishedSubagents = subagents.filter((agent) => isDone(agent.status));
  const inspectedAgent = subagents.find((agent) => agent.id === inspectedAgentId) ?? null;

  const chatMessages = useMemo(() => buildProjectChat(selectedProject, selectedRun, subagents), [
    selectedProject,
    selectedRun,
    subagents,
  ]);

  async function loadInitialState() {
    setLoadState("loading");
    setError(null);
    try {
      const nextProjects = await listProjects();
      setProjects(nextProjects);
      const projectId = selectedScope === "project" ? selectedProjectId : null;
      if (projectId) {
        await loadProject(projectId, selectedRun?.id);
      }
      setLoadState("idle");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load projects");
      setLoadState("error");
    }
  }

  async function loadProject(projectId: string, preferredRunId?: string | null) {
    const project = await getProject(projectId);
    setProjects((current) => [
      project,
      ...current.filter((candidate) => candidate.id !== project.id),
    ]);
    const runId =
      preferredRunId && project.runs?.some((run) => run.id === preferredRunId)
        ? preferredRunId
        : project.runs?.[0]?.id;
    if (runId) {
      setSelectedRun(await getRun(project.id, runId));
    } else {
      setSelectedRun(null);
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
      setInspectedAgentId(null);
      setShowCreateProject(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to create project");
    }
  }

  async function handleSubmitMessage(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedProjectId || !message.trim()) return;
    setError(null);
    try {
      const run = await submitRun(selectedProjectId, message.trim());
      setSelectedRun(run);
      setInspectedAgentId(null);
      setMessage("");
      await loadProject(selectedProjectId, run.id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to send message");
    }
  }

  useEffect(() => {
    void loadInitialState();
  }, []);

  useEffect(() => {
    if (!selectedProjectId) return;
    const id = window.setInterval(() => {
      void loadProject(selectedProjectId, selectedRun?.id);
    }, 2500);
    return () => window.clearInterval(id);
  }, [selectedProjectId, selectedRun?.id]);

  return (
    <main className="app-shell">
      <aside className="projects-pane">
        <div className="brand">
          <div className="brand-mark">
            <Sparkles size={19} aria-hidden="true" />
          </div>
          <div>
            <strong>Rorven</strong>
            <span>Durable workbench</span>
          </div>
        </div>

        <button
          className={selectedScope === "root" ? "root-project active" : "root-project"}
          onClick={() => {
            setSelectedScope("root");
            setSelectedProjectId(null);
            setSelectedRun(null);
            setInspectedAgentId(null);
          }}
          type="button"
        >
          <strong>Root project</strong>
          <span>Project search, statistics, setup</span>
        </button>

        <div className="sidebar-actions">
          <button className="small-button" onClick={() => setShowCreateProject(true)} type="button">
            <Plus size={14} aria-hidden="true" />
            Project
          </button>
          <button className="small-button" onClick={() => setShowSettings(true)} type="button">
            <Settings size={14} aria-hidden="true" />
            Settings
          </button>
        </div>

        <div className="section-label">
          <Search size={14} aria-hidden="true" />
          <span>Your projects</span>
        </div>

        <nav className="project-list" aria-label="Projects">
          {projects.map((project) => (
            <button
              key={project.id}
              className={
                selectedScope === "project" && project.id === selectedProjectId
                  ? "project-card active"
                  : "project-card"
              }
              onClick={async () => {
                setSelectedProjectId(project.id);
                setSelectedScope("project");
                setSelectedRun(null);
                setInspectedAgentId(null);
                await loadProject(project.id, null);
              }}
              type="button"
            >
              <strong>{project.name}</strong>
              <span>{project.workspace.workspace_root}</span>
            </button>
          ))}
        </nav>
      </aside>

      <section className="chat-pane">
        {inspectedAgent ? (
          <AgentWorkView agent={inspectedAgent} run={selectedRun} onBack={() => setInspectedAgentId(null)} />
        ) : selectedScope === "root" ? (
          <RootProjectView projectCount={projects.length} />
        ) : (
          <>
            <header className="chat-header">
              <div>
                <p>{selectedProject?.workspace.workspace_root ?? "No workspace selected"}</p>
                <h1>{selectedProject?.name ?? "Choose a project"}</h1>
              </div>
              <ConnectionState state={loadState} />
            </header>

            {error ? <div className="error-banner">{error}</div> : null}

            <div className="message-list" aria-label="Project orchestrator chat">
              {chatMessages.length > 0 ? (
                chatMessages.map((item) => <ChatBubble item={item} key={item.id} />)
              ) : (
                <div className="empty-chat">
                  <MessageSquare size={28} aria-hidden="true" />
                  <strong>Talk to the project orchestrator.</strong>
                  <span>Subagents run in the background and appear in the activity rail.</span>
                </div>
              )}
            </div>

            <form className="composer" onSubmit={handleSubmitMessage}>
              <textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Message the project orchestrator"
                rows={1}
              />
              <button className="send-button" disabled={!selectedProjectId} type="submit">
                <Send size={16} aria-hidden="true" />
                Send
              </button>
            </form>
          </>
        )}
      </section>

      <aside className="subagents-pane">
        <header className="subagents-header">
          <p>Subagent activity</p>
          <h2>{subagents.length ? `${subagents.length} spawned` : "Idle"}</h2>
        </header>

        <SubagentGroup
          title="Running"
          agents={runningSubagents}
          emptyText="No active subagents."
          onInspect={(agent) => setInspectedAgentId(agent.id)}
        />
        <SubagentGroup
          title="Finished"
          agents={finishedSubagents}
          emptyText="No completed subagents."
          onInspect={(agent) => setInspectedAgentId(agent.id)}
        />
      </aside>

      {showCreateProject ? (
        <Modal title="Create project" onClose={() => setShowCreateProject(false)}>
          <form className="modal-form" onSubmit={handleCreateProject}>
            <label>
              <span>Name</span>
              <input
                value={newProject.name}
                onChange={(event) => setNewProject({ ...newProject, name: event.target.value })}
              />
            </label>
            <label>
              <span>Workspace root</span>
              <input
                value={newProject.workspace_root}
                onChange={(event) =>
                  setNewProject({ ...newProject, workspace_root: event.target.value })
                }
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
            <button className="primary-button" type="submit">
              Create project
            </button>
          </form>
        </Modal>
      ) : null}

      {showSettings ? (
        <Modal title="Settings" onClose={() => setShowSettings(false)}>
          <div className="settings-list">
            <div>
              <strong>API endpoint</strong>
              <span>{import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"}</span>
            </div>
            <div>
              <strong>Runtime</strong>
              <span>Local deterministic adapter</span>
            </div>
            <div>
              <strong>Frontend framework</strong>
              <span>React + Vite, custom CSS tokens, lucide icons</span>
            </div>
          </div>
        </Modal>
      ) : null}
    </main>
  );
}

function ChatBubble({ item }: { item: ChatMessage }) {
  return (
    <article className={`chat-bubble ${item.side}`}>
      <div className="bubble-icon">
        {item.side === "user" ? <User size={16} aria-hidden="true" /> : <Bot size={16} aria-hidden="true" />}
      </div>
      <div className="bubble-body">
        <div className="bubble-meta">
          <strong>{item.title}</strong>
          <time>{new Date(item.time).toLocaleTimeString()}</time>
        </div>
        <p>{item.body}</p>
        {item.status ? <StatusPill status={item.status} /> : null}
      </div>
    </article>
  );
}

function RootProjectView({ projectCount }: { projectCount: number }) {
  return (
    <section className="root-view">
      <header className="chat-header">
        <div>
          <p>System project</p>
          <h1>Root project</h1>
        </div>
        <ConnectionState state="idle" />
      </header>
      <div className="root-content">
        <article>
          <strong>Projects</strong>
          <span>{projectCount}</span>
          <p>Browse workspace-scoped projects from the left rail.</p>
        </article>
        <article>
          <strong>Search</strong>
          <span>Planned</span>
          <p>Find projects, memories, runs, and artifacts across the local installation.</p>
        </article>
        <article>
          <strong>Statistics</strong>
          <span>Planned</span>
          <p>Track agent runs, costs, model profiles, failures, and recovery events.</p>
        </article>
      </div>
    </section>
  );
}

function SubagentGroup({
  title,
  agents,
  emptyText,
  onInspect,
}: {
  title: string;
  agents: AgentRun[];
  emptyText: string;
  onInspect: (agent: AgentRun) => void;
}) {
  return (
    <section className="subagent-group">
      <div className="subagent-group-title">
        <span>{title}</span>
        <strong>{agents.length}</strong>
      </div>
      {agents.length ? (
        <div className="subagent-list">
          {agents.map((agent) => (
            <button className="subagent-card" key={agent.id} onClick={() => onInspect(agent)} type="button">
              <div className="agent-avatar">
                <Bot size={17} aria-hidden="true" />
              </div>
              <div className="subagent-copy">
                <strong>{agent.definition.name}</strong>
                <span>
                  {agent.definition.model_profile} / run {agent.id.slice(0, 8)}
                </span>
              </div>
              <StatusPill status={agent.status} />
            </button>
          ))}
        </div>
      ) : (
        <div className="subagent-empty">{emptyText}</div>
      )}
    </section>
  );
}

function AgentWorkView({
  agent,
  run,
  onBack,
}: {
  agent: AgentRun;
  run: RunState | null;
  onBack: () => void;
}) {
  const entries = buildAgentWork(agent, run);
  return (
    <section className="agent-work-view">
      <header className="agent-work-header">
        <button className="back-button" onClick={onBack} type="button" aria-label="Back to project chat">
          <ChevronLeft size={18} aria-hidden="true" />
        </button>
        <div>
          <p>Subagent run</p>
          <h1>{agent.definition.name}</h1>
        </div>
        <StatusPill status={agent.status} />
      </header>

      <div className="agent-work-meta">
        <div>
          <strong>Model profile</strong>
          <span>{agent.definition.model_profile}</span>
        </div>
        <div>
          <strong>Version</strong>
          <span>{agent.definition.version}</span>
        </div>
        <div>
          <strong>Run id</strong>
          <span>{agent.id.slice(0, 8)}</span>
        </div>
      </div>

      <div className="agent-work-log">
        {entries.map((entry) => (
          <article className={`work-entry ${entry.side}`} key={entry.title}>
            <div className="bubble-icon">
              {entry.side === "system" ? <User size={16} aria-hidden="true" /> : <Bot size={16} aria-hidden="true" />}
            </div>
            <div>
              <strong>{entry.title}</strong>
              <p>{entry.body}</p>
            </div>
          </article>
        ))}
      </div>

      <div className="agent-interrupt">
        <input placeholder="Interrupt or add context for this subagent" />
        <button className="secondary-button" type="button">
          Interrupt
        </button>
      </div>
    </section>
  );
}

function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal" role="dialog" aria-modal="true" aria-label={title}>
        <header className="modal-header">
          <h2>{title}</h2>
          <button className="small-button" onClick={onClose} type="button">
            Close
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}

function ConnectionState({ state }: { state: LoadState }) {
  return (
    <div className={`connection-state ${state}`}>
      <CircleDashed size={14} aria-hidden="true" />
      <span>{state === "loading" ? "Syncing" : state === "error" ? "Offline" : "Live"}</span>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  return <span className={`status-pill ${status}`}>{status}</span>;
}

function buildProjectChat(
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
      ? `All ${subagents.length} subagents finished. I am ready to summarize the result.`
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

function isDone(status: string) {
  return status === "completed" || status === "failed" || status === "canceled";
}

function buildAgentWork(agent: AgentRun, run: RunState | null) {
  const task = run?.tasks.find((candidate) => candidate.agent_run_id === agent.id);
  const entries = [
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
      body: `My result artifact is available: ${agent.result_artifact_id.slice(0, 8)}.`,
    });
  }
  return entries;
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
