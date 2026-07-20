# ADR-0007: Minimal Direct Provenance with Referenced Full Graphs

Status: proposed

## Context

Embedding complete provenance graphs in every object creates duplication, while relying only on private graph storage makes exports uninterpretable.

## Decision

Each envelope carries the minimum direct provenance required to identify creator, creation activity and immediate sources. Richer graphs may be referenced by immutable version identifiers. Exports include enough direct context to remain intelligible without private storage.

## Consequences

- Direct summaries and full graph records have distinct roles.
- Acceptance and edits add provenance; they do not replace machine or source origin.
- Graph references must be resolvable or explicitly unavailable.
- Cycles and self-derivation remain invalid.

## Verification

Lifecycle fixtures prove import, derivation, generation, acceptance, editing and export without origin loss.
