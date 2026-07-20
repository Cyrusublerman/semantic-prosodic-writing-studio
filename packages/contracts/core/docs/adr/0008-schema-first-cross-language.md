# ADR-0008: Released Schema as the Cross-Language Boundary

Status: proposed

## Context

Python models are the current implementation source, but consumers must not depend on Python-specific behaviour or private modules.

## Decision

Released JSON Schema, normative specification and fixtures form the language-neutral boundary. TypeScript declarations are generated convenience artifacts; runtime schema and semantic validation remain authoritative. At least one independent consumer must validate without importing implementation internals.

## Consequences

- Python-only behaviour that is absent from the specification or semantic validation contract is not portable authority.
- Generated types do not replace runtime validation.
- Every cross-field invariant needs a portable requirement and fixture outcome.
- Schema generation changes require reproducibility and compatibility checks.

## Verification

Python, Ajv and Hyperjump fixture parity, TypeScript compilation and an independent consumer suite are required.
