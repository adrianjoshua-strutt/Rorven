import { CircleDashed } from "lucide-react";
import { LoadState } from "../../types";

export function ConnectionState({ state }: { state: LoadState }) {
  return (
    <div className={`connection-state ${state}`}>
      <CircleDashed size={14} aria-hidden="true" />
      <span>{state === "loading" ? "Syncing" : state === "error" ? "Offline" : "Live"}</span>
    </div>
  );
}
