import { Button, TextInput } from "@mantine/core";
import { Bot, Check, ChevronLeft, User, X } from "lucide-react";
import { AgentRun, ApprovalRecord, RunState } from "../../api";
import { buildAgentWork } from "../../utils/chat";
import { StatusPill } from "../status/StatusPill";

export function AgentWorkView({
  agent,
  run,
  onBack,
  onApprove,
  onReject,
}: {
  agent: AgentRun;
  run: RunState | null;
  onBack: () => void;
  onApprove: (approval: ApprovalRecord) => void;
  onReject: (approval: ApprovalRecord) => void;
}) {
  const entries = buildAgentWork(agent, run);
  const approvals = run?.approvals.filter((approval) => approval.agent_run_id === agent.id) ?? [];
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
              <div className="work-entry-title">
                <strong>{entry.title}</strong>
                {entry.created_at ? <time>{new Date(entry.created_at).toLocaleTimeString()}</time> : null}
              </div>
              <p>{entry.body}</p>
            </div>
          </article>
        ))}
      </div>

      {approvals.length ? (
        <section className="approval-panel" aria-label="Approvals">
          <header>
            <span>Approvals</span>
            <strong>{approvals.length}</strong>
          </header>
          {approvals.map((approval) => {
            const artifact = run?.artifacts.find((item) => item.id === approval.artifact_id);
            const isPending = approval.status === "pending";
            return (
              <article className="approval-card" key={approval.id}>
                <div className="approval-card-header">
                  <div>
                    <strong>{approval.action}</strong>
                    <span>{approval.status}</span>
                  </div>
                  <StatusPill status={approval.status} />
                </div>
                {artifact?.content ? <pre>{artifact.content}</pre> : null}
                {approval.failure_reason ? <p className="approval-error">{approval.failure_reason}</p> : null}
                {isPending ? (
                  <div className="approval-actions">
                    <Button
                      className="secondary-button"
                      leftSection={<X size={15} aria-hidden="true" />}
                      onClick={() => onReject(approval)}
                      type="button"
                      variant="default"
                    >
                      Reject
                    </Button>
                    <Button
                      leftSection={<Check size={15} aria-hidden="true" />}
                      onClick={() => onApprove(approval)}
                      type="button"
                    >
                      Approve
                    </Button>
                  </div>
                ) : null}
              </article>
            );
          })}
        </section>
      ) : null}

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
