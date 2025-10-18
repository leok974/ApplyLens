#!/usr/bin/env python3
"""
SLO Compliance Checker

Queries Prometheus to validate SLO compliance after chaos testing.
Checks error rate and P95 latency against defined targets.

Usage:
    python check_slo_compliance.py --environment staging --duration-minutes 10
    python check_slo_compliance.py --environment production --duration-minutes 5

Exit Codes:
    0: SLO compliance verified
    1: SLO violation detected
    2: Error querying Prometheus or invalid input
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import requests


class SLOComplianceChecker:
    """Check SLO compliance via Prometheus queries."""

    def __init__(self, prometheus_url: str, environment: str):
        """
        Initialize SLO compliance checker.

        Args:
            prometheus_url: Base URL for Prometheus API
            environment: Environment to check (staging, canary, production)
        """
        self.prometheus_url = prometheus_url.rstrip("/")
        self.environment = environment
        self.api_url = f"{self.prometheus_url}/api/v1/query"

    def query_prometheus(
        self, query: str, time: Optional[datetime] = None
    ) -> Optional[float]:
        """
        Query Prometheus and return the result value.

        Args:
            query: PromQL query string
            time: Optional timestamp for the query (default: now)

        Returns:
            Float value from Prometheus, or None if query failed
        """
        params = {"query": query}
        if time:
            params["time"] = time.isoformat()

        try:
            response = requests.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            if data["status"] != "success":
                print(f"❌ Prometheus query failed: {data.get('error', 'Unknown error')}")
                return None

            result = data["data"]["result"]
            if not result:
                print(f"⚠️  No data returned for query: {query}")
                return None

            # Extract the value from the result
            value = float(result[0]["value"][1])
            return value

        except requests.exceptions.RequestException as e:
            print(f"❌ Error querying Prometheus: {e}")
            return None
        except (KeyError, IndexError, ValueError) as e:
            print(f"❌ Error parsing Prometheus response: {e}")
            return None

    def check_error_rate(self, duration_minutes: int) -> Tuple[bool, float]:
        """
        Check error rate SLO.

        Target: Error rate <2%

        Args:
            duration_minutes: Time window to check

        Returns:
            Tuple of (is_compliant, error_rate)
        """
        query = f"""
        (
          sum(rate(applylens_agent_errors_total{{environment="{self.environment}"}}[{duration_minutes}m]))
          /
          sum(rate(applylens_agent_requests_total{{environment="{self.environment}"}}[{duration_minutes}m]))
        ) * 100
        """

        error_rate = self.query_prometheus(query)
        if error_rate is None:
            return False, 0.0

        is_compliant = error_rate < 2.0
        return is_compliant, error_rate

    def check_p95_latency(self, duration_minutes: int) -> Tuple[bool, float]:
        """
        Check P95 latency SLO.

        Target: P95 latency <1.5s (1500ms)

        Args:
            duration_minutes: Time window to check

        Returns:
            Tuple of (is_compliant, p95_latency_ms)
        """
        query = f"""
        histogram_quantile(
          0.95,
          sum(rate(applylens_agent_latency_bucket{{environment="{self.environment}"}}[{duration_minutes}m])) by (le)
        ) * 1000
        """

        p95_latency = self.query_prometheus(query)
        if p95_latency is None:
            return False, 0.0

        is_compliant = p95_latency < 1500.0
        return is_compliant, p95_latency

    def check_all_slos(self, duration_minutes: int) -> Dict[str, any]:
        """
        Check all SLO targets.

        Args:
            duration_minutes: Time window to check

        Returns:
            Dictionary with SLO compliance results
        """
        print(f"\n{'='*60}")
        print(f"SLO Compliance Check")
        print(f"{'='*60}")
        print(f"Environment: {self.environment}")
        print(f"Duration: {duration_minutes} minutes")
        print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
        print(f"{'='*60}\n")

        results = {
            "environment": self.environment,
            "duration_minutes": duration_minutes,
            "timestamp": datetime.utcnow().isoformat(),
            "slos": {},
            "compliant": True,
        }

        # Check error rate SLO
        print("Checking error rate SLO...")
        error_rate_ok, error_rate = self.check_error_rate(duration_minutes)
        results["slos"]["error_rate"] = {
            "target": "<2%",
            "actual": f"{error_rate:.2f}%",
            "compliant": error_rate_ok,
        }

        if error_rate_ok:
            print(f"✅ Error rate: {error_rate:.2f}% (target: <2%)")
        else:
            print(f"❌ Error rate: {error_rate:.2f}% (target: <2%) - VIOLATION")
            results["compliant"] = False

        # Check P95 latency SLO
        print("\nChecking P95 latency SLO...")
        latency_ok, p95_latency = self.check_p95_latency(duration_minutes)
        results["slos"]["p95_latency"] = {
            "target": "<1500ms",
            "actual": f"{p95_latency:.2f}ms",
            "compliant": latency_ok,
        }

        if latency_ok:
            print(f"✅ P95 latency: {p95_latency:.2f}ms (target: <1500ms)")
        else:
            print(
                f"❌ P95 latency: {p95_latency:.2f}ms (target: <1500ms) - VIOLATION"
            )
            results["compliant"] = False

        print(f"\n{'='*60}")
        if results["compliant"]:
            print("✅ All SLOs compliant")
        else:
            print("❌ SLO violations detected")
        print(f"{'='*60}\n")

        return results

    def generate_report(self, results: Dict[str, any]) -> str:
        """
        Generate markdown report from compliance check results.

        Args:
            results: Compliance check results

        Returns:
            Markdown-formatted report
        """
        timestamp = results["timestamp"]
        environment = results["environment"]
        duration = results["duration_minutes"]

        report = f"""# SLO Compliance Report

**Environment:** {environment}  
**Duration:** {duration} minutes  
**Timestamp:** {timestamp}  
**Status:** {'✅ COMPLIANT' if results['compliant'] else '❌ VIOLATION'}

---

## SLO Targets

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
"""

        for slo_name, slo_data in results["slos"].items():
            name = slo_name.replace("_", " ").title()
            target = slo_data["target"]
            actual = slo_data["actual"]
            status = "✅ Pass" if slo_data["compliant"] else "❌ Fail"
            report += f"| {name} | {target} | {actual} | {status} |\n"

        report += "\n---\n\n"

        if results["compliant"]:
            report += "## Summary\n\n"
            report += "All SLO targets met during the measurement period. "
            report += "System maintained resilience and performance within acceptable bounds.\n"
        else:
            report += "## Violations\n\n"
            violations = [
                name.replace("_", " ").title()
                for name, data in results["slos"].items()
                if not data["compliant"]
            ]
            report += f"The following SLOs were violated:\n\n"
            for violation in violations:
                report += f"- {violation}\n"
            report += "\n"
            report += "### Recommended Actions\n\n"
            report += "1. Review logs for errors during the measurement period\n"
            report += "2. Check for infrastructure issues or resource constraints\n"
            report += "3. Verify retry logic and circuit breakers are functioning\n"
            report += "4. Consider implementing additional resilience patterns\n"
            report += "5. If chaos testing, this is expected - verify recovery worked\n"

        report += "\n---\n\n"
        report += "_Generated by SLO Compliance Checker_\n"

        return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check SLO compliance via Prometheus queries"
    )
    parser.add_argument(
        "--environment",
        type=str,
        default="staging",
        choices=["staging", "canary", "production"],
        help="Environment to check (default: staging)",
    )
    parser.add_argument(
        "--duration-minutes",
        type=int,
        default=10,
        help="Time window to check in minutes (default: 10)",
    )
    parser.add_argument(
        "--prometheus-url",
        type=str,
        default=os.getenv("PROMETHEUS_URL", "http://localhost:9090"),
        help="Prometheus base URL (default: from PROMETHEUS_URL env or localhost)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for markdown report (default: print to stdout)",
    )

    args = parser.parse_args()

    # Validate inputs
    if args.duration_minutes < 1 or args.duration_minutes > 60:
        print("❌ Duration must be between 1 and 60 minutes")
        return 2

    # Create checker
    checker = SLOComplianceChecker(args.prometheus_url, args.environment)

    # Check SLO compliance
    results = checker.check_all_slos(args.duration_minutes)

    # Generate report
    report = checker.generate_report(results)

    # Output report
    if args.output:
        try:
            with open(args.output, "w") as f:
                f.write(report)
            print(f"📝 Report written to {args.output}")
        except IOError as e:
            print(f"❌ Error writing report: {e}")
            return 2
    else:
        print("\n" + report)

    # Return appropriate exit code
    if results["compliant"]:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
