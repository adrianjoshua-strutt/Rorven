import { SimpleGrid } from "@mantine/core";
import { Database } from "lucide-react";
import { SettingsSnapshot } from "../../api";
import { SectionTitle } from "./SectionTitle";
import { SettingsTile } from "./SettingsTile";

export function RuntimeSection({
  apiEndpoint,
  settings,
}: {
  apiEndpoint: string;
  settings: SettingsSnapshot | null;
}) {
  return (
    <section className="settings-section">
      <SectionTitle
        icon={<Database size={17} />}
        title="Runtime and storage"
        subtitle="Walking skeleton now, production adapters next."
      />
      <SimpleGrid className="settings-grid" cols={{ base: 1, md: 2, xl: 4 }}>
        <SettingsTile label="API endpoint" value={apiEndpoint} state="configured" detail="Console control plane." />
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
  );
}
