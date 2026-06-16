import { FormEvent } from "react";
import { ChatMessage } from "../../types";
import { ChatBubble } from "../chat/ChatBubble";
import { Composer } from "../chat/Composer";
import { ConnectionState } from "../status/ConnectionState";

export function RootProjectView({
  messages,
  message,
  onMessageChange,
  onSubmit,
}: {
  messages: ChatMessage[];
  message: string;
  onMessageChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
}) {
  return (
    <section className="root-view">
      <header className="chat-header">
        <div>
          <p>System project / local installation</p>
          <h1>Root project</h1>
        </div>
        <ConnectionState state="idle" />
      </header>

      <div className="message-list" aria-label="Root project orchestrator chat">
        {messages.map((item) => (
          <ChatBubble item={item} key={item.id} />
        ))}
      </div>

      <Composer
        value={message}
        onChange={onMessageChange}
        onSubmit={onSubmit}
        placeholder="Message the root orchestrator"
      />
    </section>
  );
}
