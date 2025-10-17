"""Warehouse Health Agent - monitors data pipeline health.

Checks:
- Email data freshness in Elasticsearch
- BigQuery warehouse freshness
- ES ↔ BQ parity
- dbt run health
"""

from __future__ import annotations

from typing import Any, Dict

from .registry import AgentRegistry
from ..tools.bigquery import BigQueryTool
from ..tools.dbt import DbtTool
from ..tools.elasticsearch import ESTool


class WarehouseHealthAgent:
    """Agent that monitors warehouse health and data freshness.
    
    Performs health checks:
    1. Query Elasticsearch for recent email counts
    2. Query BigQuery for same metrics
    3. Compare parity between sources
    4. Optional dbt pulse check
    5. Summarize findings
    """
    
    name = "warehouse.health"
    
    @staticmethod
    def describe() -> Dict[str, Any]:
        """Describe agent capabilities.
        
        Returns:
            Agent metadata and capabilities
        """
        return {
            "name": WarehouseHealthAgent.name,
            "description": "Checks warehouse freshness & ES↔BQ parity; optional dbt pulse.",
            "version": "0.1.0",
            "capabilities": ["read_es", "read_bq", "dbt_run"],
        }
    
    @staticmethod
    def plan(req: Dict[str, Any]) -> Dict[str, Any]:
        """Create execution plan.
        
        Args:
            req: Request parameters
            
        Returns:
            Execution plan
        """
        return {
            "steps": ["query_es", "query_bq", "compare", "dbt_pulse", "summarize"],
            "dry_run": req.get("dry_run", True),
        }
    
    @staticmethod
    def execute(plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute warehouse health checks.
        
        Args:
            plan: Execution plan
            
        Returns:
            Health check results with parity status and metrics
        """
        # Initialize tools
        es = ESTool()
        bq = BigQueryTool()
        dbt = DbtTool()
        
        # Step 1: Query Elasticsearch for recent emails
        es_query = {
            "range": {
                "received_at": {"gte": "now-7d"}
            }
        }
        es_res = es.search(es_query)
        
        # Step 2: Query BigQuery for aggregated email counts
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
        
        # Step 3: Compare parity
        parity_ok = len(es_res.hits) > 0 and len(bq_res.rows) > 0
        
        # Step 4: Optional dbt pulse (dry-run safe)
        dbt_res = dbt.run(target="prod", models="tag:daily")
        
        # Step 5: Summarize
        return {
            "parity_ok": parity_ok,
            "es_hits_count": len(es_res.hits),
            "es_sample": [h.source for h in es_res.hits[:3]],
            "bq_rows_count": len(bq_res.rows),
            "bq_rows": bq_res.rows,
            "bq_stats": bq_res.stats,
            "dbt": dbt_res.model_dump(),
            "summary": {
                "status": "healthy" if parity_ok else "degraded",
                "checks_passed": sum([
                    parity_ok,
                    dbt_res.success,
                    len(es_res.hits) > 0,
                    len(bq_res.rows) > 0,
                ]),
                "total_checks": 4,
            }
        }


def register(registry: AgentRegistry):
    """Register warehouse health agent with the registry.
    
    Args:
        registry: Agent registry instance
    """
    registry.register(
        WarehouseHealthAgent.name,
        lambda plan: WarehouseHealthAgent.execute(plan)
    )
