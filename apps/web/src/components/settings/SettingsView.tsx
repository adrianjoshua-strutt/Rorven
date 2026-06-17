import { ActionIcon } from "@mantine/core";
import { CircleDashed } from "lucide-react";
import { SettingsSnapshot } from "../../api";
import { LoadState } from "../../types";
import { ConnectionState } from "../status/ConnectionState";
import { CredentialsSection } from "./CredentialsSection";
import { ModelProfilesSection } from "./ModelProfilesSection";
import { ProjectDefaultsSection } from "./ProjectDefaultsSection";
import { RuntimeSection } from "./RuntimeSection";
import { SafetyPolicySection } from "./SafetyPolicySection";

export function SettingsView({
  settings,
  loadState,
  apiEndpoint,
  onReload,
  onUpdateWorkspaceBaseRoot,
}: {
  settings: SettingsSnapshot | null;
  loadState: LoadState;
  apiEndpoint: string;
  onReload: () => void;
  onUpdateWorkspaceBaseRoot: (workspaceBaseRoot: string) => void;
}) {
  const credential = settings?.credentials[0] ?? null;
  const showMissingCredentialPrompt = credential?.configured === false;
  const envVarName = credential?.environment_variable ?? "OPENROUTER_API_KEY";
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
        {showMissingCredentialPrompt ? (
          <section className="settings-missing-credential" role="status" aria-live="polite">
            <strong>Action required: add your OpenRouter API key</strong>
            <p>
              Set <code>{envVarName}</code> in your environment, then restart the API process.
            </p>
          </section>
        ) : null}
        <CredentialsSection credential={credential} />
        <ModelProfilesSection settings={settings} />
        <RuntimeSection apiEndpoint={apiEndpoint} settings={settings} />
        <SafetyPolicySection settings={settings} />
        <ProjectDefaultsSection
          settings={settings}
          onUpdateWorkspaceBaseRoot={onUpdateWorkspaceBaseRoot}
        />
      </div>
    </section>
  );
}
