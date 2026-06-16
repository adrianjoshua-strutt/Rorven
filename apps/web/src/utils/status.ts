export function isDone(status: string) {
  return status === "completed" || status === "failed" || status === "canceled";
}

export function statusColor(status: string) {
  if (isDone(status)) {
    return status === "failed" ? "red" : "teal";
  }
  return status === "started" || status === "leased" ? "blue" : "yellow";
}
