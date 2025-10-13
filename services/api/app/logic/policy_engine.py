"""
Policy Engine for Email Automation

Evaluates JSON-based policies against email objects to propose actions.
Supports conditional logic (all/any), multiple operators, and "now" placeholder resolution.
"""

import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

# Supported operators for policy conditions
OPS = {
    "=": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: (a is not None and b is not None and a > b),
    ">=": lambda a, b: (a is not None and b is not None and a >= b),
    "<": lambda a, b: (a is not None and b is not None and a < b),
    "<=": lambda a, b: (a is not None and b is not None and a <= b),
    "contains": lambda a, b: (
        a is not None
        and b is not None
        and (b in a if hasattr(a, "__contains__") else False)
    ),
    "in": lambda a, b: (
        a is not None
        and b is not None
        and (
            # If a is a list, check if any element is in b
            any(item in b for item in a)
            if isinstance(a, list)
            # Otherwise check if a is in b
            else a in b
        )
    ),
    "regex": lambda a, b: (
        a is not None and b is not None and re.search(str(b), str(a), re.I) is not None
    ),
}


def _get(field: str, obj: Dict[str, Any]) -> Any:
    """
    Get nested field value from object using dot notation.
    Example: _get("features.spam_score", obj) -> obj["features"]["spam_score"]
    """
    cur = obj
    for part in field.split("."):
        if cur is None:
            return None
        cur = cur.get(part)
    return cur


def _eval_clause(cl: Dict[str, Any], obj: Dict[str, Any]) -> bool:
    """
    Evaluate a single condition clause against an object.

    Args:
        cl: Condition clause with "field", "op", and "value" keys
        obj: Object to evaluate against

    Returns:
        True if condition matches, False otherwise

    Raises:
        ValueError: If operator is not supported
    """
    field, op, value = cl["field"], cl["op"], cl.get("value")
    left = _get(field, obj)
    fn = OPS.get(op)
    if not fn:
        raise ValueError(f"Unsupported op: {op}")
    # simple "now" placeholder is resolved earlier (router) for dates if needed
    return bool(fn(left, value))


def _eval_cond(cond: Dict[str, Any], obj: Dict[str, Any]) -> bool:
    """
    Recursively evaluate a condition (which may contain nested all/any logic).

    Args:
        cond: Condition dictionary with "all", "any", or leaf clause
        obj: Object to evaluate against

    Returns:
        True if condition matches, False otherwise
    """
    if "all" in cond:
        return all(
            _eval_clause(c, obj) if "field" in c else _eval_cond(c, obj)
            for c in cond["all"]
        )
    if "any" in cond:
        return any(
            _eval_clause(c, obj) if "field" in c else _eval_cond(c, obj)
            for c in cond["any"]
        )
    # single leaf clause
    return _eval_clause(cond, obj)


@dataclass
class ProposedAction:
    """Represents an action proposed by a policy evaluation."""

    email_id: str
    action: str
    policy_id: str
    confidence: float
    rationale: str
    params: Optional[dict] = None


def apply_policies(
    email: Dict[str, Any], policies: List[Dict[str, Any]], now_iso: Optional[str] = None
) -> List[ProposedAction]:
    """
    Apply all policies to a single email and return proposed actions.

    Args:
        email: Email object with id, category, risk_score, expires_at, etc.
        policies: List of policy dictionaries with "if" and "then" clauses
        now_iso: Current timestamp in ISO format for "now" placeholder resolution

    Returns:
        List of ProposedAction objects for policies that matched

    Example policy:
        {
            "id": "promo-expired-archive",
            "if": {
                "all": [
                    {"field": "category", "op": "=", "value": "promotions"},
                    {"field": "expires_at", "op": "<", "value": "now"}
                ]
            },
            "then": {
                "action": "archive",
                "confidence_min": 0.8,
                "rationale": "expired promotion"
            }
        }
    """

    # Helper to resolve "now" literals in policy values
    def resolve_value(v):
        if isinstance(v, str) and v.lower() == "now" and now_iso:
            return now_iso
        return v

    # Helper to recursively resolve "now" in condition tree
    def resolve_cond(c):
        if isinstance(c, dict) and "field" in c:
            c = c.copy()
            c["value"] = resolve_value(c.get("value"))
            return c
        if isinstance(c, dict) and ("all" in c or "any" in c):
            key = "all" if "all" in c else "any"
            return {key: [resolve_cond(x) for x in c[key]]}
        return c

    normalized = email.copy()
    out: List[ProposedAction] = []

    for p in policies:
        cond = p.get("if", {})
        # Resolve any 'value':'now' in conditions
        cond = resolve_cond(cond)

        # Evaluate condition against email
        if _eval_cond(cond, normalized):
            then = p.get("then", {})
            action = then.get("action")
            conf_min = then.get("confidence_min", 0.5)
            rationale = then.get("rationale", p.get("id", "policy"))

            out.append(
                ProposedAction(
                    email_id=email["id"],
                    action=action,
                    policy_id=p.get("id", "policy"),
                    confidence=max(conf_min, 0.5),
                    rationale=rationale,
                    params=then.get("params", {}),
                )
            )

    return out
