# ADR-0003: Separate Raw Bytes, Decoded Text and Normalised Text

Status: proposed

## Context

Decoding and normalisation can change bytes, offsets, digests and interpretation. Treating derived text as the source destroys evidence.

## Decision

Exact source bytes, decoded text and normalised text are distinct versioned representations. Every derivation records its source, activity, software profile, warnings and mapping where coordinates are relevant.

## Consequences

- Importers preserve source bytes whenever available.
- Digests are representation-specific.
- Normalised text never replaces raw evidence.
- Markdown and direct typed text use the same shared representation primitives rather than ad hoc fields.

## Verification

Fixtures must prove malformed decoding, line-ending changes, Unicode normalisation, derivative provenance and span mapping.
