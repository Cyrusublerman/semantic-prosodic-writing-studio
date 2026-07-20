from __future__ import annotations

from .identifiers import DecisionId
from .policy_records import PolicyConstraint, PolicyContext, PolicyDecision, UsageRule
from .policy_types import ConstraintOperator, PolicyDecisionOutcome, PolicyEffect


_CONSEQUENTIAL_OPERATIONS = {
    "spws.operation.external_transmission",
    "spws.operation.model_training",
    "spws.operation.publish",
    "spws.operation.redistribute",
    "spws.operation.delete",
}


def _target_matches(rule: UsageRule, context: PolicyContext) -> bool:
    if rule.target is None:
        return True
    if context.target is None:
        return False
    if rule.target.object_id != context.target.object_id:
        return False
    if rule.target.version_id is not None and rule.target.version_id != context.target.version_id:
        return False
    return True


def _agent_matches(rule: UsageRule, context: PolicyContext) -> bool:
    return rule.agent is None or (
        context.agent is not None and rule.agent.agent_id == context.agent.agent_id
    )


def _constraint_matches(constraint: PolicyConstraint, context: PolicyContext) -> bool:
    key = constraint.constraint_type.rsplit(".", 1)[-1]
    actual = context.attributes.get(key)
    expected = constraint.value
    if key == "purpose":
        actual = context.purpose
    operator = constraint.operator
    if operator is ConstraintOperator.EQUALS:
        return actual == expected
    if operator is ConstraintOperator.NOT_EQUALS:
        return actual != expected
    if operator is ConstraintOperator.IN:
        return isinstance(expected, (list, tuple, set, frozenset)) and actual in expected
    if operator is ConstraintOperator.NOT_IN:
        return isinstance(expected, (list, tuple, set, frozenset)) and actual not in expected
    if operator is ConstraintOperator.LESS_THAN_OR_EQUAL:
        return actual is not None and actual <= expected
    if operator is ConstraintOperator.GREATER_THAN_OR_EQUAL:
        return actual is not None and actual >= expected
    if operator is ConstraintOperator.CONTAINS:
        return actual is not None and expected in actual
    return False


def _rule_applies(rule: UsageRule, context: PolicyContext) -> bool:
    if rule.operation != context.operation:
        return False
    if not rule.effective_window.contains(context.evaluated_at):
        return False
    if rule.purpose is not None and rule.purpose != context.purpose:
        return False
    if not _target_matches(rule, context) or not _agent_matches(rule, context):
        return False
    return all(_constraint_matches(item, context) for item in rule.constraints)


def evaluate_policy(
    rules: tuple[UsageRule, ...] | list[UsageRule],
    context: PolicyContext,
    *,
    decision_id: DecisionId,
) -> PolicyDecision:
    applicable = [rule for rule in rules if _rule_applies(rule, context)]
    if not applicable:
        return PolicyDecision(
            decision_id=decision_id,
            operation=context.operation,
            outcome=PolicyDecisionOutcome.INDETERMINATE,
            allowed=False,
            explanation=(
                "No applicable policy rule; operation is not permitted without an explicit rule."
                if context.operation in _CONSEQUENTIAL_OPERATIONS
                else "No applicable policy rule."
            ),
            evaluated_at=context.evaluated_at,
        )

    highest = max(rule.authority_tier for rule in applicable)
    highest_rules = [rule for rule in applicable if rule.authority_tier == highest]
    lower_rules = [rule for rule in applicable if rule.authority_tier < highest]
    highest_prohibitions = [rule for rule in highest_rules if rule.effect is PolicyEffect.PROHIBIT]
    highest_permits = [rule for rule in highest_rules if rule.effect is PolicyEffect.PERMIT]

    if highest_prohibitions:
        return PolicyDecision(
            decision_id=decision_id,
            operation=context.operation,
            outcome=PolicyDecisionOutcome.DENY,
            allowed=False,
            highest_authority_tier=highest,
            applied_rule_ids=tuple(rule.rule_id for rule in highest_prohibitions),
            rejected_rule_ids=tuple(rule.rule_id for rule in highest_permits + lower_rules),
            explanation="A prohibition at the highest applicable authority tier overrides permits.",
            evaluated_at=context.evaluated_at,
        )

    lower_prohibitions = [rule for rule in lower_rules if rule.effect is PolicyEffect.PROHIBIT]
    if lower_prohibitions and not any(rule.override_lower_authority for rule in highest_permits):
        return PolicyDecision(
            decision_id=decision_id,
            operation=context.operation,
            outcome=PolicyDecisionOutcome.DENY,
            allowed=False,
            highest_authority_tier=highest,
            applied_rule_ids=tuple(rule.rule_id for rule in lower_prohibitions),
            rejected_rule_ids=tuple(rule.rule_id for rule in highest_permits),
            explanation="A higher-tier permit lacked explicit authority to override inherited prohibitions.",
            evaluated_at=context.evaluated_at,
        )

    unsatisfied = [
        duty.duty_type
        for rule in highest_permits
        for duty in rule.duties
        if not duty.satisfied
    ]
    if unsatisfied:
        return PolicyDecision(
            decision_id=decision_id,
            operation=context.operation,
            outcome=PolicyDecisionOutcome.DENY_PENDING_DUTY,
            allowed=False,
            highest_authority_tier=highest,
            applied_rule_ids=tuple(rule.rule_id for rule in highest_permits),
            rejected_rule_ids=tuple(rule.rule_id for rule in lower_rules),
            unsatisfied_duties=tuple(sorted(set(unsatisfied))),
            explanation="A permit applies but one or more attached duties are unsatisfied.",
            evaluated_at=context.evaluated_at,
        )

    return PolicyDecision(
        decision_id=decision_id,
        operation=context.operation,
        outcome=PolicyDecisionOutcome.PERMIT,
        allowed=True,
        highest_authority_tier=highest,
        applied_rule_ids=tuple(rule.rule_id for rule in highest_permits),
        rejected_rule_ids=tuple(rule.rule_id for rule in lower_rules),
        explanation="Highest-authority applicable permit survived conflict and duty evaluation.",
        evaluated_at=context.evaluated_at,
    )
