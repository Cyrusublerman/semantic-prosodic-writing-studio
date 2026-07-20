"""Fail-closed rights and privacy enforcement for PKL retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from spws_contracts_core.domain import PrivacyState, RightsState

from .config import PolicySettings


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    reason: str | None = None


def parse_rights(value: object | None) -> RightsState:
    if value is None:
        return RightsState.UNKNOWN
    text = str(value).strip().lower()
    try:
        return RightsState(text)
    except ValueError:
        return RightsState.UNKNOWN


def parse_privacy(value: object | None) -> PrivacyState:
    if value is None:
        return PrivacyState.UNKNOWN
    text = str(value).strip().lower()
    try:
        return PrivacyState(text)
    except ValueError:
        return PrivacyState.UNKNOWN


def catalogue_exclusion(
    rights: RightsState,
    privacy: PrivacyState,
    policy: PolicySettings,
) -> PolicyDecision:
    """Decide whether content may enter full-text / embedding indexes.

    Objects with unknown or restricted rights/privacy are catalogued as
    excluded (metadata only) and never contribute searchable text.
    """
    if policy.fail_closed_on_unknown_rights and rights is RightsState.UNKNOWN:
        return PolicyDecision(False, "unknown rights")
    if policy.fail_closed_on_unknown_privacy and privacy is PrivacyState.UNKNOWN:
        return PolicyDecision(False, "unknown privacy")
    if rights in {RightsState.PRIVATE, RightsState.RESTRICTED}:
        return PolicyDecision(False, f"rights {rights.value}")
    if privacy in {PrivacyState.PRIVATE, PrivacyState.SENSITIVE}:
        return PolicyDecision(False, f"privacy {privacy.value}")
    return PolicyDecision(True)


def allows_retrieval(
    rights: RightsState,
    privacy: PrivacyState,
    policy: PolicySettings,
    *,
    rights_filter: list[RightsState],
    privacy_filter: list[PrivacyState],
) -> PolicyDecision:
    exclusion = catalogue_exclusion(rights, privacy, policy)
    if not exclusion.allowed:
        return exclusion
    if rights not in rights_filter:
        return PolicyDecision(False, f"rights {rights.value} not in filter")
    if privacy not in privacy_filter:
        return PolicyDecision(False, f"privacy {privacy.value} not in filter")
    return PolicyDecision(True)


def allows_embeddings(
    rights: RightsState,
    privacy: PrivacyState,
    policy: PolicySettings,
) -> PolicyDecision:
    return catalogue_exclusion(rights, privacy, policy)
