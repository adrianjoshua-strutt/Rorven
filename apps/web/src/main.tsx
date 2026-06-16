import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Bot,
  CircleDashed,
  FolderPlus,
  MessageSquare,
  Search,
  Send,
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
      const projectId = selectedProjectId ?? nextProjects[0]?.id ?? null;
      setSelectedProjectId(projectId);
      if (projectId) {
        await loadProject(projectId);
      }
      setLoadState("idle");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load projects");
      setLoadState("error");
    }
  }

  async function loadProject(projectId: string, preferredRunId = selectedRun?.id) {
    const project = await getProject(projectId);
    setProjects((current) => [
      project,
      ...current.filter((candidate) => candidate.id !== project.id),
    ]);
    const runId = preferredRunId ?? project.runs?.[0]?.id;
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
      void loadProject(selectedProjectId);
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

        <button className="root-project" type="button">
          <strong>Root project</strong>
          <span>Project search, statistics, setup</span>
        </button>

        <form className="new-project" onSubmit={handleCreateProject}>
          <div className="section-label">
            <FolderPlus size={14} aria-hidden="true" />
            <span>New workspace project</span>
          </div>
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
            Create
          </button>
        </form>

        <div className="section-label">
          <Search size={14} aria-hidden="true" />
          <span>Projects</span>
        </div>

        <nav className="project-list" aria-label="Projects">
          {projects.map((project) => (
            <button
              key={project.id}
              className={project.id === selectedProjectId ? "project-card active" : "project-card"}
              onClick={async () => {
                setSelectedProjectId(project.id);
                await loadProject(project.id);
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
            placeholder="Tell the project orchestrator what to do..."
            rows={3}
          />
          <button className="send-button" disabled={!selectedProjectId} type="submit">
            <Send size={16} aria-hidden="true" />
            Send
          </button>
        </form>
      </section>

      <aside className="subagents-pane">
        <header className="subagents-header">
          <p>Subagent activity</p>
          <h2>{subagents.length ? `${subagents.length} spawned` : "Idle"}</h2>
        </header>

        <SubagentGroup title="Running" agents={runningSubagents} emptyText="No active subagents." />
        <SubagentGroup title="Finished" agents={finishedSubagents} emptyText="No completed subagents." />
      </aside>
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

function SubagentGroup({
  title,
  agents,
  emptyText,
}: {
  title: string;
  agents: AgentRun[];
  emptyText: string;
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
            <article className="subagent-card" key={agent.id}>
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
            </article>
          ))}
        </div>
      ) : (
        <div className="subagent-empty">{emptyText}</div>
      )}
    </section>
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

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

