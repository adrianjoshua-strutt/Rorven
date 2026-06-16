import { Badge } from "@mantine/core";
import { statusColor } from "../../utils/status";

export function StatusPill({ status }: { status: string }) {
  return (
    <Badge color={statusColor(status)} size="sm" variant="outline">
      {status}
    </Badge>
  );
}
