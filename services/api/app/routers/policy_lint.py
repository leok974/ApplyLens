# Phase 5.5 PR2: Policy Lint Endpoint
# REST API for linting policy rules

from typing import Any

from fastapi import APIRouter, Body
from pydantic import BaseModel

from app.policy.lint import lint_rules, LintResult, LintAnnotation


router = APIRouter(prefix="/policy", tags=["policy"])


class PolicyLintRequest(BaseModel):
    """Request model for linting policy rules."""
    rules: list[dict[str, Any]]


class PolicyLintResponse(BaseModel):
    """Response model for lint results."""
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    info: list[dict[str, Any]]
    summary: dict[str, int]
    passed: bool


@router.post("/lint", response_model=PolicyLintResponse)
async def lint_policy(
    request: PolicyLintRequest = Body(...)
) -> PolicyLintResponse:
    """
    Lint a list of policy rules.
    
    Performs static analysis to detect:
    - Duplicate rule IDs
    - Conflicting allow/deny rules
    - Missing or insufficient reasons
    - Unreachable rules (shadowed by higher priority)
    - Budget sanity checks (approval rules need budgets)
    - Invalid condition operators
    - Disabled rules
    
    Returns actionable annotations with severity levels.
    """
    # Run linter
    result: LintResult = lint_rules(request.rules)
    
    # Convert to response format
    return PolicyLintResponse(
        errors=[ann.model_dump() for ann in result.errors],
        warnings=[ann.model_dump() for ann in result.warnings],
        info=[ann.model_dump() for ann in result.info],
        summary={
            "total_rules": len(request.rules),
            "errors": len(result.errors),
            "warnings": len(result.warnings),
            "info": len(result.info),
            "total_issues": result.total_issues
        },
        passed=not result.has_errors
    )
