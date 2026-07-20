# ADR-0004: Typed Digest Domains and RFC 8785 Canonicalisation

Status: proposed

## Context

A digest is meaningful only when the exact representation and projection are known. Cross-language JSON numbers and serialization can otherwise produce inconsistent bytes.

## Decision

Digest records identify algorithm, basis and byte length. Raw, text and canonical-JSON digests are distinct domains. JSON uses the declared RFC 8785 profile and rejects unsupported numeric values. Record digests use a versioned projection that excludes the digest itself.

## Consequences

- Digest mismatches are explicit corruption or disagreement failures.
- Canonicalisation cannot silently coerce unsupported values.
- Projection changes require a new projection version and compatibility analysis.
- Cross-language canonical byte fixtures remain release evidence.

## Verification

Official and adversarial vectors, mutation tests and bit-flip corruption tests must pass in every supported runtime.
