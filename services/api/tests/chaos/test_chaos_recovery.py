"""
Chaos Engineering Test Suite

This module contains integration tests that validate system resilience
under various failure scenarios using chaos engineering principles.

Tests verify:
1. Automatic recovery after failures
2. SLO compliance during chaos
3. Error handling and retry logic
4. Circuit breaker behavior
5. Graceful degradation

Usage:
    pytest services/api/tests/chaos/test_chaos_recovery.py -v
"""

import pytest
import time
from typing import List

from app.chaos.injector import (
    chaos_injector,
    ChaosType,
    ChaosException,
)


@pytest.fixture(autouse=True)
def enable_chaos():
    """Enable chaos injection for tests and clean up after."""
    chaos_injector.enable_experiment_mode()
    chaos_injector.reset_metrics()
    yield
    chaos_injector.disable_experiment_mode()
    chaos_injector.reset_metrics()


@pytest.fixture
def mock_api_call():
    """Mock external API call."""

    def _call(fail_count: int = 0):
        """
        Simulate API call that can fail.
        Args:
            fail_count: Number of times to fail before succeeding
        """
        call_count = 0

        def api_call():
            nonlocal call_count
            call_count += 1

            if call_count <= fail_count:
                raise ChaosException("API call failed")

            return {"status": "success", "data": "test"}

        return api_call

    return _call


@pytest.fixture
def mock_database_query():
    """Mock database query."""

    def _query(latency_ms: int = 0):
        """
        Simulate database query with optional latency.
        Args:
            latency_ms: Latency to inject in milliseconds
        """

        def query():
            if latency_ms > 0:
                time.sleep(latency_ms / 1000)
            return [{"id": 1, "name": "test"}]

        return query

    return _query


class TestAPIOutageChaos:
    """Test system behavior during API outages."""

    def test_api_outage_injection(self):
        """Test that API outage chaos is properly injected."""
        with pytest.raises(ChaosException, match="API outage"):
            with chaos_injector.inject(ChaosType.API_OUTAGE):
                # This should raise exception
                pass

    def test_api_outage_with_probability(self):
        """Test probabilistic chaos injection."""
        success_count = 0
        failure_count = 0
        iterations = 100

        for _ in range(iterations):
            try:
                with chaos_injector.inject(ChaosType.API_OUTAGE, probability=0.5):
                    success_count += 1
            except ChaosException:
                failure_count += 1

        # With 50% probability, should have roughly 50 successes and 50 failures
        # Allow 20% variance (40-60 range)
        assert 40 <= success_count <= 60, f"Expected ~50 successes, got {success_count}"
        assert 40 <= failure_count <= 60, f"Expected ~50 failures, got {failure_count}"

    def test_api_outage_recovery_with_retry(self, mock_api_call):
        """Test automatic recovery using retry logic."""
        api_call = mock_api_call(fail_count=2)  # Fail twice, then succeed

        # Simulate retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = api_call()
                chaos_injector.record_recovery_attempt(
                    ChaosType.API_OUTAGE, success=True
                )
                assert result["status"] == "success"
                break
            except ChaosException:
                if attempt < max_retries - 1:
                    chaos_injector.record_recovery_attempt(
                        ChaosType.API_OUTAGE, success=False
                    )
                    time.sleep(0.1)  # Backoff
                else:
                    raise

        metrics = chaos_injector.get_metrics(ChaosType.API_OUTAGE)
        assert metrics[ChaosType.API_OUTAGE.value].recovery_attempts == 3
        assert metrics[ChaosType.API_OUTAGE.value].recovery_successes == 1

    def test_api_outage_circuit_breaker(self, mock_api_call):
        """Test circuit breaker pattern during sustained API outages."""
        api_call = mock_api_call(fail_count=100)  # Always fail

        failure_threshold = 5
        circuit_open = False
        consecutive_failures = 0

        for i in range(10):
            if circuit_open:
                # Circuit breaker open, don't attempt call
                break

            try:
                api_call()
                consecutive_failures = 0
            except ChaosException:
                consecutive_failures += 1

                if consecutive_failures >= failure_threshold:
                    circuit_open = True
                    chaos_injector.record_recovery_attempt(
                        ChaosType.API_OUTAGE, success=False
                    )

        # Circuit breaker should have opened after 5 failures
        assert circuit_open, "Circuit breaker should have opened"
        assert consecutive_failures >= failure_threshold

    def test_api_outage_custom_status_code(self):
        """Test API outage with custom HTTP status code."""
        with pytest.raises(ChaosException, match="HTTP 500"):
            with chaos_injector.inject(ChaosType.API_OUTAGE, status_code=500):
                pass


class TestLatencyChaos:
    """Test system behavior under high latency conditions."""

    def test_latency_injection(self):
        """Test that latency chaos is properly injected."""
        start = time.perf_counter()

        with chaos_injector.inject(ChaosType.HIGH_LATENCY, delay_ms=500):
            pass

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should take at least 500ms
        assert elapsed_ms >= 500, f"Expected ≥500ms delay, got {elapsed_ms:.2f}ms"

    def test_latency_impact_on_slo(self, mock_database_query):
        """Test that high latency affects SLO compliance."""
        query = mock_database_query(latency_ms=100)
        slo_target_ms = 1000  # P95 latency target
        latencies: List[float] = []

        for _ in range(100):
            start = time.perf_counter()

            try:
                with chaos_injector.inject(
                    ChaosType.HIGH_LATENCY, delay_ms=1500, probability=0.1
                ):
                    query()
            except Exception:
                pass

            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)

        # Calculate P95 latency
        latencies.sort()
        p95_latency = latencies[94]  # 95th percentile

        # With 10% of requests having 1500ms latency, P95 should exceed SLO
        assert (
            p95_latency > slo_target_ms
        ), f"P95 latency {p95_latency:.2f}ms should exceed {slo_target_ms}ms"

    def test_latency_timeout_handling(self, mock_database_query):
        """Test timeout handling during high latency."""
        query = mock_database_query(latency_ms=0)
        timeout_ms = 500

        start = time.perf_counter()
        timed_out = False

        try:
            with chaos_injector.inject(ChaosType.HIGH_LATENCY, delay_ms=1000):
                # Check if elapsed time exceeds timeout
                if (time.perf_counter() - start) * 1000 > timeout_ms:
                    timed_out = True
                    raise TimeoutError("Request timeout")

                query()
        except TimeoutError:
            timed_out = True

        assert timed_out, "Request should have timed out"

    def test_latency_graceful_degradation(self, mock_database_query):
        """Test graceful degradation under high latency (use cache instead)."""
        query = mock_database_query(latency_ms=0)
        cache = {"result": [{"id": 1, "name": "cached"}]}
        latency_threshold_ms = 800

        start = time.perf_counter()

        try:
            with chaos_injector.inject(ChaosType.HIGH_LATENCY, delay_ms=1000):
                elapsed_ms = (time.perf_counter() - start) * 1000

                if elapsed_ms > latency_threshold_ms:
                    # Use cache instead
                    result = cache["result"]
                else:
                    result = query()
        except Exception:
            result = cache["result"]

        # Should have used cache
        assert result == cache["result"], "Should have fallen back to cache"


class TestRateLimitChaos:
    """Test system behavior under rate limiting."""

    def test_rate_limit_injection(self):
        """Test that rate limit chaos is properly injected."""
        with pytest.raises(ChaosException, match="Rate limit"):
            with chaos_injector.inject(ChaosType.RATE_LIMIT):
                pass

    def test_rate_limit_backoff(self, mock_api_call):
        """Test exponential backoff during rate limiting."""
        api_call = mock_api_call(fail_count=2)

        backoff_seconds = 0.1
        max_retries = 3

        for attempt in range(max_retries):
            try:
                with chaos_injector.inject(
                    ChaosType.RATE_LIMIT, probability=0.0 if attempt == 2 else 1.0
                ):
                    result = api_call()
                    break
            except ChaosException:
                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = backoff_seconds * (2**attempt)
                    time.sleep(wait_time)
                else:
                    raise

        assert result["status"] == "success"

    def test_rate_limit_queue_requests(self):
        """Test request queuing during rate limiting."""
        request_queue = []

        # Try to send 10 requests
        for i in range(10):
            try:
                with chaos_injector.inject(ChaosType.RATE_LIMIT, probability=0.5):
                    request_queue.append({"id": i, "status": "sent"})
            except ChaosException:
                # Queue for later
                request_queue.append({"id": i, "status": "queued"})

        # Some requests should be queued
        queued_count = sum(1 for r in request_queue if r["status"] == "queued")
        assert queued_count > 0, "Some requests should have been queued"


class TestDatabaseErrorChaos:
    """Test system behavior during database errors."""

    def test_database_error_injection(self):
        """Test that database error chaos is properly injected."""
        with pytest.raises(ChaosException, match="Database"):
            with chaos_injector.inject(ChaosType.DATABASE_ERROR):
                pass

    def test_database_error_retry(self, mock_database_query):
        """Test retry logic for transient database errors."""
        query = mock_database_query(latency_ms=0)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Only inject error on first two attempts
                probability = 1.0 if attempt < 2 else 0.0
                with chaos_injector.inject(
                    ChaosType.DATABASE_ERROR, probability=probability
                ):
                    result = query()
                    break
            except ChaosException:
                if attempt < max_retries - 1:
                    time.sleep(0.1)
                else:
                    raise

        assert result is not None


class TestSLOComplianceDuringChaos:
    """Test that SLOs are maintained or gracefully degraded during chaos."""

    def test_error_rate_during_chaos(self):
        """Test error rate stays within acceptable bounds during chaos."""
        total_requests = 100
        successful_requests = 0
        error_budget = 0.02  # 2% error budget (98% SLO)

        for _ in range(total_requests):
            try:
                with chaos_injector.inject(ChaosType.API_OUTAGE, probability=0.015):
                    # Simulate request
                    successful_requests += 1
            except ChaosException:
                pass

        error_rate = 1 - (successful_requests / total_requests)

        # Error rate should be within error budget
        assert (
            error_rate <= error_budget
        ), f"Error rate {error_rate:.1%} exceeds budget {error_budget:.1%}"

    def test_latency_p95_during_chaos(self):
        """Test P95 latency stays within SLO during chaos."""
        latencies: List[float] = []
        slo_target_ms = 1500  # P95 latency SLO

        for _ in range(100):
            start = time.perf_counter()

            with chaos_injector.inject(
                ChaosType.HIGH_LATENCY, delay_ms=200, probability=0.05
            ):
                # Simulate request
                time.sleep(0.001)

            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)

        latencies.sort()
        p95_latency = latencies[94]

        # P95 should be within SLO
        assert (
            p95_latency <= slo_target_ms
        ), f"P95 latency {p95_latency:.2f}ms exceeds SLO {slo_target_ms}ms"

    def test_recovery_time_objective(self, mock_api_call):
        """Test that recovery happens within RTO."""
        api_call = mock_api_call(fail_count=1)
        rto_seconds = 5  # Recovery Time Objective

        start = time.perf_counter()
        recovered = False

        # Keep trying until recovery
        while (time.perf_counter() - start) < rto_seconds:
            try:
                api_call()
                recovered = True
                break
            except ChaosException:
                time.sleep(0.1)

        recovery_time = time.perf_counter() - start

        assert recovered, "System should have recovered within RTO"
        assert (
            recovery_time <= rto_seconds
        ), f"Recovery took {recovery_time:.2f}s, exceeds RTO {rto_seconds}s"


class TestChaosMetrics:
    """Test chaos metrics collection and reporting."""

    def test_metrics_collection(self):
        """Test that metrics are properly collected during chaos."""
        iterations = 10

        for _ in range(iterations):
            try:
                with chaos_injector.inject(ChaosType.API_OUTAGE, probability=0.5):
                    pass
            except ChaosException:
                pass

        metrics = chaos_injector.get_metrics(ChaosType.API_OUTAGE)
        assert ChaosType.API_OUTAGE.value in metrics

        m = metrics[ChaosType.API_OUTAGE.value]
        assert m.injections_attempted == iterations
        assert (
            0 < m.injections_successful < iterations
        )  # Some should succeed, some fail

    def test_recovery_metrics(self):
        """Test recovery metrics tracking."""
        chaos_injector.record_recovery_attempt(ChaosType.API_OUTAGE, success=True)
        chaos_injector.record_recovery_attempt(ChaosType.API_OUTAGE, success=True)
        chaos_injector.record_recovery_attempt(ChaosType.API_OUTAGE, success=False)

        metrics = chaos_injector.get_metrics(ChaosType.API_OUTAGE)
        m = metrics[ChaosType.API_OUTAGE.value]

        assert m.recovery_attempts == 3
        assert m.recovery_successes == 2
        assert abs(m.recovery_rate - 0.666) < 0.01  # ~66.7%

    def test_chaos_report_generation(self):
        """Test chaos experiment report generation."""
        # Execute some chaos
        for _ in range(5):
            try:
                with chaos_injector.inject(ChaosType.API_OUTAGE):
                    pass
            except ChaosException:
                pass

        chaos_injector.record_recovery_attempt(ChaosType.API_OUTAGE, success=True)

        report = chaos_injector.generate_report()

        assert "Chaos Engineering Report" in report
        assert "api_outage" in report
        assert "Recovery Rate" in report
        assert "Injections" in report


class TestChaosIntegration:
    """Integration tests combining multiple chaos types."""

    def test_combined_chaos_api_and_latency(self, mock_api_call):
        """Test system under combined API outage and latency chaos."""
        api_call = mock_api_call(fail_count=0)

        total_requests = 50
        successful_requests = 0
        latencies: List[float] = []

        for _ in range(total_requests):
            start = time.perf_counter()

            try:
                with chaos_injector.inject(ChaosType.API_OUTAGE, probability=0.05):
                    with chaos_injector.inject(
                        ChaosType.HIGH_LATENCY, delay_ms=100, probability=0.1
                    ):
                        api_call()
                        successful_requests += 1
            except ChaosException:
                pass

            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)

        # System should handle combined chaos gracefully
        success_rate = successful_requests / total_requests
        assert (
            success_rate >= 0.90
        ), f"Success rate {success_rate:.1%} too low under combined chaos"

        latencies.sort()
        p95_latency = latencies[int(len(latencies) * 0.95)]
        assert (
            p95_latency < 500
        ), f"P95 latency {p95_latency:.2f}ms too high under combined chaos"

    def test_cascading_failure_prevention(self, mock_api_call, mock_database_query):
        """Test that failures don't cascade across services."""
        api_call = mock_api_call(fail_count=0)
        db_query = mock_database_query(latency_ms=0)

        # API fails, but database should still work
        api_failed = False
        db_succeeded = False

        try:
            with chaos_injector.inject(ChaosType.API_OUTAGE, probability=1.0):
                api_call()
        except ChaosException:
            api_failed = True

        try:
            # Database should not be affected
            db_query()
            db_succeeded = True
        except Exception:
            pass

        assert api_failed, "API should have failed"
        assert db_succeeded, "Database should have succeeded despite API failure"


@pytest.mark.asyncio
class TestChaosScheduler:
    """Test chaos scheduler for automated experiments."""

    async def test_scheduler_basic(self):
        """Test basic chaos scheduling."""
        from app.chaos.injector import chaos_scheduler

        # Schedule short experiment
        chaos_scheduler.schedule(
            chaos_type=ChaosType.HIGH_LATENCY,
            interval_seconds=2,
            duration_seconds=1,
            delay_ms=100,
        )

        # Verify experiment was scheduled
        assert len(chaos_scheduler._scheduled_experiments) == 1

        exp = chaos_scheduler._scheduled_experiments[0]
        assert exp["chaos_type"] == ChaosType.HIGH_LATENCY
        assert exp["interval_seconds"] == 2
        assert exp["duration_seconds"] == 1
