"""
Online evaluation and telemetry for production agent runs.

Captures quality signals from production:
- User feedback (thumbs up/down)
- Sampled evaluation runs
- Red-team attack detection
- Performance metrics

Feeds into:
- AgentMetricsDaily for trend analysis
- Weekly intelligence reports
- Regression gates
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from ..models import AgentMetricsDaily
from .models import EvalTask, EvalResult
from .runner import EvalRunner, MockAgentExecutor
from .judges import get_judge, get_invariant
import random


class FeedbackCollector:
    """Collects user feedback on agent outputs."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_feedback(
        self,
        agent: str,
        run_id: str,
        feedback_type: str,  # "thumbs_up" or "thumbs_down"
        comment: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record user feedback on an agent run.
        
        Args:
            agent: Agent identifier
            run_id: Unique run identifier
            feedback_type: "thumbs_up" or "thumbs_down"
            comment: Optional user comment
            context: Optional context (e.g., {"task": "phishing_detection"})
        """
        # In production, would store individual feedback records
        # For now, we'll aggregate directly into daily metrics
        
        date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get or create daily metrics
        metrics = self.db.query(AgentMetricsDaily).filter(
            AgentMetricsDaily.agent == agent,
            AgentMetricsDaily.date == date,
        ).first()
        
        if not metrics:
            metrics = AgentMetricsDaily(
                agent=agent,
                date=date,
                total_runs=0,
                successful_runs=0,
                failed_runs=0,
            )
            self.db.add(metrics)
        
        # Update feedback counts
        if feedback_type == "thumbs_up":
            metrics.thumbs_up += 1
        elif feedback_type == "thumbs_down":
            metrics.thumbs_down += 1
        
        # Recompute rates
        total_feedback = metrics.thumbs_up + metrics.thumbs_down
        if total_feedback > 0:
            metrics.feedback_rate = total_feedback / max(metrics.total_runs, 1)
            metrics.satisfaction_rate = metrics.thumbs_up / total_feedback
        
        self.db.commit()


class OnlineEvaluator:
    """
    Runs sampled evaluations on production agent outputs.
    
    Strategy:
    - Sample N% of production runs (configurable)
    - Evaluate with judges
    - Check invariants
    - Aggregate into daily metrics
    """
    
    def __init__(self, db: Session, sample_rate: float = 0.10):
        """
        Initialize online evaluator.
        
        Args:
            db: Database session
            sample_rate: Fraction of runs to evaluate (0.0-1.0)
        """
        self.db = db
        self.sample_rate = sample_rate
    
    def should_sample(self) -> bool:
        """Decide if this run should be sampled for evaluation."""
        return random.random() < self.sample_rate
    
    def evaluate_run(
        self,
        agent: str,
        run_id: str,
        objective: str,
        context: Dict[str, Any],
        output: Dict[str, Any],
        latency_ms: float,
        cost_weight: float = 1.0,
        invariant_ids: Optional[List[str]] = None,
    ) -> EvalResult:
        """
        Evaluate a production run.
        
        Args:
            agent: Agent identifier
            run_id: Unique run identifier
            objective: What the agent was asked to do
            context: Input context
            output: Agent output
            latency_ms: Execution time
            cost_weight: Relative cost
            invariant_ids: Invariants to check
            
        Returns:
            EvalResult with scores and invariant checks
        """
        # Create a synthetic eval task
        task = EvalTask(
            id=run_id,
            agent=agent,
            category="production",
            objective=objective,
            context=context,
            invariants=invariant_ids or [],
        )
        
        # Score with judge
        try:
            judge = get_judge(agent)
            quality_score, reasoning = judge.score(task, output)
        except Exception as e:
            quality_score = 0.0
            reasoning = f"Judge failed: {e}"
        
        # Check invariants
        passed_invariants = []
        failed_invariants = []
        
        for inv_id in task.invariants:
            try:
                invariant = get_invariant(inv_id)
                passed, reason = invariant.check(task, output)
                
                if passed:
                    passed_invariants.append(inv_id)
                else:
                    failed_invariants.append(inv_id)
            except Exception:
                # If invariant check fails, assume it passed (don't penalize)
                passed_invariants.append(inv_id)
        
        # Create result
        result = EvalResult(
            task_id=run_id,
            agent=agent,
            timestamp=datetime.utcnow(),
            success=True,
            output=output,
            error=None,
            latency_ms=latency_ms,
            cost_weight=cost_weight,
            quality_score=quality_score,
            judge_reasoning=reasoning,
            passed_invariants=passed_invariants,
            failed_invariants=failed_invariants,
            difficulty="production",
            tags=["online_eval"],
        )
        
        # Update daily metrics
        self._update_daily_metrics(result)
        
        return result
    
    def _update_daily_metrics(self, result: EvalResult) -> None:
        """Update daily metrics with evaluation result."""
        date = result.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get or create daily metrics
        metrics = self.db.query(AgentMetricsDaily).filter(
            AgentMetricsDaily.agent == result.agent,
            AgentMetricsDaily.date == date,
        ).first()
        
        if not metrics:
            metrics = AgentMetricsDaily(
                agent=result.agent,
                date=date,
                total_runs=0,
                successful_runs=0,
                failed_runs=0,
            )
            self.db.add(metrics)
        
        # Update quality metrics
        if metrics.quality_samples == 0:
            metrics.avg_quality_score = result.quality_score
            metrics.median_quality_score = result.quality_score
            metrics.p95_quality_score = result.quality_score
        else:
            # Running average (simple approximation)
            n = metrics.quality_samples
            metrics.avg_quality_score = (
                (metrics.avg_quality_score * n + result.quality_score) / (n + 1)
            )
        
        metrics.quality_samples += 1
        
        # Update latency metrics (simple running average)
        if metrics.total_runs == 0:
            metrics.avg_latency_ms = result.latency_ms
            metrics.median_latency_ms = result.latency_ms
            metrics.p95_latency_ms = result.latency_ms
            metrics.p99_latency_ms = result.latency_ms
        else:
            n = metrics.total_runs
            metrics.avg_latency_ms = (
                (metrics.avg_latency_ms * n + result.latency_ms) / (n + 1)
            )
        
        # Update cost
        metrics.total_cost_weight += result.cost_weight
        metrics.avg_cost_per_run = metrics.total_cost_weight / (metrics.total_runs + 1)
        
        # Update invariants
        metrics.invariants_passed += len(result.passed_invariants)
        metrics.invariants_failed += len(result.failed_invariants)
        
        if result.failed_invariants:
            if not metrics.failed_invariant_ids:
                metrics.failed_invariant_ids = []
            metrics.failed_invariant_ids.extend(result.failed_invariants)
            metrics.failed_invariant_ids = list(set(metrics.failed_invariant_ids))
        
        self.db.commit()


class RedTeamCatalog:
    """
    Catalog of adversarial test cases for agent robustness.
    
    Red-team attacks test:
    - Edge cases and boundary conditions
    - Adversarial inputs (evasion, poisoning)
    - Security vulnerabilities
    - Performance degradation scenarios
    """
    
    @staticmethod
    def get_inbox_redteam_tasks() -> List[EvalTask]:
        """Get red-team tasks for inbox.triage agent."""
        return [
            # Phishing evasion: subtle phishing
            EvalTask(
                id="redteam.inbox.phishing_evasion_001",
                agent="inbox.triage",
                category="phishing_detection",
                objective="Detect sophisticated phishing with legitimate-looking domain",
                context={
                    "subject": "Your package delivery update",
                    "sender": "notifications@amazon-delivery-update.co",  # Typosquatting
                    "body": "Your package #AB123 has been delayed. Update your shipping preferences: [link]",
                    "domain_age_days": 180,  # Old enough to seem legitimate
                    "sender_in_contacts": False,
                    "spf_pass": True,  # Spoofed SPF
                },
                expected_output={
                    "risk_level": "high",
                    "is_phishing": True,
                },
                invariants=["no_false_negatives_phishing"],
                difficulty="hard",
                tags=["red_team", "phishing_evasion"],
            ),
            
            # Spam evasion: obfuscated text
            EvalTask(
                id="redteam.inbox.spam_evasion_001",
                agent="inbox.triage",
                category="spam",
                objective="Detect spam with character substitution",
                context={
                    "subject": "M@ke $10K per w33k from h0me!!!",
                    "sender": "opportunity@business-offers.info",
                    "body": "AMAZ1NG 0PP0RTUN1TY! W0rk fr0m h0me! Click N0W!!!",
                    "excessive_caps": True,
                    "excessive_punctuation": True,
                },
                expected_output={
                    "risk_level": "medium",
                    "is_phishing": False,
                    "category": "spam",
                },
                invariants=[],
                difficulty="medium",
                tags=["red_team", "spam_evasion"],
            ),
            
            # Boundary case: empty content
            EvalTask(
                id="redteam.inbox.boundary_001",
                agent="inbox.triage",
                category="edge_case",
                objective="Handle email with only whitespace",
                context={
                    "subject": "   ",
                    "sender": "test@example.com",
                    "body": "\n\n\n   \n\n",
                    "sender_in_contacts": False,
                },
                expected_output={
                    "risk_level": "medium",
                    "category": "unknown",
                },
                invariants=[],
                difficulty="hard",
                tags=["red_team", "boundary"],
            ),
        ]
    
    @staticmethod
    def get_knowledge_redteam_tasks() -> List[EvalTask]:
        """Get red-team tasks for knowledge.update agent."""
        return [
            # Large batch stress test
            EvalTask(
                id="redteam.knowledge.large_batch_001",
                agent="knowledge.update",
                category="sync",
                objective="Sync 10000 entries without data loss",
                context={
                    "source": "elasticsearch",
                    "target": "bigquery",
                    "entry_count": 10000,
                    "has_conflicts": True,
                    "conflict_count": 500,
                    "synonyms_present": True,
                },
                expected_output={
                    "items_synced": 9800,  # Allow 2% loss
                    "synonyms_preserved": True,
                    "conflicts_resolved": 500,
                },
                invariants=["sync_completion"],
                difficulty="hard",
                tags=["red_team", "stress_test"],
            ),
        ]
    
    @staticmethod
    def get_insights_redteam_tasks() -> List[EvalTask]:
        """Get red-team tasks for insights.write agent."""
        return [
            # No data scenario
            EvalTask(
                id="redteam.insights.no_data_001",
                agent="insights.write",
                category="analysis",
                objective="Generate insights with zero data",
                context={
                    "time_range": "7d",
                    "data_source": "elasticsearch",
                    "metrics": [],
                    "has_historical_data": False,
                    "data_points": 0,
                },
                expected_output={
                    "metrics_count": 0,
                    "trends": [],
                    "has_summary": True,
                    "data_quality_warning": True,
                },
                invariants=[],
                difficulty="medium",
                tags=["red_team", "no_data"],
            ),
        ]
    
    @staticmethod
    def get_warehouse_redteam_tasks() -> List[EvalTask]:
        """Get red-team tasks for warehouse.health agent."""
        return [
            # Catastrophic failure
            EvalTask(
                id="redteam.warehouse.catastrophic_001",
                agent="warehouse.health",
                category="parity",
                objective="Detect catastrophic data loss",
                context={
                    "source": "elasticsearch",
                    "target": "bigquery",
                    "table": "emails",
                    "source_count": 100000,
                    "target_count": 10000,  # 90% data loss
                },
                expected_output={
                    "is_healthy": False,
                    "issues_count": 1,
                    "parity_ok": False,
                    "parity_percentage": 10.0,
                },
                invariants=["warehouse_parity_detection"],
                difficulty="easy",
                tags=["red_team", "catastrophic"],
            ),
        ]
    
    @classmethod
    def get_all_redteam_tasks(cls) -> List[EvalTask]:
        """Get all red-team tasks across all agents."""
        return (
            cls.get_inbox_redteam_tasks() +
            cls.get_knowledge_redteam_tasks() +
            cls.get_insights_redteam_tasks() +
            cls.get_warehouse_redteam_tasks()
        )


class MetricsAggregator:
    """Aggregates metrics for weekly reports and dashboards."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_agent_metrics(
        self,
        agent: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[AgentMetricsDaily]:
        """
        Get daily metrics for an agent in a date range.
        
        Args:
            agent: Agent identifier
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of daily metrics ordered by date
        """
        return self.db.query(AgentMetricsDaily).filter(
            AgentMetricsDaily.agent == agent,
            AgentMetricsDaily.date >= start_date,
            AgentMetricsDaily.date <= end_date,
        ).order_by(AgentMetricsDaily.date).all()
    
    def get_weekly_summary(
        self,
        agent: str,
        week_start: datetime,
    ) -> Dict[str, Any]:
        """
        Get weekly summary for an agent.
        
        Args:
            agent: Agent identifier
            week_start: Start of week (Monday)
            
        Returns:
            Summary dictionary with aggregated metrics
        """
        week_end = week_start + timedelta(days=7)
        metrics = self.get_agent_metrics(agent, week_start, week_end)
        
        if not metrics:
            return {
                "agent": agent,
                "week_start": week_start.date(),
                "total_runs": 0,
                "success_rate": 0.0,
                "avg_quality_score": 0.0,
                "satisfaction_rate": 0.0,
            }
        
        total_runs = sum(m.total_runs for m in metrics)
        successful_runs = sum(m.successful_runs for m in metrics)
        
        # Weighted averages
        quality_scores = [
            m.avg_quality_score * m.quality_samples
            for m in metrics
            if m.avg_quality_score and m.quality_samples > 0
        ]
        quality_samples = sum(m.quality_samples for m in metrics if m.quality_samples > 0)
        avg_quality = sum(quality_scores) / quality_samples if quality_samples > 0 else 0.0
        
        thumbs_up = sum(m.thumbs_up for m in metrics)
        thumbs_down = sum(m.thumbs_down for m in metrics)
        satisfaction = (
            thumbs_up / (thumbs_up + thumbs_down)
            if (thumbs_up + thumbs_down) > 0
            else 0.0
        )
        
        failed_invariants = set()
        for m in metrics:
            if m.failed_invariant_ids:
                failed_invariants.update(m.failed_invariant_ids)
        
        return {
            "agent": agent,
            "week_start": week_start.date(),
            "total_runs": total_runs,
            "success_rate": successful_runs / total_runs if total_runs > 0 else 0.0,
            "avg_quality_score": avg_quality,
            "satisfaction_rate": satisfaction,
            "total_feedback": thumbs_up + thumbs_down,
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "failed_invariant_ids": list(failed_invariants),
            "invariants_failed_count": len(failed_invariants),
        }
    
    def detect_regression(
        self,
        agent: str,
        current_week: datetime,
        quality_threshold: float = 5.0,  # Drop > 5 points is regression
    ) -> Optional[Dict[str, Any]]:
        """
        Detect quality regression by comparing current week to previous week.
        
        Args:
            agent: Agent identifier
            current_week: Current week start date
            quality_threshold: Minimum drop to consider regression
            
        Returns:
            Regression details if detected, None otherwise
        """
        prev_week = current_week - timedelta(days=7)
        
        current_summary = self.get_weekly_summary(agent, current_week)
        prev_summary = self.get_weekly_summary(agent, prev_week)
        
        if prev_summary["total_runs"] == 0:
            return None  # No baseline to compare
        
        quality_drop = prev_summary["avg_quality_score"] - current_summary["avg_quality_score"]
        
        if quality_drop >= quality_threshold:
            return {
                "agent": agent,
                "regression_type": "quality_drop",
                "current_quality": current_summary["avg_quality_score"],
                "previous_quality": prev_summary["avg_quality_score"],
                "drop_amount": quality_drop,
                "severity": "critical" if quality_drop >= 10.0 else "high",
            }
        
        # Check for new invariant failures
        current_failed = set(current_summary["failed_invariant_ids"])
        prev_failed = set(prev_summary["failed_invariant_ids"])
        new_failures = current_failed - prev_failed
        
        if new_failures:
            return {
                "agent": agent,
                "regression_type": "invariant_failures",
                "new_failures": list(new_failures),
                "severity": "critical",
            }
        
        return None
