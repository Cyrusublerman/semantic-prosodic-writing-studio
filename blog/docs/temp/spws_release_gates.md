# SPWS release gates

R1 poetry revision: import poem → AnalysisBundle (6 analysers) → meaning-similar evidence → ≥2 method families → human decision → ManuscriptVersion (SQLite+CAS) → D014 export incl. annotated.html.

R2 collage: board → CollagePlan candidates with span provenance + EvaluationBundle → human gate → ManuscriptVersion.

R3 assist: React studio + API reword; accept/reject only; no auto-apply; five textual workspaces.

Deterministic path must pass CI without torch (hash smoke). MiniLM job required for release quality. Frontend job: pnpm test + build. LLM producer out of scope; `llm_*` fail-closed.
