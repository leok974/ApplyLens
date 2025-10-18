"""
Chaos Engineering Framework for ApplyLens

This module provides chaos engineering capabilities to test system resilience
under failure conditions. It includes:

- ChaosType: Enumeration of chaos types (API outage, latency, etc.)
- ChaosInjector: Main coordinator for chaos injection
- ChaosScheduler: Automated recurring chaos experiments
- Decorators: Convenience functions for chaos injection
- Metrics: Automatic collection and reporting

Usage:
    from app.chaos import chaos_injector, ChaosType

    # Enable chaos (only in tests!)
    chaos_injector.enable_experiment_mode()

    try:
        # Inject chaos
        with chaos_injector.inject(ChaosType.API_OUTAGE, probability=0.3):
            result = external_api_call()
    finally:
        chaos_injector.disable_experiment_mode()

Safety:
    Chaos injection is disabled by default. You must explicitly enable
    experiment mode before chaos will be injected.
"""

from .injector import (
    ChaosException,
    ChaosType,
    chaos_injector,
    chaos_scheduler,
    inject_api_outage,
    inject_latency,
    inject_rate_limit,
)

__all__ = [
    "chaos_injector",
    "chaos_scheduler",
    "ChaosType",
    "ChaosException",
    "inject_api_outage",
    "inject_latency",
    "inject_rate_limit",
]

__version__ = "1.0.0"
