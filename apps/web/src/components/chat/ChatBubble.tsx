import { Bot, Check, X, User } from "lucide-react";
import { ApprovalRecord } from "../../api";
import { ChatMessage } from "../../types";
import { StatusPill } from "../status/StatusPill";

export function ChatBubble({
  item,
  onApprove,
  onInspectAgent,
  onReject,
}: {
  item: ChatMessage;
  onApprove?: (approval: ApprovalRecord) => void;
  onInspectAgent?: (agentId: string) => void;
  onReject?: (approval: ApprovalRecord) => void;
}) {
  const isInspectable = Boolean(item.agentId && onInspectAgent);
  const isPendingApproval = item.kind === "approval" && item.approval?.status === "pending";
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
        {isPendingApproval && item.approval ? (
          <div className="approval-inline-actions">
            <button
              className="bubble-action primary"
              onClick={() => item.approval && onApprove?.(item.approval)}
              type="button"
            >
              <Check size={14} aria-hidden="true" />
              Approve once
            </button>
            <button
              className="bubble-action danger"
              onClick={() => item.approval && onReject?.(item.approval)}
              type="button"
            >
              <X size={14} aria-hidden="true" />
              Reject
            </button>
          </div>
        ) : null}
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
