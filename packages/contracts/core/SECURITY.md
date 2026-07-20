# Security Policy

## Supported status

`0.1.0-dev.2` is an immutable prerelease baseline. It is not a stable production release and must not be represented as one.

## Reporting

Do not place private source content, credentials, personal data or exploit payloads in public issues. Report suspected vulnerabilities privately to the repository owner through an available private GitHub security channel. If no private channel is configured, provide only a minimal non-sensitive notice requesting one.

A useful report identifies:

- affected commit, release and component;
- security property at risk;
- preconditions and impact;
- minimal reproduction without restricted content;
- whether integrity, privacy, rights, provenance or deletion claims may be affected.

## Response priorities

Critical issues include:

- accepted digest mismatch or forged release integrity;
- external transmission of local-only content;
- permissive treatment of unknown rights;
- erased machine or source provenance;
- content retained in tombstones;
- materially false complete-deletion claims;
- ignored unknown critical extensions;
- unsupported major versions processed as compatible.

A suspected critical defect blocks promotion and external publication until scoped.

## Disclosure and correction

Published artifacts are never replaced in place. Affected versions are marked withdrawn or superseded and a new immutable version is issued. Every correction must include a regression fixture or test and an affected-version statement.

## Security limits

Importers and stores do not enter supported status until byte, nesting, collection, archive expansion, graph traversal and diagnostic limits are implemented and tested against the threat model.
