# Core Object Contract Threat Model

Status: assurance draft. Review is required before Phase 6 ingestion or persistence work.

## 1. Protected properties

The system protects:

- identity stability and version immutability;
- payload and record integrity;
- truthful provenance and contribution history;
- rights, privacy, retention and operation policy;
- explicit uncertainty and missingness;
- text-coordinate correctness;
- deletion honesty;
- schema and release authenticity;
- confidentiality of local-only or restricted content;
- availability under bounded hostile input.

## 2. Trust boundaries

1. Untrusted source bytes and archives entering an importer.
2. Decoding and normalisation boundaries between raw bytes and text.
3. Runtime validation boundaries between JSON Schema and semantic checks.
4. Storage boundaries between process memory and the object store.
5. Export boundaries where policy decisions permit or deny transmission.
6. Language boundaries between Python and JavaScript coordinate and serialization models.
7. Release boundaries between repository source, build runner and published artifact.
8. Human review boundaries where machine-generated assertions become accepted decisions.

No boundary is implicitly trusted because it is local.

## 3. Adversary classes

- malformed or adversarial input supplied accidentally or deliberately;
- a compromised or defective dependency;
- a faulty importer or migration adapter;
- an authorised user attempting an operation outside policy;
- a build or release process producing untraceable artifacts;
- an internal implementation defect that silently changes interpretation;
- a reviewer accepting misleading machine provenance or confidence.

## 4. Threat register

| ID | Threat | Required controls | Required evidence |
|---|---|---|---|
| TM-001 | Oversized or deeply nested JSON exhausts memory or recursion | byte, depth, collection and diagnostic limits; streaming where justified | boundary and fuzz tests |
| TM-002 | Archive traversal or decompression bomb | canonical path checks, entry limits, expansion ratio and total-byte limits | malicious archive fixtures |
| TM-003 | Malformed UTF-8 or decoder disagreement changes content | strict decoding profile; preserve raw bytes; record failures explicitly | cross-runtime decoder fixtures |
| TM-004 | Unicode normalisation or confusables alter identity or anchoring | representation separation; declared Unicode profile; no implicit identifier normalisation | Unicode test corpus and span round trips |
| TM-005 | Digest substitution or wrong digest domain | typed digest basis; versioned projection; verify on write/read/export | mutation and corruption tests |
| TM-006 | Object or version identifier spoofing | strict UUID profile; uniqueness constraints; immutable bindings | collision and invalid-vector tests |
| TM-007 | Parent graph cycle causes traversal failure or false history | transactional cycle detection and bounded traversal | graph property tests |
| TM-008 | Lost update under concurrency | expected-head or compare-and-swap semantics | concurrent writer tests |
| TM-009 | Provenance forgery or origin erasure | immutable provenance; source/activity references; acceptance cannot replace origin | machine-to-human lifecycle fixtures |
| TM-010 | Unknown rights treated as permission | restrictive explicit unknown-rights profile | denial tests |
| TM-011 | Policy downgrade through inheritance or omission | deterministic conflict table; fail-closed missing context; auditable decisions | policy matrix and mutation tests |
| TM-012 | Local-only content leaks through export, logs or errors | operation gate before serialization; redacted diagnostics; no payload in denial logs | leakage tests and log review |
| TM-013 | Unknown critical extension ignored | mandatory rejection before use | extension fixtures |
| TM-014 | JSON numeric differences break canonical parity | supported numeric domain; reject unsupported values | official and adversarial RFC 8785 vectors |
| TM-015 | UTF-16/code-point confusion corrupts spans | tested conversions and explicit coordinate profile | emoji, combining and surrogate tests |
| TM-016 | Ambiguous quote relocation silently selects wrong text | return ambiguity with candidates; require disambiguation | repeated-quote fixtures |
| TM-017 | Storage corruption remains undetected | digest verification on read; quarantine and explicit failure | bit-flip and truncation tests |
| TM-018 | Tombstone retains content or deletion claim exceeds evidence | content-free tombstone; outstanding-scope report | deletion fixtures and storage inspection |
| TM-019 | Schema or artifact is modified after publication | immutable version paths, release guard, checksums and signatures | CI guard and signature verification |
| TM-020 | Compromised build dependency changes artifacts | locked dependencies, pinned actions, isolated builds, SBOM and provenance | reproducible builds and attestation |
| TM-021 | Error amplification leaks large attacker-controlled input | bounded structured errors; safe excerpts only | fuzz and snapshot tests |
| TM-022 | External schema reference causes SSRF or nondeterminism | closed registry or explicit allow-list; offline validation | network-disabled validation tests |
| TM-023 | Migration silently loses information | migration manifest, loss declaration and generated provenance | round-trip and loss fixtures |
| TM-024 | Human acceptance is inferred rather than recorded | explicit acceptance activity and responsible agent | lifecycle conformance cases |

## 5. Security invariants

The following may not be waived:

- digest mismatches never pass silently;
- unknown rights never become implicit permission;
- local-only content never receives an external-transmission permit;
- unknown critical extensions are rejected;
- machine/source origin survives human acceptance and edits;
- tombstones are content-free;
- deletion scope is reported honestly;
- unsupported major versions fail closed.

## 6. Phase 6 limits to define before implementation

The Phase 6 design must set explicit defaults for:

- maximum source bytes;
- maximum decoded text length;
- JSON nesting and collection lengths;
- archive entry count, expansion ratio and total expanded bytes;
- parent count and traversal depth;
- provenance relation count;
- extension count and value size;
- diagnostic count and per-diagnostic length;
- transaction duration and retry policy;
- export package size.

Defaults must be conservative, configurable only through a documented policy, and represented in conformance tests.

## 7. Incident handling

A suspected integrity, privacy or provenance defect requires:

1. stop promotion and external publication;
2. preserve affected artifacts and logs without leaking restricted content;
3. identify affected release versions and objects;
4. publish a scoped advisory when distribution has occurred;
5. produce a new immutable release rather than editing a published one;
6. add a regression fixture and test;
7. record whether historical claims remain valid.

## 8. Review requirements

Reviewers must include at least one person who did not author the implementation. Review must cover abuse cases, not only expected use. Approval must record residual risks, owners and review date.
