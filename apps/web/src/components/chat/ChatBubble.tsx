import { Bot, User } from "lucide-react";
import { ChatMessage } from "../../types";

export function ChatBubble({ item }: { item: ChatMessage }) {
  return (
    <article className={`chat-bubble ${item.side}`}>
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
          <time>{new Date(item.time).toLocaleTimeString()}</time>
        </div>
        <p>{item.body}</p>
      </div>
    </article>
  );
}
