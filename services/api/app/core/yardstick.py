"""
Yardstick Policy Engine - Phase 4 Agentic Actions

A lightweight DSL for evaluating policy conditions over email context.

Grammar:
- all: [list of conditions] - AND logic
- any: [list of conditions] - OR logic
- not: {condition} - NOT logic
- Comparators: eq, neq, lt, lte, gt, gte, in, regex, exists

Example Policy:
{
  "all": [
    {"eq": ["category", "promo"]},
    {"lt": ["expires_at", "now"]}
  ]
}

Context Schema:
{
  "category": "promo",
  "risk_score": 45.2,
  "expires_at": "2025-01-15T00:00:00Z",
  "sender_domain": "example.com",
  "age_days": 3,
  "quarantined": false,
  ...
}
"""
import re
import operator
from datetime import datetime
from typing import Any, Dict, Callable


# Operator mapping
OPS: Dict[str, Callable] = {
    "eq": operator.eq,
    "neq": operator.ne,
    "lt": operator.lt,
    "lte": operator.le,
    "gt": operator.gt,
    "gte": operator.ge,
    "in": lambda a, b: a in b,
    "regex": lambda s, pat: re.search(pat, s or "") is not None,
    "exists": lambda v: v is not None,
}


def _resolve(key: Any, ctx: Dict[str, Any]) -> Any:
    """
    Resolve a value from context or return literal.
    
    Special values:
    - "now" -> current datetime
    - String key -> lookup in context
    - Other -> return as-is (literal)
    """
    if key == "now":
        return datetime.utcnow()
    if isinstance(key, str):
        return ctx.get(key)
    return key


def _cmp(node: list, ctx: Dict[str, Any]) -> bool:
    """
    Evaluate a comparator node.
    
    Node format: [operator, left, right]
    Example: ["eq", "category", "promo"]
    """
    op_name = node[0]
    if op_name not in OPS:
        raise ValueError(f"Unknown operator: {op_name}")
    
    op_func = OPS[op_name]
    a = _resolve(node[1], ctx)
    
    # Unary operators (exists)
    if len(node) == 2:
        return op_func(a)
    
    # Binary operators
    b = _resolve(node[2], ctx)
    
    # Handle datetime comparisons
    if isinstance(a, str) and isinstance(b, datetime):
        try:
            a = datetime.fromisoformat(a.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass
    elif isinstance(b, str) and isinstance(a, datetime):
        try:
            b = datetime.fromisoformat(b.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass
    
    return op_func(a, b)


def _eval(expr: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
    """
    Recursively evaluate a Yardstick expression.
    
    Args:
        expr: Policy condition expression (dict)
        ctx: Email context (dict)
    
    Returns:
        bool: True if condition matches
    """
    # Logical operators
    if "all" in expr:
        return all(_eval(x, ctx) for x in expr["all"])
    
    if "any" in expr:
        return any(_eval(x, ctx) for x in expr["any"])
    
    if "not" in expr:
        return not _eval(expr["not"], ctx)
    
    # Comparator node: {"gte": ["risk_score", 80]}
    if len(expr) != 1:
        raise ValueError(f"Invalid expression: {expr}")
    
    (op_name, args), = expr.items()
    return _cmp([op_name] + args, ctx)


def evaluate_policy(policy: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
    """
    Evaluate a policy against email context.
    
    Args:
        policy: Policy dict with "condition" key
        ctx: Email context dict
    
    Returns:
        bool: True if policy matches, False otherwise (including on error)
    
    Example:
        policy = {
            "condition": {
                "all": [
                    {"eq": ["category", "promo"]},
                    {"gte": ["risk_score", 80]}
                ]
            }
        }
        ctx = {"category": "promo", "risk_score": 85}
        evaluate_policy(policy, ctx)  # Returns True
    """
    try:
        return _eval(policy["condition"], ctx)
    except Exception as e:
        # Log error but don't crash - fail closed
        print(f"Policy evaluation error: {e}")
        return False


def validate_condition(condition: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate a policy condition syntax (doesn't evaluate, just checks structure).
    
    Args:
        condition: Policy condition dict
    
    Returns:
        (valid: bool, error_msg: str)
    """
    try:
        _validate_node(condition)
        return True, ""
    except ValueError as e:
        return False, str(e)


def _validate_node(node: Any) -> None:
    """Recursively validate condition node structure."""
    if not isinstance(node, dict):
        raise ValueError(f"Node must be dict, got {type(node)}")
    
    if "all" in node:
        if not isinstance(node["all"], list):
            raise ValueError("'all' must be a list")
        for child in node["all"]:
            _validate_node(child)
        return
    
    if "any" in node:
        if not isinstance(node["any"], list):
            raise ValueError("'any' must be a list")
        for child in node["any"]:
            _validate_node(child)
        return
    
    if "not" in node:
        _validate_node(node["not"])
        return
    
    # Comparator node
    if len(node) != 1:
        raise ValueError(f"Comparator node must have exactly one key, got: {node}")
    
    (op_name, args), = node.items()
    if op_name not in OPS:
        raise ValueError(f"Unknown operator: {op_name}")
    
    if not isinstance(args, list):
        raise ValueError(f"Operator args must be a list, got {type(args)}")
    
    # Check arity
    if op_name == "exists":
        if len(args) != 1:
            raise ValueError(f"'exists' requires 1 arg, got {len(args)}")
    else:
        if len(args) != 2:
            raise ValueError(f"'{op_name}' requires 2 args, got {len(args)}")
