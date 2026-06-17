import { useConsoleController } from "./hooks/useConsoleController";
import { AgentWorkView } from "./components/agents/AgentWorkView";
import { RootAgentWorkView } from "./components/agents/RootAgentWorkView";
import { ActivityRail } from "./components/layout/ActivityRail";
import { ProjectsPane } from "./components/layout/ProjectsPane";
import { CreateProjectModal } from "./components/projects/CreateProjectModal";
import { ProjectChatView } from "./components/projects/ProjectChatView";
import { RootProjectView } from "./components/projects/RootProjectView";
import { SettingsView } from "./components/settings/SettingsView";

export function App() {
  const consoleState = useConsoleController();
  const modelCredential = consoleState.settingsSnapshot?.credentials[0] ?? null;
  const isModelProviderConfigured = modelCredential?.configured ?? false;
  const modelProviderEnvVar = modelCredential?.environment_variable ?? "OPENROUTER_API_KEY";

  return (
    <main className="app-shell">
      <ProjectsPane
        projects={consoleState.projects}
        selectedProjectId={consoleState.selectedProjectId}
        selectedScope={consoleState.selectedScope}
        onCreateProject={() => consoleState.setShowCreateProject(true)}
        onSelectProject={(projectId) => void consoleState.selectProject(projectId)}
        onSelectRoot={consoleState.selectRoot}
        onSelectSettings={consoleState.selectSettings}
      />

      <section className="chat-pane">
        {consoleState.inspectedProjectAgent ? (
          <AgentWorkView
            agent={consoleState.inspectedProjectAgent}
            run={consoleState.selectedRun}
            onBack={() => consoleState.setInspectedAgent(null)}
          />
        ) : consoleState.inspectedRootAgent ? (
          <RootAgentWorkView
            agent={consoleState.inspectedRootAgent}
            onBack={() => consoleState.setInspectedAgent(null)}
          />
        ) : consoleState.selectedScope === "root" ? (
          <RootProjectView
            error={consoleState.rootError}
            isPending={consoleState.rootIsPending}
            messages={consoleState.rootMessages}
            message={consoleState.rootMessage}
            onMessageChange={consoleState.setRootMessage}
            onOpenSettings={consoleState.selectSettings}
            onSubmit={consoleState.handleSubmitRootMessage}
            isModelProviderConfigured={isModelProviderConfigured}
            modelProviderEnvVar={modelProviderEnvVar}
          />
        ) : consoleState.selectedScope === "settings" ? (
          <SettingsView
            apiEndpoint={import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"}
            loadState={consoleState.settingsLoadState}
            settings={consoleState.settingsSnapshot}
            onReload={() => void consoleState.loadSettings()}
            onUpdateWorkspaceBaseRoot={(value) =>
              void consoleState.handleUpdateWorkspaceBaseRoot(value)
            }
          />
        ) : (
          <ProjectChatView
            chatMessages={consoleState.chatMessages}
            error={consoleState.error}
            loadState={consoleState.loadState}
            message={consoleState.message}
            onMessageChange={consoleState.setMessage}
            onSubmit={consoleState.handleSubmitMessage}
            project={consoleState.selectedProject}
          />
        )}
      </section>

      <ActivityRail
        total={consoleState.activityCards.length}
        running={consoleState.runningSubagents}
        finished={consoleState.finishedSubagents}
        onInspect={consoleState.inspectActivity}
      />

      {consoleState.showCreateProject ? (
        <CreateProjectModal
          draft={consoleState.newProject}
          onChange={consoleState.setNewProject}
          onClose={() => consoleState.setShowCreateProject(false)}
          onSubmit={consoleState.handleCreateProject}
        />
      ) : null}
    </main>
  );
}
