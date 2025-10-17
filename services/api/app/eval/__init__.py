"""
Eval harness for agent quality assurance.

This package provides offline evaluation capabilities:
- Golden tasks: Representative test cases per agent
- Judges: Automated scoring of agent outputs
- Invariants: Must-never-regress rules
- Runner: Execute eval suites and export results
"""

from .models import EvalTask, EvalResult, Judge, Invariant
from .runner import EvalRunner

__all__ = [
    "EvalTask",
    "EvalResult",
    "Judge",
    "Invariant",
    "EvalRunner",
]
