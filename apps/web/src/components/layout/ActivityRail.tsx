import { Bot } from "lucide-react";
import { ActivityCard } from "../../types";
import { StatusPill } from "../status/StatusPill";

export function ActivityRail({
  total,
  running,
  finished,
  onInspect,
}: {
  total: number;
  running: ActivityCard[];
  finished: ActivityCard[];
  onInspect: (agent: ActivityCard) => void;
}) {
  return (
    <aside className="subagents-pane">
      <header className="subagents-header">
        <p>Subagent activity</p>
        <h2>{total ? `${total} spawned` : "Idle"}</h2>
      </header>

      <SubagentGroup
        title="Running"
        agents={running}
        emptyText="No active subagents."
        onInspect={onInspect}
      />
      <SubagentGroup
        title="Finished"
        agents={finished}
        emptyText="No completed subagents."
        onInspect={onInspect}
      />
    </aside>
  );
}

function SubagentGroup({
  title,
  agents,
  emptyText,
  onInspect,
}: {
  title: string;
  agents: ActivityCard[];
  emptyText: string;
  onInspect: (agent: ActivityCard) => void;
}) {
  return (
    <section className="subagent-group">
      <div className="subagent-group-title">
        <span>{title}</span>
        <strong>{agents.length}</strong>
      </div>
      {agents.length ? (
        <div className="subagent-list">
          {agents.map((agent) => (
            <button className="subagent-card" key={agent.id} onClick={() => onInspect(agent)} type="button">
              <div className="agent-avatar">
                <Bot size={17} aria-hidden="true" />
              </div>
              <div className="subagent-copy">
                <strong>{agent.title}</strong>
                <span>{agent.subtitle}</span>
              </div>
              <StatusPill status={agent.status} />
            </button>
          ))}
        </div>
      ) : (
        <div className="subagent-empty">{emptyText}</div>
      )}
    </section>
  );
}
