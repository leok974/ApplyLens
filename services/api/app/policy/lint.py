# Phase 5.5 PR2: Policy Linter
# Static analysis and validation for policy rules

from typing import Any, Literal

from pydantic import BaseModel


class LintAnnotation(BaseModel):
    """A single lint annotation (error/warning)."""
    rule_id: str | None
    severity: Literal["error", "warning", "info"]
    message: str
    line: int | None = None  # For future UI integration
    suggestion: str | None = None


class LintResult(BaseModel):
    """Result of linting a policy bundle."""
    errors: list[LintAnnotation] = []
    warnings: list[LintAnnotation] = []
    info: list[LintAnnotation] = []
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    @property
    def total_issues(self) -> int:
        """Total number of issues."""
        return len(self.errors) + len(self.warnings) + len(self.info)
    
    def add(self, annotation: LintAnnotation) -> None:
        """Add an annotation to the appropriate list."""
        if annotation.severity == "error":
            self.errors.append(annotation)
        elif annotation.severity == "warning":
            self.warnings.append(annotation)
        else:
            self.info.append(annotation)


def lint_rules(rules: list[dict[str, Any]]) -> LintResult:
    """
    Lint a list of policy rules.
    
    Checks:
    - Duplicate rule IDs
    - Conflicting allow/deny rules
    - Missing reasons
    - Unreachable rules (always shadowed by higher priority)
    - Budget sanity (needs_approval requires budget)
    - Invalid condition operators
    """
    result = LintResult()
    
    # Check 1: Duplicate rule IDs
    _check_duplicate_ids(rules, result)
    
    # Check 2: Missing reasons
    _check_missing_reasons(rules, result)
    
    # Check 3: Conflicting rules
    _check_conflicts(rules, result)
    
    # Check 4: Unreachable rules
    _check_unreachable(rules, result)
    
    # Check 5: Budget sanity
    _check_budget_sanity(rules, result)
    
    # Check 6: Invalid conditions
    _check_invalid_conditions(rules, result)
    
    # Check 7: Disabled rules
    _check_disabled_rules(rules, result)
    
    return result


def _check_duplicate_ids(rules: list[dict[str, Any]], result: LintResult) -> None:
    """Check for duplicate rule IDs."""
    seen_ids: dict[str, int] = {}
    
    for idx, rule in enumerate(rules):
        rule_id = rule.get("id")
        if not rule_id:
            result.add(LintAnnotation(
                rule_id=None,
                severity="error",
                message=f"Rule at index {idx} is missing an 'id' field",
                line=idx
            ))
            continue
        
        if rule_id in seen_ids:
            result.add(LintAnnotation(
                rule_id=rule_id,
                severity="error",
                message=f"Duplicate rule ID '{rule_id}' (first seen at index {seen_ids[rule_id]})",
                line=idx,
                suggestion=f"Use a unique ID like '{rule_id}_v2' or '{rule_id}_alt'"
            ))
        else:
            seen_ids[rule_id] = idx


def _check_missing_reasons(rules: list[dict[str, Any]], result: LintResult) -> None:
    """Check for missing or too-short reasons."""
    for idx, rule in enumerate(rules):
        rule_id = rule.get("id", f"rule_{idx}")
        reason = rule.get("reason", "")
        
        if not reason:
            result.add(LintAnnotation(
                rule_id=rule_id,
                severity="error",
                message=f"Rule '{rule_id}' is missing a 'reason' field",
                line=idx,
                suggestion="Add a clear explanation for audit and debugging"
            ))
        elif len(reason) < 10:
            result.add(LintAnnotation(
                rule_id=rule_id,
                severity="warning",
                message=f"Rule '{rule_id}' has a very short reason (< 10 chars)",
                line=idx,
                suggestion="Provide a more detailed explanation"
            ))


def _check_conflicts(rules: list[dict[str, Any]], result: LintResult) -> None:
    """Check for conflicting allow/deny rules."""
    # Group rules by (agent, action)
    rule_groups: dict[tuple[str, str], list[tuple[int, dict]]] = {}
    
    for idx, rule in enumerate(rules):
        agent = rule.get("agent", "")
        action = rule.get("action", "")
        key = (agent, action)
        
        if key not in rule_groups:
            rule_groups[key] = []
        rule_groups[key].append((idx, rule))
    
    # Check each group for conflicts
    for (agent, action), group in rule_groups.items():
        if len(group) < 2:
            continue
        
        # Sort by priority (higher first)
        sorted_group = sorted(group, key=lambda x: x[1].get("priority", 50), reverse=True)
        
        # Check for allow/deny conflicts
        effects = [r[1].get("effect") for _, r in sorted_group]
        
        if "allow" in effects and "deny" in effects:
            allow_rules = [r[1].get("id") for _, r in sorted_group if r[1].get("effect") == "allow"]
            deny_rules = [r[1].get("id") for _, r in sorted_group if r[1].get("effect") == "deny"]
            
            # This is a conflict if conditions overlap
            result.add(LintAnnotation(
                rule_id=sorted_group[0][1].get("id"),
                severity="warning",
                message=f"Conflicting allow/deny rules for {agent}.{action}: allow={allow_rules}, deny={deny_rules}",
                line=sorted_group[0][0],
                suggestion="Ensure conditions are mutually exclusive or use priority to order correctly"
            ))


def _check_unreachable(rules: list[dict[str, Any]], result: LintResult) -> None:
    """Check for unreachable rules (always shadowed by higher priority)."""
    # Group rules by (agent, action)
    rule_groups: dict[tuple[str, str], list[tuple[int, dict]]] = {}
    
    for idx, rule in enumerate(rules):
        agent = rule.get("agent", "")
        action = rule.get("action", "")
        enabled = rule.get("enabled", True)
        
        if not enabled:
            continue  # Skip disabled rules
        
        key = (agent, action)
        if key not in rule_groups:
            rule_groups[key] = []
        rule_groups[key].append((idx, rule))
    
    # Check each group
    for (agent, action), group in rule_groups.items():
        if len(group) < 2:
            continue
        
        # Sort by priority (higher first)
        sorted_group = sorted(group, key=lambda x: x[1].get("priority", 50), reverse=True)
        
        # Check if lower priority rules have no conditions
        # (which makes them unreachable if a higher priority rule exists without conditions)
        for i in range(len(sorted_group)):
            idx_i, rule_i = sorted_group[i]
            conditions_i = rule_i.get("conditions", {})
            
            # If this rule has no conditions, all lower-priority rules are unreachable
            if not conditions_i:
                for j in range(i + 1, len(sorted_group)):
                    idx_j, rule_j = sorted_group[j]
                    rule_id_j = rule_j.get("id", f"rule_{idx_j}")
                    
                    result.add(LintAnnotation(
                        rule_id=rule_id_j,
                        severity="warning",
                        message=f"Rule '{rule_id_j}' may be unreachable (shadowed by '{rule_i.get('id')}' with higher priority and no conditions)",
                        line=idx_j,
                        suggestion=f"Add specific conditions to '{rule_i.get('id')}' or increase priority of '{rule_id_j}'"
                    ))
                break  # No need to check further


def _check_budget_sanity(rules: list[dict[str, Any]], result: LintResult) -> None:
    """Check that rules requiring approval have budget information."""
    for idx, rule in enumerate(rules):
        rule_id = rule.get("id", f"rule_{idx}")
        effect = rule.get("effect")
        budget = rule.get("budget")
        
        if effect == "needs_approval" and not budget:
            result.add(LintAnnotation(
                rule_id=rule_id,
                severity="warning",
                message=f"Rule '{rule_id}' requires approval but has no budget information",
                line=idx,
                suggestion="Add 'budget' field with cost, compute, and risk estimates"
            ))
        
        # Check for unrealistic budgets
        if budget:
            cost = budget.get("cost", 0)
            if cost > 1000:
                result.add(LintAnnotation(
                    rule_id=rule_id,
                    severity="warning",
                    message=f"Rule '{rule_id}' has very high estimated cost: ${cost}",
                    line=idx,
                    suggestion="Review cost estimate and consider if action is necessary"
                ))


def _check_invalid_conditions(rules: list[dict[str, Any]], result: LintResult) -> None:
    """Check for invalid condition operators."""
    valid_operators = {">=", "<=", ">", "<", "==", "!="}
    
    for idx, rule in enumerate(rules):
        rule_id = rule.get("id", f"rule_{idx}")
        conditions = rule.get("conditions", {})
        
        if not isinstance(conditions, dict):
            result.add(LintAnnotation(
                rule_id=rule_id,
                severity="error",
                message=f"Rule '{rule_id}' has invalid conditions (must be a dict)",
                line=idx
            ))
            continue
        
        for key, value in conditions.items():
            # Check if key starts with an operator
            has_operator = False
            for op in valid_operators:
                if key.startswith(op):
                    has_operator = True
                    break
            
            # If key starts with operator but isn't valid, warn
            if key and key[0] in "><=!" and not has_operator:
                result.add(LintAnnotation(
                    rule_id=rule_id,
                    severity="warning",
                    message=f"Rule '{rule_id}' has suspicious condition key: '{key}'",
                    line=idx,
                    suggestion=f"Valid operators: {', '.join(sorted(valid_operators))}"
                ))


def _check_disabled_rules(rules: list[dict[str, Any]], result: LintResult) -> None:
    """Report on disabled rules."""
    for idx, rule in enumerate(rules):
        rule_id = rule.get("id", f"rule_{idx}")
        enabled = rule.get("enabled", True)
        
        if not enabled:
            result.add(LintAnnotation(
                rule_id=rule_id,
                severity="info",
                message=f"Rule '{rule_id}' is disabled",
                line=idx,
                suggestion="Remove rule if no longer needed, or re-enable"
            ))
