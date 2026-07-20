# SPWS Contracts Core — Phases 4–5 Reference Implementation

This package implements the common Core Object Contract primitives and publishes immutable schema prerelease `0.1.0-dev.2`.

## Contents

- UUIDv7 identity, typed references and UTC time records;
- payload and record digests with RFC 8785 canonicalisation;
- provenance, contribution, rights, policy, privacy and retention records;
- explicit missingness, confidence, reviews, warnings and failures;
- Unicode code-point spans, quote selectors, mappings and relocation;
- minimal compositional `CoreObjectEnvelope`;
- 39 self-contained Draft 2020-12 model schemas;
- 21 positive and negative fixtures;
- generated TypeScript declarations and independent validation evidence;
- deterministic digest-addressed release archive.

## Release

```text
schemas/contracts-core/0.1.0-dev.2/
src/spws_contracts_core/data/releases/contracts-core-0.1.0-dev.2.zip
```

The published directory and archive are immutable. Corrections require a new release version.

## Rebuild and validate

```bash
python -m pip install -e '.[test]'
bash tools/build_phase5_release.sh
pytest --cov=spws_contracts_core --cov-branch
python -m build
python tools/check_assurance_gate.py
python tools/verify_immutable_release.py
```

## Phase 5.5 assurance

The assurance programme is defined by:

- `ASSURANCE_GATE.json`;
- `docs/specification/core-object-contract-0.1.md`;
- `docs/adr/`;
- `docs/security/threat-model.md`;
- `docs/governance/`;
- `docs/conformance/assurance-matrix.md`.

Phase 6 implementation is deliberately blocked until:

```bash
python tools/check_assurance_gate.py --require phase6
```

passes with approved evidence.

## Boundary

This is a complete Phase 5 prerelease retained in PKL until the dedicated runtime repository exists. It is not stable production authority. Phase 5.5 must establish the repository boundary, normative approval, adversarial assurance, licensing and independent review before Phase 6 proves `InputPackage`, `RawSource`, persistence and export without private schema forks.
