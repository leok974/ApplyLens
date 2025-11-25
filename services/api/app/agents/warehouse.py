"""Warehouse Health Agent - monitors data pipeline health.

Checks:
- Email data freshness in Elasticsearch
- BigQuery warehouse freshness
- ES ↔ BQ parity (real count comparison)
- Freshness SLO (30min threshold)
- dbt run health
- Auto-remediation (optional)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .registry import AgentRegistry
from ..providers import provider_factory
from ..tools.bigquery import BigQueryTool
from ..tools.dbt import DbtTool
from ..tools.elasticsearch import ESTool


class WarehouseHealthAgent:
    """Agent that monitors warehouse health and data freshness.

    Performs health checks (v2):
    1. Query Elasticsearch for daily email counts (7 days)
    2. Query BigQuery for same metrics
    3. Compare parity between sources (real count comparison)
    4. Check freshness SLO (latest event within 30min)
    5. Optional dbt pulse check
    6. Optional auto-remediation (trigger dbt run if stale)
    7. Summarize findings
    """

    name = "warehouse.health"
    version = "2.0.0"

    # Thresholds
    FRESHNESS_SLO_MINUTES = 30  # Max acceptable lag
    PARITY_THRESHOLD_PERCENT = 5.0  # Max acceptable difference (%)

    @staticmethod
    def describe() -> Dict[str, Any]:
        """Describe agent capabilities.

        Returns:
            Agent metadata and capabilities
        """
        return {
            "name": WarehouseHealthAgent.name,
            "description": "Checks warehouse freshness, ES↔BQ parity, and auto-remediation",
            "version": WarehouseHealthAgent.version,
            "capabilities": ["read_es", "read_bq", "dbt_run", "auto_remediate"],
            "thresholds": {
                "freshness_slo_minutes": WarehouseHealthAgent.FRESHNESS_SLO_MINUTES,
                "parity_threshold_percent": WarehouseHealthAgent.PARITY_THRESHOLD_PERCENT,
            },
        }

    @staticmethod
    def plan(req: Dict[str, Any]) -> Dict[str, Any]:
        """Create execution plan.

        Args:
            req: Request parameters (dry_run, allow_actions)

        Returns:
            Execution plan
        """
        return {
            "steps": [
                "query_es_daily",
                "query_bq_daily",
                "check_parity",
                "check_freshness",
                "dbt_pulse",
                "auto_remediate",
                "summarize",
            ],
            "dry_run": req.get("dry_run", True),
            "allow_actions": req.get("allow_actions", False),  # Enable auto-remediation
        }

    @staticmethod
    def execute(plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute warehouse health checks (v2 with real parity & freshness).

        Args:
            plan: Execution plan with dry_run and allow_actions flags

        Returns:
            Health check results with detailed parity, freshness, and remediation status
        """
        # Initialize tools
        ESTool()
        bq = BigQueryTool()
        dbt = DbtTool()

        # Get providers for enhanced functionality
        es_provider = provider_factory.es()
        provider_factory.bigquery()

        results = {
            "parity": {},
            "freshness": {},
            "dbt": {},
            "remediation": {},
            "summary": {},
        }

        # Step 1: Query Elasticsearch for daily email counts (7 days)
        try:
            es_daily = es_provider.aggregate_daily(days=7)
            # es_daily = [{"day": "2025-01-15", "emails": 42}, ...]
            results["es_daily_counts"] = es_daily
            results["es_total"] = sum(d.get("emails", 0) for d in es_daily)
        except Exception as e:
            results["es_error"] = str(e)
            es_daily = []
            results["es_total"] = 0

        # Step 2: Query BigQuery for daily email counts (7 days)
        try:
            bq_query = """
                SELECT
                    DATE(received_at) AS day,
                    COUNT(*) AS emails
                FROM emails
                WHERE received_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
                GROUP BY day
                ORDER BY day DESC
            """
            bq_res = bq.query(bq_query)
            bq_daily = [
                {"day": str(row.get("day")), "emails": int(row.get("emails", 0))}
                for row in bq_res.rows
            ]
            results["bq_daily_counts"] = bq_daily
            results["bq_total"] = sum(d.get("emails", 0) for d in bq_daily)
        except Exception as e:
            results["bq_error"] = str(e)
            bq_daily = []
            results["bq_total"] = 0

        # Step 3: Check parity (real count comparison)
        es_total = results["es_total"]
        bq_total = results["bq_total"]

        if es_total > 0 and bq_total > 0:
            diff = abs(es_total - bq_total)
            parity_pct = (diff / max(es_total, bq_total)) * 100
            parity_ok = parity_pct <= WarehouseHealthAgent.PARITY_THRESHOLD_PERCENT

            results["parity"] = {
                "status": "ok" if parity_ok else "degraded",
                "es_count": es_total,
                "bq_count": bq_total,
                "difference": diff,
                "difference_percent": round(parity_pct, 2),
                "threshold_percent": WarehouseHealthAgent.PARITY_THRESHOLD_PERCENT,
                "within_threshold": parity_ok,
            }
        else:
            results["parity"] = {
                "status": "failed",
                "es_count": es_total,
                "bq_count": bq_total,
                "error": "One or both sources returned zero counts",
            }

        # Step 4: Check freshness SLO (latest event within 30min)
        freshness_ok = False
        try:
            # Get latest event timestamp from ES
            latest_es_ts = es_provider.latest_event_ts()

            if latest_es_ts:
                # Parse ISO timestamp
                latest_dt = datetime.fromisoformat(latest_es_ts.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                age_minutes = (now - latest_dt).total_seconds() / 60
                freshness_ok = age_minutes <= WarehouseHealthAgent.FRESHNESS_SLO_MINUTES

                results["freshness"] = {
                    "status": "ok" if freshness_ok else "stale",
                    "latest_event_ts": latest_es_ts,
                    "age_minutes": round(age_minutes, 2),
                    "slo_minutes": WarehouseHealthAgent.FRESHNESS_SLO_MINUTES,
                    "within_slo": freshness_ok,
                }
            else:
                results["freshness"] = {
                    "status": "unknown",
                    "error": "No events found in Elasticsearch",
                }
        except Exception as e:
            results["freshness"] = {
                "status": "error",
                "error": str(e),
            }

        # Step 5: dbt pulse check (always safe - just status)
        try:
            dbt_res = dbt.run(target="prod", models="tag:daily")
            results["dbt"] = {
                "success": dbt_res.success,
                "models_run": dbt_res.models_run,
                "duration_sec": dbt_res.duration_sec,
            }
        except Exception as e:
            results["dbt"] = {
                "success": False,
                "error": str(e),
            }

        # Step 6: Auto-remediation (only if allow_actions=True)
        parity_bad = results["parity"].get("status") == "degraded"
        freshness_bad = results["freshness"].get("status") == "stale"

        if plan.get("allow_actions") and (parity_bad or freshness_bad):
            try:
                # Trigger full dbt run to refresh warehouse
                dbt_remediation = dbt.run(target="prod", models="all")
                results["remediation"] = {
                    "triggered": True,
                    "reason": "parity_bad" if parity_bad else "freshness_bad",
                    "dbt_success": dbt_remediation.success,
                    "models_run": dbt_remediation.models_run,
                    "duration_sec": dbt_remediation.duration_sec,
                }
            except Exception as e:
                results["remediation"] = {
                    "triggered": True,
                    "success": False,
                    "error": str(e),
                }
        else:
            results["remediation"] = {
                "triggered": False,
                "reason": "dry_run" if not plan.get("allow_actions") else "not_needed",
            }

        # Step 7: Summarize
        checks_passed = sum(
            [
                results["parity"].get("status") == "ok",
                results["freshness"].get("status") == "ok",
                results["dbt"].get("success", False),
            ]
        )

        results["summary"] = {
            "status": "healthy"
            if checks_passed == 3
            else "degraded"
            if checks_passed >= 1
            else "failed",
            "checks_passed": checks_passed,
            "total_checks": 3,
            "issues": [],
        }

        # Add specific issues
        if results["parity"].get("status") != "ok":
            results["summary"]["issues"].append(
                {
                    "type": "parity",
                    "severity": "high",
                    "message": f"ES/BQ parity off by {results['parity'].get('difference_percent', 0)}%",
                }
            )

        if results["freshness"].get("status") == "stale":
            results["summary"]["issues"].append(
                {
                    "type": "freshness",
                    "severity": "high",
                    "message": f"Data stale by {results['freshness'].get('age_minutes', 0)} minutes",
                }
            )

        if not results["dbt"].get("success"):
            results["summary"]["issues"].append(
                {
                    "type": "dbt",
                    "severity": "medium",
                    "message": "dbt pulse check failed",
                }
            )

        return results


def register(registry: AgentRegistry):
    """Register warehouse health agent with the registry.

    Args:
        registry: Agent registry instance
    """
    registry.register(
        WarehouseHealthAgent.name, lambda plan: WarehouseHealthAgent.execute(plan)
    )
