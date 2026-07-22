import type { AnalysisPayload } from "../types";

const SIX_ANALYSERS = [
  "lexical",
  "prosodic",
  "semantic",
  "structural",
  "repetition_motif",
  "provenance",
] as const;

type Props = {
  onAnalyse: () => void;
  summary: string;
  busy?: boolean;
  analysis?: AnalysisPayload | null;
};

function itemsForAnalyser(
  analysis: AnalysisPayload | null | undefined,
  analyser: string,
): string[] {
  const versions = analysis?.bundle?.component_versions || {};
  const annotations = analysis?.bundle?.annotations || [];
  const version = versions[analyser];
  const fromAnn = annotations
    .filter((a) => (a.analyser || "").includes(analyser) || a.analyser === analyser)
    .map((a) => {
      const feature = a.feature || "annotation";
      const value =
        a.value === undefined || a.value === null
          ? ""
          : typeof a.value === "object"
            ? JSON.stringify(a.value)
            : String(a.value);
      return value ? `${feature}: ${value}` : feature;
    });
  const items = [...fromAnn];
  if (version !== undefined) {
    items.unshift(`version: ${version}`);
  }
  if (!items.length && analysis) {
    items.push("(no annotations)");
  }
  return items;
}

export function AnalysisWorkspace({ onAnalyse, summary, busy, analysis }: Props) {
  return (
    <section
      className="panel workspace"
      id="ws-analysis"
      data-testid="ws-analysis"
      data-workspace="analysis"
    >
      <h2>Analysis</h2>
      <p className="hint">Run the analysis suite and review the textual diagnosis and confidence.</p>
      <div className="actions">
        <button
          type="button"
          id="btn-analyse"
          data-testid="btn-analyse"
          onClick={onAnalyse}
          disabled={busy}
        >
          Analyse
        </button>
      </div>
      <pre className="summary" id="sum-analysis" data-testid="sum-analysis">
        {summary}
      </pre>
      <div data-testid="analysis-components" className="analysis-components">
        <h3>Analyser components</h3>
        {SIX_ANALYSERS.map((name) => {
          const items = itemsForAnalyser(analysis, name);
          return (
            <div key={name} data-analyser={name} className="analyser-block">
              <h4>{name}</h4>
              <ul>
                {items.length ? (
                  items.map((item, index) => <li key={`${name}-${index}`}>{item}</li>)
                ) : (
                  <li>Not run yet.</li>
                )}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}
