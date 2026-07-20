# Release and Supply-Chain Policy

Status: assurance draft.

## 1. Release authority

A release is authoritative only when all of the following identify the same content:

- source commit;
- annotated tag;
- release manifest;
- schema release directory;
- wheel and source distribution;
- schema archive;
- checksums;
- SBOM;
- build provenance;
- signatures or verifiable attestations.

The release process must never modify an already published version directory.

## 2. Required artifacts

Every promoted release must publish:

1. source archive;
2. Python wheel and source distribution;
3. schema and fixture ZIP;
4. generated TypeScript declarations;
5. release manifest with all artifact SHA-256 digests;
6. compatibility report;
7. capability report that distinguishes tested from unsupported behaviour;
8. CycloneDX or SPDX SBOM for Python and Node dependencies;
9. provenance attestation identifying repository, commit, workflow and builder;
10. signature or identity-bound verification material;
11. changelog and migration notes.

## 3. Build requirements

- Builds run from a clean checkout of the tagged commit.
- Network access during the artifact-build step should be disabled after dependencies are restored.
- Python and Node dependency graphs must be locked.
- GitHub Actions must be pinned to immutable commit SHAs.
- Workflow permissions must be least privilege.
- Release jobs must use protected environments when credentials or publishing authority are involved.
- Artifact digests must be recomputed after download in an independent verification job.
- Repeated builds on supported builders must produce identical schema archives and semantically identical package contents.

## 4. Promotion gates

### Prerelease

Requires passing schemas, fixtures, package builds, compatibility declaration, threat-model review status and truthful capability report.

### Release candidate

Additionally requires supported runtime matrices, property/mutation/fuzz suites, independent consumer validation, licence resolution, SBOM and provenance.

### Stable

Additionally requires Phase 6 proving contracts, Phase 7 independent conformance, independent human approval, zero unresolved critical/high risks and documented operational support.

## 5. Signing

The owner must select and record the signing identity. Keyless identity-based signing is preferred where verification can bind the artifact to the repository and protected workflow. Long-lived private keys must not be stored in repository secrets unless a documented key-management design requires them.

Verification instructions must be tested from a clean environment.

## 6. Revocation and defects

Published artifacts are not replaced. A defective release is marked withdrawn or superseded and a new version is issued. Security defects require an advisory and affected-version statement.

## 7. Baseline `0.1.0-dev.2`

The current baseline is immutable in repository history and has deterministic release and archive digests. It still requires an annotated tag, external prerelease publication, SBOM, provenance, signature and independent verification before satisfying the Phase 5.5 release gate.
