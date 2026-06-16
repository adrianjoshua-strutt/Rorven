import { FormEvent, useEffect, useState } from "react";
import { getRootDashboard, submitRootMessage } from "../api";
import { ChatMessage, RootAgentActivity } from "../types";

export function useRootProjectController() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [subagents, setSubagents] = useState<RootAgentActivity[]>([]);
  const [message, setMessage] = useState("Create a new project for this repository.");

  async function loadRootState() {
    try {
      const root = await getRootDashboard();
      setMessages(
        root.messages.map((entry) => ({
          id: entry.id,
          side: entry.side,
          title: entry.title,
          body: entry.body,
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
      console.error("Failed to load root dashboard", e);
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const command = message.trim();
    if (!command) return;

    setMessage("");
    try {
      const root = await submitRootMessage(command);
      setMessages(
        root.messages.map((entry) => ({
          id: entry.id,
          side: entry.side,
          title: entry.title,
          body: entry.body,
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
      console.error("Failed to submit root message", e);
      setMessage(command);
    }
  }

  useEffect(() => {
    void loadRootState();
  }, []);

  return {
    handleSubmit,
    message,
    messages,
    setMessage,
    subagents,
    loadRootState,
  };
}
