import { SimpleGrid } from "@mantine/core";
import { Database } from "lucide-react";
import { SettingsSnapshot } from "../../api";
import { SectionTitle } from "./SectionTitle";
import { SettingsTile } from "./SettingsTile";

export function ProjectDefaultsSection({ settings }: { settings: SettingsSnapshot | null }) {
  return (
    <section className="settings-section">
      <SectionTitle
        icon={<Database size={17} />}
        title="Project defaults"
        subtitle="Defaults used when the root project creates or registers projects."
      />
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
  );
}
