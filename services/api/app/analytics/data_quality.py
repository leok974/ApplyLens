"""
Data quality monitoring and lineage tracking.

Integrates with dbt to run quality checks and track data lineage.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
import subprocess
import json


class QualityCheckType(str, Enum):
    """Types of quality checks."""
    NULL_CHECK = "null_check"
    DUPLICATE_CHECK = "duplicate_check"
    SCHEMA_DRIFT = "schema_drift"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    VALUE_RANGE = "value_range"
    FRESHNESS = "freshness"
    NULL_RATE = "null_rate"
    VALUE_DISTRIBUTION = "value_distribution"
    MONOTONIC_IDS = "monotonic_ids"


class QualityCheckStatus(str, Enum):
    """Quality check execution status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    ERROR = "error"


class QualityCheckResult(BaseModel):
    """Result of a quality check."""
    table_name: str
    column_name: Optional[str] = None
    check_type: QualityCheckType
    status: QualityCheckStatus
    failed_rows: int = 0
    details: Dict = Field(default_factory=dict)
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def is_passing(self) -> bool:
        """Check if quality check passed."""
        return self.status == QualityCheckStatus.PASSED


class LineageNode(BaseModel):
    """Node in the data lineage graph."""
    node_id: str
    node_name: str
    node_type: str  # source, dbt_model, agent
    schema_name: Optional[str] = None
    depth_level: int = 0
    downstream_count: int = 0
    impact_level: str = "low"  # low, medium, high


class LineageEdge(BaseModel):
    """Edge in the data lineage graph."""
    from_node: str
    to_node: str
    flow_type: str  # transformation, consumption


class DataQualityConfig(BaseModel):
    """Configuration for data quality checks."""
    table_name: str
    null_checks: List[str] = Field(default_factory=list)
    unique_keys: List[str] = Field(default_factory=list)
    freshness_column: Optional[str] = None
    freshness_max_hours: int = 24
    value_ranges: Dict[str, tuple] = Field(default_factory=dict)
    expected_values: Dict[str, List[str]] = Field(default_factory=dict)


class DataQualityMonitor:
    """
    Monitor data quality using dbt tests and custom checks.
    
    Runs daily quality checks on warehouse tables and alerts on failures.
    """
    
    def __init__(self, dbt_project_dir: str = "./analytics/dbt"):
        self.dbt_project_dir = dbt_project_dir
        self.quality_configs: Dict[str, DataQualityConfig] = {}
        self.check_results: List[QualityCheckResult] = []
    
    def register_table(self, config: DataQualityConfig):
        """Register a table for quality monitoring."""
        self.quality_configs[config.table_name] = config
    
    def run_dbt_tests(self, models: Optional[List[str]] = None) -> Dict:
        """
        Run dbt tests for specified models.
        
        Args:
            models: List of model names to test. If None, test all.
        
        Returns:
            Test results with pass/fail counts
        """
        cmd = ["dbt", "test", "--project-dir", self.dbt_project_dir]
        
        if models:
            for model in models:
                cmd.extend(["--select", model])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes
            )
            
            # Parse dbt output
            output = result.stdout
            
            # Extract test results
            passed = output.count("PASS")
            failed = output.count("FAIL")
            warnings = output.count("WARN")
            
            return {
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "success": result.returncode == 0,
                "output": output,
            }
        
        except subprocess.TimeoutExpired:
            return {
                "passed": 0,
                "failed": 0,
                "warnings": 0,
                "success": False,
                "error": "Test execution timeout",
            }
        except Exception as e:
            return {
                "passed": 0,
                "failed": 0,
                "warnings": 0,
                "success": False,
                "error": str(e),
            }
    
    def check_table_quality(self, table_name: str) -> List[QualityCheckResult]:
        """
        Run quality checks for a specific table.
        
        Args:
            table_name: Name of the table to check
        
        Returns:
            List of quality check results
        """
        if table_name not in self.quality_configs:
            raise ValueError(f"Table {table_name} not registered for quality monitoring")
        
        config = self.quality_configs[table_name]
        results = []
        
        # Null checks
        for column in config.null_checks:
            result = self._check_nulls(table_name, column)
            results.append(result)
        
        # Duplicate checks
        if config.unique_keys:
            result = self._check_duplicates(table_name, config.unique_keys)
            results.append(result)
        
        # Freshness check
        if config.freshness_column:
            result = self._check_freshness(
                table_name,
                config.freshness_column,
                config.freshness_max_hours,
            )
            results.append(result)
        
        # Value range checks
        for column, (min_val, max_val) in config.value_ranges.items():
            result = self._check_value_range(table_name, column, min_val, max_val)
            results.append(result)
        
        # Value distribution checks
        for column, expected_values in config.expected_values.items():
            result = self._check_value_distribution(table_name, column, expected_values)
            results.append(result)
        
        self.check_results.extend(results)
        return results
    
    def _check_nulls(self, table_name: str, column_name: str) -> QualityCheckResult:
        """Check for null values in a column."""
        # Placeholder - in production, this would query the database
        failed_rows = 0  # Mock result
        
        status = QualityCheckStatus.PASSED if failed_rows == 0 else QualityCheckStatus.FAILED
        
        return QualityCheckResult(
            table_name=table_name,
            column_name=column_name,
            check_type=QualityCheckType.NULL_CHECK,
            status=status,
            failed_rows=failed_rows,
        )
    
    def _check_duplicates(self, table_name: str, key_columns: List[str]) -> QualityCheckResult:
        """Check for duplicate records."""
        failed_rows = 0  # Mock result
        
        status = QualityCheckStatus.PASSED if failed_rows == 0 else QualityCheckStatus.FAILED
        
        return QualityCheckResult(
            table_name=table_name,
            column_name=", ".join(key_columns),
            check_type=QualityCheckType.DUPLICATE_CHECK,
            status=status,
            failed_rows=failed_rows,
            details={"key_columns": key_columns},
        )
    
    def _check_freshness(
        self,
        table_name: str,
        column_name: str,
        max_hours: int,
    ) -> QualityCheckResult:
        """Check table freshness."""
        # Mock: latest data is within threshold
        age_hours = 2.0  # Mock result
        failed_rows = 0 if age_hours <= max_hours else 1
        
        status = QualityCheckStatus.PASSED if failed_rows == 0 else QualityCheckStatus.FAILED
        
        return QualityCheckResult(
            table_name=table_name,
            column_name=column_name,
            check_type=QualityCheckType.FRESHNESS,
            status=status,
            failed_rows=failed_rows,
            details={
                "age_hours": age_hours,
                "max_hours": max_hours,
            },
        )
    
    def _check_value_range(
        self,
        table_name: str,
        column_name: str,
        min_val: float,
        max_val: float,
    ) -> QualityCheckResult:
        """Check if values are within expected range."""
        failed_rows = 0  # Mock result
        
        status = QualityCheckStatus.PASSED if failed_rows == 0 else QualityCheckStatus.FAILED
        
        return QualityCheckResult(
            table_name=table_name,
            column_name=column_name,
            check_type=QualityCheckType.VALUE_RANGE,
            status=status,
            failed_rows=failed_rows,
            details={
                "min_value": min_val,
                "max_value": max_val,
            },
        )
    
    def _check_value_distribution(
        self,
        table_name: str,
        column_name: str,
        expected_values: List[str],
    ) -> QualityCheckResult:
        """Check if column values match expected distribution."""
        failed_rows = 0  # Mock result
        
        status = QualityCheckStatus.PASSED if failed_rows == 0 else QualityCheckStatus.FAILED
        
        return QualityCheckResult(
            table_name=table_name,
            column_name=column_name,
            check_type=QualityCheckType.VALUE_DISTRIBUTION,
            status=status,
            failed_rows=failed_rows,
            details={"expected_values": expected_values},
        )
    
    def get_quality_summary(self, days: int = 7) -> Dict:
        """
        Get quality check summary for the past N days.
        
        Returns:
            Summary with pass/fail rates, failing tables, etc.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        recent_results = [
            r for r in self.check_results
            if r.checked_at >= cutoff
        ]
        
        total_checks = len(recent_results)
        passed = sum(1 for r in recent_results if r.status == QualityCheckStatus.PASSED)
        failed = sum(1 for r in recent_results if r.status == QualityCheckStatus.FAILED)
        warnings = sum(1 for r in recent_results if r.status == QualityCheckStatus.WARNING)
        
        # Find failing tables
        failing_tables = set()
        for result in recent_results:
            if result.status == QualityCheckStatus.FAILED:
                failing_tables.add(result.table_name)
        
        pass_rate = (passed / total_checks * 100) if total_checks > 0 else 100.0
        
        return {
            "period_days": days,
            "total_checks": total_checks,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "pass_rate": pass_rate,
            "failing_tables": list(failing_tables),
        }
    
    def generate_quality_report(self) -> str:
        """Generate a quality report for the last 7 days."""
        summary = self.get_quality_summary(days=7)
        
        report = f"""# Data Quality Report

**Period:** Last 7 days
**Generated:** {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}

## Summary

- **Total Checks:** {summary['total_checks']}
- **Passed:** {summary['passed']}
- **Failed:** {summary['failed']}
- **Warnings:** {summary['warnings']}
- **Pass Rate:** {summary['pass_rate']:.1f}%

"""
        
        if summary['failing_tables']:
            report += "## Failing Tables\n\n"
            for table in summary['failing_tables']:
                report += f"- `{table}`\n"
        
        # Recent failures
        recent_failures = [
            r for r in self.check_results[-20:]
            if r.status == QualityCheckStatus.FAILED
        ]
        
        if recent_failures:
            report += "\n## Recent Failures\n\n"
            for result in recent_failures:
                report += f"### {result.table_name}.{result.column_name}\n\n"
                report += f"- **Check Type:** {result.check_type.value}\n"
                report += f"- **Failed Rows:** {result.failed_rows}\n"
                report += f"- **Checked At:** {result.checked_at.strftime('%Y-%m-%d %H:%M')}\n"
                if result.details:
                    report += f"- **Details:** {result.details}\n"
                report += "\n"
        
        return report


class LineageTracker:
    """
    Track data lineage across the warehouse.
    
    Uses dbt lineage model to understand dependencies.
    """
    
    def __init__(self):
        self.nodes: Dict[str, LineageNode] = {}
        self.edges: List[LineageEdge] = []
    
    def load_lineage_from_dbt(self) -> Dict:
        """
        Load lineage from dbt lineage_map model.
        
        Returns:
            Lineage graph with nodes and edges
        """
        # Placeholder - in production, query lineage_map table
        
        # Mock lineage data
        self.nodes = {
            "public.raw_inbox_events": LineageNode(
                node_id="public.raw_inbox_events",
                node_name="raw_inbox_events",
                node_type="source",
                depth_level=0,
                downstream_count=1,
                impact_level="medium",
            ),
            "analytics.inbox_triage_events": LineageNode(
                node_id="analytics.inbox_triage_events",
                node_name="inbox_triage_events",
                node_type="dbt_model",
                depth_level=1,
                downstream_count=1,
                impact_level="high",
            ),
            "agent.inbox.triage": LineageNode(
                node_id="agent.inbox.triage",
                node_name="inbox.triage",
                node_type="agent",
                depth_level=2,
                downstream_count=0,
                impact_level="high",
            ),
        }
        
        self.edges = [
            LineageEdge(
                from_node="public.raw_inbox_events",
                to_node="analytics.inbox_triage_events",
                flow_type="transformation",
            ),
            LineageEdge(
                from_node="analytics.inbox_triage_events",
                to_node="agent.inbox.triage",
                flow_type="consumption",
            ),
        ]
        
        return {
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
        }
    
    def get_downstream_impact(self, node_id: str) -> List[str]:
        """
        Get all downstream nodes affected by changes to this node.
        
        Args:
            node_id: ID of the node to analyze
        
        Returns:
            List of downstream node IDs
        """
        downstream = []
        
        # Direct children
        for edge in self.edges:
            if edge.from_node == node_id:
                downstream.append(edge.to_node)
                # Recursively get children's children
                downstream.extend(self.get_downstream_impact(edge.to_node))
        
        return list(set(downstream))
    
    def get_upstream_dependencies(self, node_id: str) -> List[str]:
        """Get all upstream nodes this node depends on."""
        upstream = []
        
        for edge in self.edges:
            if edge.to_node == node_id:
                upstream.append(edge.from_node)
                # Recursively get parent's parents
                upstream.extend(self.get_upstream_dependencies(edge.from_node))
        
        return list(set(upstream))


# Global instances
_quality_monitor = None
_lineage_tracker = None


def get_quality_monitor() -> DataQualityMonitor:
    """Get global data quality monitor instance."""
    global _quality_monitor
    if _quality_monitor is None:
        _quality_monitor = DataQualityMonitor()
    return _quality_monitor


def get_lineage_tracker() -> LineageTracker:
    """Get global lineage tracker instance."""
    global _lineage_tracker
    if _lineage_tracker is None:
        _lineage_tracker = LineageTracker()
    return _lineage_tracker
