# ADR-0001: Dedicated Runtime Repository Boundary

Status: proposed

## Context

PKL currently contains both programme knowledge and the executable reference package. Runtime development requires release-focused controls and should not be coupled to knowledge-library validation or generated catalogue behaviour.

## Decision

Create a dedicated `spws-contracts-core` repository. PKL remains authoritative for research and programme decisions; the dedicated repository becomes authoritative for runtime code, schemas, fixtures, tests and releases. References between them use immutable commits and tags.

## Consequences

- Phase 6 is blocked until extraction is verified.
- Active runtime source must not diverge across repositories.
- Migration provenance and byte-for-byte baseline verification are mandatory.
- PKL may retain a frozen historical copy but not a competing active authority.

## Verification

A fresh clone of the dedicated repository must reproduce `0.1.0-dev.2` and its archive digest without files from PKL.
