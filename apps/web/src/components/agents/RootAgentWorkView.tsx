import { Bot, User } from "lucide-react";
import { RootAgentActivity } from "../../types";
import { AgentHeader, InterruptBar, MetaTile } from "./AgentWorkView";

export function RootAgentWorkView({
  agent,
  onBack,
}: {
  agent: RootAgentActivity;
  onBack: () => void;
}) {
  return (
    <section className="agent-work-view">
      <AgentHeader title={agent.name} subtitle="Root subagent" status={agent.status} onBack={onBack} />

      <div className="agent-work-meta">
        <MetaTile label="Model profile" value={agent.modelProfile} />
        <MetaTile label="Scope" value="Root project" />
        <MetaTile label="Run id" value={agent.id.slice(0, 8)} />
      </div>

      <div className="agent-work-log">
        <article className="work-entry system">
          <div className="bubble-icon">
            <User size={16} aria-hidden="true" />
          </div>
          <div>
            <strong>Assignment</strong>
            <p>{agent.summary}</p>
          </div>
        </article>
        <article className="work-entry agent">
          <div className="bubble-icon">
            <Bot size={16} aria-hidden="true" />
          </div>
          <div>
            <strong>Status</strong>
            <p>
              I am scoped to root-level project operations, not repository code work inside a
              workspace project.
            </p>
          </div>
        </article>
      </div>

      <InterruptBar placeholder="Interrupt or add context for this root subagent" />
    </section>
  );
}
