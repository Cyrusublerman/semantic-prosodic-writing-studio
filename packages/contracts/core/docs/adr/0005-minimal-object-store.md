# ADR-0005: Minimal SQLite Object Store

Status: proposed

## Context

Phase 6 must prove persistence invariants without prematurely building a general repository, event platform or distributed system.

## Decision

Use SQLite for the first proving store. Store immutable object versions, parent edges, direct provenance/policy summaries, schema versions and verification state. Enforce foreign keys and transactions. Verify digests on write and read. Use expected-head optimistic concurrency.

## Consequences

- The store is deliberately narrow and replaceable.
- Schema migrations require an append-only migration ledger and tests.
- No hidden mutable document column may bypass version rules.
- Tombstones and outstanding deletion scope are first-class records.

## Verification

Persistence tests cover atomic writes, rollback, cycles, concurrency, corruption, retrieval, export and tombstones.
