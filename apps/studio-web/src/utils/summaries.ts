import type {
  AnalysisPayload,
  Candidate,
  EvalResult,
  ExportPayload,
  PlanPayload,
  RevisionOperation,
} from "../types";

export function summariseImport(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) return "No draft loaded.";
  const lines = trimmed.split(/\r?\n/).length;
  return `Loaded ${lines} lines · ${trimmed.length} characters. Draft preserved exactly as entered.`;
}

export function summariseAnalysis(data: AnalysisPayload | null): string {
  if (!data) return "No analysis yet.";
  const diag = data.diagnosis;
  if (!diag) return "Analysis returned without a diagnosis.";
  const conf = data.field_confidence || {};
  const rights = data.rights ? `Rights: ${data.rights}` : "Rights: not stated";
  const privacy = data.privacy ? `Privacy: ${data.privacy}` : "Privacy: not stated";
  return [
    `Kind: ${data.kind || "poem"}`,
    `Problem: ${diag.problem_type || "—"}`,
    `Target line: ${diag.target_line_index ?? "—"}`,
    `Suggested brief: ${diag.suggested_brief || "—"}`,
    `Syllable confidence: ${conf.syllable ?? "—"}`,
    `Semantic confidence: ${conf.semantic ?? "—"}`,
    rights,
    privacy,
  ].join("\n");
}

export function summarisePlan(plan: PlanPayload | null): string {
  if (!plan) return "No plan yet.";
  const wp = plan.work_plan || {};
  return [
    `Plan id: ${wp.plan_id || "—"}`,
    `Confirmed: ${plan.confirmed === true}`,
    `Confirmed at: ${plan.confirmed_at || "—"}`,
    `Brief: ${plan.brief || "—"}`,
    `Form: ${(plan.work_specification || {}).form || "—"}`,
    `Constraints: ${((wp.constraints) || []).length}`,
  ].join("\n");
}

export function summariseCandidates(
  candidates: Candidate[],
  payload?: { status?: string; proposal?: { status?: string } } | null,
): string {
  const families = [
    ...new Set(candidates.map((c) => c.method_family || c.mode || "?")),
  ];
  return [
    `Count: ${candidates.length}`,
    `Families: ${families.join(", ") || "—"}`,
    `Status: ${payload?.status || payload?.proposal?.status || "proposed"}`,
    `Auto-apply: false — human gate required.`,
  ].join("\n");
}

export function summariseExport(exp: ExportPayload | string | null | undefined): string {
  if (!exp) return "No export yet.";
  if (typeof exp === "string") return exp;
  const paths = exp.paths || exp.files || exp;
  if (Array.isArray(paths)) {
    return ["Export files:", ...paths.map((p) => `· ${p}`)].join("\n");
  }
  if (paths && typeof paths === "object") {
    const entries = Object.entries(paths as Record<string, string>);
    if (!entries.length) return "Export recorded with no file list.";
    return ["Export files:", ...entries.map(([k, v]) => `· ${k}: ${v}`)].join("\n");
  }
  return "Export recorded.";
}

/** Build per-criterion improve/degrade lines from evaluation results + operations. */
export function tradeOffLines(
  evaluationResults: EvalResult[] | undefined,
  operations: RevisionOperation[] | undefined,
  candidateId?: string,
): string[] {
  const lines: string[] = [];
  const ops = (operations || []).filter((op) =>
    candidateId ? op.candidate_id === candidateId : true,
  );
  if (ops.length) {
    for (const op of ops) {
      const improve = op.predicted_improvements || [];
      const degrade = op.predicted_degradations || [];
      for (const name of improve) {
        lines.push(`${name}: improve`);
      }
      for (const name of degrade) {
        lines.push(`${name}: degrade`);
      }
    }
  }
  if (!lines.length && evaluationResults?.length) {
    const names = [
      ...new Set(
        evaluationResults
          .filter((r) => (candidateId ? r.subject_id === candidateId : true))
          .map((r) => r.criterion)
          .filter((c): c is string => Boolean(c)),
      ),
    ];
    for (const name of names) {
      lines.push(`${name}: measured`);
    }
  }
  return lines;
}

export function criterionNamesFromEval(results: EvalResult[]): string[] {
  return [
    ...new Set(results.map((r) => r.criterion).filter((c): c is string => Boolean(c))),
  ];
}
