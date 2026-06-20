import { Bot, User } from "lucide-react";
import { ChatMessage } from "../../types";
import { StatusPill } from "../status/StatusPill";

export function ChatBubble({
  item,
  onInspectAgent,
}: {
  item: ChatMessage;
  onInspectAgent?: (agentId: string) => void;
}) {
  const isInspectable = Boolean(item.agentId && onInspectAgent);
  return (
    <article className={`chat-bubble ${item.side} ${item.kind ?? "chat"}`}>
      <div className="bubble-icon">
        {item.side === "user" ? (
          <User size={16} aria-hidden="true" />
        ) : (
          <Bot size={16} aria-hidden="true" />
        )}
      </div>
      <div className="bubble-body">
        <div className="bubble-meta">
          <strong>{item.title}</strong>
          <span>
            {item.status ? <StatusPill status={item.status} /> : null}
            <time>{new Date(item.time).toLocaleTimeString()}</time>
          </span>
        </div>
        <p>{item.body}</p>
        {isInspectable ? (
          <button
            className="bubble-action"
            onClick={() => item.agentId && onInspectAgent?.(item.agentId)}
            type="button"
          >
            {item.actionLabel ?? "Open subagent"}
          </button>
        ) : null}
      </div>
    </article>
  );
}
