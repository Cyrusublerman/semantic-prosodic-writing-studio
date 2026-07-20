# ADR-0010: Reproducible, Attested and Signed Releases

Status: proposed

## Context

Checksums prove content identity but do not prove who built an artifact, from which source or under which workflow.

## Decision

Promoted releases use clean locked builds, immutable source commits, deterministic schema archives, manifest checksums, SBOMs, build provenance and identity-bound artifact verification. Keyless signing is preferred where it can bind artifacts to the repository and protected workflow.

## Consequences

- Git tags alone are insufficient release evidence.
- Published artifacts are withdrawn or superseded, never replaced in place.
- Workflow permissions and release authority are separated from ordinary validation.
- Verification instructions are part of the release and must be tested independently.

## Verification

An independent job downloads artifacts, verifies provenance/signatures and recomputes all manifest digests before publication completes.
