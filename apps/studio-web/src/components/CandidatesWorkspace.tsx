import { TradeOffSummary } from "./TradeOffSummary";
import type {
  AssistMode,
  Candidate,
  DecisionKind,
  EvalResult,
  RevisionOperation,
} from "../types";

const ASSIST_MODES: AssistMode[] = [
  "rarefy",
  "ground_to_library",
  "meter_fit",
  "theme_align",
];

const DECISIONS: { kind: DecisionKind; label: string }[] = [
  { kind: "accept", label: "Accept" },
  { kind: "reject", label: "Reject" },
  { kind: "combine", label: "Combine" },
  { kind: "defer", label: "Defer" },
  { kind: "manual_replace", label: "Manual replace" },
];

type Props = {
  assistMode: AssistMode;
  onAssistModeChange: (mode: AssistMode) => void;
  selection: string;
  onSelectionChange: (value: string) => void;
  onPropose: () => void;
  onAssist: () => void;
  onDecide: (index: number, kind: DecisionKind) => void;
  candidates: Candidate[];
  evaluationResults?: EvalResult[];
  operations?: RevisionOperation[];
  summary: string;
  busy?: boolean;
};

export function CandidatesWorkspace({
  assistMode,
  onAssistModeChange,
  selection,
  onSelectionChange,
  onPropose,
  onAssist,
  onDecide,
  candidates,
  evaluationResults,
  operations,
  summary,
  busy,
}: Props) {
  return (
    <section
      className="panel workspace"
      id="ws-candidates"
      data-testid="ws-candidates"
      data-workspace="candidates"
    >
      <h2>Candidates / Decision</h2>
      <p className="hint">
        Propose revision candidates, then Accept, Reject, Combine, Defer, or Manual replace.
        Assist modes are selection-scoped and never auto-apply.
      </p>

      <label htmlFor="assist-mode">Assist mode</label>
      <select
        id="assist-mode"
        value={assistMode}
        onChange={(e) => onAssistModeChange(e.target.value as AssistMode)}
      >
        {ASSIST_MODES.map((mode) => (
          <option key={mode} value={mode}>
            {mode}
          </option>
        ))}
      </select>

      <label htmlFor="selection-scope">Selection (assist scope)</label>
      <textarea
        id="selection-scope"
        rows={3}
        placeholder="Optional span to reword — leave blank to use the full draft"
        value={selection}
        onChange={(e) => onSelectionChange(e.target.value)}
      />

      <div className="actions">
        <button
          type="button"
          id="btn-propose"
          data-testid="btn-propose"
          onClick={onPropose}
          disabled={busy}
        >
          Propose
        </button>
        <button type="button" id="btn-assist" data-testid="btn-assist" onClick={onAssist} disabled={busy}>
          Assist reword
        </button>
      </div>

      <ul id="candidates" data-testid="candidates">
        {candidates.map((item, index) => {
          const revised = item.revised || item.content || item.revised_text || "";
          const method = item.method_family || item.mode || "candidate";
          const cid = item.candidate_id || String(index);
          return (
            <li key={cid}>
              <div className="cand-text">{revised}</div>
              <div className="meta">
                {method} · {cid}
              </div>
              <TradeOffSummary
                evaluationResults={evaluationResults}
                operations={operations}
                candidateId={item.candidate_id}
              />
              <div className="actions">
                {DECISIONS.map(({ kind, label }) => (
                  <button
                    key={kind}
                    type="button"
                    data-act={kind}
                    data-i={index}
                    data-testid={kind === "accept" ? `btn-accept-${index}` : `btn-${kind}-${index}`}
                    onClick={() => onDecide(index, kind)}
                    disabled={busy}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </li>
          );
        })}
      </ul>

      <pre className="summary" id="sum-candidates" data-testid="sum-candidates">
        {summary}
      </pre>
    </section>
  );
}
