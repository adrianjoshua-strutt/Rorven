import { Badge, Group, Paper, Text } from "@mantine/core";

type TileState = "configured" | "missing" | "deferred";

export function SettingsTile({
  label,
  value,
  state,
  detail,
}: {
  label: string;
  value: string;
  state: TileState;
  detail: string;
}) {
  return (
    <Paper className="settings-tile" component="article" withBorder>
      <Group justify="space-between" gap="sm" wrap="nowrap">
        <Text fw={700} truncate>
          {label}
        </Text>
        <StatusBadge state={state} />
      </Group>
      <Text className="settings-tile-value">{value}</Text>
      <Text c="dimmed" size="sm" mt={8}>
        {detail}
      </Text>
    </Paper>
  );
}

export function StatusBadge({ state }: { state: TileState }) {
  const color = state === "configured" ? "teal" : state === "missing" ? "red" : "yellow";
  return (
    <Badge color={color} size="sm" variant="light">
      {state}
    </Badge>
  );
}
