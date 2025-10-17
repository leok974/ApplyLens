"""Guard subsystem for planner regression detection and auto-rollback.

Monitors V1 vs V2 performance and automatically triggers rollback
when regressions are detected.
"""

__all__ = ["RegressionDetector"]

from .regression_detector import RegressionDetector
