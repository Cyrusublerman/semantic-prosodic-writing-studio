# ADR-0006: Policy Enforcement Before Serialization and Transmission

Status: proposed

## Context

Checking policy after serialization, logging or export preparation can already disclose restricted content.

## Decision

Operation policy is evaluated before payload serialization, external model calls, network transmission or diagnostic rendering that could contain restricted content. Decisions are explicit, auditable and fail closed when required context is unavailable.

## Consequences

- Local-only restrictions are enforced at operation boundaries, not UI hints.
- Denials contain stable reasons and redacted explanations.
- Policy inheritance and conflict resolution use one versioned decision table.
- Unknown rights are restrictive rather than permissive.

## Verification

Decision-table tests, inheritance properties, leakage tests and external-transmission denial proofs are mandatory.
