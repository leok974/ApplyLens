"""
Eval runner for executing evaluation suites.

The runner:
1. Executes eval tasks against agents
2. Scores outputs using judges
3. Checks invariants
4. Aggregates results
5. Exports JSONL for trend analysis
"""
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from .models import EvalTask, EvalResult, EvalSuite, EvalRun
from .judges import get_judge, get_invariant


class MockAgentExecutor:
    """
    Mock agent executor for testing.
    
    In production, this would call the actual agent system.
    For CI/testing, we generate deterministic mock outputs.
    """
    
    def execute(self, agent: str, objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent with objective and context.
        
        Returns mock output based on agent type and context.
        """
        # Simulate execution time
        base_latency = {
            "inbox.triage": 1200,
            "knowledge.update": 800,
            "insights.write": 2000,
            "warehouse.health": 1500,
        }.get(agent, 1000)
        
        time.sleep(base_latency / 5000)  # Scaled down for testing
        
        # Generate mock output based on agent type
        if agent == "inbox.triage":
            return self._mock_inbox_output(context)
        elif agent == "knowledge.update":
            return self._mock_knowledge_output(context)
        elif agent == "insights.write":
            return self._mock_insights_output(context)
        elif agent == "warehouse.health":
            return self._mock_warehouse_output(context)
        else:
            return {"error": f"Unknown agent: {agent}"}
    
    def _mock_inbox_output(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock output for inbox.triage."""
        # Detect phishing signals
        subject = context.get("subject", "").lower()
        body = context.get("body", "").lower()
        sender = context.get("sender", "").lower()
        
        is_phishing = any(
            keyword in subject + body + sender
            for keyword in ["verify", "urgent", "suspicious", "account", "click", "confirm"]
        )
        
        has_suspicious_domain = any(
            tld in sender
            for tld in [".net", ".biz", ".info"]
        ) and "suspicious" in sender
        
        if is_phishing or has_suspicious_domain or context.get("domain_age_days", 1000) < 30:
            risk_level = "high"
            is_phishing_flag = True
            category = "phishing"
            confidence = 0.90
        elif context.get("sender_in_contacts", False):
            risk_level = "low"
            is_phishing_flag = False
            category = "personal"
            confidence = 0.95
        elif context.get("unsubscribe_link", False):
            risk_level = "low"
            is_phishing_flag = False
            category = "promotion"
            confidence = 0.92
        elif "job" in subject.lower() or "opportunity" in subject.lower():
            risk_level = "low"
            is_phishing_flag = False
            category = "offer"
            confidence = 0.85
        elif context.get("excessive_caps", False) or context.get("excessive_punctuation", False):
            risk_level = "medium"
            is_phishing_flag = False
            category = "spam"
            confidence = 0.90
        else:
            risk_level = "medium"
            is_phishing_flag = False
            category = "unknown"
            confidence = 0.50
        
        return {
            "risk_level": risk_level,
            "is_phishing": is_phishing_flag,
            "category": category,
            "confidence": confidence,
        }
    
    def _mock_knowledge_output(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock output for knowledge.update."""
        entry_count = context.get("entry_count", 0)
        has_conflicts = context.get("has_conflicts", False)
        conflict_count = context.get("conflict_count", 0)
        
        # Simulate 98% success rate
        success_rate = 0.98
        items_synced = int(entry_count * success_rate)
        
        return {
            "items_synced": items_synced,
            "synonyms_preserved": context.get("synonyms_present", True),
            "conflicts_resolved": conflict_count if has_conflicts else 0,
            "duration_ms": entry_count * 10,
            "config_updated": context.get("config_type") is not None,
            "synonym_groups_intact": len(context.get("synonym_groups", [])),
            "strategy_used": context.get("conflict_strategy", "last_write_wins"),
        }
    
    def _mock_insights_output(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock output for insights.write."""
        metrics = context.get("metrics", [])
        time_range = context.get("time_range", "1d")
        has_historical = context.get("has_historical_data", True)
        
        # Metrics count based on time range and data availability
        metrics_count = len(metrics) if metrics else 3
        if time_range in ["30d", "90d"]:
            metrics_count += 2
        if context.get("include_forecasts", False):
            metrics_count += 2
        
        # Trends based on time range
        trends = []
        if has_historical and time_range not in ["1h", "1d"]:
            trends = ["volume_stable", "efficiency_improved"]
            if context.get("include_anomalies", False):
                trends.append("anomaly_detected")
        
        return {
            "metrics_count": metrics_count,
            "trends": trends,
            "has_summary": context.get("report_type") is not None or time_range != "1h",
            "has_recommendations": time_range in ["7d", "30d", "90d"],
            "charts_generated": 3 if context.get("include_charts", False) else 0,
            "anomalies_detected": 2 if context.get("include_anomalies", False) else 0,
            "comparison_included": context.get("comparison_mode") is not None,
            "data_quality_warning": not has_historical or context.get("data_points", 100) < 10,
            "real_time": time_range == "1h",
            "forecasts_included": context.get("include_forecasts", False),
        }
    
    def _mock_warehouse_output(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock output for warehouse.health."""
        source_count = context.get("source_count", 0)
        target_count = context.get("target_count", 0)
        
        # Calculate parity
        if source_count > 0:
            parity_percentage = (target_count / source_count) * 100
            parity_ok = parity_percentage >= 95.0
        else:
            parity_percentage = 100.0
            parity_ok = True
        
        # Check for issues
        issues = []
        if not parity_ok:
            issues.append("parity_discrepancy")
        if context.get("stale_data", False):
            issues.append("stale_data")
        if context.get("run_status") == "failed":
            issues.extend(context.get("error_models", []))
        
        expected_tables = context.get("expected_tables", 0)
        actual_tables = context.get("actual_tables", expected_tables)
        if actual_tables < expected_tables:
            issues.append("missing_tables")
        
        is_healthy = len(issues) == 0
        checks_passed = len(context.get("check_types", [])) - len(issues)
        
        return {
            "is_healthy": is_healthy,
            "issues_count": len(issues),
            "parity_ok": parity_ok,
            "parity_percentage": parity_percentage,
            "checks_passed": checks_passed,
            "dbt_status": context.get("run_status", "success"),
            "performance_ok": context.get("avg_query_time_ms", 500) < 1000,
            "quality_score": 95.0 if is_healthy else 70.0,
            "audit_score": 98.0 if is_healthy else 60.0,
        }


class EvalRunner:
    """Runner for executing evaluation suites."""
    
    def __init__(self, use_mock_executor: bool = True, output_dir: Optional[Path] = None):
        """
        Initialize eval runner.
        
        Args:
            use_mock_executor: If True, use mock executor for testing
            output_dir: Directory for JSONL exports (default: eval_results/)
        """
        self.use_mock_executor = use_mock_executor
        self.executor = MockAgentExecutor() if use_mock_executor else None
        self.output_dir = output_dir or Path("eval_results")
        self.output_dir.mkdir(exist_ok=True)
    
    def run_suite(self, suite: EvalSuite) -> EvalRun:
        """
        Execute an eval suite.
        
        Args:
            suite: The eval suite to run
            
        Returns:
            EvalRun with all results
        """
        run_id = str(uuid.uuid4())[:8]
        run = EvalRun(
            run_id=run_id,
            suite_name=suite.name,
            agent=suite.agent,
            timestamp=datetime.utcnow(),
        )
        
        print(f"\n🏃 Running eval suite: {suite.name} ({len(suite.tasks)} tasks)")
        
        for task in suite.tasks:
            result = self._run_task(task)
            run.add_result(result)
            
            status = "✅" if result.success else "❌"
            print(f"  {status} {task.id}: score={result.quality_score:.1f}, latency={result.latency_ms:.0f}ms")
        
        # Export results
        self._export_run(run)
        
        # Print summary
        self._print_summary(run)
        
        return run
    
    def _run_task(self, task: EvalTask) -> EvalResult:
        """Execute a single eval task."""
        start_time = time.time()
        
        try:
            # Execute agent
            output = self.executor.execute(task.agent, task.objective, task.context)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Score output with judge
            judge = get_judge(task.agent)
            quality_score, reasoning = judge.score(task, output)
            
            # Check invariants
            passed_invariants = []
            failed_invariants = []
            
            for inv_id in task.invariants:
                invariant = get_invariant(inv_id)
                passed, reason = invariant.check(task, output)
                
                if passed:
                    passed_invariants.append(inv_id)
                else:
                    failed_invariants.append(inv_id)
            
            # Create result
            return EvalResult(
                task_id=task.id,
                agent=task.agent,
                success=True,
                output=output,
                error=None,
                latency_ms=latency_ms,
                cost_weight=1.0,  # Mock cost
                quality_score=quality_score,
                judge_reasoning=reasoning,
                passed_invariants=passed_invariants,
                failed_invariants=failed_invariants,
                difficulty=task.difficulty,
                tags=task.tags,
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            return EvalResult(
                task_id=task.id,
                agent=task.agent,
                success=False,
                output=None,
                error=str(e),
                latency_ms=latency_ms,
                cost_weight=0.0,
                quality_score=0.0,
                judge_reasoning=f"Execution failed: {e}",
                passed_invariants=[],
                failed_invariants=task.invariants,
                difficulty=task.difficulty,
                tags=task.tags,
            )
    
    def _export_run(self, run: EvalRun) -> None:
        """Export run results to JSONL."""
        filename = f"{run.agent}_{run.run_id}_{run.timestamp.strftime('%Y%m%d_%H%M%S')}.jsonl"
        filepath = self.output_dir / filename
        
        with open(filepath, "w") as f:
            # Write run summary
            f.write(json.dumps(run.to_jsonl_record()) + "\n")
            
            # Write individual results
            for result in run.results:
                result_dict = result.model_dump()
                # Convert datetime to ISO format
                if "timestamp" in result_dict:
                    result_dict["timestamp"] = result_dict["timestamp"].isoformat()
                f.write(json.dumps(result_dict) + "\n")
        
        print(f"\n📊 Results exported to: {filepath}")
    
    def _print_summary(self, run: EvalRun) -> None:
        """Print summary of eval run."""
        print(f"\n{'='*60}")
        print(f"📈 Eval Summary: {run.suite_name}")
        print(f"{'='*60}")
        print(f"Agent: {run.agent}")
        print(f"Total tasks: {run.total_tasks}")
        print(f"Success rate: {run.success_rate:.1%}")
        print(f"Avg quality score: {run.avg_quality_score:.1f}/100")
        print(f"Avg latency: {run.avg_latency_ms:.0f}ms")
        print(f"Total cost weight: {run.total_cost_weight:.2f}")
        print(f"\nInvariants:")
        print(f"  ✅ Passed: {run.invariants_passed}")
        print(f"  ❌ Failed: {run.invariants_failed}")
        
        if run.failed_invariant_ids:
            print(f"  Failed IDs: {', '.join(run.failed_invariant_ids)}")
        
        if run.quality_by_difficulty:
            print(f"\nQuality by difficulty:")
            for diff, score in run.quality_by_difficulty.items():
                print(f"  {diff}: {score:.1f}/100")
        
        print(f"{'='*60}\n")
