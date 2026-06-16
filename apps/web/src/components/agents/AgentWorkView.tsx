import { Button, TextInput } from "@mantine/core";
import { Bot, ChevronLeft, User } from "lucide-react";
import { AgentRun, RunState } from "../../api";
import { buildAgentWork } from "../../utils/chat";
import { StatusPill } from "../status/StatusPill";

export function AgentWorkView({
  agent,
  run,
  onBack,
}: {
  agent: AgentRun;
  run: RunState | null;
  onBack: () => void;
}) {
  const entries = buildAgentWork(agent, run);
  return (
    <section className="agent-work-view">
      <AgentHeader title={agent.definition.name} subtitle="Subagent run" status={agent.status} onBack={onBack} />

      <div className="agent-work-meta">
        <MetaTile label="Model profile" value={agent.definition.model_profile} />
        <MetaTile label="Version" value={agent.definition.version} />
        <MetaTile label="Run id" value={agent.id.slice(0, 8)} />
      </div>

      <div className="agent-work-log">
        {entries.map((entry) => (
          <article className={`work-entry ${entry.side}`} key={entry.title}>
            <div className="bubble-icon">
              {entry.side === "system" ? <User size={16} aria-hidden="true" /> : <Bot size={16} aria-hidden="true" />}
            </div>
            <div>
              <strong>{entry.title}</strong>
              <p>{entry.body}</p>
            </div>
          </article>
        ))}
      </div>

      <InterruptBar placeholder="Interrupt or add context for this subagent" />
    </section>
  );
}

export function AgentHeader({
  title,
  subtitle,
  status,
  onBack,
}: {
  title: string;
  subtitle: string;
  status: string;
  onBack: () => void;
}) {
  return (
    <header className="agent-work-header">
      <button className="back-button" onClick={onBack} type="button" aria-label="Back to project chat">
        <ChevronLeft size={18} aria-hidden="true" />
      </button>
      <div>
        <p>{subtitle}</p>
        <h1>{title}</h1>
      </div>
      <StatusPill status={status} />
    </header>
  );
}

export function MetaTile({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <strong>{label}</strong>
      <span>{value}</span>
    </div>
  );
}

export function InterruptBar({ placeholder }: { placeholder: string }) {
  return (
    <div className="agent-interrupt">
      <TextInput placeholder={placeholder} />
      <Button className="secondary-button" type="button" variant="default">
        Interrupt
      </Button>
    </div>
  );
}
