#!/usr/bin/env python3
"""
CLI script for running quality gates in CI.

Usage:
    python -m app.eval.run_gates [--agent AGENT] [--fail-on-warning]

Examples:
    # Check all agents
    python -m app.eval.run_gates
    
    # Check specific agent
    python -m app.eval.run_gates --agent inbox.triage
    
    # Fail on warnings (default only fails on critical)
    python -m app.eval.run_gates --fail-on-warning

Exit Codes:
    0 - All gates passed
    1 - Critical violations found
    2 - Warnings found (only with --fail-on-warning)
"""
import argparse
import sys
from sqlalchemy.orm import Session
from ..db import SessionLocal
from .budgets import GateEvaluator, format_gate_report


def main():
    parser = argparse.ArgumentParser(
        description="Run quality gates for agent evaluation"
    )
    parser.add_argument(
        "--agent",
        type=str,
        help="Specific agent to evaluate (default: all)",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=7,
        help="Days to evaluate (default: 7)",
    )
    parser.add_argument(
        "--baseline-days",
        type=int,
        default=14,
        help="Days for baseline comparison (default: 14)",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Fail build on warnings (default: only fail on critical)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    
    args = parser.parse_args()
    
    db: Session = SessionLocal()
    
    try:
        evaluator = GateEvaluator(db)
        
        if args.agent:
            # Single agent evaluation
            result = evaluator.evaluate_agent(
                agent=args.agent,
                lookback_days=args.lookback_days,
                baseline_days=args.baseline_days,
            )
        else:
            # All agents evaluation
            result = evaluator.evaluate_all_agents(
                lookback_days=args.lookback_days,
                baseline_days=args.baseline_days,
            )
        
        # Output
        if args.format == "json":
            import json
            # Convert violations to dicts
            if "results" in result:
                for agent_result in result["results"].values():
                    agent_result["violations"] = [
                        {
                            "agent": v.agent,
                            "budget_type": v.budget_type,
                            "threshold": v.threshold,
                            "actual": v.actual,
                            "severity": v.severity,
                            "message": v.message,
                        }
                        for v in agent_result["violations"]
                    ]
                    # Remove budget object (not serializable)
                    if "budget" in agent_result:
                        del agent_result["budget"]
            else:
                result["violations"] = [
                    {
                        "agent": v.agent,
                        "budget_type": v.budget_type,
                        "threshold": v.threshold,
                        "actual": v.actual,
                        "severity": v.severity,
                        "message": v.message,
                    }
                    for v in result["violations"]
                ]
                if "budget" in result:
                    del result["budget"]
            
            print(json.dumps(result, indent=2))
        else:
            # Text format
            report = format_gate_report(result)
            print(report)
        
        # Exit code
        if result["passed"]:
            sys.exit(0)
        
        # Check severity
        if "results" in result:
            # Multi-agent
            has_critical = result["critical_violations"] > 0
            has_warnings = result["total_violations"] > result["critical_violations"]
        else:
            # Single agent
            has_critical = any(v.severity == "critical" for v in result["violations"])
            has_warnings = any(v.severity in ("warning", "error") for v in result["violations"])
        
        if has_critical:
            sys.exit(1)
        elif has_warnings and args.fail_on_warning:
            sys.exit(2)
        else:
            sys.exit(0)
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
