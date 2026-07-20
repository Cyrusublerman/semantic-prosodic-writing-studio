/* Generated from contracts-core 0.1.0-dev.2. Runtime validation remains authoritative. */

export type ContractsCoreBundle =
  | SchemaReference
  | VersionRange
  | ExternalIdentifier
  | AgentReference
  | ObjectReference
  | VersionReference
  | ReferenceSet
  | TimeWindow
  | DigestRecord
  | ExtensionRecord
  | ActivityReference
  | ProvenanceRelation
  | ContributionRecord
  | DirectProvenanceSummary
  | EvidenceRecord
  | RightsAssertion
  | PolicyConstraint
  | DutyRecord
  | UsageRule
  | PolicyContext
  | PolicyDecision
  | PrivacyPolicy
  | RetentionPolicy
  | DirectPolicySummary
  | ConfidenceRecord
  | AlternativeRecord
  | ReviewRecord
  | WarningRecord
  | FailureRecord
  | QualifiedValue
  | TextQuoteSelector
  | TextRepresentation
  | TextSpan
  | SpanMapSegment
  | SpanMapping
  | RelocationRecord
  | PayloadDescriptor
  | CoreObjectEnvelope
  | EvidenceRecord4;
export type SchemaDigest = string | null;
export type IncludeMaximum = boolean;
export type IncludeMinimum = boolean;
export type RequiredMajor = number | null;
export type ResolutionState = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value = string;
export type AgentType = "person" | "organisation" | "software_component" | "model" | "service" | "system";
export type DisplayName = string | null;
export type ResolutionState1 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value1 = string;
export type ExternalIdentifiers = ExternalIdentifier1[];
export type Version = string | null;
export type Digest = string | null;
export type ResolutionState2 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value2 = string;
export type ExternalIdentifiers1 = ExternalIdentifier2[];
export type Digest1 = string | null;
export type Digest2 = string | null;
export type References = VersionReference1[];
export type DigestAlgorithm = "sha-256";
export type DigestBasis = "raw_bytes" | "utf8_text" | "jcs_json" | "record_projection";
export type ByteLength = number;
export type CanonicalisationMethod = "none" | "unicode_profile" | "rfc8785_jcs" | "domain_projection";
export type Version1 = string | null;
export type CharacterEncoding = string | null;
export type MediaType = string | null;
export type Value3 = string;
export type VerificationState = "unverified" | "verified" | "mismatch";
export type Critical = boolean;
export type Namespace = string;
export type SchemaDigest1 = string | null;
export type ActivityType = string;
export type ComponentVersion = string | null;
export type ParametersDigest = string | null;
export type AgentType1 = "person" | "organisation" | "software_component" | "model" | "service" | "system";
export type DisplayName1 = string | null;
export type ResolutionState3 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value4 = string;
export type ExternalIdentifiers2 = ExternalIdentifier3[];
export type Version2 = string | null;
export type ResponsibleAgents = AgentReference1[];
export type ProcessingState =
  | "pending"
  | "running"
  | "awaiting_human"
  | "succeeded"
  | "partially_succeeded"
  | "failed"
  | "cancelled"
  | "timed_out"
  | "blocked"
  | "skipped";
export type EntityRole = string | null;
export type Method = string | null;
export type Object = VersionReference2 | ObjectReference1;
export type Digest3 = string | null;
export type Digest4 = string | null;
export type ResolutionState4 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value5 = string;
export type ExternalIdentifiers3 = ExternalIdentifier4[];
export type ParametersDigest1 = string | null;
export type RelationType = string;
export type ReviewState =
  "unreviewed" | "machine_checked" | "human_reviewed" | "approved" | "rejected" | "disputed" | "superseded";
export type SourceSpanIds = string[];
export type TargetSpanIds = string[];
export type AgentType2 = "person" | "organisation" | "software_component" | "model" | "service" | "system";
export type DisplayName2 = string | null;
export type ResolutionState5 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value6 = string;
export type ExternalIdentifiers4 = ExternalIdentifier5[];
export type Version3 = string | null;
export type Description = string | null;
export type ReviewState1 =
  "unreviewed" | "machine_checked" | "human_reviewed" | "approved" | "rejected" | "disputed" | "superseded";
export type Role = string;
export type Digest5 = string | null;
export type Sources = VersionReference3[];
export type AgentType3 = "person" | "organisation" | "software_component" | "model" | "service" | "system";
export type DisplayName3 = string | null;
export type ResolutionState6 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value7 = string;
export type ExternalIdentifiers5 = ExternalIdentifier6[];
export type Version4 = string | null;
export type Description1 = string | null;
export type ReviewState2 =
  "unreviewed" | "machine_checked" | "human_reviewed" | "approved" | "rejected" | "disputed" | "superseded";
export type Role1 = string;
export type Digest6 = string | null;
export type Sources1 = VersionReference4[];
export type ContributionRecords = ContributionRecord1[];
export type ActivityType1 = string;
export type ComponentVersion1 = string | null;
export type ParametersDigest2 = string | null;
export type ResponsibleAgents1 = AgentReference3[];
export type ProcessingState1 =
  | "pending"
  | "running"
  | "awaiting_human"
  | "succeeded"
  | "partially_succeeded"
  | "failed"
  | "cancelled"
  | "timed_out"
  | "blocked"
  | "skipped";
export type EntityRole1 = string | null;
export type Method1 = string | null;
export type Object1 = VersionReference4 | ObjectReference2;
export type Digest7 = string | null;
export type ExternalIdentifiers6 = ExternalIdentifier6[];
export type ParametersDigest3 = string | null;
export type RelationType1 = string;
export type ReviewState3 =
  "unreviewed" | "machine_checked" | "human_reviewed" | "approved" | "rejected" | "disputed" | "superseded";
export type SourceSpanIds1 = string[];
export type TargetSpanIds1 = string[];
export type DirectRelations = ProvenanceRelation1[];
export type FullProvenanceRecords = ObjectReference2[];
export type Description2 = string | null;
export type Digest8 = string | null;
export type ResolutionState7 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value8 = string;
export type ExternalIdentifiers7 = ExternalIdentifier7[];
export type Verified = boolean;
export type AgentType4 = "person" | "organisation" | "software_component" | "model" | "service" | "system";
export type DisplayName4 = string | null;
export type ExternalIdentifiers8 = ExternalIdentifier7[];
export type Version5 = string | null;
export type AssertionType = string;
export type PolicyEffect = "permit" | "prohibit";
export type Description3 = string | null;
export type Digest9 = string | null;
export type ResolutionState8 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value9 = string;
export type ExternalIdentifiers9 = ExternalIdentifier8[];
export type Verified1 = boolean;
export type AgentType5 = "person" | "organisation" | "software_component" | "model" | "service" | "system";
export type DisplayName5 = string | null;
export type ExternalIdentifiers10 = ExternalIdentifier8[];
export type Version6 = string | null;
export type Evidence = EvidenceRecord1[];
export type Jurisdiction = string | null;
export type Notes = string | null;
export type ReviewState4 =
  "unreviewed" | "machine_checked" | "human_reviewed" | "approved" | "rejected" | "disputed" | "superseded";
export type ConstraintType = string;
export type ConstraintOperator = "equals" | "not_equals" | "in" | "not_in" | "lte" | "gte" | "contains";
export type DutyType = string;
export type Description4 = string | null;
export type Digest10 = string | null;
export type ResolutionState9 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value10 = string;
export type ExternalIdentifiers11 = ExternalIdentifier9[];
export type Verified2 = boolean;
export type AgentType6 = "person" | "organisation" | "software_component" | "model" | "service" | "system";
export type DisplayName6 = string | null;
export type ExternalIdentifiers12 = ExternalIdentifier9[];
export type Version7 = string | null;
export type Evidence1 = EvidenceRecord2[];
export type Notes1 = string | null;
export type Satisfied = boolean;
export type AgentType7 = "person" | "organisation" | "software_component" | "model" | "service" | "system";
export type DisplayName7 = string | null;
export type ResolutionState10 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value11 = string;
export type ExternalIdentifiers13 = ExternalIdentifier10[];
export type Version8 = string | null;
export type AuthorityTier = 0 | 10 | 20 | 30 | 40 | 50;
export type ConstraintType1 = string;
export type ConstraintOperator1 = "equals" | "not_equals" | "in" | "not_in" | "lte" | "gte" | "contains";
export type Constraints = PolicyConstraint1[];
export type DutyType1 = string;
export type Description5 = string | null;
export type Digest11 = string | null;
export type ExternalIdentifiers14 = ExternalIdentifier10[];
export type Verified3 = boolean;
export type Evidence2 = EvidenceRecord3[];
export type Notes2 = string | null;
export type Satisfied1 = boolean;
export type Duties = DutyRecord1[];
export type PolicyEffect1 = "permit" | "prohibit";
export type Evidence3 = EvidenceRecord3[];
export type Explanation = string | null;
export type Operation = string;
export type OverrideLowerAuthority = boolean;
export type Purpose = string | null;
export type SourceAssertions = string[];
export type AgentType8 = "person" | "organisation" | "software_component" | "model" | "service" | "system";
export type DisplayName8 = string | null;
export type ResolutionState11 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value12 = string;
export type ExternalIdentifiers15 = ExternalIdentifier11[];
export type Version9 = string | null;
export type Operation1 = string;
export type Purpose1 = string | null;
export type Digest12 = string | null;
export type ExternalIdentifiers16 = ExternalIdentifier11[];
export type Allowed = boolean;
export type AppliedRuleIds = string[];
export type Explanation1 = string;
export type AuthorityTier1 = 0 | 10 | 20 | 30 | 40 | 50;
export type Operation2 = string;
export type PolicyDecisionOutcome = "permit" | "deny" | "deny_pending_duty" | "indeterminate";
export type RejectedRuleIds = string[];
export type UnsatisfiedDuties = string[];
export type AllowedRecipients = string[];
export type ConsentRequired = boolean;
export type Notes3 = string | null;
export type PrivacyClass = "public" | "internal" | "private" | "sensitive" | "highly_sensitive";
export type TransmissionClass =
  "public_allowed" | "private_share_allowed" | "external_with_consent" | "local_only" | "blocked";
export type DeletionMode =
  "hard_delete_payload" | "tombstone_only" | "cryptographic_erasure" | "external_reference_removal" | "blocked_by_hold";
export type Digest13 = string | null;
export type ResolutionState12 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value13 = string;
export type ExternalIdentifiers17 = ExternalIdentifier12[];
export type LegalHold = boolean;
export type Notes4 = string | null;
export type RetentionClass =
  "ephemeral" | "session" | "project_lifetime" | "until_date" | "indefinite" | "legal_hold" | "delete_on_request";
export type Allowed1 = boolean;
export type AppliedRuleIds1 = string[];
export type Explanation2 = string;
export type AuthorityTier2 = 0 | 10 | 20 | 30 | 40 | 50;
export type Operation3 = string;
export type PolicyDecisionOutcome1 = "permit" | "deny" | "deny_pending_duty" | "indeterminate";
export type RejectedRuleIds1 = string[];
export type UnsatisfiedDuties1 = string[];
export type Decisions = PolicyDecision1[];
export type Digest14 = string | null;
export type ResolutionState13 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value14 = string;
export type ExternalIdentifiers18 = ExternalIdentifier13[];
export type PolicyBundleRefs = ObjectReference9[];
export type AllowedRecipients1 = string[];
export type ConsentRequired1 = boolean;
export type Notes5 = string | null;
export type PrivacyClass1 = "public" | "internal" | "private" | "sensitive" | "highly_sensitive";
export type TransmissionClass1 =
  "public_allowed" | "private_share_allowed" | "external_with_consent" | "local_only" | "blocked";
export type DeletionMode1 =
  "hard_delete_payload" | "tombstone_only" | "cryptographic_erasure" | "external_reference_removal" | "blocked_by_hold";
export type LegalHold1 = boolean;
export type Notes6 = string | null;
export type RetentionClass1 =
  "ephemeral" | "session" | "project_lifetime" | "until_date" | "indefinite" | "legal_hold" | "delete_on_request";
export type Digest15 = string | null;
export type ConfidenceKind =
  "probability" | "calibrated_probability" | "agreement" | "coverage" | "heuristic_strength" | "ordinal";
export type Method2 = string;
export type Notes7 = string | null;
export type SampleSize = number | null;
export type Value15 = number | string;
export type Digest16 = string | null;
export type ConfidenceKind1 =
  "probability" | "calibrated_probability" | "agreement" | "coverage" | "heuristic_strength" | "ordinal";
export type Method3 = string;
export type Notes8 = string | null;
export type SampleSize1 = number | null;
export type Value16 = number | string;
export type Rationale = string | null;
export type Digest17 = string | null;
export type ResolutionState14 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value18 = string;
export type ExternalIdentifiers19 = ExternalIdentifier14[];
export type Evidence4 = ObjectReference10[];
export type Rationale1 = string | null;
export type AgentType9 = "person" | "organisation" | "software_component" | "model" | "service" | "system";
export type DisplayName9 = string | null;
export type ExternalIdentifiers20 = ExternalIdentifier14[];
export type Version10 = string | null;
export type ReviewState5 =
  "unreviewed" | "machine_checked" | "human_reviewed" | "approved" | "rejected" | "disputed" | "superseded";
export type Code = string;
export type Message = string | null;
export type Name = string;
export type Digest18 = string | null;
export type ResolutionState15 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value19 = string;
export type ExternalIdentifiers21 = ExternalIdentifier15[];
export type RelatedObjects = ObjectReference11[];
export type Remediation = string | null;
export type Retryable = boolean;
export type Scope = string;
export type Severity = "info" | "warning" | "error" | "fatal";
export type Code1 = string;
export type Message1 = string | null;
export type Name1 = string;
export type Digest19 = string | null;
export type ResolutionState16 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value20 = string;
export type ExternalIdentifiers22 = ExternalIdentifier16[];
export type RelatedObjects1 = ObjectReference12[];
export type Remediation1 = string | null;
export type Retryable1 = boolean;
export type Scope1 = string;
export type Severity1 = "info" | "warning" | "error" | "fatal";
export type Digest20 = string | null;
export type ConfidenceKind2 =
  "probability" | "calibrated_probability" | "agreement" | "coverage" | "heuristic_strength" | "ordinal";
export type Method4 = string;
export type Notes9 = string | null;
export type SampleSize2 = number | null;
export type Value21 = number | string;
export type Rationale2 = string | null;
export type Alternatives = AlternativeRecord1[];
export type EvidenceMethod =
  | "measured"
  | "parsed"
  | "retrieved"
  | "computed"
  | "derived"
  | "rule_inferred"
  | "statistical_inferred"
  | "model_inferred"
  | "human_asserted"
  | "human_reviewed"
  | "imported"
  | "defaulted";
export type Code2 = string;
export type Message2 = string | null;
export type Name2 = string;
export type Digest21 = string | null;
export type ResolutionState17 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value23 = string;
export type ExternalIdentifiers23 = ExternalIdentifier17[];
export type RelatedObjects2 = ObjectReference13[];
export type Remediation2 = string | null;
export type Retryable2 = boolean;
export type Scope2 = string;
export type Severity2 = "info" | "warning" | "error" | "fatal";
export type Failures = FailureRecord1[];
export type PresenceState =
  | "present"
  | "absent"
  | "unknown"
  | "not_applicable"
  | "not_requested"
  | "unavailable"
  | "withheld"
  | "failed"
  | "ambiguous";
export type ReviewState6 =
  "unreviewed" | "machine_checked" | "human_reviewed" | "approved" | "rejected" | "disputed" | "superseded";
export type Code3 = string;
export type Message3 = string | null;
export type Name3 = string;
export type RelatedObjects3 = ObjectReference13[];
export type Remediation3 = string | null;
export type Retryable3 = boolean;
export type Scope3 = string;
export type Severity3 = "info" | "warning" | "error" | "fatal";
export type Warnings = WarningRecord1[];
export type Exact = string;
export type Prefix = string | null;
export type Suffix = string | null;
export type ByteLength1 = number | null;
export type CharacterEncoding1 = string | null;
export type CodePointLength = number | null;
export type DigestAlgorithm1 = "sha-256";
export type DigestBasis1 = "raw_bytes" | "utf8_text" | "jcs_json" | "record_projection";
export type ByteLength2 = number;
export type CanonicalisationMethod1 = "none" | "unicode_profile" | "rfc8785_jcs" | "domain_projection";
export type Version11 = string | null;
export type CharacterEncoding2 = string | null;
export type MediaType1 = string | null;
export type Value25 = string;
export type VerificationState1 = "unverified" | "verified" | "mismatch";
export type MediaType2 = string;
export type NormalisationProfile = string | null;
export type Digest22 = string | null;
export type RepresentationType =
  "raw_bytes" | "decoded_text" | "normalised_text" | "rendered_text" | "token_sequence" | "structured_json";
export type RuntimeUnicodeVersion = string | null;
export type SegmentationProfile = string | null;
export type CoordinateProfile = string;
export type End = number;
export type Exact1 = string;
export type Prefix1 = string | null;
export type Suffix1 = string | null;
export type Digest23 = string | null;
export type RuntimeUnicodeVersion1 = string | null;
export type SpanId = string;
export type Start = number;
export type DerivedEnd = number;
export type DerivedStart = number;
export type MappingKind = "equal" | "replace" | "insert" | "delete" | "reorder" | "unknown";
export type RawEnd = number;
export type RawStart = number;
export type DerivedEnd1 = number;
export type DerivedStart1 = number;
export type MappingKind1 = "equal" | "replace" | "insert" | "delete" | "reorder" | "unknown";
export type RawEnd1 = number;
export type RawStart1 = number;
export type Segments = SpanMapSegment1[];
export type SourceLength = number;
export type TargetLength = number;
export type CandidateRanges = [unknown, unknown][];
export type Explanation3 = string | null;
export type RelocatedEnd = number | null;
export type RelocatedStart = number | null;
export type RelocationResult = "unique" | "ambiguous" | "missing" | "invalid_source" | "representation_mismatch";
export type CoordinateProfile1 = string;
export type End1 = number;
export type Exact2 = string;
export type Prefix2 = string | null;
export type Suffix2 = string | null;
export type Digest24 = string | null;
export type RuntimeUnicodeVersion2 = string | null;
export type SpanId1 = string;
export type Start1 = number;
export type DigestAlgorithm2 = "sha-256";
export type DigestBasis2 = "raw_bytes" | "utf8_text" | "jcs_json" | "record_projection";
export type ByteLength3 = number;
export type CanonicalisationMethod2 = "none" | "unicode_profile" | "rfc8785_jcs" | "domain_projection";
export type Version12 = string | null;
export type CharacterEncoding3 = string | null;
export type MediaType3 = string | null;
export type Value26 = string;
export type VerificationState2 = "unverified" | "verified" | "mismatch";
export type LocationReference = string | null;
export type MediaType4 = string | null;
export type PayloadKind = "embedded" | "object_store" | "external" | "tombstone";
export type SizeBytes = number | null;
export type Critical1 = boolean;
export type Namespace1 = string;
export type SchemaDigest2 = string | null;
export type Extensions = ExtensionRecord1[];
export type Code4 = string;
export type Message4 = string | null;
export type Name4 = string;
export type Digest25 = string | null;
export type ResolutionState18 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value27 = string;
export type ExternalIdentifiers24 = ExternalIdentifier18[];
export type RelatedObjects4 = ObjectReference14[];
export type Remediation4 = string | null;
export type Retryable4 = boolean;
export type Scope4 = string;
export type Severity4 = "info" | "warning" | "error" | "fatal";
export type Failures1 = FailureRecord2[];
export type ParentVersionIds = string[];
export type DigestAlgorithm3 = "sha-256";
export type DigestBasis3 = "raw_bytes" | "utf8_text" | "jcs_json" | "record_projection";
export type ByteLength4 = number;
export type CanonicalisationMethod3 = "none" | "unicode_profile" | "rfc8785_jcs" | "domain_projection";
export type Version13 = string | null;
export type CharacterEncoding4 = string | null;
export type MediaType5 = string | null;
export type Value28 = string;
export type VerificationState3 = "unverified" | "verified" | "mismatch";
export type LocationReference1 = string | null;
export type MediaType6 = string | null;
export type PayloadKind1 = "embedded" | "object_store" | "external" | "tombstone";
export type SizeBytes1 = number | null;
export type Allowed2 = boolean;
export type AppliedRuleIds2 = string[];
export type Explanation4 = string;
export type AuthorityTier3 = 0 | 10 | 20 | 30 | 40 | 50;
export type Operation4 = string;
export type PolicyDecisionOutcome2 = "permit" | "deny" | "deny_pending_duty" | "indeterminate";
export type RejectedRuleIds2 = string[];
export type UnsatisfiedDuties2 = string[];
export type Decisions1 = PolicyDecision2[];
export type PolicyBundleRefs1 = ObjectReference14[];
export type AllowedRecipients2 = string[];
export type ConsentRequired2 = boolean;
export type Notes10 = string | null;
export type PrivacyClass2 = "public" | "internal" | "private" | "sensitive" | "highly_sensitive";
export type TransmissionClass2 =
  "public_allowed" | "private_share_allowed" | "external_with_consent" | "local_only" | "blocked";
export type DeletionMode2 =
  "hard_delete_payload" | "tombstone_only" | "cryptographic_erasure" | "external_reference_removal" | "blocked_by_hold";
export type LegalHold2 = boolean;
export type Notes11 = string | null;
export type RetentionClass2 =
  "ephemeral" | "session" | "project_lifetime" | "until_date" | "indefinite" | "legal_hold" | "delete_on_request";
export type AgentType10 = "person" | "organisation" | "software_component" | "model" | "service" | "system";
export type DisplayName10 = string | null;
export type ExternalIdentifiers25 = ExternalIdentifier18[];
export type Version14 = string | null;
export type Description6 = string | null;
export type ReviewState7 =
  "unreviewed" | "machine_checked" | "human_reviewed" | "approved" | "rejected" | "disputed" | "superseded";
export type Role2 = string;
export type Digest26 = string | null;
export type Sources2 = VersionReference11[];
export type ContributionRecords1 = ContributionRecord2[];
export type ActivityType2 = string;
export type ComponentVersion2 = string | null;
export type ParametersDigest4 = string | null;
export type ResponsibleAgents2 = AgentReference10[];
export type ProcessingState2 =
  | "pending"
  | "running"
  | "awaiting_human"
  | "succeeded"
  | "partially_succeeded"
  | "failed"
  | "cancelled"
  | "timed_out"
  | "blocked"
  | "skipped";
export type EntityRole2 = string | null;
export type Method5 = string | null;
export type Object2 = VersionReference11 | ObjectReference14;
export type ParametersDigest5 = string | null;
export type RelationType2 = string;
export type ReviewState8 =
  "unreviewed" | "machine_checked" | "human_reviewed" | "approved" | "rejected" | "disputed" | "superseded";
export type SourceSpanIds2 = string[];
export type TargetSpanIds2 = string[];
export type DirectRelations1 = ProvenanceRelation2[];
export type FullProvenanceRecords1 = ObjectReference14[];
export type ReviewState9 =
  "unreviewed" | "machine_checked" | "human_reviewed" | "approved" | "rejected" | "disputed" | "superseded";
export type Evidence5 = ObjectReference14[];
export type Rationale3 = string | null;
export type ReviewState10 =
  "unreviewed" | "machine_checked" | "human_reviewed" | "approved" | "rejected" | "disputed" | "superseded";
export type Reviews = ReviewRecord1[];
export type ObjectState = "active" | "superseded" | "invalidated" | "tombstoned";
export type Code5 = string;
export type Message5 = string | null;
export type Name5 = string;
export type RelatedObjects5 = ObjectReference14[];
export type Remediation5 = string | null;
export type Retryable5 = boolean;
export type Scope5 = string;
export type Severity5 = "info" | "warning" | "error" | "fatal";
export type Warnings1 = WarningRecord2[];
export type Description7 = string | null;
export type Digest27 = string | null;
export type ResolutionState19 = "unresolved" | "resolved" | "unavailable" | "invalid";
export type Value29 = string;
export type ExternalIdentifiers26 = ExternalIdentifier19[];
export type Verified4 = boolean;
export type AgentType11 = "person" | "organisation" | "software_component" | "model" | "service" | "system";
export type DisplayName11 = string | null;
export type ExternalIdentifiers27 = ExternalIdentifier19[];
export type Version15 = string | null;

export interface SchemaReference {
  schema_digest?: SchemaDigest;
  schema_id: string;
  schema_version: string;
}
export interface VersionRange {
  include_maximum?: IncludeMaximum;
  include_minimum?: IncludeMinimum;
  maximum?: string | null;
  minimum?: string | null;
  required_major?: RequiredMajor;
}
export interface ExternalIdentifier {
  namespace: string;
  resolution_state?: ResolutionState;
  uri?: string | null;
  value: Value;
}
export interface AgentReference {
  agent_id: string;
  agent_type: AgentType;
  display_name?: DisplayName;
  external_identifiers?: ExternalIdentifiers;
  version?: Version;
}
export interface ExternalIdentifier1 {
  namespace: string;
  resolution_state?: ResolutionState1;
  uri?: string | null;
  value: Value1;
}
export interface ObjectReference {
  digest?: Digest;
  external_identifiers?: ExternalIdentifiers1;
  object_id: string;
  object_type?: string | null;
  uri?: string | null;
  version_id?: string | null;
}
export interface ExternalIdentifier2 {
  namespace: string;
  resolution_state?: ResolutionState2;
  uri?: string | null;
  value: Value2;
}
export interface VersionReference {
  digest?: Digest1;
  object_id: string;
  object_type?: string | null;
  version_id: string;
}
export interface ReferenceSet {
  references?: References;
}
export interface VersionReference1 {
  digest?: Digest2;
  object_id: string;
  object_type?: string | null;
  version_id: string;
}
export interface TimeWindow {
  end?: string | null;
  start?: string | null;
}
export interface DigestRecord {
  algorithm?: DigestAlgorithm;
  basis: DigestBasis;
  byte_length: ByteLength;
  canonicalisation?: CanonicalisationRecord | null;
  character_encoding?: CharacterEncoding;
  media_type?: MediaType;
  value: Value3;
  verification_state?: VerificationState;
}
export interface CanonicalisationRecord {
  method: CanonicalisationMethod;
  version?: Version1;
}
export interface ExtensionRecord {
  critical?: Critical;
  namespace: Namespace;
  schema: SchemaReference1;
  value: unknown;
}
export interface SchemaReference1 {
  schema_digest?: SchemaDigest1;
  schema_id: string;
  schema_version: string;
}
export interface ActivityReference {
  activity_id: string;
  activity_type: ActivityType;
  component_version?: ComponentVersion;
  ended_at?: string | null;
  parameters_digest?: ParametersDigest;
  responsible_agents: ResponsibleAgents;
  run_id?: string | null;
  started_at: string;
  status: ProcessingState;
  step_run_id?: string | null;
}
export interface AgentReference1 {
  agent_id: string;
  agent_type: AgentType1;
  display_name?: DisplayName1;
  external_identifiers?: ExternalIdentifiers2;
  version?: Version2;
}
export interface ExternalIdentifier3 {
  namespace: string;
  resolution_state?: ResolutionState3;
  uri?: string | null;
  value: Value4;
}
export interface ProvenanceRelation {
  activity_id?: string | null;
  entity_role?: EntityRole;
  method?: Method;
  object: Object;
  parameters_digest?: ParametersDigest1;
  relation_id: string;
  relation_type: RelationType;
  review_state?: ReviewState;
  source_span_ids?: SourceSpanIds;
  subject: VersionReference2;
  target_span_ids?: TargetSpanIds;
}
export interface VersionReference2 {
  digest?: Digest3;
  object_id: string;
  object_type?: string | null;
  version_id: string;
}
export interface ObjectReference1 {
  digest?: Digest4;
  external_identifiers?: ExternalIdentifiers3;
  object_id: string;
  object_type?: string | null;
  uri?: string | null;
  version_id?: string | null;
}
export interface ExternalIdentifier4 {
  namespace: string;
  resolution_state?: ResolutionState4;
  uri?: string | null;
  value: Value5;
}
export interface ContributionRecord {
  activity_id?: string | null;
  agent: AgentReference2;
  contribution_id: string;
  description?: Description;
  review_state?: ReviewState1;
  role: Role;
  sources?: Sources;
  target: VersionReference3;
}
export interface AgentReference2 {
  agent_id: string;
  agent_type: AgentType2;
  display_name?: DisplayName2;
  external_identifiers?: ExternalIdentifiers4;
  version?: Version3;
}
export interface ExternalIdentifier5 {
  namespace: string;
  resolution_state?: ResolutionState5;
  uri?: string | null;
  value: Value6;
}
export interface VersionReference3 {
  digest?: Digest5;
  object_id: string;
  object_type?: string | null;
  version_id: string;
}
export interface DirectProvenanceSummary {
  contribution_records?: ContributionRecords;
  creation_activity: ActivityReference1;
  creator: AgentReference3;
  direct_relations?: DirectRelations;
  full_provenance_records?: FullProvenanceRecords;
}
export interface ContributionRecord1 {
  activity_id?: string | null;
  agent: AgentReference3;
  contribution_id: string;
  description?: Description1;
  review_state?: ReviewState2;
  role: Role1;
  sources?: Sources1;
  target: VersionReference4;
}
export interface AgentReference3 {
  agent_id: string;
  agent_type: AgentType3;
  display_name?: DisplayName3;
  external_identifiers?: ExternalIdentifiers5;
  version?: Version4;
}
export interface ExternalIdentifier6 {
  namespace: string;
  resolution_state?: ResolutionState6;
  uri?: string | null;
  value: Value7;
}
export interface VersionReference4 {
  digest?: Digest6;
  object_id: string;
  object_type?: string | null;
  version_id: string;
}
export interface ActivityReference1 {
  activity_id: string;
  activity_type: ActivityType1;
  component_version?: ComponentVersion1;
  ended_at?: string | null;
  parameters_digest?: ParametersDigest2;
  responsible_agents: ResponsibleAgents1;
  run_id?: string | null;
  started_at: string;
  status: ProcessingState1;
  step_run_id?: string | null;
}
export interface ProvenanceRelation1 {
  activity_id?: string | null;
  entity_role?: EntityRole1;
  method?: Method1;
  object: Object1;
  parameters_digest?: ParametersDigest3;
  relation_id: string;
  relation_type: RelationType1;
  review_state?: ReviewState3;
  source_span_ids?: SourceSpanIds1;
  subject: VersionReference4;
  target_span_ids?: TargetSpanIds1;
}
export interface ObjectReference2 {
  digest?: Digest7;
  external_identifiers?: ExternalIdentifiers6;
  object_id: string;
  object_type?: string | null;
  uri?: string | null;
  version_id?: string | null;
}
export interface EvidenceRecord {
  description?: Description2;
  source: ObjectReference3;
  verified?: Verified;
  verified_at?: string | null;
  verifier?: AgentReference4 | null;
}
export interface ObjectReference3 {
  digest?: Digest8;
  external_identifiers?: ExternalIdentifiers7;
  object_id: string;
  object_type?: string | null;
  uri?: string | null;
  version_id?: string | null;
}
export interface ExternalIdentifier7 {
  namespace: string;
  resolution_state?: ResolutionState7;
  uri?: string | null;
  value: Value8;
}
export interface AgentReference4 {
  agent_id: string;
  agent_type: AgentType4;
  display_name?: DisplayName4;
  external_identifiers?: ExternalIdentifiers8;
  version?: Version5;
}
export interface RightsAssertion {
  assertion_id: string;
  assertion_type: AssertionType;
  effect?: PolicyEffect | null;
  effective_window?: TimeWindow1;
  evidence?: Evidence;
  issuer: AgentReference5;
  jurisdiction?: Jurisdiction;
  notes?: Notes;
  review_state?: ReviewState4;
  target: ObjectReference4;
}
export interface TimeWindow1 {
  end?: string | null;
  start?: string | null;
}
export interface EvidenceRecord1 {
  description?: Description3;
  source: ObjectReference4;
  verified?: Verified1;
  verified_at?: string | null;
  verifier?: AgentReference5 | null;
}
export interface ObjectReference4 {
  digest?: Digest9;
  external_identifiers?: ExternalIdentifiers9;
  object_id: string;
  object_type?: string | null;
  uri?: string | null;
  version_id?: string | null;
}
export interface ExternalIdentifier8 {
  namespace: string;
  resolution_state?: ResolutionState8;
  uri?: string | null;
  value: Value9;
}
export interface AgentReference5 {
  agent_id: string;
  agent_type: AgentType5;
  display_name?: DisplayName5;
  external_identifiers?: ExternalIdentifiers10;
  version?: Version6;
}
export interface PolicyConstraint {
  constraint_type: ConstraintType;
  operator?: ConstraintOperator;
  value: unknown;
}
export interface DutyRecord {
  duty_type: DutyType;
  evidence?: Evidence1;
  notes?: Notes1;
  satisfied?: Satisfied;
}
export interface EvidenceRecord2 {
  description?: Description4;
  source: ObjectReference5;
  verified?: Verified2;
  verified_at?: string | null;
  verifier?: AgentReference6 | null;
}
export interface ObjectReference5 {
  digest?: Digest10;
  external_identifiers?: ExternalIdentifiers11;
  object_id: string;
  object_type?: string | null;
  uri?: string | null;
  version_id?: string | null;
}
export interface ExternalIdentifier9 {
  namespace: string;
  resolution_state?: ResolutionState9;
  uri?: string | null;
  value: Value10;
}
export interface AgentReference6 {
  agent_id: string;
  agent_type: AgentType6;
  display_name?: DisplayName6;
  external_identifiers?: ExternalIdentifiers12;
  version?: Version7;
}
export interface UsageRule {
  agent?: AgentReference7 | null;
  authority_tier: AuthorityTier;
  constraints?: Constraints;
  duties?: Duties;
  effect: PolicyEffect1;
  effective_window?: TimeWindow2;
  evidence?: Evidence3;
  explanation?: Explanation;
  operation: Operation;
  override_lower_authority?: OverrideLowerAuthority;
  purpose?: Purpose;
  rule_id: string;
  source_assertions?: SourceAssertions;
  target?: ObjectReference6 | null;
}
export interface AgentReference7 {
  agent_id: string;
  agent_type: AgentType7;
  display_name?: DisplayName7;
  external_identifiers?: ExternalIdentifiers13;
  version?: Version8;
}
export interface ExternalIdentifier10 {
  namespace: string;
  resolution_state?: ResolutionState10;
  uri?: string | null;
  value: Value11;
}
export interface PolicyConstraint1 {
  constraint_type: ConstraintType1;
  operator?: ConstraintOperator1;
  value: unknown;
}
export interface DutyRecord1 {
  duty_type: DutyType1;
  evidence?: Evidence2;
  notes?: Notes2;
  satisfied?: Satisfied1;
}
export interface EvidenceRecord3 {
  description?: Description5;
  source: ObjectReference6;
  verified?: Verified3;
  verified_at?: string | null;
  verifier?: AgentReference7 | null;
}
export interface ObjectReference6 {
  digest?: Digest11;
  external_identifiers?: ExternalIdentifiers14;
  object_id: string;
  object_type?: string | null;
  uri?: string | null;
  version_id?: string | null;
}
export interface TimeWindow2 {
  end?: string | null;
  start?: string | null;
}
export interface PolicyContext {
  agent?: AgentReference8 | null;
  attributes?: Attributes;
  evaluated_at: string;
  operation: Operation1;
  purpose?: Purpose1;
  target?: ObjectReference7 | null;
}
export interface AgentReference8 {
  agent_id: string;
  agent_type: AgentType8;
  display_name?: DisplayName8;
  external_identifiers?: ExternalIdentifiers15;
  version?: Version9;
}
export interface ExternalIdentifier11 {
  namespace: string;
  resolution_state?: ResolutionState11;
  uri?: string | null;
  value: Value12;
}
export interface Attributes {
  [k: string]: unknown;
}
export interface ObjectReference7 {
  digest?: Digest12;
  external_identifiers?: ExternalIdentifiers16;
  object_id: string;
  object_type?: string | null;
  uri?: string | null;
  version_id?: string | null;
}
export interface PolicyDecision {
  allowed: Allowed;
  applied_rule_ids?: AppliedRuleIds;
  decision_id: string;
  evaluated_at: string;
  explanation: Explanation1;
  highest_authority_tier?: AuthorityTier1 | null;
  operation: Operation2;
  outcome: PolicyDecisionOutcome;
  rejected_rule_ids?: RejectedRuleIds;
  unsatisfied_duties?: UnsatisfiedDuties;
}
export interface PrivacyPolicy {
  allowed_recipients?: AllowedRecipients;
  consent_required?: ConsentRequired;
  notes?: Notes3;
  privacy_class: PrivacyClass;
  transmission_class: TransmissionClass;
}
export interface RetentionPolicy {
  delete_after?: string | null;
  deletion_mode: DeletionMode;
  hold_reference?: ObjectReference8 | null;
  legal_hold?: LegalHold;
  notes?: Notes4;
  retention_class: RetentionClass;
}
export interface ObjectReference8 {
  digest?: Digest13;
  external_identifiers?: ExternalIdentifiers17;
  object_id: string;
  object_type?: string | null;
  uri?: string | null;
  version_id?: string | null;
}
export interface ExternalIdentifier12 {
  namespace: string;
  resolution_state?: ResolutionState12;
  uri?: string | null;
  value: Value13;
}
export interface DirectPolicySummary {
  decisions?: Decisions;
  policy_bundle_refs?: PolicyBundleRefs;
  privacy: PrivacyPolicy1;
  retention: RetentionPolicy1;
}
export interface PolicyDecision1 {
  allowed: Allowed1;
  applied_rule_ids?: AppliedRuleIds1;
  decision_id: string;
  evaluated_at: string;
  explanation: Explanation2;
  highest_authority_tier?: AuthorityTier2 | null;
  operation: Operation3;
  outcome: PolicyDecisionOutcome1;
  rejected_rule_ids?: RejectedRuleIds1;
  unsatisfied_duties?: UnsatisfiedDuties1;
}
export interface ObjectReference9 {
  digest?: Digest14;
  external_identifiers?: ExternalIdentifiers18;
  object_id: string;
  object_type?: string | null;
  uri?: string | null;
  version_id?: string | null;
}
export interface ExternalIdentifier13 {
  namespace: string;
  resolution_state?: ResolutionState13;
  uri?: string | null;
  value: Value14;
}
export interface PrivacyPolicy1 {
  allowed_recipients?: AllowedRecipients1;
  consent_required?: ConsentRequired1;
  notes?: Notes5;
  privacy_class: PrivacyClass1;
  transmission_class: TransmissionClass1;
}
export interface RetentionPolicy1 {
  delete_after?: string | null;
  deletion_mode: DeletionMode1;
  hold_reference?: ObjectReference9 | null;
  legal_hold?: LegalHold1;
  notes?: Notes6;
  retention_class: RetentionClass1;
}
export interface ConfidenceRecord {
  calibration_set?: VersionReference5 | null;
  kind: ConfidenceKind;
  method: Method2;
  notes?: Notes7;
  sample_size?: SampleSize;
  value: Value15;
}
export interface VersionReference5 {
  digest?: Digest15;
  object_id: string;
  object_type?: string | null;
  version_id: string;
}
export interface AlternativeRecord {
  confidence?: ConfidenceRecord1 | null;
  rationale?: Rationale;
  value: Value17;
}
export interface ConfidenceRecord1 {
  calibration_set?: VersionReference6 | null;
  kind: ConfidenceKind1;
  method: Method3;
  notes?: Notes8;
  sample_size?: SampleSize1;
  value: Value16;
}
export interface VersionReference6 {
  digest?: Digest16;
  object_id: string;
  object_type?: string | null;
  version_id: string;
}
export interface Value17 {
  [k: string]: unknown;
}
export interface ReviewRecord {
  evidence?: Evidence4;
  rationale?: Rationale1;
  review_id: string;
  reviewed_at: string;
  reviewer: AgentReference9;
  state: ReviewState5;
}
export interface ObjectReference10 {
  digest?: Digest17;
  external_identifiers?: ExternalIdentifiers19;
  object_id: string;
  object_type?: string | null;
  uri?: string | null;
  version_id?: string | null;
}
export interface ExternalIdentifier14 {
  namespace: string;
  resolution_state?: ResolutionState14;
  uri?: string | null;
  value: Value18;
}
export interface AgentReference9 {
  agent_id: string;
  agent_type: AgentType9;
  display_name?: DisplayName9;
  external_identifiers?: ExternalIdentifiers20;
  version?: Version10;
}
export interface WarningRecord {
  code: Code;
  message?: Message;
  name: Name;
  related_objects?: RelatedObjects;
  remediation?: Remediation;
  retryable?: Retryable;
  scope: Scope;
  severity: Severity;
  warning_id: string;
}
export interface ObjectReference11 {
  digest?: Digest18;
  external_identifiers?: ExternalIdentifiers21;
  object_id: string;
  object_type?: string | null;
  uri?: string | null;
  version_id?: string | null;
}
export interface ExternalIdentifier15 {
  namespace: string;
  resolution_state?: ResolutionState15;
  uri?: string | null;
  value: Value19;
}
export interface FailureRecord {
  code: Code1;
  failure_id: string;
  message?: Message1;
  name: Name1;
  related_objects?: RelatedObjects1;
  remediation?: Remediation1;
  retryable?: Retryable1;
  scope: Scope1;
  severity?: Severity1;
}
export interface ObjectReference12 {
  digest?: Digest19;
  external_identifiers?: ExternalIdentifiers22;
  object_id: string;
  object_type?: string | null;
  uri?: string | null;
  version_id?: string | null;
}
export interface ExternalIdentifier16 {
  namespace: string;
  resolution_state?: ResolutionState16;
  uri?: string | null;
  value: Value20;
}
export interface QualifiedValue {
  alternatives?: Alternatives;
  confidence?: ConfidenceRecord2 | null;
  evidence_method?: EvidenceMethod | null;
  failures?: Failures;
  presence: PresenceState;
  review_state?: ReviewState6;
  value?: unknown;
  warnings?: Warnings;
}
export interface AlternativeRecord1 {
  confidence?: ConfidenceRecord2 | null;
  rationale?: Rationale2;
  value: Value22;
}
export interface ConfidenceRecord2 {
  calibration_set?: VersionReference7 | null;
  kind: ConfidenceKind2;
  method: Method4;
  notes?: Notes9;
  sample_size?: SampleSize2;
  value: Value21;
}
export interface VersionReference7 {
  digest?: Digest20;
  object_id: string;
  object_type?: string | null;
  version_id: string;
}
export interface Value22 {
  [k: string]: unknown;
}
export interface FailureRecord1 {
  code: Code2;
  failure_id: string;
  message?: Message2;
  name: Name2;
  related_objects?: RelatedObjects2;
  remediation?: Remediation2;
  retryable?: Retryable2;
  scope: Scope2;
  severity?: Severity2;
}
export interface ObjectReference13 {
  digest?: Digest21;
  external_identifiers?: ExternalIdentifiers23;
  object_id: string;
  object_type?: string | null;
  uri?: string | null;
  version_id?: string | null;
}
export interface ExternalIdentifier17 {
  namespace: string;
  resolution_state?: ResolutionState17;
  uri?: string | null;
  value: Value23;
}
export interface WarningRecord1 {
  code: Code3;
  message?: Message3;
  name: Name3;
  related_objects?: RelatedObjects3;
  remediation?: Remediation3;
  retryable?: Retryable3;
  scope: Scope3;
  severity: Severity3;
  warning_id: string;
}
export interface TextQuoteSelector {
  exact: Exact;
  prefix?: Prefix;
  suffix?: Suffix;
}
export interface TextRepresentation {
  byte_length?: ByteLength1;
  character_encoding?: CharacterEncoding1;
  code_point_length?: CodePointLength;
  content_digest: DigestRecord1;
  media_type: MediaType2;
  normalisation_profile?: NormalisationProfile;
  owner_version: VersionReference8;
  representation_id: string;
  representation_type: RepresentationType;
  runtime_unicode_version?: RuntimeUnicodeVersion;
  segmentation_profile?: SegmentationProfile;
}
export interface DigestRecord1 {
  algorithm?: DigestAlgorithm1;
  basis: DigestBasis1;
  byte_length: ByteLength2;
  canonicalisation?: CanonicalisationRecord1 | null;
  character_encoding?: CharacterEncoding2;
  media_type?: MediaType1;
  value: Value25;
  verification_state?: VerificationState1;
}
export interface CanonicalisationRecord1 {
  method: CanonicalisationMethod1;
  version?: Version11;
}
export interface VersionReference8 {
  digest?: Digest22;
  object_id: string;
  object_type?: string | null;
  version_id: string;
}
export interface TextSpan {
  coordinate_profile?: CoordinateProfile;
  end: End;
  quote?: TextQuoteSelector1 | null;
  representation_id: string;
  representation_version: VersionReference9;
  runtime_unicode_version?: RuntimeUnicodeVersion1;
  span_id: SpanId;
  start: Start;
}
export interface TextQuoteSelector1 {
  exact: Exact1;
  prefix?: Prefix1;
  suffix?: Suffix1;
}
export interface VersionReference9 {
  digest?: Digest23;
  object_id: string;
  object_type?: string | null;
  version_id: string;
}
export interface SpanMapSegment {
  derived_end: DerivedEnd;
  derived_start: DerivedStart;
  kind: MappingKind;
  raw_end: RawEnd;
  raw_start: RawStart;
}
export interface SpanMapping {
  mapping_id: string;
  segments: Segments;
  source_length: SourceLength;
  source_representation_id: string;
  target_length: TargetLength;
  target_representation_id: string;
}
export interface SpanMapSegment1 {
  derived_end: DerivedEnd1;
  derived_start: DerivedStart1;
  kind: MappingKind1;
  raw_end: RawEnd1;
  raw_start: RawStart1;
}
export interface RelocationRecord {
  candidate_ranges?: CandidateRanges;
  explanation?: Explanation3;
  relocated_end?: RelocatedEnd;
  relocated_start?: RelocatedStart;
  result: RelocationResult;
  source_span: TextSpan1;
  target_representation_id: string;
}
export interface TextSpan1 {
  coordinate_profile?: CoordinateProfile1;
  end: End1;
  quote?: TextQuoteSelector2 | null;
  representation_id: string;
  representation_version: VersionReference10;
  runtime_unicode_version?: RuntimeUnicodeVersion2;
  span_id: SpanId1;
  start: Start1;
}
export interface TextQuoteSelector2 {
  exact: Exact2;
  prefix?: Prefix2;
  suffix?: Suffix2;
}
export interface VersionReference10 {
  digest?: Digest24;
  object_id: string;
  object_type?: string | null;
  version_id: string;
}
export interface PayloadDescriptor {
  digest?: DigestRecord2 | null;
  location_reference?: LocationReference;
  media_type?: MediaType4;
  payload_kind: PayloadKind;
  size_bytes?: SizeBytes;
  uri?: string | null;
  value?: unknown;
}
export interface DigestRecord2 {
  algorithm?: DigestAlgorithm2;
  basis: DigestBasis2;
  byte_length: ByteLength3;
  canonicalisation?: CanonicalisationRecord2 | null;
  character_encoding?: CharacterEncoding3;
  media_type?: MediaType3;
  value: Value26;
  verification_state?: VerificationState2;
}
export interface CanonicalisationRecord2 {
  method: CanonicalisationMethod2;
  version?: Version12;
}
export interface CoreObjectEnvelope {
  created_at: string;
  extensions?: Extensions;
  failures?: Failures1;
  object_id: string;
  object_type: string;
  parent_version_ids?: ParentVersionIds;
  payload: PayloadDescriptor1;
  policy: DirectPolicySummary1;
  provenance: DirectProvenanceSummary1;
  record_digest?: DigestRecord3 | null;
  review_state?: ReviewState9;
  reviews?: Reviews;
  schema: SchemaReference2;
  state?: ObjectState;
  version_id: string;
  warnings?: Warnings1;
}
export interface ExtensionRecord1 {
  critical?: Critical1;
  namespace: Namespace1;
  schema: SchemaReference2;
  value: unknown;
}
export interface SchemaReference2 {
  schema_digest?: SchemaDigest2;
  schema_id: string;
  schema_version: string;
}
export interface FailureRecord2 {
  code: Code4;
  failure_id: string;
  message?: Message4;
  name: Name4;
  related_objects?: RelatedObjects4;
  remediation?: Remediation4;
  retryable?: Retryable4;
  scope: Scope4;
  severity?: Severity4;
}
export interface ObjectReference14 {
  digest?: Digest25;
  external_identifiers?: ExternalIdentifiers24;
  object_id: string;
  object_type?: string | null;
  uri?: string | null;
  version_id?: string | null;
}
export interface ExternalIdentifier18 {
  namespace: string;
  resolution_state?: ResolutionState18;
  uri?: string | null;
  value: Value27;
}
export interface PayloadDescriptor1 {
  digest?: DigestRecord3 | null;
  location_reference?: LocationReference1;
  media_type?: MediaType6;
  payload_kind: PayloadKind1;
  size_bytes?: SizeBytes1;
  uri?: string | null;
  value?: unknown;
}
export interface DigestRecord3 {
  algorithm?: DigestAlgorithm3;
  basis: DigestBasis3;
  byte_length: ByteLength4;
  canonicalisation?: CanonicalisationRecord3 | null;
  character_encoding?: CharacterEncoding4;
  media_type?: MediaType5;
  value: Value28;
  verification_state?: VerificationState3;
}
export interface CanonicalisationRecord3 {
  method: CanonicalisationMethod3;
  version?: Version13;
}
export interface DirectPolicySummary1 {
  decisions?: Decisions1;
  policy_bundle_refs?: PolicyBundleRefs1;
  privacy: PrivacyPolicy2;
  retention: RetentionPolicy2;
}
export interface PolicyDecision2 {
  allowed: Allowed2;
  applied_rule_ids?: AppliedRuleIds2;
  decision_id: string;
  evaluated_at: string;
  explanation: Explanation4;
  highest_authority_tier?: AuthorityTier3 | null;
  operation: Operation4;
  outcome: PolicyDecisionOutcome2;
  rejected_rule_ids?: RejectedRuleIds2;
  unsatisfied_duties?: UnsatisfiedDuties2;
}
export interface PrivacyPolicy2 {
  allowed_recipients?: AllowedRecipients2;
  consent_required?: ConsentRequired2;
  notes?: Notes10;
  privacy_class: PrivacyClass2;
  transmission_class: TransmissionClass2;
}
export interface RetentionPolicy2 {
  delete_after?: string | null;
  deletion_mode: DeletionMode2;
  hold_reference?: ObjectReference14 | null;
  legal_hold?: LegalHold2;
  notes?: Notes11;
  retention_class: RetentionClass2;
}
export interface DirectProvenanceSummary1 {
  contribution_records?: ContributionRecords1;
  creation_activity: ActivityReference2;
  creator: AgentReference10;
  direct_relations?: DirectRelations1;
  full_provenance_records?: FullProvenanceRecords1;
}
export interface ContributionRecord2 {
  activity_id?: string | null;
  agent: AgentReference10;
  contribution_id: string;
  description?: Description6;
  review_state?: ReviewState7;
  role: Role2;
  sources?: Sources2;
  target: VersionReference11;
}
export interface AgentReference10 {
  agent_id: string;
  agent_type: AgentType10;
  display_name?: DisplayName10;
  external_identifiers?: ExternalIdentifiers25;
  version?: Version14;
}
export interface VersionReference11 {
  digest?: Digest26;
  object_id: string;
  object_type?: string | null;
  version_id: string;
}
export interface ActivityReference2 {
  activity_id: string;
  activity_type: ActivityType2;
  component_version?: ComponentVersion2;
  ended_at?: string | null;
  parameters_digest?: ParametersDigest4;
  responsible_agents: ResponsibleAgents2;
  run_id?: string | null;
  started_at: string;
  status: ProcessingState2;
  step_run_id?: string | null;
}
export interface ProvenanceRelation2 {
  activity_id?: string | null;
  entity_role?: EntityRole2;
  method?: Method5;
  object: Object2;
  parameters_digest?: ParametersDigest5;
  relation_id: string;
  relation_type: RelationType2;
  review_state?: ReviewState8;
  source_span_ids?: SourceSpanIds2;
  subject: VersionReference11;
  target_span_ids?: TargetSpanIds2;
}
export interface ReviewRecord1 {
  evidence?: Evidence5;
  rationale?: Rationale3;
  review_id: string;
  reviewed_at: string;
  reviewer: AgentReference10;
  state: ReviewState10;
}
export interface WarningRecord2 {
  code: Code5;
  message?: Message5;
  name: Name5;
  related_objects?: RelatedObjects5;
  remediation?: Remediation5;
  retryable?: Retryable5;
  scope: Scope5;
  severity: Severity5;
  warning_id: string;
}
export interface EvidenceRecord4 {
  description?: Description7;
  source: ObjectReference15;
  verified?: Verified4;
  verified_at?: string | null;
  verifier?: AgentReference11 | null;
}
export interface ObjectReference15 {
  digest?: Digest27;
  external_identifiers?: ExternalIdentifiers26;
  object_id: string;
  object_type?: string | null;
  uri?: string | null;
  version_id?: string | null;
}
export interface ExternalIdentifier19 {
  namespace: string;
  resolution_state?: ResolutionState19;
  uri?: string | null;
  value: Value29;
}
export interface AgentReference11 {
  agent_id: string;
  agent_type: AgentType11;
  display_name?: DisplayName11;
  external_identifiers?: ExternalIdentifiers27;
  version?: Version15;
}
