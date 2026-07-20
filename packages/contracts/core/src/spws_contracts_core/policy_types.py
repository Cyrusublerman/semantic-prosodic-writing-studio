from __future__ import annotations

from enum import IntEnum, StrEnum


class PolicyEffect(StrEnum):
    PERMIT = "permit"
    PROHIBIT = "prohibit"


class AuthorityTier(IntEnum):
    DEFAULT_SAFETY = 0
    USER_PREFERENCE = 10
    PROJECT_POLICY = 20
    OWNERSHIP_LICENCE_CONTRACT = 30
    CONSENT_PRIVACY = 40
    LEGAL_REGULATORY = 50


class ConstraintOperator(StrEnum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    IN = "in"
    NOT_IN = "not_in"
    LESS_THAN_OR_EQUAL = "lte"
    GREATER_THAN_OR_EQUAL = "gte"
    CONTAINS = "contains"


class PolicyDecisionOutcome(StrEnum):
    PERMIT = "permit"
    DENY = "deny"
    DENY_PENDING_DUTY = "deny_pending_duty"
    INDETERMINATE = "indeterminate"


class PrivacyClass(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"
    SENSITIVE = "sensitive"
    HIGHLY_SENSITIVE = "highly_sensitive"


class TransmissionClass(StrEnum):
    PUBLIC_ALLOWED = "public_allowed"
    PRIVATE_SHARE_ALLOWED = "private_share_allowed"
    EXTERNAL_WITH_CONSENT = "external_with_consent"
    LOCAL_ONLY = "local_only"
    BLOCKED = "blocked"


class RetentionClass(StrEnum):
    EPHEMERAL = "ephemeral"
    SESSION = "session"
    PROJECT_LIFETIME = "project_lifetime"
    UNTIL_DATE = "until_date"
    INDEFINITE = "indefinite"
    LEGAL_HOLD = "legal_hold"
    DELETE_ON_REQUEST = "delete_on_request"


class DeletionMode(StrEnum):
    HARD_DELETE_PAYLOAD = "hard_delete_payload"
    TOMBSTONE_ONLY = "tombstone_only"
    CRYPTOGRAPHIC_ERASURE = "cryptographic_erasure"
    EXTERNAL_REFERENCE_REMOVAL = "external_reference_removal"
    BLOCKED_BY_HOLD = "blocked_by_hold"


