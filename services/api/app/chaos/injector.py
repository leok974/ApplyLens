"""
Chaos Engineering Injection Framework

This module provides utilities for injecting controlled failures into the system
to validate resilience, automatic recovery, and SLO compliance.

Usage:
    from app.chaos.injector import chaos_injector, ChaosType

    # Inject API failure
    with chaos_injector.inject(ChaosType.API_OUTAGE, probability=0.3):
        result = external_api_call()

    # Inject latency
    with chaos_injector.inject(ChaosType.HIGH_LATENCY, delay_ms=500):
        result = database_query()
"""

import asyncio
import logging
import random
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChaosType(Enum):
    """Types of chaos that can be injected."""

    API_OUTAGE = "api_outage"
    HIGH_LATENCY = "high_latency"
    DATABASE_ERROR = "database_error"
    NETWORK_PARTITION = "network_partition"
    MEMORY_PRESSURE = "memory_pressure"
    CPU_SPIKE = "cpu_spike"
    DISK_FULL = "disk_full"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"


class ChaosException(Exception):
    """Exception raised during chaos injection."""

    pass


@dataclass
class ChaosConfig:
    """Configuration for chaos injection."""

    chaos_type: ChaosType
    probability: float = 1.0  # Probability of injection (0.0-1.0)
    duration_seconds: Optional[float] = None  # Duration of chaos (None = one-time)
    delay_ms: Optional[int] = None  # Delay to inject in milliseconds
    error_message: Optional[str] = None  # Custom error message
    status_code: Optional[int] = None  # HTTP status code for API errors
    enabled: bool = True  # Whether chaos is enabled
    target_services: Optional[List[str]] = None  # Services to target (None = all)


@dataclass
class ChaosMetrics:
    """Metrics collected during chaos experiments."""

    chaos_type: ChaosType
    start_time: datetime
    end_time: Optional[datetime] = None
    injections_attempted: int = 0
    injections_successful: int = 0
    errors_raised: int = 0
    recovery_attempts: int = 0
    recovery_successes: int = 0
    average_impact_ms: float = 0.0

    @property
    def duration(self) -> Optional[timedelta]:
        """Get duration of chaos experiment."""
        if self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def success_rate(self) -> float:
        """Get success rate of injections."""
        if self.injections_attempted == 0:
            return 0.0
        return self.injections_successful / self.injections_attempted

    @property
    def recovery_rate(self) -> float:
        """Get recovery success rate."""
        if self.recovery_attempts == 0:
            return 0.0
        return self.recovery_successes / self.recovery_attempts


class ChaosInjector:
    """
    Central coordinator for chaos injection experiments.

    This class manages chaos experiments, tracks metrics, and provides
    context managers for controlled failure injection.
    """

    def __init__(self):
        self._active_chaos: Dict[ChaosType, ChaosConfig] = {}
        self._metrics: Dict[ChaosType, ChaosMetrics] = {}
        self._global_enabled: bool = False  # Safety: disabled by default
        self._experiment_mode: bool = False  # Only enabled during tests

    def enable_experiment_mode(self):
        """Enable chaos injection (only for testing)."""
        self._experiment_mode = True
        self._global_enabled = True
        logger.warning("Chaos injection ENABLED - experiment mode active")

    def disable_experiment_mode(self):
        """Disable chaos injection."""
        self._experiment_mode = False
        self._global_enabled = False
        self._active_chaos.clear()
        logger.info("Chaos injection DISABLED")

    def is_enabled(self) -> bool:
        """Check if chaos injection is globally enabled."""
        return self._global_enabled and self._experiment_mode

    @contextmanager
    def inject(self, chaos_type: ChaosType, **kwargs):
        """
        Context manager for injecting chaos.

        Args:
            chaos_type: Type of chaos to inject
            **kwargs: Configuration parameters (probability, delay_ms, etc.)

        Example:
            with chaos_injector.inject(ChaosType.API_OUTAGE, probability=0.5):
                result = api_call()
        """
        if not self.is_enabled():
            # Chaos injection disabled, pass through
            yield
            return

        config = ChaosConfig(chaos_type=chaos_type, **kwargs)

        # Check probability
        if random.random() > config.probability:
            # Skip injection this time
            yield
            return

        # Initialize metrics if first injection
        if chaos_type not in self._metrics:
            self._metrics[chaos_type] = ChaosMetrics(
                chaos_type=chaos_type, start_time=datetime.utcnow()
            )

        metrics = self._metrics[chaos_type]
        metrics.injections_attempted += 1

        try:
            # Store active chaos config
            self._active_chaos[chaos_type] = config

            # Inject chaos
            start = time.perf_counter()
            self._execute_injection(config)
            impact_ms = (time.perf_counter() - start) * 1000

            metrics.injections_successful += 1
            metrics.average_impact_ms = (
                metrics.average_impact_ms * (metrics.injections_successful - 1)
                + impact_ms
            ) / metrics.injections_successful

            logger.warning(
                f"Chaos injected: {chaos_type.value}, "
                f"impact: {impact_ms:.2f}ms, "
                f"probability: {config.probability}"
            )

            yield

        finally:
            # Clean up
            if chaos_type in self._active_chaos:
                del self._active_chaos[chaos_type]

    def _execute_injection(self, config: ChaosConfig):
        """Execute the chaos injection based on configuration."""

        if config.chaos_type == ChaosType.API_OUTAGE:
            # Simulate API outage with HTTP error
            status_code = config.status_code or 503
            raise ChaosException(
                config.error_message or f"Chaos: API outage (HTTP {status_code})"
            )

        elif config.chaos_type == ChaosType.HIGH_LATENCY:
            # Inject artificial delay
            delay_seconds = (config.delay_ms or 1000) / 1000
            time.sleep(delay_seconds)

        elif config.chaos_type == ChaosType.DATABASE_ERROR:
            # Simulate database error
            raise ChaosException(
                config.error_message or "Chaos: Database connection failed"
            )

        elif config.chaos_type == ChaosType.RATE_LIMIT:
            # Simulate rate limiting
            status_code = config.status_code or 429
            raise ChaosException(
                config.error_message
                or f"Chaos: Rate limit exceeded (HTTP {status_code})"
            )

        elif config.chaos_type == ChaosType.TIMEOUT:
            # Simulate timeout
            raise TimeoutError(config.error_message or "Chaos: Request timeout")

        elif config.chaos_type == ChaosType.NETWORK_PARTITION:
            # Simulate network partition
            raise ConnectionError(config.error_message or "Chaos: Network partition")

        else:
            logger.warning(f"Unimplemented chaos type: {config.chaos_type}")

    def record_recovery_attempt(self, chaos_type: ChaosType, success: bool):
        """Record a recovery attempt after chaos injection."""
        if chaos_type not in self._metrics:
            return

        metrics = self._metrics[chaos_type]
        metrics.recovery_attempts += 1
        if success:
            metrics.recovery_successes += 1

        logger.info(
            f"Recovery attempt for {chaos_type.value}: "
            f"{'SUCCESS' if success else 'FAILED'} "
            f"(rate: {metrics.recovery_rate:.1%})"
        )

    def get_metrics(
        self, chaos_type: Optional[ChaosType] = None
    ) -> Dict[str, ChaosMetrics]:
        """Get metrics for chaos experiments."""
        if chaos_type:
            return {chaos_type.value: self._metrics.get(chaos_type)}
        return {ct.value: m for ct, m in self._metrics.items()}

    def reset_metrics(self):
        """Reset all metrics."""
        self._metrics.clear()
        logger.info("Chaos metrics reset")

    def generate_report(self) -> str:
        """Generate a human-readable chaos experiment report."""
        if not self._metrics:
            return "No chaos experiments executed"

        lines = ["Chaos Engineering Report", "=" * 50, ""]

        for chaos_type, metrics in self._metrics.items():
            lines.append(f"Chaos Type: {chaos_type.value}")
            lines.append(f"  Duration: {metrics.duration}")
            lines.append(
                f"  Injections: {metrics.injections_successful}/{metrics.injections_attempted}"
            )
            lines.append(f"  Success Rate: {metrics.success_rate:.1%}")
            lines.append(f"  Average Impact: {metrics.average_impact_ms:.2f}ms")
            lines.append(f"  Recovery Rate: {metrics.recovery_rate:.1%}")
            lines.append(
                f"  Recovery Attempts: {metrics.recovery_successes}/{metrics.recovery_attempts}"
            )
            lines.append("")

        return "\n".join(lines)


# Global singleton instance
chaos_injector = ChaosInjector()


def inject_api_outage(probability: float = 1.0, status_code: int = 503):
    """
    Decorator to inject API outage chaos into a function.

    Example:
        @inject_api_outage(probability=0.3)
        def fetch_data():
            return requests.get("https://api.example.com/data")
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with chaos_injector.inject(
                ChaosType.API_OUTAGE, probability=probability, status_code=status_code
            ):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def inject_latency(delay_ms: int = 1000, probability: float = 1.0):
    """
    Decorator to inject latency chaos into a function.

    Example:
        @inject_latency(delay_ms=500, probability=0.5)
        def query_database():
            return db.query("SELECT * FROM users")
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with chaos_injector.inject(
                ChaosType.HIGH_LATENCY, delay_ms=delay_ms, probability=probability
            ):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def inject_rate_limit(probability: float = 1.0, status_code: int = 429):
    """
    Decorator to inject rate limiting chaos into a function.

    Example:
        @inject_rate_limit(probability=0.2)
        def call_external_api():
            return api.get_data()
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with chaos_injector.inject(
                ChaosType.RATE_LIMIT, probability=probability, status_code=status_code
            ):
                return func(*args, **kwargs)

        return wrapper

    return decorator


class ChaosScheduler:
    """
    Schedule chaos experiments to run at specific times or intervals.

    This allows for automated, continuous chaos testing in production-like environments.
    """

    def __init__(self):
        self._scheduled_experiments: List[Dict[str, Any]] = []

    def schedule(
        self,
        chaos_type: ChaosType,
        interval_seconds: int,
        duration_seconds: int,
        **chaos_kwargs,
    ):
        """
        Schedule a recurring chaos experiment.

        Args:
            chaos_type: Type of chaos to inject
            interval_seconds: How often to run the experiment
            duration_seconds: How long each experiment should last
            **chaos_kwargs: Additional chaos configuration
        """
        experiment = {
            "chaos_type": chaos_type,
            "interval_seconds": interval_seconds,
            "duration_seconds": duration_seconds,
            "chaos_kwargs": chaos_kwargs,
            "last_run": None,
            "next_run": datetime.utcnow() + timedelta(seconds=interval_seconds),
        }
        self._scheduled_experiments.append(experiment)
        logger.info(
            f"Scheduled chaos experiment: {chaos_type.value} "
            f"every {interval_seconds}s for {duration_seconds}s"
        )

    async def run(self):
        """Run the chaos scheduler (infinite loop)."""
        logger.info("Chaos scheduler started")

        while True:
            now = datetime.utcnow()

            for experiment in self._scheduled_experiments:
                if now >= experiment["next_run"]:
                    # Time to run experiment
                    logger.info(
                        f"Running chaos experiment: {experiment['chaos_type'].value}"
                    )

                    # Enable chaos for duration
                    chaos_injector.enable_experiment_mode()

                    # Wait for duration
                    await asyncio.sleep(experiment["duration_seconds"])

                    # Disable chaos
                    chaos_injector.disable_experiment_mode()

                    # Schedule next run
                    experiment["last_run"] = now
                    experiment["next_run"] = now + timedelta(
                        seconds=experiment["interval_seconds"]
                    )

                    logger.info(
                        f"Chaos experiment complete: {experiment['chaos_type'].value}, "
                        f"next run: {experiment['next_run']}"
                    )

            # Check every 10 seconds
            await asyncio.sleep(10)


# Global scheduler instance
chaos_scheduler = ChaosScheduler()
