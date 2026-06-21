import { SimpleGrid } from "@mantine/core";
import { ShieldCheck } from "lucide-react";
import { SettingsSnapshot } from "../../api";
import { SectionTitle } from "./SectionTitle";
import { SettingsTile } from "./SettingsTile";

const approvalLabels: Record<string, string> = {
  ask_each_time: "Ask each time",
  auto_apply_text_file_writes: "Auto-apply text file writes",
  reject_text_file_writes: "Reject text file writes",
};

export function SafetyPolicySection({
  settings,
  onUpdateApprovalPolicy,
}: {
  settings: SettingsSnapshot | null;
  onUpdateApprovalPolicy: (textFileWrite: string) => void;
}) {
  const selectedMode = settings?.policy.text_file_write_approval ?? "ask_each_time";
  const modes = settings?.policy.text_file_write_approval_modes ?? [
    "ask_each_time",
    "auto_apply_text_file_writes",
    "reject_text_file_writes",
  ];
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
      <div className="approval-policy-control" aria-label="Text file write approval policy">
        <div>
          <strong>Text file write approvals</strong>
          <span>Legacy setting retained for existing local state.</span>
        </div>
        <div className="approval-policy-options">
          {modes.map((mode) => (
            <button
              className={mode === selectedMode ? "selected" : ""}
              key={mode}
              onClick={() => onUpdateApprovalPolicy(mode)}
              type="button"
            >
              {approvalLabels[mode] ?? mode}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
