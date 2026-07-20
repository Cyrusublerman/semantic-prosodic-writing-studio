from datetime import timedelta

import pytest
from pydantic import ValidationError

from spws_contracts_core.identifiers import new_uuid7
from spws_contracts_core.policy import (
    AuthorityTier,
    ConstraintOperator,
    DeletionMode,
    DutyRecord,
    PolicyConstraint,
    PolicyContext,
    PolicyDecisionOutcome,
    PolicyEffect,
    PrivacyClass,
    PrivacyPolicy,
    RetentionClass,
    RetentionPolicy,
    TransmissionClass,
    UsageRule,
    evaluate_policy,
)
from spws_contracts_core.references import ObjectReference


def make_rule(operation, effect, tier, **kwargs):
    return UsageRule(
        rule_id=new_uuid7(),
        operation=operation,
        effect=effect,
        authority_tier=tier,
        **kwargs,
    )


def make_context(operation, now, **kwargs):
    return PolicyContext(operation=operation, evaluated_at=now, **kwargs)


def test_same_tier_prohibition_overrides_permit(now):
    op = "spws.operation.publish"
    permit = make_rule(op, PolicyEffect.PERMIT, AuthorityTier.PROJECT_POLICY)
    prohibit = make_rule(op, PolicyEffect.PROHIBIT, AuthorityTier.PROJECT_POLICY)
    decision = evaluate_policy((permit, prohibit), make_context(op, now), decision_id=new_uuid7())
    assert decision.outcome is PolicyDecisionOutcome.DENY
    assert not decision.allowed


def test_higher_permit_needs_explicit_override_of_lower_prohibit(now):
    op = "spws.operation.external_transmission"
    lower = make_rule(op, PolicyEffect.PROHIBIT, AuthorityTier.PROJECT_POLICY)
    higher = make_rule(op, PolicyEffect.PERMIT, AuthorityTier.CONSENT_PRIVACY)
    denied = evaluate_policy((lower, higher), make_context(op, now), decision_id=new_uuid7())
    assert denied.outcome is PolicyDecisionOutcome.DENY
    allowed = evaluate_policy(
        (lower, higher.model_copy(update={"override_lower_authority": True})),
        make_context(op, now),
        decision_id=new_uuid7(),
    )
    assert allowed.allowed


def test_unmet_duty_blocks_permit(now):
    op = "spws.operation.publish"
    permit = make_rule(
        op,
        PolicyEffect.PERMIT,
        AuthorityTier.OWNERSHIP_LICENCE_CONTRACT,
        duties=(DutyRecord(duty_type="spws.duty.attribute"),),
    )
    decision = evaluate_policy((permit,), make_context(op, now), decision_id=new_uuid7())
    assert decision.outcome is PolicyDecisionOutcome.DENY_PENDING_DUTY


def test_no_rule_is_indeterminate_and_not_allowed(now):
    op = "spws.operation.publish"
    decision = evaluate_policy((), make_context(op, now), decision_id=new_uuid7())
    assert decision.outcome is PolicyDecisionOutcome.INDETERMINATE
    assert not decision.allowed


def test_constraint_matching(now):
    op = "spws.operation.quote"
    rule = make_rule(
        op,
        PolicyEffect.PERMIT,
        AuthorityTier.OWNERSHIP_LICENCE_CONTRACT,
        constraints=(
            PolicyConstraint(
                constraint_type="spws.constraint.excerpt_length",
                operator=ConstraintOperator.LESS_THAN_OR_EQUAL,
                value=20,
            ),
        ),
    )
    context = make_context(op, now, attributes={"excerpt_length": 10})
    assert evaluate_policy((rule,), context, decision_id=new_uuid7()).allowed


def test_privacy_and_retention_invariants(now):
    with pytest.raises(ValidationError):
        PrivacyPolicy(
            privacy_class=PrivacyClass.PRIVATE,
            transmission_class=TransmissionClass.EXTERNAL_WITH_CONSENT,
            consent_required=False,
        )
    with pytest.raises(ValidationError):
        RetentionPolicy(
            retention_class=RetentionClass.UNTIL_DATE,
            deletion_mode=DeletionMode.TOMBSTONE_ONLY,
        )
