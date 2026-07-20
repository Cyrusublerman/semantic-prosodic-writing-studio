# Compatibility and Deprecation Policy

Status: assurance draft. Applies to schemas, fixtures, Python APIs, generated TypeScript declarations and serialized records.

## 1. Version model

Published release directories and artifacts are immutable.

- `dev` — exploratory prerelease; no compatibility promise between prereleases, but each published artifact remains immutable.
- `alpha` — contract shape remains open; migrations must be documented.
- `beta` — feature-complete target; incompatible changes require explicit approval and migration evidence.
- `rc` — intended release; only defect corrections and evidence changes are permitted.
- stable — semantic-version compatibility commitments apply.

## 2. Change classification

A change is **breaking** when an existing conforming consumer may reject, misinterpret or process differently a record that was valid under the previous supported release.

Breaking changes include:

- changing field meaning, units, coordinate systems or digest domains;
- making an optional field required;
- narrowing accepted values without a security correction process;
- removing or renaming fields, enum values or schemas;
- changing policy precedence or provenance semantics;
- changing canonical serialization or record projection;
- changing the meaning of missingness or confidence;
- altering generated TypeScript types incompatibly.

Additive optional fields are not automatically compatible. Their processing rules and criticality must be considered.

## 3. Compatibility requirements

1. Every release must declare supported predecessor versions.
2. A compatibility comparator must run against the immediately preceding supported release.
3. Existing valid fixtures must remain valid and semantically equivalent for a claimed backward-compatible release.
4. Existing invalid fixtures must not become valid unless the change is reviewed and documented.
5. Migration adapters must declare information loss, defaults, warnings and generated provenance.
6. Unknown major versions must be rejected.
7. Unknown critical extensions must be rejected.
8. Deprecation must not weaken privacy, rights, retention, deletion honesty or provenance.

## 4. Deprecation

Stable features require at least one minor release of deprecation before removal unless continued support creates a documented critical security or integrity risk.

A deprecation notice must include:

- affected identifiers and versions;
- replacement;
- migration instructions;
- earliest removal version;
- information-loss statement;
- contact or tracking issue.

## 5. Security corrections

A security correction may narrow previously accepted input. The release notes must explain the affected behaviour without publishing exploit details prematurely. A regression fixture and advisory are required when distributed users may be affected.

## 6. Adapter requirements

Adapters are explicit versioned components. They must:

- validate the source before migration;
- emit the target schema version;
- preserve source object and version identity where semantics permit;
- create a new version when content or interpretation changes;
- record migration activity and software identity;
- report dropped or synthesised information;
- verify the target after migration;
- support deterministic replay where claimed.

## 7. Stable promotion

Stable promotion is prohibited until `InputPackage` and `RawSource` integrations pass the complete Phase 7 suite and at least one independent consumer demonstrates interoperability without importing internal implementation modules.
