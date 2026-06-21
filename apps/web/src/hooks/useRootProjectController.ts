import { FormEvent, useEffect, useState } from "react";
import { getRootDashboard, submitRootMessage } from "../api";
import { ChatMessage, RootAgentActivity } from "../types";
import { cleanChatBody } from "../utils/chat";

export function useRootProjectController() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [subagents, setSubagents] = useState<RootAgentActivity[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  async function loadRootState() {
    try {
      setError(null);
      const root = await getRootDashboard();
      setMessages(
        root.messages.map((entry) => ({
          id: entry.id,
          side: entry.side,
          title: entry.title,
          body: cleanChatBody(entry.body),
          time: entry.time,
          status: entry.status,
        })),
      );
      setSubagents(
        root.activities.map((activity) => ({
          id: activity.id,
          name: activity.name,
          modelProfile: activity.modelProfile,
          status: activity.status,
          createdAt: activity.createdAt,
          summary: activity.summary,
        })),
      );
    } catch (e) {
      const reason = e instanceof Error ? e.message : "Failed to load root dashboard";
      setError(reason);
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const command = message.trim();
    if (!command) return;

    setError(null);
    setMessage("");
    setIsPending(true);

    // Optimistically add the user message so it appears instantly
    const optimisticId = `optimistic-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      {
        id: optimisticId,
        side: "user" as const,
        title: "You",
        body: command,
        time: new Date().toISOString(),
      },
    ]);

    try {
      const root = await submitRootMessage(command);
      setMessages(
        root.messages.map((entry) => ({
          id: entry.id,
          side: entry.side,
          title: entry.title,
          body: cleanChatBody(entry.body),
          time: entry.time,
          status: entry.status,
        })),
      );
      setSubagents(
        root.activities.map((activity) => ({
          id: activity.id,
          name: activity.name,
          modelProfile: activity.modelProfile,
          status: activity.status,
          createdAt: activity.createdAt,
          summary: activity.summary,
        })),
      );
    } catch (e) {
      const reason = e instanceof Error ? e.message : "Failed to submit root message";
      setError(reason);
      setMessage(command);
      // Replace optimistic message with real persisted state
      try {
        const root = await getRootDashboard();
        setMessages(
          root.messages.map((entry) => ({
            id: entry.id,
            side: entry.side,
            title: entry.title,
            body: cleanChatBody(entry.body),
            time: entry.time,
            status: entry.status,
          })),
        );
      } catch {
        // Remove the optimistic message on total failure
        setMessages((prev) => prev.filter((m) => m.id !== optimisticId));
      }
    } finally {
      setIsPending(false);
    }
  }

  useEffect(() => {
    void loadRootState();
  }, []);

  return {
    error,
    handleSubmit,
    isPending,
    message,
    messages,
    setMessage,
    subagents,
    loadRootState,
  };
}
