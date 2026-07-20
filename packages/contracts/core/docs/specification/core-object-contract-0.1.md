# Core Object Contract 0.1 — Normative Specification

Status: assurance draft. This document is not a stable compatibility commitment until approved under the human-review protocol.

Normative terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT** and **MAY** are to be interpreted as requirements. Requirement identifiers are stable within this specification series.

## 1. Scope

The Core Object Contract defines interoperable identity, immutable versioning, payload integrity, provenance, policy, uncertainty, text anchoring and extension behaviour for SPWS and related PKL systems.

It does not define domain-specific writing objects, a general event-sourcing platform, legal conclusions, public-key identity or a universal provenance ontology.

## 2. Authority and conformance

**COC-NORM-AUTH-001** A conforming implementation MUST satisfy this specification, its released JSON Schemas and the associated conformance fixtures.

**COC-NORM-AUTH-002** Cross-field, graph, cryptographic and contextual invariants that cannot be represented completely in JSON Schema MUST be enforced by runtime validation.

**COC-NORM-AUTH-003** An implementation MUST NOT claim conformance solely because an instance passes JSON Schema validation.

**COC-NORM-AUTH-004** Unknown requirements or unsupported major schema versions MUST cause explicit rejection rather than permissive fallback.

## 3. Identity and immutable versions

**COC-NORM-ID-001** `object_id` identifies a logical object across all versions and MUST remain stable.

**COC-NORM-ID-002** `version_id` identifies one immutable snapshot and MUST be unique within the object history.

**COC-NORM-ID-003** Domain identifiers MUST conform to the selected UUIDv7 profile unless a field explicitly defines another identifier class.

**COC-NORM-ID-004** A stored version MUST NOT be modified in place. A semantic or byte-level change MUST create a new version.

**COC-NORM-ID-005** A version MUST NOT list itself as a parent, directly or transitively.

**COC-NORM-ID-006** Parent relationships MUST form a directed acyclic graph.

**COC-NORM-ID-007** Concurrent writes derived from the same expected head MUST be detected. Silent last-write-wins behaviour is non-conforming.

## 4. Time

**COC-NORM-TIME-001** Instants MUST use RFC 3339 timestamps with an explicit offset.

**COC-NORM-TIME-002** Canonical serialized instants MUST be normalised to UTC where the field profile requires canonical comparison.

**COC-NORM-TIME-003** A time window with both bounds present MUST have an end not earlier than its start.

**COC-NORM-TIME-004** Unknown, withheld and unavailable times MUST use explicit presence semantics rather than sentinel dates.

## 5. Payloads and representations

**COC-NORM-PAYLOAD-001** Exact source bytes, decoded text and normalised text MUST be represented as distinct representations when more than one exists.

**COC-NORM-PAYLOAD-002** Normalisation or decoding MUST NOT overwrite or masquerade as the original representation.

**COC-NORM-PAYLOAD-003** Every transformation MUST identify its source representation and transformation activity.

**COC-NORM-PAYLOAD-004** A tombstone payload MUST be content-free.

**COC-NORM-PAYLOAD-005** Media type, character encoding and representation kind MUST be explicit whenever ambiguity would affect interpretation or digest verification.

## 6. Digests and canonicalisation

**COC-NORM-DIGEST-001** Raw-byte digests MUST be calculated over the exact bytes represented by the digest record.

**COC-NORM-DIGEST-002** Text digests MUST state the encoding and normalisation assumptions of the hashed representation.

**COC-NORM-DIGEST-003** Canonical JSON digests MUST use the declared RFC 8785 profile and MUST reject values outside the supported numeric domain.

**COC-NORM-DIGEST-004** Record digests MUST use a versioned projection that excludes the record-digest field itself and any other explicitly excluded non-authoritative fields.

**COC-NORM-DIGEST-005** A digest mismatch MUST be reported as corruption or representation disagreement. It MUST NOT be silently repaired.

**COC-NORM-DIGEST-006** Digest verification results MUST distinguish unverified, verified and failed states.

## 7. Provenance and contribution

**COC-NORM-PROV-001** Creation provenance MUST identify the creating activity and the responsible agent when known.

**COC-NORM-PROV-002** Unknown agents MUST be represented explicitly. They MUST NOT be replaced by invented identities.

**COC-NORM-PROV-003** Derived representations MUST preserve references to source versions and transformation activities.

**COC-NORM-PROV-004** Machine generation, human selection, human editing and human acceptance MUST remain distinguishable.

**COC-NORM-PROV-005** Human acceptance MUST NOT erase machine or source origin.

**COC-NORM-PROV-006** A provenance relation MUST NOT relate a version to itself where the relation asserts derivation, replacement or ancestry.

**COC-NORM-PROV-007** Exported objects MUST contain sufficient direct provenance to remain interpretable without access to a private provenance graph.

## 8. Rights, privacy, retention and policy

**COC-NORM-POLICY-001** Absence of rights evidence MUST NOT be interpreted as permission.

**COC-NORM-POLICY-002** Unknown rights MUST produce an explicit restrictive rights state.

**COC-NORM-POLICY-003** Policy evaluation MUST follow the released priority and conflict table.

**COC-NORM-POLICY-004** A prohibition MUST take precedence over an otherwise matching permission unless the specification explicitly defines a narrower reviewed exception.

**COC-NORM-POLICY-005** Local-only content MUST NOT receive an external-transmission permit.

**COC-NORM-POLICY-006** Operation decisions MUST include a stable outcome, machine-readable reason and safe human-readable explanation.

**COC-NORM-POLICY-007** Policy inheritance MUST be deterministic and auditable.

**COC-NORM-POLICY-008** Error messages and logs MUST NOT disclose content prohibited from the attempted operation.

**COC-NORM-POLICY-009** Exported objects MUST include enough direct policy context for safe handling without private policy storage.

**COC-NORM-POLICY-010** Retention expiry MUST NOT be represented as completed deletion unless all required deletion actions and outstanding scopes are reported honestly.

## 9. Missingness, evidence and confidence

**COC-NORM-QUAL-001** Missing, unavailable, withheld, ambiguous and failed values MUST be distinct states.

**COC-NORM-QUAL-002** A present value SHOULD identify its evidence method where the field can affect attribution, policy, ranking or user trust.

**COC-NORM-QUAL-003** Ambiguous values MUST preserve alternatives rather than selecting one without evidence.

**COC-NORM-QUAL-004** Confidence MUST state its scale or profile and MUST NOT imply calibration unless calibration evidence exists.

**COC-NORM-QUAL-005** Failed derivation MUST preserve a stable failure code and safe diagnostic context.

## 10. Text spans and mappings

**COC-NORM-TEXT-001** The canonical text span coordinate system is Unicode code-point indexing unless a representation profile explicitly states otherwise.

**COC-NORM-TEXT-002** JavaScript UTF-16 offsets MUST be converted through tested mapping functions. They MUST NOT be treated as code-point offsets.

**COC-NORM-TEXT-003** Span bounds MUST be within the identified representation version.

**COC-NORM-TEXT-004** Quote selectors SHOULD accompany offsets where relocation or verification is required.

**COC-NORM-TEXT-005** Repeated exact quotes MUST use prefix, suffix or another disambiguator when a unique relocation is required.

**COC-NORM-TEXT-006** Raw-to-derived mappings MUST explicitly represent equal, replacement, insertion and deletion regions.

**COC-NORM-TEXT-007** Relocation ambiguity MUST be returned as ambiguity. An implementation MUST NOT silently choose an arbitrary match.

## 11. Extensions

**COC-NORM-EXT-001** Extensions MUST use a collision-resistant namespace and identify their schema where applicable.

**COC-NORM-EXT-002** Unknown non-critical extensions MAY be preserved without interpretation.

**COC-NORM-EXT-003** Unknown critical extensions MUST cause rejection.

**COC-NORM-EXT-004** Extension processing MUST NOT weaken core identity, integrity, provenance, privacy or policy invariants.

## 12. Version compatibility

**COC-NORM-COMPAT-001** Major-version changes indicate potentially incompatible interpretation or validation behaviour.

**COC-NORM-COMPAT-002** Minor-version changes MAY add backward-compatible optional capability but MUST NOT change the meaning of existing valid records.

**COC-NORM-COMPAT-003** Patch-version changes MUST be defect corrections that preserve the documented contract.

**COC-NORM-COMPAT-004** Prerelease identifiers do not create a stable compatibility promise, but each published prerelease remains immutable.

**COC-NORM-COMPAT-005** Migration adapters MUST declare source version, target version, information loss and generated provenance.

## 13. Deletion and tombstones

**COC-NORM-DELETE-001** Deletion of an immutable version MUST be represented by a new tombstone or deletion event rather than mutation of historical evidence.

**COC-NORM-DELETE-002** A tombstone MUST retain only the metadata needed to identify the deletion and its provenance, policy and outstanding scope.

**COC-NORM-DELETE-003** Derived copies, exports, backups or external systems that may remain MUST be reported as outstanding scope.

**COC-NORM-DELETE-004** A system MUST NOT claim cryptographic erasure, physical erasure or complete external deletion without evidence appropriate to that claim.

## 14. Security and resource limits

**COC-NORM-SEC-001** Implementations MUST enforce documented limits on input bytes, nesting, collection lengths, graph traversal and decompression.

**COC-NORM-SEC-002** Validation failures MUST be bounded in size and safe for logs.

**COC-NORM-SEC-003** Importers MUST prevent archive path traversal and unsafe external reference resolution.

**COC-NORM-SEC-004** Verification and policy decisions MUST fail closed when required evidence cannot be evaluated safely.

## 15. Conformance claims

**COC-NORM-CONF-001** A release claim MUST identify the exact specification, schema release, fixture release and implementation version tested.

**COC-NORM-CONF-002** A cross-language parity claim MUST identify the compared canonical bytes or fixture outcomes.

**COC-NORM-CONF-003** A reproducibility claim MUST state the environment, inputs, tools and expected artifact digests.

**COC-NORM-CONF-004** Stable promotion is prohibited until `InputPackage` and `RawSource` proving contracts pass persistence, export, policy, provenance and corruption tests.

## 16. Open assurance items

Before approval, reviewers must resolve:

- the exact supported JSON numeric domain;
- resource-limit defaults and override policy;
- the licence boundary for code, schemas, fixtures and documentation;
- the dedicated runtime repository and package authority;
- signing identity and release provenance mechanism;
- the independent conformance implementation requirement.
