import { FormEvent } from "react";
import { Project } from "../../api";
import { ChatMessage, LoadState } from "../../types";
import { ChatBubble } from "../chat/ChatBubble";
import { Composer } from "../chat/Composer";
import { ConnectionState } from "../status/ConnectionState";
import { MessageSquare } from "lucide-react";

export function ProjectChatView({
  chatMessages,
  error,
  loadState,
  message,
  onMessageChange,
  onSubmit,
  project,
}: {
  chatMessages: ChatMessage[];
  error: string | null;
  loadState: LoadState;
  message: string;
  onMessageChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
  project: Project | null;
}) {
  return (
    <>
      <header className="chat-header">
        <div>
          <p>{project?.workspace.workspace_root ?? "No workspace selected"}</p>
          <h1>{project?.name ?? "Choose a project"}</h1>
        </div>
        <ConnectionState state={loadState} />
      </header>

      {error ? <div className="error-banner">{error}</div> : null}

      <div className="message-list" aria-label="Project orchestrator chat">
        {chatMessages.length > 0 ? (
          chatMessages.map((item) => <ChatBubble item={item} key={item.id} />)
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
