import { FormEvent, useState } from "react";
import { ChatMessage, RootAgentActivity } from "../types";
import { chooseRootSubagents } from "../utils/rootAgents";

export function useRootProjectController() {
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: "root-orchestrator-ready",
      side: "orchestrator",
      title: "Root orchestrator",
      body:
        "I manage the local Rorven installation. Ask me to create projects, find projects, inspect runs, or summarize workspace activity.",
      time: new Date().toISOString(),
      status: "ready",
    },
  ]);
  const [subagents, setSubagents] = useState<RootAgentActivity[]>([]);
  const [message, setMessage] = useState("Create a new project for this repository.");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const command = message.trim();
    if (!command) return;

    const now = new Date().toISOString();
    const spawned = chooseRootSubagents(command, now);
    setMessages((current) => [
      ...current,
      { id: `root-user-${now}`, side: "user", title: "You", body: command, time: now },
      {
        id: `root-orchestrator-${now}`,
        side: "orchestrator",
        title: "Root orchestrator",
        body: spawned.length
          ? `I started ${spawned.length} root subagent${spawned.length === 1 ? "" : "s"} for this request.`
          : "I can route this through root-level project tools once the durable root runtime is wired.",
        time: now,
        status: spawned.length ? "started" : "waiting",
      },
    ]);
    setSubagents((current) => [...spawned, ...current]);
    setMessage("");
  }

  return {
    handleSubmit,
    message,
    messages,
    setMessage,
    subagents,
  };
}
