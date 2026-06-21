import { FormEvent, useEffect, useRef } from "react";
import { ChatMessage } from "../../types";
import { ChatBubble } from "../chat/ChatBubble";
import { ChatThinkingBubble } from "../chat/ChatThinkingBubble";
import { Composer } from "../chat/Composer";
import { ConnectionState } from "../status/ConnectionState";

export function RootProjectView({
  error,
  isPending,
  messages,
  message,
  isModelProviderConfigured,
  modelProviderEnvVar,
  onMessageChange,
  onOpenSettings,
  onSubmit,
}: {
  error: string | null;
  isPending: boolean;
  messages: ChatMessage[];
  message: string;
  isModelProviderConfigured: boolean;
  modelProviderEnvVar: string;
  onMessageChange: (value: string) => void;
  onOpenSettings: () => void;
  onSubmit: (event: FormEvent) => void;
}) {
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    list.scrollTop = list.scrollHeight;
  }, [messages.length, isPending]);

  return (
    <section className="root-view">
      <header className="chat-header">
        <div>
          <p>System project / live workspace inventory</p>
          <h1>Root project</h1>
        </div>
        <ConnectionState state={isPending ? "loading" : "idle"} />
      </header>

      {!isModelProviderConfigured ? (
        <div className="missing-credential-banner" role="status" aria-live="polite">
          <div>
            <strong>OpenRouter API key is not configured.</strong>
            <p>
              Model requests are disabled. Add {modelProviderEnvVar} and restart the API service to
              enable real OpenRouter calls.
            </p>
          </div>
          <button className="secondary-button" onClick={onOpenSettings} type="button">
            Open settings
          </button>
        </div>
      ) : null}

      <div className="message-list" aria-label="Root project orchestrator chat" ref={listRef}>
        {error ? <div className="error-banner">{error}</div> : null}
        {messages.map((item) => (
          <ChatBubble item={item} key={item.id} />
        ))}
        {isPending ? <ChatThinkingBubble title="Root orchestrator" /> : null}
      </div>

      <Composer
        disabled={isPending}
        value={message}
        onChange={onMessageChange}
        onSubmit={onSubmit}
        placeholder="Message the root orchestrator"
      />
    </section>
  );
}
