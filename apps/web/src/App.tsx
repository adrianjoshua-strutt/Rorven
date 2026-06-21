import { useConsoleController } from "./hooks/useConsoleController";
import { AgentWorkView } from "./components/agents/AgentWorkView";
import { RootAgentWorkView } from "./components/agents/RootAgentWorkView";
import { ActivityRail } from "./components/layout/ActivityRail";
import { ProjectsPane } from "./components/layout/ProjectsPane";
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
        projectSortMode={consoleState.projectSortMode}
        selectedProjectId={consoleState.selectedProjectId}
        selectedScope={consoleState.selectedScope}
        onSelectProject={(projectId) => void consoleState.selectProject(projectId)}
        onSelectRoot={consoleState.selectRoot}
        onSelectSettings={consoleState.selectSettings}
        onSortChange={consoleState.setProjectSortMode}
        unreadProjectIds={consoleState.unreadProjectIds}
      />

      <section className="chat-pane">
        {consoleState.inspectedProjectAgent ? (
          <AgentWorkView
            agent={consoleState.inspectedProjectAgent}
            run={consoleState.selectedRun}
            onBack={consoleState.closeInspectedAgent}
            onApprove={(approval) => void consoleState.handleApprovalDecision(approval, "approve")}
            onReject={(approval) => void consoleState.handleApprovalDecision(approval, "reject")}
          />
        ) : consoleState.inspectedRootAgent ? (
          <RootAgentWorkView
            agent={consoleState.inspectedRootAgent}
            onBack={consoleState.closeInspectedAgent}
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
            loadState={consoleState.settingsLoadState}
            settings={consoleState.settingsSnapshot}
            modelCatalog={consoleState.modelCatalog}
            onReload={() => void consoleState.loadSettings()}
            onUpdateWorkspaceBaseRoot={(value) =>
              void consoleState.handleUpdateWorkspaceBaseRoot(value)
            }
            onUpdateModelProfile={(name, modelId) =>
              void consoleState.handleUpdateModelProfile(name, modelId)
            }
          />
        ) : (
          <ProjectChatView
            chatMessages={consoleState.chatMessages}
            error={consoleState.error}
            loadState={consoleState.loadState}
            message={consoleState.message}
            onMessageChange={consoleState.setMessage}
            onApprove={(approval) => void consoleState.handleApprovalDecision(approval, "approve")}
            onInspectAgent={(agentId) => void consoleState.inspectProjectAgent(agentId)}
            onReject={(approval) => void consoleState.handleApprovalDecision(approval, "reject")}
            onSubmit={consoleState.handleSubmitMessage}
            project={consoleState.selectedProject}
            run={consoleState.selectedRun}
            subagents={consoleState.subagents}
          />
        )}
      </section>

      {consoleState.selectedScope !== "settings" ? (
        <ActivityRail
          total={consoleState.activityCards.length}
          running={consoleState.runningSubagents}
          finished={consoleState.finishedSubagents}
          onInspect={consoleState.inspectActivity}
        />
      ) : null}
    </main>
  );
}
