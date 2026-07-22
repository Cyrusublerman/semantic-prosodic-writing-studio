from __future__ import annotations
from importlib.resources import files
from typing import TypeAlias
from pydantic import BaseModel
from .digests import DigestRecord
from .envelope import CoreObjectEnvelope, PayloadDescriptor
from .extensions import ExtensionRecord
from .policy_records import (DirectPolicySummary, DutyRecord, EvidenceRecord, PolicyConstraint, PolicyContext, PolicyDecision, PrivacyPolicy, RetentionPolicy, RightsAssertion, UsageRule)
from .provenance import ActivityReference, ContributionRecord, DirectProvenanceSummary, ProvenanceRelation
from .quality import AlternativeRecord, ConfidenceRecord, FailureRecord, QualifiedValue, ReviewRecord, WarningRecord
from .references import AgentReference, ExternalIdentifier, ObjectReference, ReferenceSet, VersionReference
from .schema import SchemaReference, VersionRange
from .text_mapping import RelocationRecord, SpanMapSegment, SpanMapping
from .text_types import TextQuoteSelector, TextRepresentation, TextSpan
from .time import TimeWindow
SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
SCHEMA_RELEASE_VERSION = "0.1.0-dev.2"
SCHEMA_PREFIX = "urn:pkl:spws:schema:contracts-core"
BUNDLE_SCHEMA_ID = f"{SCHEMA_PREFIX}:bundle:{SCHEMA_RELEASE_VERSION}"
# Domain models (InputPackage, PKL*, Meaning*, etc.) live under schemas/domain/
# and are not part of the frozen contracts-core release bundle.
RELEASE_MODELS: dict[str, type[BaseModel]] = {
    "schema-reference": SchemaReference, "version-range": VersionRange,
    "external-identifier": ExternalIdentifier, "agent-reference": AgentReference,
    "object-reference": ObjectReference, "version-reference": VersionReference,
    "reference-set": ReferenceSet, "time-window": TimeWindow,
    "digest-record": DigestRecord, "extension-record": ExtensionRecord,
    "activity-reference": ActivityReference, "provenance-relation": ProvenanceRelation,
    "contribution-record": ContributionRecord, "direct-provenance-summary": DirectProvenanceSummary,
    "evidence-record": EvidenceRecord, "rights-assertion": RightsAssertion,
    "policy-constraint": PolicyConstraint, "duty-record": DutyRecord,
    "usage-rule": UsageRule, "policy-context": PolicyContext,
    "policy-decision": PolicyDecision, "privacy-policy": PrivacyPolicy,
    "retention-policy": RetentionPolicy, "direct-policy-summary": DirectPolicySummary,
    "confidence-record": ConfidenceRecord, "alternative-record": AlternativeRecord,
    "review-record": ReviewRecord, "warning-record": WarningRecord,
    "failure-record": FailureRecord, "qualified-value": QualifiedValue,
    "text-quote-selector": TextQuoteSelector, "text-representation": TextRepresentation,
    "text-span": TextSpan, "span-map-segment": SpanMapSegment,
    "span-mapping": SpanMapping, "relocation-record": RelocationRecord,
    "payload-descriptor": PayloadDescriptor, "core-object-envelope": CoreObjectEnvelope,
    "policy-evidence-record": EvidenceRecord,
}

def schema_id_for(slug: str) -> str:
    if slug not in RELEASE_MODELS: raise KeyError(slug)
    return f"{SCHEMA_PREFIX}:{slug}:{SCHEMA_RELEASE_VERSION}"

def release_archive_resource():
    return files("spws_contracts_core").joinpath("data/releases/contracts-core-0.1.0-dev.2.zip")
