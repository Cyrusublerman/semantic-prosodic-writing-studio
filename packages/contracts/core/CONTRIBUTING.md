# Contributing

This package is governed as a contract and assurance project, not an ordinary feature library.

## Before changing code

1. Identify the affected normative requirement.
2. Determine whether an ADR or specification change is required.
3. Classify compatibility impact.
4. Add negative as well as positive evidence.
5. Confirm that no published release directory is modified.

## Change requirements

Every behaviour change must include:

- rationale and affected requirement identifiers;
- implementation and schema impact;
- portable fixture impact;
- Python and JavaScript validation where applicable;
- compatibility and migration analysis;
- threat-model impact;
- capability-report changes without overstated claims.

Critical invariant changes require property and mutation evidence. Parser, importer and relocation changes require fuzz or adversarial corpus evidence.

## Published releases

Files under a published version directory and its packaged archive are immutable. Create a new release version for corrections.

## Commit and pull-request discipline

- Keep normative, implementation and generated-artifact changes reviewable.
- Do not combine unrelated PKL catalogue outputs with runtime changes.
- Do not commit local environments, caches or unreviewed generated dependency graphs.
- Workflows must use least privilege and pinned action commits.
- CI must reproduce generated artifacts without a diff.

## Review

Passing CI is necessary but not sufficient. Normative, security, compatibility and release changes require review under `docs/governance/human-review-protocol.md`.

## Phase 6 restriction

`InputPackage`, `RawSource`, persistence and export implementation is blocked until `python tools/check_assurance_gate.py --require phase6` succeeds.
