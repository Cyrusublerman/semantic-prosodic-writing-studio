# Human and Independent Review Protocol

Status: assurance draft.

## 1. Purpose

Machine validation can demonstrate internal consistency but cannot establish that the chosen semantics are correct, safe or appropriate. This protocol governs approval of the normative specification, threat model, ADRs and stable-release claims.

## 2. Reviewer independence

At least one approving reviewer must not have authored the implementation under review. A reviewer may not approve solely on the basis of passing CI.

Where one person controls the project, external review must be sought for at least:

- identity and version semantics;
- canonicalisation and digest projection;
- provenance and contribution survival;
- rights, privacy, retention and policy precedence;
- deletion claims;
- Unicode coordinate and mapping rules;
- supply-chain and release controls.

## 3. Required review passes

1. **Normative semantics:** each MUST/MUST NOT is reviewed for necessity, clarity and testability.
2. **Adversarial review:** reviewers attempt to identify unsafe permissive interpretations and failure modes.
3. **Fixture review:** expected outcomes are checked against intended semantics rather than current implementation.
4. **Implementation traceability:** every critical requirement maps to runtime and negative-test evidence.
5. **Capability-claim review:** reports are checked for unsupported or overstated claims.
6. **Release review:** artifact digests, reproducibility, licence and verification instructions are checked independently.

## 4. Review record

Each review record must contain:

- reviewed commit and release;
- reviewer identity and relationship to the work;
- scope and exclusions;
- findings with severity;
- decisions and rationale;
- residual risks;
- required follow-up issues;
- approval state and date.

Approval states are `rejected`, `changes_required`, `conditionally_approved` or `approved`.

## 5. Severity

- **Critical:** can violate integrity, privacy, rights, deletion honesty or release authenticity. Blocks all promotion.
- **High:** can produce materially incorrect interpretation or irreversible migration. Blocks Phase 6 or promotion as applicable.
- **Medium:** important ambiguity, coverage or maintainability gap. Requires tracked remediation.
- **Low:** editorial or limited-risk improvement.

## 6. Approval constraints

The following cannot be conditionally waived:

- silent digest mismatch;
- permissive unknown rights;
- local-only external transmission;
- erased machine/source provenance;
- content-bearing tombstones;
- unsupported major-version fallback;
- ignored critical extensions;
- false complete-deletion claims.

## 7. Re-review triggers

Re-review is required for:

- changes to normative meaning;
- digest projection or canonicalisation changes;
- policy precedence changes;
- new persistence or export boundaries;
- stable compatibility commitments;
- security incidents;
- significant dependency or build-pipeline changes.
