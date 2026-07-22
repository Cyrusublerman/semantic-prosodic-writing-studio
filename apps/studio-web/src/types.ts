export type WorkspaceId = "import" | "analysis" | "plan" | "candidates" | "export";

export type AssistMode = "rarefy" | "ground_to_library" | "meter_fit" | "theme_align";

export type DecisionKind = "accept" | "reject" | "combine" | "defer" | "manual_replace";

export type EvalResult = {
  criterion?: string;
  subject_id?: string;
  measured_value?: number | null;
};

export type RevisionOperation = {
  candidate_id?: string;
  predicted_improvements?: string[];
  predicted_degradations?: string[];
  revised_text?: string;
  original_text?: string;
  operation?: string;
};

export type Candidate = {
  candidate_id?: string;
  content?: string;
  revised?: string;
  revised_text?: string;
  method_family?: string;
  mode?: string;
  line_index?: number;
  rights?: string;
};

export type AnalysisAnnotation = {
  analyser?: string;
  feature?: string;
  value?: unknown;
};

export type AnalysisPayload = {
  kind?: string;
  diagnosis?: {
    problem_type?: string;
    target_line_index?: number;
    suggested_brief?: string;
  };
  field_confidence?: {
    syllable?: number;
    semantic?: number;
  };
  rights?: string;
  privacy?: string;
  bundle?: {
    component_versions?: Record<string, string>;
    annotations?: AnalysisAnnotation[];
  };
};

export type PlanPayload = {
  confirmed?: boolean;
  confirmed_at?: string | null;
  brief?: string;
  work_plan?: {
    plan_id?: string;
    constraints?: unknown[];
  };
  work_specification?: {
    form?: string;
  };
};

export type ExportPayload = {
  paths?: Record<string, string> | string[];
  files?: string[] | Record<string, string>;
  clean?: string;
  bundle?: string;
  provenance?: string;
};
