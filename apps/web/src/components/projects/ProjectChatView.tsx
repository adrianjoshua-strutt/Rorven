import { FormEvent, useEffect, useRef } from "react";
import { AgentRun, Project, RunState } from "../../api";
import { ChatMessage, LoadState } from "../../types";
import { buildSubagentSummaries } from "../../utils/chat";
import { ChatBubble } from "../chat/ChatBubble";
import { Composer } from "../chat/Composer";
import { ConnectionState } from "../status/ConnectionState";
import { StatusPill } from "../status/StatusPill";
import { Bot, ChevronRight, MessageSquare } from "lucide-react";

export function ProjectChatView({
  chatMessages,
  error,
  loadState,
  message,
  onMessageChange,
  onInspectAgent,
  onSubmit,
  project,
  run,
  subagents,
}: {
  chatMessages: ChatMessage[];
  error: string | null;
  loadState: LoadState;
  message: string;
  onMessageChange: (value: string) => void;
  onInspectAgent: (agentId: string) => void;
  onSubmit: (event: FormEvent) => void;
  project: Project | null;
  run: RunState | null;
  subagents: AgentRun[];
}) {
  const listRef = useRef<HTMLDivElement | null>(null);
  const subagentSummaries = buildSubagentSummaries(run, subagents);

  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    list.scrollTop = list.scrollHeight;
  }, [chatMessages.length]);

  return (
    <>
      <header className="chat-header">
        <div>
          <p>{project?.workspace.workspace_root ?? "No workspace selected"}</p>
          <h1>{project?.name ?? "Choose a project"}</h1>
        </div>
        <ConnectionState state={loadState} />
      </header>

      <div className="message-list" aria-label="Project orchestrator chat" ref={listRef}>
        {error ? <div className="error-banner">{error}</div> : null}
        {chatMessages.length > 0 ? (
          <>
            {chatMessages.map((item) => <ChatBubble item={item} key={item.id} />)}
            {subagentSummaries.length ? (
              <section className="subagent-inline-panel" aria-label="Subagent work returned">
                <div className="subagent-inline-title">
                  <span>
                    <Bot size={15} aria-hidden="true" />
                    Retrieved from subagents
                  </span>
                  <strong>{subagentSummaries.length}</strong>
                </div>
                <div className="subagent-inline-list">
                  {subagentSummaries.map((summary) => (
                    <button
                      className="subagent-inline-card"
                      key={summary.id}
                      onClick={() => onInspectAgent(summary.id)}
                      type="button"
                    >
                      <div>
                        <div className="subagent-inline-meta">
                          <strong>{summary.title}</strong>
                          <StatusPill status={summary.status} />
                        </div>
                        <p>{summary.summary}</p>
                        <span>
                          {summary.detailCount} log entries
                          {summary.approvalCount ? ` / ${summary.approvalCount} approval` : ""}
                        </span>
                      </div>
                      <ChevronRight size={17} aria-hidden="true" />
                    </button>
                  ))}
                </div>
              </section>
            ) : null}
          </>
        ) : (
          <div className="empty-chat">
            <MessageSquare size={28} aria-hidden="true" />
            <strong>Talk to the project orchestrator.</strong>
            <span>Subagents run in the background and appear in the activity rail.</span>
          </div>
        )}
      </div>

      <Composer
        disabled={!project}
        value={message}
        onChange={onMessageChange}
        onSubmit={onSubmit}
        placeholder="Message the project orchestrator"
      />
    </>
  );
}
