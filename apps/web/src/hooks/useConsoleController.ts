import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  ApprovalRecord,
  ModelCatalogEntry,
  Project,
  RunState,
  SettingsSnapshot,
  approveApproval,
  createProject,
  getModelCatalog,
  getProject,
  getRun,
  getSettings,
  listProjects,
  rejectApproval,
  submitRun,
  updateApprovalPolicy,
  updateModelProfiles,
  updateProjectDefaults,
} from "../api";
import {
  ActivityCard,
  InspectedAgent,
  LoadState,
  NewProjectDraft,
  ProjectSortMode,
  SelectedScope,
} from "../types";
import { buildProjectChat } from "../utils/chat";
import { replaceProjectPreservingOrder, sortProjects } from "../utils/projects";
import { isDone } from "../utils/status";
import { useRootProjectController } from "./useRootProjectController";

export function useConsoleController() {
  const projectLoadSequence = useRef(0);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedScope, setSelectedScope] = useState<SelectedScope>("root");
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<RunState | null>(null);
  const [inspectedAgent, setInspectedAgent] = useState<InspectedAgent | null>(null);
  const rootProject = useRootProjectController();
  const [settingsSnapshot, setSettingsSnapshot] = useState<SettingsSnapshot | null>(null);
  const [modelCatalog, setModelCatalog] = useState<ModelCatalogEntry[]>([]);
  const [projectSortMode, setProjectSortMode] = useState<ProjectSortMode>("latest_activity");
  const [seenProjectActivity, setSeenProjectActivity] = useState<Record<string, string>>(() =>
    readSeenProjectActivity(),
  );
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [settingsLoadState, setSettingsLoadState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [newProject, setNewProject] = useState<NewProjectDraft>({
    name: "Rorven Local",
    allowed_root: "D:/Cloud/Dropbox/GitHub",
    workspace_root: "D:/Cloud/Dropbox/GitHub/rorven",
  });
  const [message, setMessage] = useState("");

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  );
  const sortedProjects = useMemo(
    () => sortProjects(projects, projectSortMode),
    [projects, projectSortMode],
  );
  const unreadProjectIds = useMemo(() => {
    const ids = new Set<string>();
    for (const project of projects) {
      const last = project.last_activity_at;
      if (!last) continue;
      const seen = seenProjectActivity[project.id];
      if ((project.pending_approval_count ?? 0) > 0 || new Date(last) > new Date(seen ?? 0)) {
        ids.add(project.id);
      }
    }
    return ids;
  }, [projects, seenProjectActivity]);

  const subagents = useMemo(
    () =>
      selectedScope === "project"
        ? selectedProject?.agent_runs?.filter((agentRun) => agentRun.parent_agent_run_id !== null) ??
          selectedRun?.agent_runs.filter((agentRun) => agentRun.parent_agent_run_id !== null) ??
          []
        : [],
    [selectedProject?.agent_runs, selectedRun, selectedScope],
  );

  const activityCards = useMemo<ActivityCard[]>(() => {
    if (selectedScope === "root") {
      return rootProject.subagents.map((agent) => ({
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
  }, [rootProject.subagents, selectedScope, subagents]);

  const runningSubagents = activityCards.filter((agent) => !isDone(agent.status));
  const finishedSubagents = activityCards.filter((agent) => isDone(agent.status));
  const inspectedProjectAgent =
    inspectedAgent?.scope === "project"
      ? subagents.find((agent) => agent.id === inspectedAgent.id) ??
        selectedRun?.agent_runs.find((agent) => agent.id === inspectedAgent.id) ??
        null
      : null;
  const inspectedRootAgent =
    inspectedAgent?.scope === "root"
      ? rootProject.subagents.find((agent) => agent.id === inspectedAgent.id) ?? null
      : null;

  const chatMessages = useMemo(
    () => buildProjectChat(selectedProject, selectedRun, subagents),
    [selectedProject, selectedRun, subagents],
  );

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

  async function loadModelCatalog() {
    try {
      setModelCatalog(await getModelCatalog());
    } catch {
      setModelCatalog([]);
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
    const sortedRuns = [...(project.runs ?? [])].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
    const runId =
      preferredRunId && project.runs?.some((run) => run.id === preferredRunId)
        ? preferredRunId
        : sortedRuns[0]?.id;
    if (runId) {
      const run = await getRun(project.id, runId);
      setSelectedRun(run);
    } else {
      setSelectedRun(null);
    }
    markProjectSeen(project);
  }

  async function handleCreateProject(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const createdProject = await createProject(newProject);
      const loadToken = ++projectLoadSequence.current;
      
      // Reset form immediately
      setNewProject({
        name: "Rorven Local",
        allowed_root: "D:/Cloud/Dropbox/GitHub",
        workspace_root: "D:/Cloud/Dropbox/GitHub/rorven",
      });
      setShowCreateProject(false);
      
      // Fetch fresh projects list
      const refreshedProjects = await listProjects();
      setProjects(refreshedProjects);
      
      // Select and load the newly created project
      setSelectedProjectId(createdProject.id);
      setSelectedScope("project");
      setSelectedRun(null);
      setInspectedAgent(null);
      await loadProject(createdProject.id, null, loadToken);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to create project");
    }
  }

  async function handleSubmitMessage(event: FormEvent) {
    event.preventDefault();
    const command = message.trim();
    if (!selectedProjectId || !command) return;
    setError(null);
    setMessage("");
    try {
      const loadToken = ++projectLoadSequence.current;
      const run = await submitRun(selectedProjectId, command);
      setInspectedAgent(null);
      await loadProject(selectedProjectId, run.id, loadToken);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to send message");
      setMessage(command);
    }
  }

  async function handleSubmitRootMessage(event: FormEvent) {
    await rootProject.handleSubmit(event);
    try {
      setProjects(await listProjects());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to refresh projects");
    }
  }

  async function handleUpdateWorkspaceBaseRoot(workspaceBaseRoot: string) {
    setSettingsLoadState("loading");
    setError(null);
    try {
      setSettingsSnapshot(
        await updateProjectDefaults({ workspace_base_root: workspaceBaseRoot }),
      );
      setSettingsLoadState("idle");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to update project defaults");
      setSettingsLoadState("error");
    }
  }

  async function handleUpdateApprovalPolicy(textFileWrite: string) {
    setSettingsLoadState("loading");
    setError(null);
    try {
      setSettingsSnapshot(
        await updateApprovalPolicy({ text_file_write: textFileWrite }),
      );
      setSettingsLoadState("idle");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to update approval policy");
      setSettingsLoadState("error");
    }
  }

  async function handleUpdateModelProfile(name: string, modelId: string) {
    setSettingsLoadState("loading");
    setError(null);
    try {
      setSettingsSnapshot(await updateModelProfiles({ [name]: modelId }));
      setSettingsLoadState("idle");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to update model profile");
      setSettingsLoadState("error");
    }
  }

  async function handleApprovalDecision(approval: ApprovalRecord, decision: "approve" | "reject") {
    setError(null);
    try {
      if (decision === "approve") {
        await approveApproval(approval.project_id, approval.run_id, approval.id);
      } else {
        await rejectApproval(approval.project_id, approval.run_id, approval.id);
      }
      if (selectedProjectId) {
        await loadProject(selectedProjectId, approval.run_id);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `Unable to ${decision} approval`);
    }
  }

  function selectRoot() {
    setRouteHash("#/root");
    projectLoadSequence.current += 1;
    setSelectedScope("root");
    setSelectedProjectId(null);
    setSelectedRun(null);
    setInspectedAgent(null);
  }

  function selectSettings() {
    setRouteHash("#/settings");
    projectLoadSequence.current += 1;
    setSelectedScope("settings");
    setSelectedProjectId(null);
    setSelectedRun(null);
    setInspectedAgent(null);
    void loadSettings();
    void loadModelCatalog();
  }

  async function selectProject(projectId: string) {
    setRouteHash(projectRoute(projectId));
    const loadToken = ++projectLoadSequence.current;
    setSelectedProjectId(projectId);
    setSelectedScope("project");
    setSelectedRun(null);
    setInspectedAgent(null);
    setError(null);
    try {
      await loadProject(projectId, null, loadToken);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load project");
    }
  }

  function inspectActivity(agent: ActivityCard) {
    if (selectedScope === "root") {
      setInspectedAgent({ scope: "root", id: agent.id });
      return;
    }
    void inspectProjectAgent(agent.id);
  }

  async function inspectProjectAgent(agentId: string) {
    const agent = subagents.find((candidate) => candidate.id === agentId);
    if (!agent || !selectedProjectId) {
      setInspectedAgent({ scope: "project", id: agentId });
      setRouteHash(agentRoute(selectedProjectId, agentId));
      return;
    }
    if (selectedRun?.id !== agent.run_id) {
      try {
        setSelectedRun(await getRun(selectedProjectId, agent.run_id));
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Unable to load subagent run");
        return;
      }
    }
    setInspectedAgent({ scope: "project", id: agentId });
    setRouteHash(agentRoute(selectedProjectId, agentId));
  }

  function closeInspectedAgent() {
    setInspectedAgent(null);
    setRouteHash(selectedProjectId ? projectRoute(selectedProjectId) : "#/root");
  }

  useEffect(() => {
    // Load initial state on mount - fetch projects and settings
    setLoadState("loading");
    setError(null);
    Promise.all([listProjects(), getSettings()])
      .then(([nextProjects, nextSettings]) => {
        setProjects(nextProjects);
        setSettingsSnapshot(nextSettings);
        setLoadState("idle");
        void applyRouteFromHash(nextProjects);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load initial state");
        setLoadState("error");
      });
  }, []);

  useEffect(() => {
    function handleHashChange() {
      void applyRouteFromHash(projects);
    }
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, [projects]);

  useEffect(() => {
    if (selectedScope !== "project" || !selectedProjectId) return;
    const id = window.setInterval(() => {
      void loadProject(selectedProjectId, selectedRun?.id);
    }, 2500);
    return () => window.clearInterval(id);
  }, [selectedScope, selectedProjectId, selectedRun?.id]);

  async function applyRouteFromHash(currentProjects: Project[]) {
    const route = parseRouteHash();
    if (route.scope === "settings") {
      projectLoadSequence.current += 1;
      setSelectedScope("settings");
      setSelectedProjectId(null);
      setSelectedRun(null);
      setInspectedAgent(null);
      await loadSettings();
      await loadModelCatalog();
      return;
    }
    if (route.scope === "project" && route.projectId) {
      const exists = currentProjects.some((project) => project.id === route.projectId);
      if (!exists && currentProjects.length) return;
      const loadToken = ++projectLoadSequence.current;
      setSelectedProjectId(route.projectId);
      setSelectedScope("project");
      setSelectedRun(null);
      setInspectedAgent(null);
      await loadProject(route.projectId, null, loadToken);
      if (route.agentId) {
        setInspectedAgent({ scope: "project", id: route.agentId });
      }
      return;
    }
    projectLoadSequence.current += 1;
    setSelectedScope("root");
    setSelectedProjectId(null);
    setSelectedRun(null);
    setInspectedAgent(null);
    if (!window.location.hash) {
      window.history.replaceState(null, "", "#/root");
    }
  }

  function markProjectSeen(project: Project) {
    const last = project.last_activity_at;
    if (!last) return;
    setSeenProjectActivity((current) => {
      if (current[project.id] === last) return current;
      const next = { ...current, [project.id]: last };
      window.localStorage.setItem("rorven.seenProjectActivity", JSON.stringify(next));
      return next;
    });
  }

  return {
    activityCards,
    chatMessages,
    closeInspectedAgent,
    error,
    finishedSubagents,
    handleCreateProject,
    handleSubmitMessage,
    handleSubmitRootMessage,
    handleUpdateWorkspaceBaseRoot,
    handleApprovalDecision,
    handleUpdateApprovalPolicy,
    handleUpdateModelProfile,
    rootIsPending: rootProject.isPending,
    inspectActivity,
    inspectProjectAgent,
    inspectedProjectAgent,
    inspectedRootAgent,
    loadSettings,
    loadState,
    message,
    modelCatalog,
    newProject,
    projects: sortedProjects,
    projectSortMode,
    rootMessage: rootProject.message,
    rootMessages: rootProject.messages,
    rootError: rootProject.error,
    runningSubagents,
    selectedProject,
    selectedProjectId,
    selectedRun,
    selectedScope,
    selectProject,
    selectRoot,
    selectSettings,
    setInspectedAgent,
    setMessage,
    setNewProject,
    setProjectSortMode,
    setRootMessage: rootProject.setMessage,
    setShowCreateProject,
    settingsLoadState,
    settingsSnapshot,
    showCreateProject,
    subagents,
    unreadProjectIds,
  };
}

function setRouteHash(hash: string) {
  if (window.location.hash !== hash) {
    window.location.hash = hash;
  }
}

function projectRoute(projectId: string) {
  return `#/projects/${projectId}`;
}

function agentRoute(projectId: string | null, agentId: string) {
  return projectId ? `#/projects/${projectId}/agents/${agentId}` : "#/root";
}

function parseRouteHash():
  | { scope: "root" }
  | { scope: "settings" }
  | { scope: "project"; projectId: string; agentId?: string } {
  const hash = window.location.hash || "#/root";
  if (hash === "#/settings") return { scope: "settings" };
  const match = hash.match(/^#\/projects\/([^/]+)(?:\/agents\/([^/]+))?$/);
  if (match) {
    return { scope: "project", projectId: match[1], agentId: match[2] };
  }
  return { scope: "root" };
}

function readSeenProjectActivity(): Record<string, string> {
  try {
    const raw = window.localStorage.getItem("rorven.seenProjectActivity");
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}
