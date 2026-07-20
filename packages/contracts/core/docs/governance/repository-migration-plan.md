# Dedicated Runtime Repository Migration Plan

Status: assurance draft. Repository creation and settings require owner action.

Provisional target: `Cyrusublerman/spws-contracts-core`.

## Authority boundary

PKL remains authoritative for research, programme decisions and historical handoffs. The dedicated repository will become authoritative for runtime source, schemas, fixtures, tests, package documentation and releases.

The two repositories must not retain divergent active implementations.

## Migration source record

The extraction record must identify:

- source repository and path;
- source commit;
- Phase 5 release root and archive digests;
- extraction method;
- migration date and responsible agent.

## Target layout

```text
.github/
docs/
schemas/
src/
tests/
tools/
typescript/
ASSURANCE_GATE.json
CHANGELOG.md
CONTRIBUTING.md
LICENSE
README.md
SECURITY.md
THIRD_PARTY_NOTICES.md
pyproject.toml
```

## Controlled sequence

1. Owner creates an empty dedicated repository.
2. Copy the approved package allow-list from the reviewed PKL commit.
3. Preserve file modes and binary release archives.
4. Commit a migration provenance record.
5. Run the full assurance workflow from a clean clone.
6. Compare every `0.1.0-dev.2` file and digest with PKL.
7. Tag and publish the baseline only after byte-for-byte verification.
8. Update PKL links to the dedicated tag and release.
9. Freeze or remove the active PKL runtime copy in a separate reviewed change.

## Required repository controls

Before Phase 6 begins, the owner must configure protected default-branch changes, mandatory assurance checks, reviewed changes to normative/security/release files, least-privilege workflows, dependency updates, secret and dependency scanning where available, release-environment controls and CODEOWNERS.

## Completion criteria

Migration is complete only when:

- a fresh clone reproduces the schema archive digest;
- supported Python and Node matrices pass;
- installed-wheel tests pass outside the source tree;
- the old release matches byte-for-byte;
- PKL references the dedicated authority;
- the assurance gate records the repository URL, commit and tag.

A failed extraction is discarded and repeated from the approved source rather than repaired through undocumented artifact edits.
