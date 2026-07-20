# Core Object Contract Assurance Matrix

This matrix is the minimum traceability model for Phase 5.5 and later promotion. Every normative requirement must eventually map to implementation, schema, fixture and test evidence. Blank evidence is a blocking gap, not an implied pass.

## Evidence classes

- **SPEC** — normative requirement;
- **SCHEMA** — structural validation;
- **RUNTIME** — cross-field, graph, policy or cryptographic validation;
- **FIXTURE** — portable example with expected outcomes;
- **PROPERTY** — generated invariant testing;
- **MUTATION** — evidence that tests kill defective logic;
- **FUZZ** — malformed or adversarial input testing;
- **XPLAT** — cross-runtime or cross-platform evidence;
- **REVIEW** — human or independent review;
- **RELEASE** — immutable artifact, digest, SBOM, signature or provenance.

## Critical assurance rows

| Requirement group | Existing evidence | Required additional evidence | Phase 6 gate |
|---|---|---|---|
| `COC-NORM-ID-*` identity and immutability | Pydantic models, schemas, invalid identity and parent fixtures | graph property suite, concurrent writer tests, 100% branch coverage, mutation tests | blocking |
| `COC-NORM-DIGEST-*` integrity | SHA-256/JCS implementation, canonical parity, invalid digest fixture | official RFC 8785 vectors, numeric-domain rejection, bit-flip corpus, mutation tests | blocking |
| `COC-NORM-PROV-*` provenance survival | provenance models and self-relation fixture | machine generation → human acceptance → edit lifecycle fixtures, export proof | blocking |
| `COC-NORM-POLICY-*` rights/privacy/policy | policy models, local-only invalid fixture, transmission denial fixture | complete decision table tests, inheritance properties, error leakage review | blocking |
| `COC-NORM-QUAL-*` missingness/confidence | qualified-value fixtures | calibrated-confidence negative cases, alternative preservation properties | blocking |
| `COC-NORM-TEXT-*` text anchoring | emoji, combining, CRLF and repeated-quote fixtures | full Unicode normalisation data, UTF-16 round-trip properties, relocation fuzzing | blocking |
| `COC-NORM-EXT-*` extensions | critical-extension fixture | unsupported critical schema and oversized extension tests | blocking |
| `COC-NORM-COMPAT-*` compatibility | release version and compatibility report | adapter contract, backwards-compatibility comparator, immutable-release guard | blocking |
| `COC-NORM-DELETE-*` deletion | tombstone fixture | store-level deletion and outstanding-scope proof | Phase 7 blocking |
| `COC-NORM-SEC-*` security limits | threat model | implemented resource limits, archive attack corpus, bounded diagnostics | blocking before importers |
| `COC-NORM-CONF-*` claims | capability report and deterministic archive | independent consumer, SBOM, signed provenance, human approval | stable blocking |

## Release evidence ledger

| Evidence | Current state | Required authority |
|---|---|---|
| Immutable schema directory `0.1.0-dev.2` | present | repository history and release guard |
| Release root digest | present | deterministic rebuild |
| Deterministic ZIP digest | present | deterministic rebuild |
| Python fixtures | pass | locked Python matrix |
| Ajv fixtures | pass | locked Node matrix |
| Hyperjump fixtures | pass | locked Node matrix |
| TypeScript compilation | pass | generated declarations and consumer compile |
| Canonical byte parity | four cases pass | official/adversarial vectors and supported-domain statement |
| Python tests | 73 pass | expanded property/mutation/fuzz suites |
| Combined coverage | 90% | 95% package branch; 100% critical branches |
| Human review | absent | recorded independent review |
| Dedicated runtime repository | absent | owner-created repository and migration verification |
| Tagged prerelease | absent | immutable tag and GitHub prerelease |
| SBOM | absent | SPDX or CycloneDX artifact |
| Build provenance | absent | verifiable provenance attestation |
| Artifact signatures | absent | documented signing identity and verification |
| Licence decision | unresolved | owner approval and committed licences |

## Definition of satisfied

A gate is `satisfied` only when:

1. the evidence is stored in an immutable commit or external release;
2. the evidence identifies exact tool and artifact versions;
3. negative tests demonstrate rejection behaviour;
4. the result is reproducible by a fresh clone;
5. required human review is recorded;
6. no unresolved critical or high residual risk remains.

A passing test run without requirement traceability is implementation evidence, not complete assurance evidence.
