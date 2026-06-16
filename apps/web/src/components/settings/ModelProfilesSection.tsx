import { Paper, Table, Text } from "@mantine/core";
import { Layers3 } from "lucide-react";
import { SettingsSnapshot } from "../../api";
import { SectionTitle } from "./SectionTitle";
import { StatusBadge } from "./SettingsTile";

export function ModelProfilesSection({ settings }: { settings: SettingsSnapshot | null }) {
  return (
    <section className="settings-section">
      <SectionTitle
        icon={<Layers3 size={17} />}
        title="Model tiers"
        subtitle="Agents ask for these profiles, not provider model IDs."
      />
      <Paper className="profile-table" withBorder>
        <Table.ScrollContainer minWidth={680}>
          <Table verticalSpacing="sm" horizontalSpacing="md">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Tier</Table.Th>
                <Table.Th>Adapter</Table.Th>
                <Table.Th>Model</Table.Th>
                <Table.Th>Timeout</Table.Th>
                <Table.Th>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {settings?.model_profiles.map((profile) => (
                <Table.Tr key={profile.name}>
                  <Table.Td>
                    <Text fw={700}>{profile.name}</Text>
                  </Table.Td>
                  <Table.Td>{profile.adapter}</Table.Td>
                  <Table.Td>
                    <Text c={profile.model_id_configured ? undefined : "dimmed"}>
                      {profile.model_id}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    {profile.request_timeout_seconds ? `${profile.request_timeout_seconds}s` : "Unset"}
                  </Table.Td>
                  <Table.Td>
                    <StatusBadge state={profile.model_id_configured ? "configured" : "missing"} />
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
        {!settings ? <div className="settings-empty">Settings metadata is not loaded.</div> : null}
      </Paper>
    </section>
  );
}
