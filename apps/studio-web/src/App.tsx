import { useState } from "react";
import { apiGet, apiPost } from "./api";
import { AnalysisWorkspace } from "./components/AnalysisWorkspace";
import { CandidatesWorkspace } from "./components/CandidatesWorkspace";
import { ExportWorkspace } from "./components/ExportWorkspace";
import { ImportWorkspace } from "./components/ImportWorkspace";
import { PlanWorkspace } from "./components/PlanWorkspace";
import type {
  AnalysisPayload,
  AssistMode,
  Candidate,
  DecisionKind,
  EvalResult,
  ExportPayload,
  PlanPayload,
  RevisionOperation,
  WorkspaceId,
} from "./types";
import {
  summariseAnalysis,
  summariseCandidates,
  summariseExport,
  summariseImport,
  summarisePlan,
} from "./utils/summaries";

const TABS: { id: WorkspaceId; label: string }[] = [
  { id: "import", label: "Import" },
  { id: "analysis", label: "Analysis" },
  { id: "plan", label: "Plan" },
  { id: "candidates", label: "Candidates" },
  { id: "export", label: "Versions / Export" },
];

type ProposalState = {
  proposal_path?: string;
  status?: string;
  proposal?: { status?: string; candidate_set?: { candidates?: Candidate[] } };
  candidate_set?: { candidates?: Candidate[] };
  evaluation?: { results?: EvalResult[] };
  operations?: RevisionOperation[];
};

function extractCandidates(data: ProposalState | Record<string, unknown>): Candidate[] {
  const root = data as ProposalState;
  const nested = (root.proposal || root) as ProposalState;
  return (nested.candidate_set || root.candidate_set)?.candidates || [];
}

function extractEvalAndOps(data: ProposalState): {
  results: EvalResult[];
  operations: RevisionOperation[];
} {
  const nested = (data.proposal || data) as ProposalState & {
    evaluation?: { results?: EvalResult[] };
    operations?: RevisionOperation[];
  };
  return {
    results: nested.evaluation?.results || data.evaluation?.results || [],
    operations: nested.operations || data.operations || [],
  };
}

export default function App() {
  const [tab, setTab] = useState<WorkspaceId>("import");
  const [draft, setDraft] = useState("");
  const [brief, setBrief] = useState("improve diction");
  const [assistMode, setAssistMode] = useState<AssistMode>("rarefy");
  const [selection, setSelection] = useState("");
  const [busy, setBusy] = useState(false);

  const [analysis, setAnalysis] = useState<AnalysisPayload | null>(null);
  const [plan, setPlan] = useState<PlanPayload | null>(null);
  const [proposal, setProposal] = useState<ProposalState | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [evalResults, setEvalResults] = useState<EvalResult[]>([]);
  const [operations, setOperations] = useState<RevisionOperation[]>([]);
  const [lastExport, setLastExport] = useState<ExportPayload | null>(null);

  const [sumImport, setSumImport] = useState("No draft loaded.");
  const [sumAnalysis, setSumAnalysis] = useState("No analysis yet.");
  const [sumPlan, setSumPlan] = useState("No plan yet.");
  const [sumCandidates, setSumCandidates] = useState("No candidates yet.");
  const [sumExport, setSumExport] = useState("No export yet.");

  async function run(task: () => Promise<void>) {
    setBusy(true);
    try {
      await task();
    } finally {
      setBusy(false);
    }
  }

  function handleLoad() {
    setSumImport(summariseImport(draft));
  }

  function handleAnalyse() {
    void run(async () => {
      try {
        const data = await apiPost<AnalysisPayload>("/analyse", {
          text: draft,
          kind: "poem",
        });
        setAnalysis(data);
        setSumAnalysis(summariseAnalysis(data));
      } catch (err) {
        setSumAnalysis(String(err));
      }
    });
  }

  function handlePlanCreate() {
    void run(async () => {
      try {
        const data = await apiPost<PlanPayload>("/plan/create", {
          brief: brief || "improve diction",
          form: "free_verse",
          diagnosis: analysis?.diagnosis,
        });
        setPlan(data);
        setSumPlan(summarisePlan(data));
      } catch (err) {
        setSumPlan(String(err));
      }
    });
  }

  function handlePlanConfirm() {
    void run(async () => {
      try {
        const data = await apiPost<PlanPayload>("/plan/confirm", {
          plan,
          confirmed: true,
        });
        setPlan(data);
        setSumPlan(summarisePlan(data));
      } catch (err) {
        setSumPlan(String(err));
      }
    });
  }

  function applyCandidatePayload(data: ProposalState) {
    const cands = extractCandidates(data);
    const { results, operations: ops } = extractEvalAndOps(data);
    setProposal(data);
    setCandidates(cands);
    setEvalResults(results);
    setOperations(ops);
    setSumCandidates(summariseCandidates(cands, data));
  }

  function handlePropose() {
    void run(async () => {
      try {
        const data = await apiPost<ProposalState>("/revise/propose", {
          text: draft,
          brief: brief || "improve diction",
          work_plan: plan,
          diagnosis: analysis?.diagnosis,
        });
        applyCandidatePayload(data);
      } catch (err) {
        setSumCandidates(String(err));
      }
    });
  }

  function handleAssist() {
    void run(async () => {
      try {
        const text = selection.trim() || draft;
        const data = await apiPost<{
          candidates?: Candidate[];
          evaluation?: { results?: EvalResult[] };
          operations?: RevisionOperation[];
          status?: string;
          auto_apply?: boolean;
        }>("/assist/reword", {
          text,
          mode: assistMode,
        });
        const cands = data.candidates || [];
        setCandidates(cands);
        setEvalResults(data.evaluation?.results || []);
        setOperations(data.operations || []);
        setSumCandidates(summariseCandidates(cands, data));
      } catch (err) {
        setSumCandidates(String(err));
      }
    });
  }

  function handleDecide(index: number, kind: DecisionKind) {
    void run(async () => {
      const item = candidates[index];
      if (!item) return;
      const candidateId = item.candidate_id;
      // R3 / D004: never apply Accept locally without a persisted Propose proposal.
      if (!candidateId || !proposal?.proposal_path) {
        setSumCandidates(
          [
            `Decision: ${kind}`,
            "Error: run Propose first — decisions require a persisted proposal path.",
            "Draft was not modified.",
          ].join("\n"),
        );
        return;
      }
      try {
        const data = await apiPost<{
          decision?: { decision_id?: string; kind?: string };
          manuscript?: { text?: string };
          manuscript_path?: string;
          export?: ExportPayload;
        }>("/revise/decide", {
          candidate_id: candidateId,
          kind,
          proposal_path: proposal.proposal_path,
          export: kind === "accept",
        });
        if (kind === "accept" && data.manuscript?.text) {
          setDraft(data.manuscript.text);
        }
        if (data.export) {
          setLastExport(data.export);
          setSumExport(summariseExport(data.export));
        }
        setSumCandidates(
          [
            `Decision: ${kind}`,
            `Decision id: ${data.decision?.decision_id || "—"}`,
            `Manuscript path: ${data.manuscript_path || "—"}`,
            data.export ? "Export pack written." : "No export for this decision kind.",
          ].join("\n"),
        );
      } catch (err) {
        setSumCandidates(String(err));
      }
    });
  }

  function handleRefreshExport() {
    void run(async () => {
      try {
        if (lastExport) {
          setSumExport(summariseExport(lastExport));
          return;
        }
        const data = await apiGet<{ last_export?: ExportPayload | null }>("/session/export");
        setLastExport(data.last_export || null);
        setSumExport(summariseExport(data.last_export));
      } catch (err) {
        setSumExport(String(err));
      }
    });
  }

  return (
    <main className="shell">
      <header className="hero-header">
        <p className="brand">SPWS</p>
        <h1>Writing Studio</h1>
        <p className="lede">
          Five workspaces — diagnose, plan, decide, export. Human gate required; nothing auto-applies.
        </p>
      </header>

      <nav className="tabs" role="tablist" aria-label="Studio workspaces">
        {TABS.map((t) => {
          const on = tab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              className={on ? "tab active" : "tab"}
              data-tab={t.id}
              role="tab"
              aria-selected={on}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          );
        })}
      </nav>

      {tab === "import" && (
        <ImportWorkspace
          draft={draft}
          onDraftChange={setDraft}
          onLoad={handleLoad}
          summary={sumImport}
        />
      )}
      {tab === "analysis" && (
        <AnalysisWorkspace
          onAnalyse={handleAnalyse}
          summary={sumAnalysis}
          busy={busy}
          analysis={analysis}
        />
      )}
      {tab === "plan" && (
        <PlanWorkspace
          brief={brief}
          onBriefChange={setBrief}
          onCreate={handlePlanCreate}
          onConfirm={handlePlanConfirm}
          summary={sumPlan}
          busy={busy}
        />
      )}
      {tab === "candidates" && (
        <CandidatesWorkspace
          assistMode={assistMode}
          onAssistModeChange={setAssistMode}
          selection={selection}
          onSelectionChange={setSelection}
          onPropose={handlePropose}
          onAssist={handleAssist}
          onDecide={handleDecide}
          candidates={candidates}
          evaluationResults={evalResults}
          operations={operations}
          summary={sumCandidates}
          busy={busy}
        />
      )}
      {tab === "export" && (
        <ExportWorkspace onRefresh={handleRefreshExport} summary={sumExport} busy={busy} />
      )}
    </main>
  );
}
