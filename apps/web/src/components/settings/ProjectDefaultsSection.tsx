import { Button, Group, SimpleGrid, TextInput } from "@mantine/core";
import { Database } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { SettingsSnapshot } from "../../api";
import { SectionTitle } from "./SectionTitle";
import { SettingsTile } from "./SettingsTile";

export function ProjectDefaultsSection({
  settings,
  onUpdateWorkspaceBaseRoot,
}: {
  settings: SettingsSnapshot | null;
  onUpdateWorkspaceBaseRoot: (workspaceBaseRoot: string) => void;
}) {
  const configuredBase = settings?.project_defaults.workspace_base_root ?? "";
  const [workspaceBaseRoot, setWorkspaceBaseRoot] = useState(configuredBase);

  useEffect(() => {
    setWorkspaceBaseRoot(configuredBase);
  }, [configuredBase]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = workspaceBaseRoot.trim();
    if (trimmed) {
      onUpdateWorkspaceBaseRoot(trimmed);
    }
  }

  return (
    <section className="settings-section">
      <SectionTitle
        icon={<Database size={17} />}
        title="Project defaults"
        subtitle="Defaults used when the root project creates or registers projects."
      />
      <form className="settings-inline-form" onSubmit={handleSubmit}>
        <TextInput
          label="Workspace base"
          value={workspaceBaseRoot}
          onChange={(event) => setWorkspaceBaseRoot(event.currentTarget.value)}
        />
        <Group justify="flex-end">
          <Button type="submit" variant="filled" size="sm">
            Save base
          </Button>
        </Group>
      </form>
      <SimpleGrid className="settings-grid" cols={{ base: 1, md: 3 }}>
        <SettingsTile
          label="Workspace base"
          value={settings?.project_defaults.workspace_base_root ?? "not configured"}
          state="configured"
          detail="Root-created projects are placed under this folder by default."
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
  );
}
