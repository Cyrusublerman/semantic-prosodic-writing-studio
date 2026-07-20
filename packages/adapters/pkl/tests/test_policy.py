from spws_contracts_core.domain import PrivacyState, RightsState

from spws_pkl_adapter.config import PolicySettings
from spws_pkl_adapter.policy import allows_embeddings, allows_retrieval, catalogue_exclusion, parse_privacy, parse_rights


def test_fail_closed_unknown_rights():
    policy = PolicySettings(
        fail_closed_on_unknown_rights=True,
        fail_closed_on_unknown_privacy=True,
        allow_working_tree_reads=True,
        allow_remote_git=False,
    )
    decision = catalogue_exclusion(RightsState.UNKNOWN, PrivacyState.PUBLIC, policy)
    assert not decision.allowed
    assert decision.reason == "unknown rights"


def test_fail_closed_unknown_privacy():
    policy = PolicySettings(
        fail_closed_on_unknown_rights=True,
        fail_closed_on_unknown_privacy=True,
        allow_working_tree_reads=True,
        allow_remote_git=False,
    )
    decision = catalogue_exclusion(RightsState.PUBLIC, PrivacyState.UNKNOWN, policy)
    assert not decision.allowed
    assert decision.reason == "unknown privacy"


def test_retrieval_respects_filters():
    policy = PolicySettings(
        fail_closed_on_unknown_rights=True,
        fail_closed_on_unknown_privacy=True,
        allow_working_tree_reads=True,
        allow_remote_git=False,
    )
    allowed = allows_retrieval(
        RightsState.PUBLIC,
        PrivacyState.PUBLIC,
        policy,
        rights_filter=[RightsState.PUBLIC],
        privacy_filter=[PrivacyState.PUBLIC],
    )
    blocked = allows_retrieval(
        RightsState.RESTRICTED,
        PrivacyState.PUBLIC,
        policy,
        rights_filter=[RightsState.PUBLIC],
        privacy_filter=[PrivacyState.PUBLIC],
    )
    assert allowed.allowed
    assert not blocked.allowed


def test_parse_enum_values():
    assert parse_rights("PUBLIC") is RightsState.PUBLIC
    assert parse_privacy("invalid") is PrivacyState.UNKNOWN
    assert not allows_embeddings(RightsState.UNKNOWN, PrivacyState.PUBLIC, PolicySettings(True, True, True, False)).allowed
