import { Bot } from "lucide-react";

export function ChatThinkingBubble({ title = "Project orchestrator" }: { title?: string }) {
  return (
    <article className="chat-bubble orchestrator thinking-bubble">
      <div className="bubble-icon">
        <Bot size={16} aria-hidden="true" />
      </div>
      <div className="bubble-body thinking-body" aria-label={`${title} is thinking`}>
        <span className="thinking-dots">
          <span>.</span>
          <span>.</span>
          <span>.</span>
        </span>
      </div>
    </article>
  );
}
