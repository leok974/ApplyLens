# Phase 5.5 PR3: Policy Simulation Endpoint
# REST API for what-if policy simulation

from typing import Any, Literal

from fastapi import APIRouter, Body, Query
from pydantic import BaseModel, Field

from app.policy.sim import (
    simulate_rules,
    SimCase,
    SimResponse,
    generate_fixtures,
    generate_synthetic
)


router = APIRouter(prefix="/policy", tags=["policy"])


class PolicySimRequest(BaseModel):
    """Request model for policy simulation."""
    rules: list[dict[str, Any]]
    dataset: Literal["fixtures", "synthetic"] = Field(
        "fixtures",
        description="Dataset to simulate against"
    )
    synthetic_count: int = Field(
        100,
        ge=1,
        le=1000,
        description="Number of synthetic cases (if dataset=synthetic)"
    )
    seed: int = Field(
        1337,
        description="Random seed for deterministic results"
    )
    custom_cases: list[dict[str, Any]] | None = Field(
        None,
        description="Custom test cases (overrides dataset)"
    )


@router.post("/simulate", response_model=SimResponse)
async def simulate_policy(
    request: PolicySimRequest = Body(...)
) -> SimResponse:
    """
    Simulate policy rules against test cases.
    
    Performs what-if analysis to show:
    - Allow/deny/approval rates
    - Budget impact (cost, compute)
    - Which rules match which cases
    - Budget/threshold breaches
    - Sample examples
    
    Supports three data sources:
    1. **Fixtures**: Curated edge cases (~10 cases)
    2. **Synthetic**: Generated test data (100-1000 cases)
    3. **Custom**: User-provided test cases
    
    Returns detailed results and summary metrics.
    """
    # Generate or use custom cases
    if request.custom_cases:
        cases = [SimCase(**case) for case in request.custom_cases]
    elif request.dataset == "fixtures":
        cases = generate_fixtures()
    else:  # synthetic
        cases = generate_synthetic(
            count=request.synthetic_count,
            seed=request.seed
        )
    
    # Run simulation
    result = simulate_rules(
        rules=request.rules,
        cases=cases,
        seed=request.seed
    )
    
    return result


@router.get("/simulate/fixtures", response_model=list[dict[str, Any]])
async def get_fixtures() -> list[dict[str, Any]]:
    """
    Get the curated fixture test cases.
    
    Returns the standard set of edge cases used for policy testing.
    Useful for understanding what scenarios are tested.
    """
    fixtures = generate_fixtures()
    return [f.model_dump() for f in fixtures]


@router.post("/simulate/compare", response_model=dict[str, Any])
async def compare_simulations(
    rules_a: list[dict[str, Any]] = Body(..., embed=True),
    rules_b: list[dict[str, Any]] = Body(..., embed=True),
    dataset: Literal["fixtures", "synthetic"] = Query("fixtures"),
    synthetic_count: int = Query(100, ge=1, le=1000),
    seed: int = Query(1337)
) -> dict[str, Any]:
    """
    Compare two policy bundles side-by-side.
    
    Shows how decisions change between versions:
    - Cases that change from allow → deny (or vice versa)
    - Cases that now require approval
    - Budget impact differences
    - Rate changes
    
    Useful for understanding the impact of policy changes before deployment.
    """
    # Generate cases
    if dataset == "fixtures":
        cases = generate_fixtures()
    else:
        cases = generate_synthetic(count=synthetic_count, seed=seed)
    
    # Run both simulations
    result_a = simulate_rules(rules_a, cases, seed)
    result_b = simulate_rules(rules_b, cases, seed)
    
    # Compare results
    changes: list[dict[str, Any]] = []
    for case, res_a, res_b in zip(cases, result_a.results, result_b.results):
        if res_a.effect != res_b.effect:
            changes.append({
                "case_id": case.case_id,
                "before": res_a.effect,
                "after": res_b.effect,
                "before_rule": res_a.matched_rule,
                "after_rule": res_b.matched_rule,
                "context": case.context
            })
    
    # Calculate deltas
    allow_delta = result_b.summary.allow_rate - result_a.summary.allow_rate
    deny_delta = result_b.summary.deny_rate - result_a.summary.deny_rate
    approval_delta = result_b.summary.approval_rate - result_a.summary.approval_rate
    cost_delta = result_b.summary.estimated_cost - result_a.summary.estimated_cost
    
    return {
        "summary_a": result_a.summary.model_dump(),
        "summary_b": result_b.summary.model_dump(),
        "deltas": {
            "allow_rate": round(allow_delta, 3),
            "deny_rate": round(deny_delta, 3),
            "approval_rate": round(approval_delta, 3),
            "cost": round(cost_delta, 2)
        },
        "changes": changes,
        "total_changes": len(changes)
    }
