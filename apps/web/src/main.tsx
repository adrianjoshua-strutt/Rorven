import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Bot,
  CheckCircle2,
  FolderPlus,
  MessageSquare,
  Play,
  RefreshCw,
  Send,
  Sparkles,
  User,
} from "lucide-react";
import {
  AgentRun,
  EventRecord,
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
type ChatMessage = {
  id: string;
  side: "user" | "agent";
  title: string;
  body: string;
  time: string;
  status?: string;
};

function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<RunState | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
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

  const agents = useMemo(
    () =>
      selectedRun?.agent_runs.filter((agentRun) => agentRun.parent_agent_run_id !== null) ?? [],
    [selectedRun],
  );

  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId) ?? agents[0] ?? null,
    [agents, selectedAgentId],
  );

  const chatMessages = useMemo(() => buildProjectChat(selectedProject, selectedRun), [
    selectedProject,
    selectedRun,
  ]);

  async function loadProjects() {
    setLoadState("loading");
    setError(null);
    try {
      const nextProjects = await listProjects();
      setProjects(nextProjects);
      const projectId = selectedProjectId ?? nextProjects[0]?.id ?? null;
      setSelectedProjectId(projectId);
      if (projectId) {
        await refreshProject(projectId);
      }
      setLoadState("idle");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load projects");
      setLoadState("error");
    }
  }

  async function refreshProject(projectId = selectedProjectId) {
    if (!projectId) return;
    const project = await getProject(projectId);
    setProjects((current) => [
      project,
      ...current.filter((candidate) => candidate.id !== project.id),
    ]);
    const currentRunId = selectedRun?.id ?? project.runs?.[0]?.id;
    if (currentRunId) {
      const run = await getRun(project.id, currentRunId);
      setSelectedRun(run);
      setSelectedAgentId((current) => current ?? run.agent_runs[1]?.id ?? null);
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
      setSelectedAgentId(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to create project");
    }
  }

  async function handleSubmitMessage(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedProjectId || !message.trim()) return;
    setError(null);
    try {
      const run = await submitRun(selectedProjectId, message);
      setSelectedRun(run);
      setSelectedAgentId(run.agent_runs[1]?.id ?? null);
      setMessage("");
      await refreshProject(selectedProjectId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to send message");
    }
  }

  async function handleWorkOnce() {
    if (!selectedProjectId || !selectedRun) return;
    setError(null);
    try {
      await workOnce();
      const run = await getRun(selectedProjectId, selectedRun.id);
      setSelectedRun(run);
      await refreshProject(selectedProjectId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to run worker");
    }
  }

  useEffect(() => {
    void loadProjects();
  }, []);

  return (
    <main className="app-shell">
      <aside className="projects-pane">
        <div className="brand">
          <div className="brand-mark">
            <Sparkles size={20} aria-hidden="true" />
          </div>
          <div>
            <strong>Rorven</strong>
            <span>Projects</span>
          </div>
        </div>

        <form className="new-project" onSubmit={handleCreateProject}>
          <label>
            <span>Name</span>
            <input
              value={newProject.name}
              onChange={(event) => setNewProject({ ...newProject, name: event.target.value })}
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
            <FolderPlus size={16} aria-hidden="true" />
            New project
          </button>
        </form>

        <nav className="project-list" aria-label="Projects">
          {projects.map((project) => (
            <button
              key={project.id}
              className={project.id === selectedProjectId ? "project-card active" : "project-card"}
              onClick={async () => {
                setSelectedProjectId(project.id);
                setSelectedRun(null);
                setSelectedAgentId(null);
                await refreshProject(project.id);
              }}
              type="button"
            >
              <strong>{project.name}</strong>
              <span>{project.runs?.length ?? 0} conversations</span>
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
          <button className="icon-button" onClick={() => void loadProjects()} type="button">
            <RefreshCw size={16} aria-hidden="true" />
            Refresh
          </button>
        </header>

        {error ? <div className="error-banner">{error}</div> : null}
        {loadState === "loading" ? <div className="quiet-note">Loading projects...</div> : null}

        <div className="message-list" aria-label="Project conversation">
          {chatMessages.length > 0 ? (
            chatMessages.map((item) => <ChatBubble item={item} key={item.id} />)
          ) : (
            <div className="empty-chat">
              <MessageSquare size={28} aria-hidden="true" />
              <strong>Start with a project message.</strong>
              <span>The orchestrator will create child agents and their work appears on the right.</span>
            </div>
          )}
        </div>

        <form className="composer" onSubmit={handleSubmitMessage}>
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Tell the orchestrator what to do..."
            rows={3}
          />
          <button className="send-button" disabled={!selectedProjectId} type="submit">
            <Send size={16} aria-hidden="true" />
            Send
          </button>
        </form>
      </section>

      <aside className="agents-pane">
        <div className="agents-header">
          <div>
            <p>Spawned agents</p>
            <h2>{agents.length ? `${agents.length} active agents` : "No agents yet"}</h2>
          </div>
          <button
            className="primary-button"
            disabled={!selectedRun}
            onClick={() => void handleWorkOnce()}
            type="button"
          >
            <Play size={16} aria-hidden="true" />
            Work once
          </button>
        </div>

        <div className="agent-list">
          {agents.map((agent) => (
            <button
              className={agent.id === selectedAgent?.id ? "agent-card active" : "agent-card"}
              key={agent.id}
              onClick={() => setSelectedAgentId(agent.id)}
              type="button"
            >
              <div className="agent-avatar">
                <Bot size={17} aria-hidden="true" />
              </div>
              <div>
                <strong>{agent.definition.name}</strong>
                <span>{agent.definition.model_profile}</span>
              </div>
              <StatusPill status={agent.status} />
            </button>
          ))}
        </div>

        <section className="agent-detail" aria-label="Agent work">
          {selectedAgent && selectedRun ? (
            <AgentTranscript agent={selectedAgent} events={selectedRun.events} />
          ) : (
            <div className="empty-agent">
              <Bot size={28} aria-hidden="true" />
              <strong>No agent selected.</strong>
              <span>Send a message to spawn work.</span>
            </div>
          )}
        </section>
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

function AgentTranscript({ agent, events }: { agent: AgentRun; events: EventRecord[] }) {
  const agentEvents = events.filter((event) => JSON.stringify(event.payload).includes(agent.id));
  return (
    <>
      <div className="agent-detail-header">
        <div className="agent-avatar large">
          <Bot size={20} aria-hidden="true" />
        </div>
        <div>
          <h3>{agent.definition.name}</h3>
          <p>
            v{agent.definition.version} / {agent.definition.model_profile}
          </p>
        </div>
        <StatusPill status={agent.status} />
      </div>

      <div className="agent-thread">
        <div className="agent-message">
          <strong>Assigned</strong>
          <p>This agent was spawned by the orchestrator for the selected project request.</p>
        </div>
        {agentEvents.map((event) => (
          <div className="agent-message" key={event.id}>
            <strong>{event.type}</strong>
            <p>{eventSummary(event)}</p>
          </div>
        ))}
        {agent.result_artifact_id ? (
          <div className="agent-message done">
            <CheckCircle2 size={16} aria-hidden="true" />
            <p>Result artifact {agent.result_artifact_id.slice(0, 8)} is ready.</p>
          </div>
        ) : null}
      </div>
    </>
  );
}

function StatusPill({ status }: { status: string }) {
  return <span className={`status-pill ${status}`}>{status}</span>;
}

function buildProjectChat(project: Project | null, run: RunState | null): ChatMessage[] {
  if (!project || !run) return [];
  const root = run.agent_runs.find((agentRun) => agentRun.parent_agent_run_id === null);
  const childAgents = run.agent_runs.filter((agentRun) => agentRun.parent_agent_run_id !== null);
  return [
    {
      id: `${run.id}-user`,
      side: "user",
      title: "You",
      body: run.command,
      time: run.created_at,
      status: run.status,
    },
    {
      id: `${run.id}-orchestrator`,
      side: "agent",
      title: root?.definition.name ?? "orchestrator",
      body: childAgents.length
        ? `I spawned ${childAgents.map((agent) => agent.definition.name).join(" and ")} for this request.`
        : "I am preparing the work plan.",
      time: root?.created_at ?? run.created_at,
      status: root?.status ?? run.status,
    },
    ...childAgents.map((agent) => ({
      id: agent.id,
      side: "agent" as const,
      title: agent.definition.name,
      body:
        agent.status === "completed"
          ? "I finished my assigned work and attached a result."
          : "I am queued for worker execution.",
      time: agent.created_at,
      status: agent.status,
    })),
  ];
}

function eventSummary(event: EventRecord) {
  if (event.type === "run.completed") return "Completed work for this run.";
  if (event.type === "run.queued") return "Queued for worker execution.";
  if (event.type === "task.leased") return "A worker picked up this task.";
  if (event.type === "task.completed") return "The task was marked complete.";
  return JSON.stringify(event.payload);
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

