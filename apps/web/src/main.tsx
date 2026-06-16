import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ActionIcon,
  Badge,
  Button,
  Group,
  MantineProvider,
  Modal as MantineModal,
  Paper,
  SimpleGrid,
  Table,
  Text,
  TextInput,
  Textarea,
  createTheme,
} from "@mantine/core";
import "@mantine/core/styles.css";
import {
  Bot,
  CircleDashed,
  ChevronLeft,
  Database,
  KeyRound,
  Layers3,
  MessageSquare,
  Plus,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  User,
} from "lucide-react";
import {
  AgentRun,
  Project,
  RunState,
  SettingsSnapshot,
  createProject,
  getSettings,
  getProject,
  getRun,
  listProjects,
  submitRun,
} from "./api";
import "./styles.css";

const theme = createTheme({
  primaryColor: "teal",
  defaultRadius: "xs",
  fontFamily: "Aptos, Segoe UI, system-ui, sans-serif",
  headings: {
    fontFamily: "Aptos, Segoe UI, system-ui, sans-serif",
  },
});

type LoadState = "idle" | "loading" | "error";
type ChatMessage = {
  id: string;
  side: "user" | "orchestrator";
  title: string;
  body: string;
  time: string;
  status?: string;
};
type SelectedScope = "root" | "project" | "settings";
type InspectedAgent =
  | { scope: "project"; id: string }
  | { scope: "root"; id: string };
type RootAgentActivity = {
  id: string;
  name: string;
  modelProfile: string;
  status: string;
  createdAt: string;
  summary: string;
};
type ActivityCard = {
  id: string;
  title: string;
  subtitle: string;
  status: string;
};

function App() {
  const projectLoadSequence = useRef(0);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedScope, setSelectedScope] = useState<SelectedScope>("root");
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<RunState | null>(null);
  const [inspectedAgent, setInspectedAgent] = useState<InspectedAgent | null>(null);
  const [rootMessages, setRootMessages] = useState<ChatMessage[]>(() => [
    {
      id: "root-orchestrator-ready",
      side: "orchestrator",
      title: "Root orchestrator",
      body:
        "I manage the local Rorven installation. Ask me to create projects, find projects, inspect runs, or summarize workspace activity.",
      time: new Date().toISOString(),
      status: "ready",
    },
  ]);
  const [rootSubagents, setRootSubagents] = useState<RootAgentActivity[]>([]);
  const [settingsSnapshot, setSettingsSnapshot] = useState<SettingsSnapshot | null>(null);
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [settingsLoadState, setSettingsLoadState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [newProject, setNewProject] = useState({
    name: "Rorven Local",
    allowed_root: "D:/Cloud/Dropbox/GitHub",
    workspace_root: "D:/Cloud/Dropbox/GitHub/rorven",
  });
  const [rootMessage, setRootMessage] = useState("Create a new project for this repository.");
  const [message, setMessage] = useState("Build the next durable platform slice.");

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  );

  const subagents = useMemo(
    () =>
      selectedScope === "project"
        ? selectedRun?.agent_runs.filter((agentRun) => agentRun.parent_agent_run_id !== null) ?? []
        : [],
    [selectedScope, selectedRun],
  );

  const activityCards = useMemo<ActivityCard[]>(() => {
    if (selectedScope === "root") {
      return rootSubagents.map((agent) => ({
        id: agent.id,
        title: agent.name,
        subtitle: `${agent.modelProfile} / root run ${agent.id.slice(0, 8)}`,
        status: agent.status,
      }));
    }
    return subagents.map((agent) => ({
      id: agent.id,
      title: agent.definition.name,
      subtitle: `${agent.definition.model_profile} / run ${agent.id.slice(0, 8)}`,
      status: agent.status,
    }));
  }, [rootSubagents, selectedScope, subagents]);
  const runningSubagents = activityCards.filter((agent) => !isDone(agent.status));
  const finishedSubagents = activityCards.filter((agent) => isDone(agent.status));
  const inspectedProjectAgent =
    inspectedAgent?.scope === "project"
      ? subagents.find((agent) => agent.id === inspectedAgent.id) ?? null
      : null;
  const inspectedRootAgent =
    inspectedAgent?.scope === "root"
      ? rootSubagents.find((agent) => agent.id === inspectedAgent.id) ?? null
      : null;

  const chatMessages = useMemo(() => buildProjectChat(selectedProject, selectedRun, subagents), [
    selectedProject,
    selectedRun,
    subagents,
  ]);

  async function loadInitialState() {
    setLoadState("loading");
    setSettingsLoadState("loading");
    setError(null);
    try {
      const [nextProjects, nextSettings] = await Promise.all([listProjects(), getSettings()]);
      setProjects(nextProjects);
      setSettingsSnapshot(nextSettings);
      const projectId = selectedScope === "project" ? selectedProjectId : null;
      if (projectId) {
        await loadProject(projectId, selectedRun?.id);
      }
      setLoadState("idle");
      setSettingsLoadState("idle");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load projects");
      setLoadState("error");
      setSettingsLoadState("error");
    }
  }

  async function loadSettings() {
    setSettingsLoadState("loading");
    setError(null);
    try {
      setSettingsSnapshot(await getSettings());
      setSettingsLoadState("idle");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load settings");
      setSettingsLoadState("error");
    }
  }

  async function loadProject(
    projectId: string,
    preferredRunId?: string | null,
    loadToken = projectLoadSequence.current,
  ) {
    const project = await getProject(projectId);
    setProjects((current) => replaceProjectPreservingOrder(current, project));
    if (loadToken !== projectLoadSequence.current) {
      return;
    }
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
      const loadToken = ++projectLoadSequence.current;
      setSelectedProjectId(project.id);
      setSelectedScope("project");
      setSelectedRun(null);
      setInspectedAgent(null);
      setShowCreateProject(false);
      await loadProject(project.id, null, loadToken);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to create project");
    }
  }

  async function handleSubmitMessage(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedProjectId || !message.trim()) return;
    setError(null);
    try {
      const loadToken = projectLoadSequence.current;
      const run = await submitRun(selectedProjectId, message.trim());
      setSelectedRun(run);
      setInspectedAgent(null);
      setMessage("");
      await loadProject(selectedProjectId, run.id, loadToken);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to send message");
    }
  }

  function handleSubmitRootMessage(event: React.FormEvent) {
    event.preventDefault();
    const command = rootMessage.trim();
    if (!command) return;

    const now = new Date().toISOString();
    const spawned = chooseRootSubagents(command, now);
    setRootMessages((current) => [
      ...current,
      {
        id: `root-user-${now}`,
        side: "user",
        title: "You",
        body: command,
        time: now,
      },
      {
        id: `root-orchestrator-${now}`,
        side: "orchestrator",
        title: "Root orchestrator",
        body: spawned.length
          ? `I started ${spawned.length} root subagent${spawned.length === 1 ? "" : "s"} for this request.`
          : "I can route this through root-level project tools once the durable root runtime is wired.",
        time: now,
        status: spawned.length ? "started" : "waiting",
      },
    ]);
    setRootSubagents((current) => [...spawned, ...current]);
    setRootMessage("");
  }

  useEffect(() => {
    void loadInitialState();
  }, []);

  useEffect(() => {
    if (selectedScope !== "project" || !selectedProjectId) return;
    const id = window.setInterval(() => {
      void loadProject(selectedProjectId, selectedRun?.id);
    }, 2500);
    return () => window.clearInterval(id);
  }, [selectedScope, selectedProjectId, selectedRun?.id]);

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
            projectLoadSequence.current += 1;
            setSelectedScope("root");
            setSelectedProjectId(null);
            setSelectedRun(null);
            setInspectedAgent(null);
          }}
          type="button"
        >
          <strong>Root project</strong>
          <span>Project search, statistics, setup</span>
        </button>

        <button
          className={selectedScope === "settings" ? "root-project active" : "root-project"}
          onClick={() => {
            projectLoadSequence.current += 1;
            setSelectedScope("settings");
            setSelectedProjectId(null);
            setSelectedRun(null);
            setInspectedAgent(null);
            void loadSettings();
          }}
          type="button"
        >
          <strong>Settings</strong>
          <span>Credentials, model tiers, runtime</span>
        </button>

        <div className="sidebar-actions">
          <Button
            className="small-button"
            leftSection={<Plus size={14} aria-hidden="true" />}
            onClick={() => setShowCreateProject(true)}
            size="xs"
            type="button"
            variant="light"
          >
            Project
          </Button>
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
                const loadToken = ++projectLoadSequence.current;
                setSelectedProjectId(project.id);
                setSelectedScope("project");
                setSelectedRun(null);
                setInspectedAgent(null);
                await loadProject(project.id, null, loadToken);
              }}
              type="button"
            >
              <strong>{project.name}</strong>
              <span>{project.workspace.workspace_root}</span>
              <small>{formatProjectCreatedAt(project.created_at)}</small>
            </button>
          ))}
        </nav>
      </aside>

      <section className="chat-pane">
        {inspectedProjectAgent ? (
          <AgentWorkView
            agent={inspectedProjectAgent}
            run={selectedRun}
            onBack={() => setInspectedAgent(null)}
          />
        ) : inspectedRootAgent ? (
          <RootAgentWorkView
            agent={inspectedRootAgent}
            onBack={() => setInspectedAgent(null)}
          />
        ) : selectedScope === "root" ? (
          <RootProjectView
            messages={rootMessages}
            message={rootMessage}
            onMessageChange={setRootMessage}
            onSubmit={handleSubmitRootMessage}
          />
        ) : selectedScope === "settings" ? (
          <SettingsView
            apiEndpoint={import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"}
            loadState={settingsLoadState}
            settings={settingsSnapshot}
            onReload={() => void loadSettings()}
          />
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
              <Textarea
                className="composer-input"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Message the project orchestrator"
                autosize={false}
              />
              <Button
                className="send-button"
                disabled={!selectedProjectId}
                leftSection={<Send size={16} aria-hidden="true" />}
                type="submit"
              >
                Send
              </Button>
            </form>
          </>
        )}
      </section>

      <aside className="subagents-pane">
        <header className="subagents-header">
          <p>Subagent activity</p>
          <h2>{activityCards.length ? `${activityCards.length} spawned` : "Idle"}</h2>
        </header>

        <SubagentGroup
          title="Running"
          agents={runningSubagents}
          emptyText="No active subagents."
          onInspect={(agent) =>
            setInspectedAgent({ scope: selectedScope === "root" ? "root" : "project", id: agent.id })
          }
        />
        <SubagentGroup
          title="Finished"
          agents={finishedSubagents}
          emptyText="No completed subagents."
          onInspect={(agent) =>
            setInspectedAgent({ scope: selectedScope === "root" ? "root" : "project", id: agent.id })
          }
        />
      </aside>

      {showCreateProject ? (
        <Modal title="Create project" onClose={() => setShowCreateProject(false)}>
          <form className="modal-form" onSubmit={handleCreateProject}>
            <TextInput
              label="Name"
              value={newProject.name}
              onChange={(event) => setNewProject({ ...newProject, name: event.target.value })}
            />
            <TextInput
              label="Workspace root"
              value={newProject.workspace_root}
              onChange={(event) =>
                setNewProject({ ...newProject, workspace_root: event.target.value })
              }
            />
            <TextInput
              label="Allowed root"
              value={newProject.allowed_root}
              onChange={(event) =>
                setNewProject({ ...newProject, allowed_root: event.target.value })
              }
            />
            <Button type="submit">
              Create project
            </Button>
          </form>
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

function RootProjectView({
  messages,
  message,
  onMessageChange,
  onSubmit,
}: {
  messages: ChatMessage[];
  message: string;
  onMessageChange: (value: string) => void;
  onSubmit: (event: React.FormEvent) => void;
}) {
  return (
    <section className="root-view">
      <header className="chat-header">
        <div>
          <p>System project / local installation</p>
          <h1>Root project</h1>
        </div>
        <ConnectionState state="idle" />
      </header>

      <div className="message-list" aria-label="Root project orchestrator chat">
        {messages.map((item) => (
          <ChatBubble item={item} key={item.id} />
        ))}
      </div>

      <form className="composer" onSubmit={onSubmit}>
        <Textarea
          className="composer-input"
          value={message}
          onChange={(event) => onMessageChange(event.target.value)}
          placeholder="Message the root orchestrator"
          autosize={false}
        />
        <Button className="send-button" leftSection={<Send size={16} aria-hidden="true" />} type="submit">
          Send
        </Button>
      </form>
    </section>
  );
}

function SettingsView({
  settings,
  loadState,
  apiEndpoint,
  onReload,
}: {
  settings: SettingsSnapshot | null;
  loadState: LoadState;
  apiEndpoint: string;
  onReload: () => void;
}) {
  const credential = settings?.credentials[0] ?? null;
  return (
    <section className="settings-view">
      <header className="chat-header">
        <div>
          <p>System setup</p>
          <h1>Settings</h1>
        </div>
        <div className="header-actions">
          <ConnectionState state={loadState} />
          <ActionIcon
            className="icon-button"
            onClick={onReload}
            type="button"
            aria-label="Reload settings"
            variant="light"
          >
            <CircleDashed size={14} aria-hidden="true" />
          </ActionIcon>
        </div>
      </header>

      <div className="settings-content">
        <section className="settings-section credentials-section">
          <div className="settings-section-title">
            <KeyRound size={17} aria-hidden="true" />
            <div>
              <strong>Credentials</strong>
              <span>Secrets stay outside run state and UI state.</span>
            </div>
          </div>
          <SimpleGrid className="settings-grid" cols={{ base: 1, sm: 2 }}>
            <SettingsTile
              label={credential?.label ?? "Model provider API key"}
              value={credential?.environment_variable ?? "RORVEN_OPENROUTER_API_KEY"}
              state={credential?.configured ? "configured" : "missing"}
              detail={credential?.notes ?? "Required before real model-provider calls are enabled."}
            />
            <SettingsTile
              label="Secret visibility"
              value={credential?.raw_value_visible ? "Visible" : "Hidden"}
              state={credential?.raw_value_visible ? "missing" : "configured"}
              detail="The API reports presence only. Raw values are never returned."
            />
          </SimpleGrid>
        </section>

        <section className="settings-section">
          <div className="settings-section-title">
            <Layers3 size={17} aria-hidden="true" />
            <div>
              <strong>Model tiers</strong>
              <span>Agents ask for these profiles, not provider model IDs.</span>
            </div>
          </div>
          <Paper className="profile-table" withBorder>
            <Table.ScrollContainer minWidth={680}>
              <Table verticalSpacing="sm" horizontalSpacing="md">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Tier</Table.Th>
                    <Table.Th>Adapter</Table.Th>
                    <Table.Th>Model</Table.Th>
                    <Table.Th>Timeout</Table.Th>
                    <Table.Th>Status</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {settings?.model_profiles.map((profile) => (
                    <Table.Tr key={profile.name}>
                      <Table.Td>
                        <Text fw={700}>{profile.name}</Text>
                      </Table.Td>
                      <Table.Td>{profile.adapter}</Table.Td>
                      <Table.Td>
                        <Text c={profile.model_id_configured ? undefined : "dimmed"}>
                          {profile.model_id}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        {profile.request_timeout_seconds ? `${profile.request_timeout_seconds}s` : "Unset"}
                      </Table.Td>
                      <Table.Td>
                        <StatusBadge state={profile.model_id_configured ? "configured" : "missing"} />
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
            {!settings ? <div className="settings-empty">Settings metadata is not loaded.</div> : null}
          </Paper>
        </section>

        <section className="settings-section">
          <div className="settings-section-title">
            <Database size={17} aria-hidden="true" />
            <div>
              <strong>Runtime and storage</strong>
              <span>Walking skeleton now, production adapters next.</span>
            </div>
          </div>
          <SimpleGrid className="settings-grid" cols={{ base: 1, md: 2, xl: 4 }}>
            <SettingsTile
              label="API endpoint"
              value={apiEndpoint}
              state="configured"
              detail="Console control plane."
            />
            <SettingsTile
              label="Runtime adapter"
              value={settings?.runtime.active_runtime_adapter ?? "Unknown"}
              state="configured"
              detail={`Planned: ${settings?.runtime.planned_runtime_adapter ?? "langgraph"}`}
            />
            <SettingsTile
              label="System of record"
              value={settings?.runtime.system_of_record ?? "Unknown"}
              state="deferred"
              detail={`Planned: ${settings?.runtime.planned_system_of_record ?? "postgresql"}`}
            />
            <SettingsTile
              label="Data directory"
              value={settings?.runtime.data_dir ?? "Unknown"}
              state="configured"
              detail="Local durable walking-skeleton state."
            />
          </SimpleGrid>
        </section>

        <section className="settings-section">
          <div className="settings-section-title">
            <ShieldCheck size={17} aria-hidden="true" />
            <div>
              <strong>Safety policy</strong>
              <span>Operational guardrails for autonomous work.</span>
            </div>
          </div>
          <SimpleGrid className="settings-grid" cols={{ base: 1, md: 3 }}>
            <SettingsTile
              label="Destructive actions"
              value={settings?.policy.destructive_actions ?? "approval-required"}
              state="configured"
              detail="Externally visible or destructive tool actions require policy evaluation."
            />
            <SettingsTile
              label="Secret exposure"
              value={settings?.policy.secret_exposure ?? "presence-only"}
              state="configured"
              detail="Raw values are not exposed to agents, logs, prompts, or UI state."
            />
            <SettingsTile
              label="Default tool access"
              value={settings?.policy.default_tool_access ?? "deny"}
              state="configured"
              detail="Agents receive explicit capabilities, not ambient machine access."
            />
          </SimpleGrid>
        </section>

        <section className="settings-section">
          <div className="settings-section-title">
            <Database size={17} aria-hidden="true" />
            <div>
              <strong>Project defaults</strong>
              <span>Defaults used when the root project creates or registers projects.</span>
            </div>
          </div>
          <SimpleGrid className="settings-grid" cols={{ base: 1, md: 3 }}>
            <SettingsTile
              label="Workspace root"
              value={settings?.project_defaults.workspace_root_source ?? "user-selected"}
              state="configured"
              detail="Project roots are explicit and scoped to allowed filesystem roots."
            />
            <SettingsTile
              label="Memory backend"
              value={settings?.project_defaults.memory_backend ?? "deferred"}
              state="deferred"
              detail="Per-project memory lands with the memory adapter slice."
            />
            <SettingsTile
              label="Sandbox"
              value={settings?.project_defaults.sandbox ?? "deferred"}
              state="deferred"
              detail="Tool execution isolation lands with the sandbox adapter slice."
            />
          </SimpleGrid>
        </section>
      </div>
    </section>
  );
}

function SettingsTile({
  label,
  value,
  state,
  detail,
}: {
  label: string;
  value: string;
  state: "configured" | "missing" | "deferred";
  detail: string;
}) {
  return (
    <Paper className="settings-tile" component="article" withBorder>
      <Group justify="space-between" gap="sm" wrap="nowrap">
        <Text fw={700} truncate>
          {label}
        </Text>
        <StatusBadge state={state} />
      </Group>
      <Text className="settings-tile-value">{value}</Text>
      <Text c="dimmed" size="sm" mt={8}>
        {detail}
      </Text>
    </Paper>
  );
}

function StatusBadge({ state }: { state: "configured" | "missing" | "deferred" }) {
  const color = state === "configured" ? "teal" : state === "missing" ? "red" : "yellow";
  return (
    <Badge color={color} size="sm" variant="light">
      {state}
    </Badge>
  );
}

function SubagentGroup({
  title,
  agents,
  emptyText,
  onInspect,
}: {
  title: string;
  agents: ActivityCard[];
  emptyText: string;
  onInspect: (agent: ActivityCard) => void;
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
                <strong>{agent.title}</strong>
                <span>{agent.subtitle}</span>
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

function RootAgentWorkView({
  agent,
  onBack,
}: {
  agent: RootAgentActivity;
  onBack: () => void;
}) {
  return (
    <section className="agent-work-view">
      <header className="agent-work-header">
        <button className="back-button" onClick={onBack} type="button" aria-label="Back to root chat">
          <ChevronLeft size={18} aria-hidden="true" />
        </button>
        <div>
          <p>Root subagent</p>
          <h1>{agent.name}</h1>
        </div>
        <StatusPill status={agent.status} />
      </header>

      <div className="agent-work-meta">
        <div>
          <strong>Model profile</strong>
          <span>{agent.modelProfile}</span>
        </div>
        <div>
          <strong>Scope</strong>
          <span>Root project</span>
        </div>
        <div>
          <strong>Run id</strong>
          <span>{agent.id.slice(0, 8)}</span>
        </div>
      </div>

      <div className="agent-work-log">
        <article className="work-entry system">
          <div className="bubble-icon">
            <User size={16} aria-hidden="true" />
          </div>
          <div>
            <strong>Assignment</strong>
            <p>{agent.summary}</p>
          </div>
        </article>
        <article className="work-entry agent">
          <div className="bubble-icon">
            <Bot size={16} aria-hidden="true" />
          </div>
          <div>
            <strong>Status</strong>
            <p>
              I am scoped to root-level project operations, not repository code work inside a
              workspace project.
            </p>
          </div>
        </article>
      </div>

      <div className="agent-interrupt">
        <input placeholder="Interrupt or add context for this root subagent" />
        <button className="secondary-button" type="button">
          Interrupt
        </button>
      </div>
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
    <MantineModal opened onClose={onClose} title={title} centered size="lg">
      {children}
    </MantineModal>
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
  const color = isDone(status)
    ? status === "failed"
      ? "red"
      : "teal"
    : status === "started" || status === "leased"
      ? "blue"
      : "yellow";
  return (
    <Badge color={color} size="sm" variant="outline">
      {status}
    </Badge>
  );
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

function replaceProjectPreservingOrder(projects: Project[], project: Project): Project[] {
  let found = false;
  const next = projects.map((candidate) => {
    if (candidate.id !== project.id) {
      return candidate;
    }
    found = true;
    return project;
  });
  return found ? next : [project, ...next];
}

function formatProjectCreatedAt(value: string): string {
  return `Created ${new Date(value).toLocaleString()}`;
}

function chooseRootSubagents(command: string, createdAt: string): RootAgentActivity[] {
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
    <MantineProvider theme={theme} defaultColorScheme="dark">
      <App />
    </MantineProvider>
  </React.StrictMode>,
);
