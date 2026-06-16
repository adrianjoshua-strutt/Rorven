import { SimpleGrid } from "@mantine/core";
import { KeyRound } from "lucide-react";
import { SettingsSnapshot } from "../../api";
import { SectionTitle } from "./SectionTitle";
import { SettingsTile } from "./SettingsTile";

export function CredentialsSection({
  credential,
}: {
  credential: SettingsSnapshot["credentials"][number] | null;
}) {
  return (
    <section className="settings-section credentials-section">
      <SectionTitle
        icon={<KeyRound size={17} />}
        title="Credentials"
        subtitle="Secrets stay outside run state and UI state."
      />
      <SimpleGrid className="settings-grid" cols={{ base: 1, sm: 2 }}>
        <SettingsTile
          label={credential?.label ?? "Model provider API key"}
          value={credential?.environment_variable ?? "RORVEN_OPENROUTER_API_KEY"}
          state={credential?.configured ? "configured" : "missing"}
          detail={credential?.notes ?? "Required before real model-provider calls are enabled."}
        />
        <SettingsTile
          label="Secret visibility"
          value={credential?.raw_value_visible ? "Visible" : "Hidden"}
          state={credential?.raw_value_visible ? "missing" : "configured"}
          detail="The API reports presence only. Raw values are never returned."
        />
      </SimpleGrid>
    </section>
  );
}
