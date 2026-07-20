# ADR-0009: Explicit Compatibility Claims and Versioned Adapters

Status: proposed

## Context

Schema validity alone cannot establish semantic compatibility. Silent coercion or undocumented migration would undermine provenance and reproducibility.

## Decision

Compatibility is claimed only through a published compatibility report and fixture comparison. Incompatible meaning changes require a major version. Migrations are explicit versioned adapters that validate source and target, record generated provenance and declare information loss.

## Consequences

- Published prereleases remain immutable even without compatibility promises.
- Unknown major versions are rejected.
- Deprecations include replacement, timeline and migration guidance.
- Security corrections may narrow acceptance but require release notes and regression evidence.

## Verification

A release comparator checks old valid/invalid fixtures, schema changes, generated types and semantic adapter outcomes.
