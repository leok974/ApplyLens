"""
Policy engine for email automation

Evaluates JSON-based policies to determine what actions to take on emails.
Supports conditional logic (all/any) and various operators (=, !=, >, <, >=, <=, in).

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
    "confidence_min": 0.7,
    "notify": false
  }
}
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import operator


class PolicyEngine:
    """
    Evaluates policies against emails to recommend actions
    """
    
    OPERATORS = {
        "=": operator.eq,
        "==": operator.eq,
        "!=": operator.ne,
        ">": operator.gt,
        "<": operator.lt,
        ">=": operator.ge,
        "<=": operator.le,
        "in": lambda a, b: a in b,
        "not_in": lambda a, b: a not in b,
        "contains": lambda a, b: b in a if isinstance(a, str) else b in a,
        "regex": lambda a, b: bool(__import__('re').search(b, str(a))),
    }
    
    def __init__(self, policies: List[Dict[str, Any]]):
        """
        Initialize policy engine with a list of policies
        
        Args:
            policies: List of policy dicts (loaded from JSON/DB)
        """
        self.policies = policies
    
    def evaluate_condition(self, condition: Dict[str, Any], email: Dict[str, Any]) -> bool:
        """
        Evaluate a single condition against an email
        
        Args:
            condition: {"field": "category", "op": "=", "value": "promotions"}
            email: Email dict to check
            
        Returns:
            True if condition matches, False otherwise
        """
        field = condition.get("field")
        op_str = condition.get("op")
        expected_value = condition.get("value")
        
        # Get actual value from email
        actual_value = email.get(field)
        
        # Handle special values
        if expected_value == "now":
            expected_value = datetime.now()
        elif expected_value == "null":
            expected_value = None
        
        # Convert dates for comparison
        if field in ["received_at", "expires_at", "created_at"] and isinstance(actual_value, str):
            try:
                actual_value = datetime.fromisoformat(actual_value.replace("Z", "+00:00"))
            except:  # noqa: E722
                pass
        
        # Get operator function
        op_func = self.OPERATORS.get(op_str)
        if not op_func:
            raise ValueError(f"Unknown operator: {op_str}")
        
        # Evaluate
        try:
            return op_func(actual_value, expected_value)
        except Exception:
            # Comparison failed (e.g., None vs int)
            return False
    
    def evaluate_conditions(self, conditions: Dict[str, Any], email: Dict[str, Any]) -> bool:
        """
        Evaluate compound conditions (all/any)
        
        Args:
            conditions: {"all": [...]} or {"any": [...]}
            email: Email dict
            
        Returns:
            True if conditions match, False otherwise
        """
        if "all" in conditions:
            # All conditions must be true (AND logic)
            return all(
                self.evaluate_condition(cond, email) if "field" in cond 
                else self.evaluate_conditions(cond, email)
                for cond in conditions["all"]
            )
        elif "any" in conditions:
            # At least one condition must be true (OR logic)
            return any(
                self.evaluate_condition(cond, email) if "field" in cond
                else self.evaluate_conditions(cond, email)
                for cond in conditions["any"]
            )
        elif "field" in conditions:
            # Single condition
            return self.evaluate_condition(conditions, email)
        else:
            return False
    
    def evaluate_policy(self, policy: Dict[str, Any], email: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluate a single policy against an email
        
        Args:
            policy: Policy dict with "if" and "then" keys
            email: Email dict
            
        Returns:
            Action dict if policy matches, None otherwise
            
        Example return:
        {
            "policy_id": "promo-expired-archive",
            "action": "archive",
            "confidence": 0.9,
            "rationale": "Expired promotion (expires_at < now)",
            "params": {}
        }
        """
        # Check if conditions match
        if not self.evaluate_conditions(policy["if"], email):
            return None
        
        # Policy matched - return action
        action_spec = policy["then"]
        
        # Build rationale
        rationale = policy.get("description", f"Policy {policy['id']} matched")
        
        # Check confidence threshold
        email_confidence = email.get("confidence", 1.0)
        min_confidence = action_spec.get("confidence_min", 0.0)
        
        if email_confidence < min_confidence:
            # Email confidence too low for this action
            return None
        
        return {
            "policy_id": policy["id"],
            "action": action_spec["action"],
            "confidence": email_confidence,
            "rationale": rationale,
            "params": action_spec.get("params", {}),
            "notify": action_spec.get("notify", False),
        }
    
    def evaluate_all(self, email: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate all policies against an email
        
        Args:
            email: Email dict
            
        Returns:
            List of recommended actions (may be empty, or multiple if policies overlap)
        """
        actions = []
        
        for policy in self.policies:
            action = self.evaluate_policy(policy, email)
            if action:
                actions.append(action)
        
        return actions
    
    def evaluate_batch(self, emails: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Evaluate policies against multiple emails
        
        Args:
            emails: List of email dicts (must have 'id' field)
            
        Returns:
            Dict mapping email_id -> list of recommended actions
        """
        results = {}
        
        for email in emails:
            email_id = email.get("id")
            if not email_id:
                continue
            
            actions = self.evaluate_all(email)
            if actions:
                results[email_id] = actions
        
        return results


# Default policies (can be loaded from JSON file or database)
DEFAULT_POLICIES = [
    {
        "id": "promo-expired-archive",
        "description": "Archive expired promotions automatically",
        "if": {
            "all": [
                {"field": "category", "op": "=", "value": "promotions"},
                {"field": "expires_at", "op": "<", "value": "now"}
            ]
        },
        "then": {
            "action": "archive",
            "confidence_min": 0.7,
            "notify": False
        }
    },
    {
        "id": "risk-quarantine",
        "description": "Quarantine high-risk emails for review",
        "if": {
            "any": [
                {"field": "risk_score", "op": ">=", "value": 80}
            ]
        },
        "then": {
            "action": "quarantine",
            "confidence_min": 0.5,
            "notify": True
        }
    },
    {
        "id": "bill-reminder",
        "description": "Add reminder label to unpaid bills",
        "if": {
            "all": [
                {"field": "category", "op": "=", "value": "bills"},
                {"field": "labels", "op": "not_in", "value": "paid"}
            ]
        },
        "then": {
            "action": "label",
            "params": {"label": "needs_attention"},
            "confidence_min": 0.6,
            "notify": False
        }
    },
    {
        "id": "application-priority",
        "description": "Mark job applications as important",
        "if": {
            "all": [
                {"field": "category", "op": "=", "value": "applications"}
            ]
        },
        "then": {
            "action": "label",
            "params": {"label": "important"},
            "confidence_min": 0.8,
            "notify": False
        }
    },
    {
        "id": "old-promo-cleanup",
        "description": "Delete very old promotional emails",
        "if": {
            "all": [
                {"field": "category", "op": "=", "value": "promotions"},
                {"field": "received_at", "op": "<", "value": "30_days_ago"}  # Note: Need to handle this special value
            ]
        },
        "then": {
            "action": "delete",
            "confidence_min": 0.9,
            "notify": False
        }
    }
]


def load_policies_from_file(filepath: str) -> List[Dict[str, Any]]:
    """
    Load policies from JSON file
    
    Args:
        filepath: Path to JSON file with policies
        
    Returns:
        List of policy dicts
    """
    import json
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data.get("policies", [])


def create_default_engine() -> PolicyEngine:
    """
    Create policy engine with default policies
    
    Returns:
        Configured PolicyEngine instance
    """
    return PolicyEngine(DEFAULT_POLICIES)


# Example usage
if __name__ == "__main__":
    # Example: Test expired promo policy
    engine = create_default_engine()
    
    test_email = {
        "id": "test_1",
        "category": "promotions",
        "expires_at": "2025-10-01T00:00:00Z",  # In the past
        "confidence": 0.85,
    }
    
    actions = engine.evaluate_all(test_email)
    print(f"Recommended actions for expired promo: {actions}")
    
    # Example: Test high-risk email
    risky_email = {
        "id": "test_2",
        "risk_score": 92,
        "category": "security",
        "confidence": 0.9,
    }
    
    actions = engine.evaluate_all(risky_email)
    print(f"Recommended actions for high-risk email: {actions}")
