import { Autocomplete, Button } from "@mantine/core";
import { Layers3 } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { ModelCatalogEntry, SettingsSnapshot } from "../../api";
import { SectionTitle } from "./SectionTitle";

export function ModelProfilesSection({
  modelCatalog,
  settings,
  onUpdateModelProfile,
}: {
  modelCatalog: ModelCatalogEntry[];
  settings: SettingsSnapshot | null;
  onUpdateModelProfile: (name: string, modelId: string) => void;
}) {
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const catalogItems = useMemo(
    () =>
      modelCatalog.map((model) => ({
        value: model.id,
        label: model.name === model.id ? model.id : `${model.name} (${model.id})`,
      })),
    [modelCatalog],
  );

  useEffect(() => {
    const next: Record<string, string> = {};
    for (const profile of settings?.model_profiles ?? []) {
      next[profile.name] = profile.model_id;
    }
    setDrafts(next);
  }, [settings]);

  function submitProfile(event: FormEvent, name: string) {
    event.preventDefault();
    const modelId = drafts[name]?.trim();
    if (modelId) {
      onUpdateModelProfile(name, modelId);
    }
  }

  return (
    <section className="settings-section">
      <SectionTitle
        icon={<Layers3 size={17} />}
        title="Model tiers"
        subtitle="Agents ask for these profiles, not provider model IDs."
      />
      <div className="model-profile-list">
        {settings?.model_profiles.map((profile) => (
          <form
            className="model-profile-row"
            key={profile.name}
            onSubmit={(event) => submitProfile(event, profile.name)}
          >
            <div className="model-profile-name">
              <strong>{profile.name}</strong>
              <span>{profile.request_timeout_seconds ? `${profile.request_timeout_seconds}s timeout` : "default timeout"}</span>
            </div>
            <Autocomplete
              data={catalogItems}
              value={drafts[profile.name] ?? ""}
              onChange={(value) => setDrafts((current) => ({ ...current, [profile.name]: value }))}
              placeholder="Search OpenRouter models"
              limit={12}
              comboboxProps={{ withinPortal: true }}
            />
            <Button type="submit" variant="filled" size="sm">
              Save
            </Button>
          </form>
        ))}
        {!settings ? <div className="settings-empty">Settings are not loaded.</div> : null}
      </div>
    </section>
  );
}
