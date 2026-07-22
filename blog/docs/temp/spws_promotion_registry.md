# SPWS component promotion registry (D017)

Stage key: identified → researched → specified → isolated_prototype → component_validated → adapter_integrated → pipeline_validated → reviewed_and_promoted

| Component | Stage | Proof |
|-----------|-------|-------|
| contracts_core | reviewed_and_promoted | `tests/contract/test_phase1_policy_contracts.py` |
| storage_hybrid | reviewed_and_promoted | `tests/integration/test_manuscript_sqlite.py` |
| analysis_fanout | reviewed_and_promoted | `tests/integration/test_analysis_fanout.py` |
| evaluation_bundle | reviewed_and_promoted | `tests/integration/test_evaluation_bundle.py` |
| orchestration_pause_resume | reviewed_and_promoted | `tests/integration/test_executor_pause_resume.py` |
| wordrare_adapter_matrix | reviewed_and_promoted | `tests/component/test_wordrare_capabilities.py` |
| poetry_revision_r1 | reviewed_and_promoted | `tests/integration/test_r1_vertical_slice.py` |
| collage_r2 | reviewed_and_promoted | `tests/integration/test_collage_r2.py` |
| studio_web_react | reviewed_and_promoted | Vitest + `tests/end_to_end/test_studio_playwright.py` + CI Playwright |
| tombstone_retention | reviewed_and_promoted | `tests/integration/test_tombstone.py` |
| llm_producer | identified | N/A non-goal; socket fail-closed MET |

Only promoted scope claimed MET in `spws_release_evidence.md`.
