import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  ApprovalRecord,
  Project,
  RunState,
  SettingsSnapshot,
  approveApproval,
  createProject,
  getProject,
  getRun,
  getSettings,
  listProjects,
  rejectApproval,
  submitRun,
  updateProjectDefaults,
} from "../api";
import {
  ActivityCard,
  InspectedAgent,
  LoadState,
  NewProjectDraft,
  SelectedScope,
} from "../types";
import { buildProjectChat } from "../utils/chat";
import { replaceProjectPreservingOrder } from "../utils/projects";
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

  const subagents = useMemo(
    () =>
      selectedScope === "project"
        ? selectedRun?.agent_runs.filter((agentRun) => agentRun.parent_agent_run_id !== null) ?? []
        : [],
    [selectedScope, selectedRun],
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
      ? subagents.find((agent) => agent.id === inspectedAgent.id) ?? null
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
    projectLoadSequence.current += 1;
    setSelectedScope("root");
    setSelectedProjectId(null);
    setSelectedRun(null);
    setInspectedAgent(null);
  }

  function selectSettings() {
    projectLoadSequence.current += 1;
    setSelectedScope("settings");
    setSelectedProjectId(null);
    setSelectedRun(null);
    setInspectedAgent(null);
    void loadSettings();
  }

  async function selectProject(projectId: string) {
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
    setInspectedAgent({ scope: selectedScope === "root" ? "root" : "project", id: agent.id });
  }

  useEffect(() => {
    // Load initial state on mount - fetch projects and settings
    setLoadState("loading");
    setError(null);
    Promise.all([listProjects(), getSettings()])
      .then(([nextProjects, nextSettings]) => {
        setProjects(nextProjects);
        setSettingsSnapshot(nextSettings);
        // Auto-select root scope on initial load
        setSelectedScope("root");
        setLoadState("idle");
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load initial state");
        setLoadState("error");
      });
  }, []);

  useEffect(() => {
    if (selectedScope !== "project" || !selectedProjectId) return;
    const id = window.setInterval(() => {
      void loadProject(selectedProjectId, selectedRun?.id);
    }, 2500);
    return () => window.clearInterval(id);
  }, [selectedScope, selectedProjectId, selectedRun?.id]);

  return {
    activityCards,
    chatMessages,
    error,
    finishedSubagents,
    handleCreateProject,
    handleSubmitMessage,
    handleSubmitRootMessage,
    handleUpdateWorkspaceBaseRoot,
    handleApprovalDecision,
    rootIsPending: rootProject.isPending,
    inspectActivity,
    inspectedProjectAgent,
    inspectedRootAgent,
    loadSettings,
    loadState,
    message,
    newProject,
    projects,
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
    setRootMessage: rootProject.setMessage,
    setShowCreateProject,
    settingsLoadState,
    settingsSnapshot,
    showCreateProject,
    subagents,
  };
}
