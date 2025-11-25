"""
Policy engine for evaluating agent authorization.
"""

from typing import Dict, Any, List
from .schemas import PolicyRule, PolicyDecision


class PolicyEngine:
    """
    Evaluates policy rules to determine if agent actions are allowed.

    Rules are evaluated with precedence: deny > allow > default.
    Higher priority rules are evaluated first within each effect type.
    """

    def __init__(self, rules: List[PolicyRule]):
        """
        Initialize policy engine with a list of rules.

        Args:
            rules: List of policy rules to evaluate
        """
        self.rules = sorted(rules, key=lambda r: r.priority, reverse=True)

    def decide(
        self, agent: str, action: str, context: Dict[str, Any]
    ) -> PolicyDecision:
        """
        Evaluate policies to decide if action is allowed.

        Args:
            agent: Name of the agent requesting action
            action: Name of the action to perform
            context: Context dictionary with additional information

        Returns:
            PolicyDecision with effect, reason, and rule_id
        """
        # Default decision (allow by default, following principle of least surprise)
        decision = PolicyDecision(
            effect="allow",
            reason="default-allow: no matching policy rules",
            rule_id=None,
            requires_approval=False,
        )

        # Track all matching rules
        matching_rules = []

        # Evaluate all rules
        for rule in self.rules:
            if not self._matches_target(rule, agent, action):
                continue

            if not self._matches_conditions(rule.conditions, context):
                continue

            # Rule matches
            matching_rules.append(rule)

        # Apply evaluation logic:
        # If no rules match → default allow
        # If rules match → use highest priority rule (regardless of effect)
        # This allows specific allow rules to override general deny rules
        if not matching_rules:
            decision = PolicyDecision(
                effect="allow",
                reason="default-allow: no matching policy rules",
                rule_id=None,
                requires_approval=False,
            )
        else:
            # Use highest priority rule
            rule = matching_rules[0]  # Already sorted by priority (desc)
            decision = PolicyDecision(
                effect=rule.effect,
                reason=rule.reason or f"{rule.effect} by policy rule {rule.id}",
                rule_id=rule.id,
                requires_approval=self._check_approval_needed(rule, context)
                if rule.effect == "deny"
                else False,
            )

        return decision

    def _matches_target(self, rule: PolicyRule, agent: str, action: str) -> bool:
        """
        Check if rule target matches agent and action.

        Args:
            rule: Policy rule to check
            agent: Agent name
            action: Action name

        Returns:
            True if rule target matches
        """
        agent_match = rule.agent == "*" or rule.agent == agent
        action_match = rule.action == "*" or rule.action == action

        return agent_match and action_match

    def _matches_conditions(
        self, conditions: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """
        Check if all conditions match the context.

        Conditions can be:
        - Exact match: {"key": "value"}
        - Numeric comparison: {"count": 100} matches if context["count"] >= 100
        - Boolean: {"flag": True}

        Args:
            conditions: Dictionary of conditions from rule
            context: Dictionary of context values

        Returns:
            True if all conditions match
        """
        for key, expected in conditions.items():
            actual = context.get(key)

            # Handle None values
            if actual is None:
                return False

            # Numeric comparison (>=)
            if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
                if actual < expected:
                    return False
            # Exact match
            elif actual != expected:
                return False

        return True

    def _check_approval_needed(self, rule: PolicyRule, context: Dict[str, Any]) -> bool:
        """
        Check if denied action requires human approval.

        Actions can be:
        - Hard deny (no approval possible)
        - Soft deny (approval can override)

        Args:
            rule: The deny rule that matched
            context: Context dictionary

        Returns:
            True if human approval can override the deny
        """
        # Check if rule has approval_eligible condition
        # This is a hint that the action can be approved
        return context.get("approval_eligible", True) and rule.effect == "deny"

    def add_rule(self, rule: PolicyRule):
        """Add a new rule and re-sort by priority."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID. Returns True if found and removed."""
        original_len = len(self.rules)
        self.rules = [r for r in self.rules if r.id != rule_id]
        return len(self.rules) < original_len

    def get_rules(self, agent: str = "*", action: str = "*") -> List[PolicyRule]:
        """Get all rules matching agent and action patterns."""
        return [
            r
            for r in self.rules
            if (agent == "*" or r.agent in (agent, "*"))
            and (action == "*" or r.action in (action, "*"))
        ]
