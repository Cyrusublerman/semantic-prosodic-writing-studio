# Core Object Contract Assurance Programme

This directory defines the Phase 5.5 assurance gate between the immutable `0.1.0-dev.2` schema baseline and Phase 6 proving contracts.

The gate exists to prevent ingestion, persistence and downstream modules from depending on behaviour that is executable but not yet normatively governed, independently reviewed or supply-chain hardened.

## Authority order

When sources disagree, authority is resolved in this order:

1. a released normative specification;
2. a released schema and fixture package;
3. a recorded architecture decision;
4. public package behaviour;
5. tests and implementation details;
6. research notes and historical documents.

An implementation defect must not be converted into a normative rule merely because existing tests reproduce it.

## Gate files

- `../specification/core-object-contract-0.1.md` — normative contract specification;
- `../adr/` — architectural decisions and consequences;
- `../security/threat-model.md` — trust boundaries, threats and required controls;
- `../governance/` — compatibility, release, review and migration policy;
- `../conformance/assurance-matrix.md` — requirement-to-evidence traceability;
- `../../ASSURANCE_GATE.json` — machine-readable gate state.

## Entry rule for Phase 6

Phase 6 implementation may begin only when every gate marked `required_for_phase6` is `satisfied`, with evidence committed or linked. Stable release promotion additionally requires every gate marked `required_for_stable`.

A waiver must be:

- explicit and time-limited;
- linked to an owner and issue;
- accompanied by risk, containment and expiry conditions;
- prohibited for integrity, privacy, deletion honesty, provenance survival or compatibility claims.

## Current status

The Phase 5 implementation and immutable release are technically validated. Governance, independent review, dedicated-repository migration, signing, SBOM publication, expanded adversarial testing and repository ontology remediation remain controlled work rather than implied completion.
