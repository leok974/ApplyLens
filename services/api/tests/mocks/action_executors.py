"""
Mock Action Executors - Phase 5.4 PR6

Mock implementations for DBT, Elasticsearch, and Planner actions.
Used in tests to avoid real infrastructure calls.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime


class MockDBTExecutor:
    """
    Mock DBT execution for testing.
    
    Simulates dbt commands without running real dbt.
    """
    
    def __init__(self):
        self.commands_executed: List[Dict[str, Any]] = []
        self.should_fail = False
        self.failure_message = "Mock dbt failure"
    
    def run_models(
        self,
        models: List[str],
        full_refresh: bool = False,
        upstream: bool = False,
        threads: int = 4,
    ) -> Dict[str, Any]:
        """Mock dbt run command."""
        command = {
            "type": "run",
            "models": models,
            "full_refresh": full_refresh,
            "upstream": upstream,
            "threads": threads,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.commands_executed.append(command)
        
        if self.should_fail:
            return {
                "success": False,
                "message": self.failure_message,
                "exit_code": 1,
                "stdout": f"ERROR: {self.failure_message}",
                "stderr": self.failure_message,
                "duration_seconds": 2.5,
            }
        
        return {
            "success": True,
            "message": f"Successfully ran {len(models)} model(s)",
            "exit_code": 0,
            "stdout": f"Completed successfully. {len(models)} model(s) passed",
            "stderr": "",
            "duration_seconds": 5.0 * len(models) * (3 if full_refresh else 1),
            "models_run": models,
        }
    
    def refresh_dependencies(self) -> Dict[str, Any]:
        """Mock dbt deps command."""
        command = {
            "type": "deps",
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.commands_executed.append(command)
        
        if self.should_fail:
            return {
                "success": False,
                "message": self.failure_message,
                "exit_code": 1,
            }
        
        return {
            "success": True,
            "message": "Dependencies refreshed successfully",
            "exit_code": 0,
            "duration_seconds": 10.0,
        }
    
    def reset(self):
        """Reset mock state."""
        self.commands_executed = []
        self.should_fail = False


class MockElasticsearchClient:
    """
    Mock Elasticsearch client for testing.
    
    Simulates ES operations without real cluster.
    """
    
    def __init__(self):
        self.operations: List[Dict[str, Any]] = []
        self.should_fail = False
        self.failure_message = "Mock ES failure"
        self.indices_closed: List[str] = []
        self.indices_opened: List[str] = []
        self.caches_cleared: List[str] = []
    
    def close_index(self, index_name: str) -> Dict[str, Any]:
        """Mock close index."""
        operation = {
            "type": "close_index",
            "index": index_name,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.operations.append(operation)
        self.indices_closed.append(index_name)
        
        if self.should_fail:
            return {
                "acknowledged": False,
                "error": self.failure_message,
            }
        
        return {
            "acknowledged": True,
            "shards_acknowledged": True,
        }
    
    def open_index(self, index_name: str) -> Dict[str, Any]:
        """Mock open index."""
        operation = {
            "type": "open_index",
            "index": index_name,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.operations.append(operation)
        self.indices_opened.append(index_name)
        
        if self.should_fail:
            return {
                "acknowledged": False,
                "error": self.failure_message,
            }
        
        return {
            "acknowledged": True,
            "shards_acknowledged": True,
        }
    
    def reload_settings(self, index_name: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Mock reload index settings."""
        operation = {
            "type": "reload_settings",
            "index": index_name,
            "settings": settings,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.operations.append(operation)
        
        if self.should_fail:
            return {
                "acknowledged": False,
                "error": self.failure_message,
            }
        
        return {
            "acknowledged": True,
        }
    
    def clear_cache(
        self,
        index_name: str,
        cache_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Mock clear cache."""
        operation = {
            "type": "clear_cache",
            "index": index_name,
            "cache_types": cache_types or ["query", "request", "fielddata"],
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.operations.append(operation)
        self.caches_cleared.append(index_name)
        
        if self.should_fail:
            return {
                "_shards": {
                    "total": 5,
                    "successful": 0,
                    "failed": 5,
                },
            }
        
        return {
            "_shards": {
                "total": 5,
                "successful": 5,
                "failed": 0,
            },
        }
    
    def reindex(
        self,
        source_index: str,
        dest_index: str,
    ) -> Dict[str, Any]:
        """Mock reindex."""
        operation = {
            "type": "reindex",
            "source": source_index,
            "dest": dest_index,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.operations.append(operation)
        
        if self.should_fail:
            return {
                "failures": [self.failure_message],
            }
        
        return {
            "took": 5000,
            "timed_out": False,
            "total": 10000,
            "created": 10000,
            "updated": 0,
            "deleted": 0,
            "batches": 10,
            "failures": [],
        }
    
    def reset(self):
        """Reset mock state."""
        self.operations = []
        self.should_fail = False
        self.indices_closed = []
        self.indices_opened = []
        self.caches_cleared = []


class MockPlannerDeployer:
    """
    Mock Planner deployment client for testing.
    
    Simulates planner version management without real deployments.
    """
    
    def __init__(self):
        self.deployments: List[Dict[str, Any]] = []
        self.rollbacks: List[Dict[str, Any]] = []
        self.traffic_adjustments: List[Dict[str, Any]] = []
        self.should_fail = False
        self.failure_message = "Mock deployment failure"
        self.current_version = "v1.0.0"
        self.canary_version = "v1.1.0-canary"
        self.canary_traffic_pct = 10
    
    def deploy_version(
        self,
        version: str,
        canary_pct: int = 10,
    ) -> Dict[str, Any]:
        """Mock deploy planner version."""
        deployment = {
            "type": "deploy",
            "version": version,
            "canary_pct": canary_pct,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.deployments.append(deployment)
        
        if self.should_fail:
            return {
                "success": False,
                "message": self.failure_message,
            }
        
        self.canary_version = version
        self.canary_traffic_pct = canary_pct
        
        return {
            "success": True,
            "message": f"Deployed {version} at {canary_pct}% traffic",
            "version": version,
            "canary_pct": canary_pct,
            "estimated_duration_minutes": 15,
        }
    
    def rollback_to_version(
        self,
        version: str,
        immediate: bool = False,
    ) -> Dict[str, Any]:
        """Mock rollback planner version."""
        rollback = {
            "type": "rollback",
            "from_version": self.canary_version,
            "to_version": version,
            "immediate": immediate,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.rollbacks.append(rollback)
        
        if self.should_fail:
            return {
                "success": False,
                "message": self.failure_message,
            }
        
        self.current_version = version
        self.canary_version = None
        self.canary_traffic_pct = 0
        
        return {
            "success": True,
            "message": f"Rolled back to {version}",
            "version": version,
            "duration_minutes": 0.5 if immediate else 15,
        }
    
    def adjust_canary_traffic(
        self,
        version: str,
        target_pct: int,
        gradual: bool = True,
    ) -> Dict[str, Any]:
        """Mock adjust canary traffic split."""
        adjustment = {
            "type": "adjust_traffic",
            "version": version,
            "from_pct": self.canary_traffic_pct,
            "to_pct": target_pct,
            "gradual": gradual,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.traffic_adjustments.append(adjustment)
        
        if self.should_fail:
            return {
                "success": False,
                "message": self.failure_message,
            }
        
        self.canary_traffic_pct = target_pct
        
        return {
            "success": True,
            "message": f"Adjusted {version} to {target_pct}% traffic",
            "version": version,
            "target_pct": target_pct,
            "duration_minutes": 10 if gradual else 1,
        }
    
    def get_current_state(self) -> Dict[str, Any]:
        """Mock get current planner state."""
        return {
            "current_version": self.current_version,
            "canary_version": self.canary_version,
            "canary_traffic_pct": self.canary_traffic_pct,
        }
    
    def reset(self):
        """Reset mock state."""
        self.deployments = []
        self.rollbacks = []
        self.traffic_adjustments = []
        self.should_fail = False
        self.current_version = "v1.0.0"
        self.canary_version = "v1.1.0-canary"
        self.canary_traffic_pct = 10


# Global mock instances for reuse
mock_dbt = MockDBTExecutor()
mock_elasticsearch = MockElasticsearchClient()
mock_planner = MockPlannerDeployer()


def reset_all_mocks():
    """Reset all mock executors to initial state."""
    mock_dbt.reset()
    mock_elasticsearch.reset()
    mock_planner.reset()
