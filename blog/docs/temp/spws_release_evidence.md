# SPWS release evidence (Phase 11 audit)

Status key: **MET** | **N/A (non-goal)**

Proof standard (D017): contract + pipeline/API + fixture/e2e + export/UI surface.

| Gate | Status | Proof |
|------|--------|-------|
| D001 source-aware poetry revision | MET | `test_r1_vertical_slice.py`, React five workspaces |
| D002.1–8 minimum outcome | MET | import preserve; 6 analysers; diagnosis; ≥2 families; trade-offs UI; decide; dual MS versions; D014 pack |
| D003 dialect AU | MET | `DialectPolicy` default en-AU; `test_phase1_policy_contracts.py`; R1 assert |
| D004 human authority | MET | pause/resume gates; no local-only Accept; `auto_apply:false` |
| D005 LLM producer | N/A (non-goal) | — |
| D005 LLM socket fail-closed | MET | `llm_socket.py`; `test_pipeline_handlers.py`; CI step |
| D006 rights/privacy | MET | `restricted_pending_review`; fail-closed retrieval; tombstone test |
| D007 evaluation dimensions | MET | 12 criteria in `evaluation.py`; `test_evaluation_bundle.py`; human_preference on decide |
| D008 WordRare extract | N/A (non-goal) | in-tree adapter boundary kept |
| D009 stack | MET | Py3.12/FastAPI/SQLAlchemy2/Alembic/React Vite/Vitest/Playwright/uv/pnpm |
| D010 pipeline runtime | MET | `test_executor_pause_resume.py` |
| D011 storage hybrid | MET | `test_manuscript_sqlite.py` |
| D012 contracts/spans | MET | LexicalRecord, ExchangeEnvelope, Classification*, PublicationBundle; envelopes on propose |
| D013 five workspaces | MET | React workspaces; analysis-components; TradeOffSummary; Playwright |
| D014 exports | MET | txt/md/html/json/provenance/diff + publication_bundle |
| D015 WordRare matrix | MET | `test_wordrare_capabilities.py` incl. all-five ok |
| D016 vertical slice | MET | `pastoral_12_lines.txt` + R1 test |
| D017 promotion | MET | `spws_promotion_registry.md` + fixture proofs |
| R1 | MET | `test_r1_vertical_slice.py` |
| R2 | MET | `test_collage_r2.py` (spans required) |
| R3 | MET | Playwright studio flow + assist accept/reject only |

Audit loop: gaps A–I closed after first Phase 11 scorecard; re-verified with full pytest (50+) + Playwright + Vitest.
