import type { EvalResult, RevisionOperation } from "../types";
import { tradeOffLines } from "../utils/summaries";

type Props = {
  evaluationResults?: EvalResult[];
  operations?: RevisionOperation[];
  candidateId?: string;
};

/** Textual per-criterion trade-off summary (improve / degrade / measured). */
export function TradeOffSummary({ evaluationResults, operations, candidateId }: Props) {
  const lines = tradeOffLines(evaluationResults, operations, candidateId);
  if (!lines.length) {
    return <p className="tradeoffs muted">No trade-off data for this candidate.</p>;
  }
  return (
    <ul className="tradeoffs" aria-label="Per-criterion trade-offs">
      {lines.map((line) => {
        const criterion = line.split(":")[0]?.trim() || line;
        return (
          <li key={line} data-criterion={criterion}>
            {line}
          </li>
        );
      })}
    </ul>
  );
}
