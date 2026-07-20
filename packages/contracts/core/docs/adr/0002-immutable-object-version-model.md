# ADR-0002: Stable Object Identity and Immutable Versions

Status: proposed

## Context

The system must preserve history, provenance and reproducibility while allowing logical objects to evolve.

## Decision

`object_id` identifies the logical object; `version_id` identifies an immutable snapshot. Changes create new versions. Parent links form a directed acyclic graph. Writes use expected-head concurrency rather than silent last-write-wins.

## Consequences

- In-place update APIs are prohibited.
- Storage must enforce uniqueness, graph acyclicity and optimistic concurrency transactionally.
- Corrections and deletion are represented by later versions or events.
- Consumers must distinguish object identity from version identity.

## Verification

Property and concurrent-writer tests must prove stability, immutability, cycle rejection and lost-update detection.
