"""
Golden tasks for warehouse.health agent.

These are representative test cases covering:
- Data warehouse health checks
- BigQuery parity verification
- DBT run monitoring
- Data quality validation
"""
from typing import List
from app.eval.models import EvalTask, EvalSuite


def get_warehouse_tasks() -> List[EvalTask]:
    """Get all warehouse.health eval tasks."""
    return [
        # Health check tasks
        EvalTask(
            id="warehouse.health.001",
            agent="warehouse.health",
            category="health_check",
            objective="Perform routine warehouse health check",
            context={
                "warehouse": "bigquery",
                "check_types": ["connectivity", "table_counts", "data_freshness"],
                "expected_tables": 50,
            },
            expected_output={
                "is_healthy": True,
                "issues_count": 0,
                "parity_ok": True,
                "checks_passed": 3,
            },
            invariants=[],
            difficulty="easy",
            tags=["health", "baseline"],
        ),
        
        EvalTask(
            id="warehouse.health.002",
            agent="warehouse.health",
            category="health_check",
            objective="Detect warehouse issues",
            context={
                "warehouse": "bigquery",
                "check_types": ["connectivity", "table_counts", "data_freshness"],
                "expected_tables": 50,
                "actual_tables": 45,
                "stale_data": True,
            },
            expected_output={
                "is_healthy": False,
                "issues_count": 2,
                "parity_ok": False,
                "checks_passed": 1,
            },
            invariants=["warehouse_parity_detection"],
            difficulty="medium",
            tags=["health", "issues", "red_team"],
        ),
        
        # Parity verification
        EvalTask(
            id="warehouse.parity.001",
            agent="warehouse.health",
            category="parity",
            objective="Verify data parity between Elasticsearch and BigQuery",
            context={
                "source": "elasticsearch",
                "target": "bigquery",
                "table": "emails",
                "source_count": 10000,
                "target_count": 10000,
            },
            expected_output={
                "is_healthy": True,
                "issues_count": 0,
                "parity_ok": True,
                "parity_percentage": 100.0,
            },
            invariants=[],
            difficulty="easy",
            tags=["parity", "validation"],
        ),
        
        EvalTask(
            id="warehouse.parity.002",
            agent="warehouse.health",
            category="parity",
            objective="Detect parity issues between sources",
            context={
                "source": "elasticsearch",
                "target": "bigquery",
                "table": "emails",
                "source_count": 10000,
                "target_count": 8500,
            },
            expected_output={
                "is_healthy": False,
                "issues_count": 1,
                "parity_ok": False,
                "parity_percentage": 85.0,
            },
            invariants=["warehouse_parity_detection"],
            difficulty="medium",
            tags=["parity", "red_team"],
        ),
        
        # DBT monitoring
        EvalTask(
            id="warehouse.dbt.001",
            agent="warehouse.health",
            category="monitoring",
            objective="Monitor DBT run status",
            context={
                "dbt_project": "applylens",
                "run_status": "success",
                "models_run": 25,
                "models_failed": 0,
                "duration_seconds": 120,
            },
            expected_output={
                "is_healthy": True,
                "issues_count": 0,
                "parity_ok": True,
                "dbt_status": "success",
            },
            invariants=[],
            difficulty="easy",
            tags=["dbt", "monitoring"],
        ),
        
        EvalTask(
            id="warehouse.dbt.002",
            agent="warehouse.health",
            category="monitoring",
            objective="Detect DBT run failures",
            context={
                "dbt_project": "applylens",
                "run_status": "failed",
                "models_run": 25,
                "models_failed": 3,
                "duration_seconds": 180,
                "error_models": ["model_a", "model_b", "model_c"],
            },
            expected_output={
                "is_healthy": False,
                "issues_count": 3,
                "parity_ok": True,
                "dbt_status": "failed",
            },
            invariants=[],
            difficulty="medium",
            tags=["dbt", "failures", "red_team"],
        ),
        
        # Data quality validation
        EvalTask(
            id="warehouse.quality.001",
            agent="warehouse.health",
            category="health_check",
            objective="Validate data quality metrics",
            context={
                "warehouse": "bigquery",
                "check_types": ["null_checks", "uniqueness", "referential_integrity"],
                "tables": ["emails", "users", "labels"],
            },
            expected_output={
                "is_healthy": True,
                "issues_count": 0,
                "parity_ok": True,
                "quality_score": 95.0,
            },
            invariants=[],
            difficulty="medium",
            tags=["quality", "validation"],
        ),
        
        # Performance monitoring
        EvalTask(
            id="warehouse.perf.001",
            agent="warehouse.health",
            category="monitoring",
            objective="Monitor warehouse query performance",
            context={
                "warehouse": "bigquery",
                "check_types": ["query_latency", "slot_usage", "bytes_processed"],
                "avg_query_time_ms": 500,
                "slot_utilization": 0.65,
            },
            expected_output={
                "is_healthy": True,
                "issues_count": 0,
                "parity_ok": True,
                "performance_ok": True,
            },
            invariants=[],
            difficulty="easy",
            tags=["performance", "monitoring"],
        ),
        
        # Edge case: critical parity failure
        EvalTask(
            id="warehouse.edge.001",
            agent="warehouse.health",
            category="edge_case",
            objective="Handle severe parity discrepancy",
            context={
                "source": "elasticsearch",
                "target": "bigquery",
                "table": "emails",
                "source_count": 10000,
                "target_count": 5000,
            },
            expected_output={
                "is_healthy": False,
                "issues_count": 1,
                "parity_ok": False,
                "parity_percentage": 50.0,
            },
            invariants=["warehouse_parity_detection"],
            difficulty="easy",
            tags=["edge_case", "critical", "red_team"],
        ),
        
        # Comprehensive health audit
        EvalTask(
            id="warehouse.audit.001",
            agent="warehouse.health",
            category="health_check",
            objective="Perform comprehensive warehouse audit",
            context={
                "warehouse": "bigquery",
                "check_types": [
                    "connectivity",
                    "table_counts",
                    "data_freshness",
                    "parity",
                    "dbt_status",
                    "query_performance",
                    "data_quality",
                ],
                "full_audit": True,
            },
            expected_output={
                "is_healthy": True,
                "issues_count": 0,
                "parity_ok": True,
                "checks_passed": 7,
                "audit_score": 98.0,
            },
            invariants=[],
            difficulty="hard",
            tags=["audit", "comprehensive"],
        ),
    ]


def get_warehouse_suite() -> EvalSuite:
    """Get the complete warehouse.health eval suite."""
    suite = EvalSuite(
        name="warehouse_health_v1",
        agent="warehouse.health",
        version="1.0",
        tasks=get_warehouse_tasks(),
        invariants=["warehouse_parity_detection"],
    )
    return suite
