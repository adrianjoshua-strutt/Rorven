import { SimpleGrid } from "@mantine/core";
import { ShieldCheck } from "lucide-react";
import { SettingsSnapshot } from "../../api";
import { SectionTitle } from "./SectionTitle";
import { SettingsTile } from "./SettingsTile";

export function SafetyPolicySection({ settings }: { settings: SettingsSnapshot | null }) {
  return (
    <section className="settings-section">
      <SectionTitle
        icon={<ShieldCheck size={17} />}
        title="Safety policy"
        subtitle="Operational guardrails for autonomous work."
      />
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
  );
}
