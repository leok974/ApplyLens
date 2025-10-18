# Phase 5.5 PR3: Policy Simulation Engine
# What-if analysis for policy decisions against fixtures and recent runs

import random
from datetime import datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel


class SimCase(BaseModel):
    """A single simulation test case."""
    case_id: str
    agent: str
    action: str
    context: dict[str, Any]  # Input data for policy evaluation
    expected_effect: str | None = None  # For fixtures with known outcomes


class SimResult(BaseModel):
    """Result of simulating one case."""
    case_id: str
    matched_rule: str | None
    effect: Literal["allow", "deny", "needs_approval"] | None
    reason: str | None
    budget: dict[str, Any] | None = None


class SimSummary(BaseModel):
    """Summary of simulation run."""
    total_cases: int
    allow_count: int
    deny_count: int
    approval_count: int
    no_match_count: int
    allow_rate: float
    deny_rate: float
    approval_rate: float
    no_match_rate: float
    estimated_cost: float
    estimated_compute: int
    breaches: list[str] = []  # Budget/threshold breaches


class SimResponse(BaseModel):
    """Complete simulation response."""
    summary: SimSummary
    results: list[SimResult]
    examples: list[dict[str, Any]] = []  # Sample cases showing changes


def simulate_rules(
    rules: list[dict[str, Any]],
    cases: list[SimCase],
    seed: int = 1337
) -> SimResponse:
    """
    Simulate policy rules against test cases.
    
    Args:
        rules: List of policy rules to evaluate
        cases: List of test cases to simulate
        seed: Random seed for determinism
    
    Returns:
        SimResponse with summary and detailed results
    """
    random.seed(seed)
    
    results: list[SimResult] = []
    allow_count = 0
    deny_count = 0
    approval_count = 0
    no_match_count = 0
    total_cost = 0.0
    total_compute = 0
    breaches: list[str] = []
    
    # Sort rules by priority (higher first)
    sorted_rules = sorted(
        [r for r in rules if r.get("enabled", True)],
        key=lambda r: r.get("priority", 50),
        reverse=True
    )
    
    for case in cases:
        # Find first matching rule
        matched_rule = None
        effect = None
        reason = None
        budget = None
        
        for rule in sorted_rules:
            if _rule_matches(rule, case):
                matched_rule = rule.get("id")
                effect = rule.get("effect")
                reason = rule.get("reason")
                budget = rule.get("budget")
                break
        
        # Count by effect
        if effect == "allow":
            allow_count += 1
        elif effect == "deny":
            deny_count += 1
        elif effect == "needs_approval":
            approval_count += 1
            if budget:
                total_cost += budget.get("cost", 0)
                total_compute += budget.get("compute", 0)
        else:
            no_match_count += 1
        
        results.append(SimResult(
            case_id=case.case_id,
            matched_rule=matched_rule,
            effect=effect,
            reason=reason,
            budget=budget
        ))
    
    # Check for breaches
    if total_cost > 1000:
        breaches.append(f"budget.cost: ${total_cost:.2f} > $1000")
    if total_compute > 100:
        breaches.append(f"budget.compute: {total_compute} > 100 units")
    
    # Calculate rates
    total_cases = len(cases)
    allow_rate = allow_count / total_cases if total_cases > 0 else 0
    deny_rate = deny_count / total_cases if total_cases > 0 else 0
    approval_rate = approval_count / total_cases if total_cases > 0 else 0
    no_match_rate = no_match_count / total_cases if total_cases > 0 else 0
    
    # Generate examples (sample of interesting cases)
    examples = _generate_examples(cases, results)
    
    return SimResponse(
        summary=SimSummary(
            total_cases=total_cases,
            allow_count=allow_count,
            deny_count=deny_count,
            approval_count=approval_count,
            no_match_count=no_match_count,
            allow_rate=round(allow_rate, 3),
            deny_rate=round(deny_rate, 3),
            approval_rate=round(approval_rate, 3),
            no_match_rate=round(no_match_rate, 3),
            estimated_cost=round(total_cost, 2),
            estimated_compute=total_compute,
            breaches=breaches
        ),
        results=results,
        examples=examples
    )


def _rule_matches(rule: dict[str, Any], case: SimCase) -> bool:
    """
    Check if a rule matches a test case.
    
    Args:
        rule: Policy rule to evaluate
        case: Test case with context
    
    Returns:
        True if rule matches the case
    """
    # Check agent and action match
    if rule.get("agent") != case.agent:
        return False
    if rule.get("action") != case.action:
        return False
    
    # Check conditions
    conditions = rule.get("conditions", {})
    if not conditions:
        # No conditions means it matches
        return True
    
    # Evaluate each condition
    for key, expected_value in conditions.items():
        # Extract operator and field name
        op = None
        field = key
        
        for operator in [">=", "<=", ">", "<", "==", "!="]:
            if key.startswith(operator):
                op = operator
                field = key[len(operator):]
                break
        
        # Get actual value from context
        actual_value = case.context.get(field)
        
        if actual_value is None:
            # Field not in context, condition fails
            return False
        
        # Evaluate condition
        if op == ">=":
            if not (actual_value >= expected_value):
                return False
        elif op == "<=":
            if not (actual_value <= expected_value):
                return False
        elif op == ">":
            if not (actual_value > expected_value):
                return False
        elif op == "<":
            if not (actual_value < expected_value):
                return False
        elif op == "==":
            if actual_value != expected_value:
                return False
        elif op == "!=":
            if actual_value == expected_value:
                return False
        else:
            # No operator, do equality check
            if actual_value != expected_value:
                return False
    
    return True


def _generate_examples(
    cases: list[SimCase],
    results: list[SimResult]
) -> list[dict[str, Any]]:
    """Generate example cases showing interesting outcomes."""
    examples: list[dict[str, Any]] = []
    
    # Find examples of each effect
    for effect in ["allow", "deny", "needs_approval"]:
        for case, result in zip(cases, results):
            if result.effect == effect and len(examples) < 10:
                examples.append({
                    "case_id": case.case_id,
                    "effect": result.effect,
                    "matched_rule": result.matched_rule,
                    "reason": result.reason,
                    "context": case.context
                })
                break
    
    return examples


def generate_fixtures() -> list[SimCase]:
    """
    Generate curated fixture test cases.
    
    These are edge cases and common scenarios for testing policies.
    """
    return [
        # High risk inbox scenarios
        SimCase(
            case_id="inbox_high_risk_new_domain",
            agent="inbox.triage",
            action="quarantine",
            context={
                "risk_score": 95,
                "domain_seen_days": 5,
                "category": "phishing",
                "confidence": 0.98
            }
        ),
        SimCase(
            case_id="inbox_high_risk_known_domain",
            agent="inbox.triage",
            action="quarantine",
            context={
                "risk_score": 92,
                "domain_seen_days": 180,
                "category": "spam",
                "confidence": 0.85
            }
        ),
        SimCase(
            case_id="inbox_low_risk",
            agent="inbox.triage",
            action="quarantine",
            context={
                "risk_score": 25,
                "domain_seen_days": 365,
                "category": "newsletter",
                "confidence": 0.90
            }
        ),
        # Knowledge scenarios
        SimCase(
            case_id="knowledge_full_reindex",
            agent="knowledge.search",
            action="reindex",
            context={
                "index_size_gb": 100,
                "num_documents": 1000000,
                "estimated_cost": 50,
                "estimated_hours": 4
            }
        ),
        SimCase(
            case_id="knowledge_small_reindex",
            agent="knowledge.search",
            action="reindex",
            context={
                "index_size_gb": 1,
                "num_documents": 10000,
                "estimated_cost": 2,
                "estimated_hours": 0.5
            }
        ),
        # Planner scenarios
        SimCase(
            case_id="planner_deploy_canary",
            agent="planner.deploy",
            action="deploy",
            context={
                "version": "v1.2.3",
                "canary_pct": 10,
                "risk_level": "medium"
            }
        ),
        SimCase(
            case_id="planner_rollback_critical",
            agent="planner.deploy",
            action="rollback",
            context={
                "from_version": "v1.2.3",
                "to_version": "v1.2.2",
                "severity": "sev1",
                "reason": "Critical regression"
            }
        ),
        # Edge cases
        SimCase(
            case_id="edge_missing_fields",
            agent="inbox.triage",
            action="escalate",
            context={
                # Minimal context
                "timestamp": datetime.now().isoformat()
            }
        ),
        SimCase(
            case_id="edge_extreme_values",
            agent="inbox.triage",
            action="quarantine",
            context={
                "risk_score": 100,
                "confidence": 1.0,
                "domain_seen_days": 0
            }
        ),
    ]


def generate_synthetic(count: int = 100, seed: int = 1337) -> list[SimCase]:
    """
    Generate synthetic test cases for simulation.
    
    Args:
        count: Number of cases to generate
        seed: Random seed for reproducibility
    
    Returns:
        List of synthetic test cases
    """
    random.seed(seed)
    cases: list[SimCase] = []
    
    agents = ["inbox.triage", "knowledge.search", "planner.deploy"]
    actions = {
        "inbox.triage": ["quarantine", "escalate", "archive"],
        "knowledge.search": ["reindex", "update", "delete"],
        "planner.deploy": ["deploy", "rollback", "adjust"]
    }
    
    for i in range(count):
        agent = random.choice(agents)
        action = random.choice(actions[agent])
        
        # Generate context based on agent
        if agent == "inbox.triage":
            context = {
                "risk_score": random.randint(0, 100),
                "domain_seen_days": random.randint(0, 365),
                "confidence": round(random.uniform(0.5, 1.0), 2),
                "category": random.choice(["spam", "phishing", "newsletter", "transactional"])
            }
        elif agent == "knowledge.search":
            context = {
                "index_size_gb": random.randint(1, 500),
                "num_documents": random.randint(1000, 10000000),
                "estimated_cost": round(random.uniform(1, 200), 2),
                "estimated_hours": round(random.uniform(0.1, 12), 1)
            }
        else:  # planner.deploy
            context = {
                "version": f"v1.{random.randint(0, 10)}.{random.randint(0, 20)}",
                "canary_pct": random.choice([0, 10, 25, 50, 100]),
                "risk_level": random.choice(["low", "medium", "high"])
            }
        
        cases.append(SimCase(
            case_id=f"synthetic_{i:04d}",
            agent=agent,
            action=action,
            context=context
        ))
    
    return cases
