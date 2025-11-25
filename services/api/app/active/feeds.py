"""Feed loaders for labeled examples.

Loads labeled training data from multiple sources:
- Agent approvals (user decisions on actions)
- Feedback API (thumbs up/down ratings)
- Gold sets (curated evaluation tasks)
- Synthetic tasks (generated examples)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models import AgentApproval, AgentMetricsDaily
from ..models_al import LabeledExample
from ..eval.models import EvalTask

logger = logging.getLogger(__name__)


class FeedLoader:
    """Loads labeled examples from various sources into unified store."""

    def __init__(self, db_session: Session):
        """Initialize feed loader.

        Args:
            db_session: Database session
        """
        self.db = db_session

    def load_from_approvals(
        self, since: Optional[datetime] = None, limit: int = 1000
    ) -> int:
        """Load labeled examples from agent approvals.

        Args:
            since: Load approvals created after this time (default: last 7 days)
            limit: Maximum number of approvals to load

        Returns:
            Number of labeled examples created
        """
        if since is None:
            since = datetime.utcnow() - timedelta(days=7)

        # Query approved or rejected approvals
        approvals = (
            self.db.query(AgentApproval)
            .filter(
                and_(
                    AgentApproval.created_at >= since,
                    AgentApproval.status.in_(["approved", "rejected"]),
                )
            )
            .order_by(AgentApproval.created_at.desc())
            .limit(limit)
            .all()
        )

        count = 0
        for approval in approvals:
            # Check if already loaded
            exists = (
                self.db.query(LabeledExample)
                .filter_by(source="approvals", source_id=approval.request_id)
                .first()
            )

            if exists:
                continue

            # Extract label from approval decision
            if approval.status == "approved":
                label = f"{approval.action}_approved"
            else:
                label = f"{approval.action}_rejected"

            # Create labeled example
            example = LabeledExample(
                agent=approval.agent,
                key=approval.request_id,
                payload=approval.context or {},
                label=label,
                source="approvals",
                source_id=approval.request_id,
                version="v1",
                confidence=100,  # Explicit human decision
                notes=approval.rationale,
            )

            self.db.add(example)
            count += 1

        if count > 0:
            self.db.commit()
            logger.info(f"Loaded {count} labeled examples from approvals")

        return count

    def load_from_feedback(
        self, since: Optional[datetime] = None, limit: int = 1000
    ) -> int:
        """Load labeled examples from feedback API.

        Note: This queries AgentMetricsDaily for aggregated feedback.
        In a full implementation, would query a dedicated feedback table.

        Args:
            since: Load feedback after this time (default: last 7 days)
            limit: Maximum number of feedback records to load

        Returns:
            Number of labeled examples created
        """
        if since is None:
            since = datetime.utcnow() - timedelta(days=7)

        # Query metrics with feedback data
        metrics = (
            self.db.query(AgentMetricsDaily)
            .filter(
                and_(
                    AgentMetricsDaily.date >= since,
                    AgentMetricsDaily.feedback_count > 0,
                )
            )
            .limit(limit)
            .all()
        )

        count = 0
        for metric in metrics:
            # Calculate label from feedback ratio
            if metric.feedback_count == 0:
                continue

            thumbs_up_ratio = metric.thumbs_up / metric.feedback_count

            if thumbs_up_ratio >= 0.8:
                label = "high_quality"
            elif thumbs_up_ratio >= 0.5:
                label = "medium_quality"
            else:
                label = "low_quality"

            # Create aggregate example (one per agent per day)
            key = f"{metric.agent}_{metric.date.date()}"

            # Check if already loaded
            exists = (
                self.db.query(LabeledExample)
                .filter_by(source="feedback", key=key)
                .first()
            )

            if exists:
                continue

            example = LabeledExample(
                agent=metric.agent,
                key=key,
                payload={
                    "feedback_count": metric.feedback_count,
                    "thumbs_up": metric.thumbs_up,
                    "thumbs_down": metric.thumbs_down,
                    "avg_quality_score": metric.avg_quality_score,
                    "success_rate": metric.success_rate,
                },
                label=label,
                source="feedback",
                source_id=str(metric.id),
                version="v1",
                confidence=int(thumbs_up_ratio * 100),
            )

            self.db.add(example)
            count += 1

        if count > 0:
            self.db.commit()
            logger.info(f"Loaded {count} labeled examples from feedback")

        return count

    def load_from_goldsets(self, agent: Optional[str] = None, limit: int = 1000) -> int:
        """Load labeled examples from gold sets (Phase 5 evaluation tasks).

        Args:
            agent: Filter by agent (optional)
            limit: Maximum number of gold tasks to load

        Returns:
            Number of labeled examples created
        """
        # Query golden tasks
        query = self.db.query(EvalTask)
        if agent:
            query = query.filter_by(agent=agent)

        tasks = query.limit(limit).all()

        count = 0
        for task in tasks:
            # Check if already loaded
            exists = (
                self.db.query(LabeledExample)
                .filter_by(source="gold", source_id=task.id)
                .first()
            )

            if exists:
                continue

            # Create labeled example
            example = LabeledExample(
                agent=task.agent,
                key=task.id,
                payload=task.input_data or {},
                label=task.expected_action or "unknown",
                source="gold",
                source_id=task.id,
                version="v1",
                confidence=100,  # Curated examples
                notes=task.description,
            )

            self.db.add(example)
            count += 1

        if count > 0:
            self.db.commit()
            logger.info(f"Loaded {count} labeled examples from gold sets")

        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics on labeled examples.

        Returns:
            Stats dictionary with counts by source and agent
        """
        total = self.db.query(LabeledExample).count()

        # Count by source
        by_source = {}
        for source in ["approvals", "feedback", "gold", "synthetic"]:
            count = self.db.query(LabeledExample).filter_by(source=source).count()
            by_source[source] = count

        # Count by agent
        agents = self.db.query(LabeledExample.agent).distinct().all()
        by_agent = {}
        for (agent,) in agents:
            count = self.db.query(LabeledExample).filter_by(agent=agent).count()
            by_agent[agent] = count

        # Recent growth (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent = (
            self.db.query(LabeledExample)
            .filter(LabeledExample.created_at >= week_ago)
            .count()
        )

        return {
            "total": total,
            "by_source": by_source,
            "by_agent": by_agent,
            "recent_7d": recent,
        }


def load_all_feeds(db_session: Session) -> Dict[str, int]:
    """Load labeled examples from all sources.

    Args:
        db_session: Database session

    Returns:
        Dictionary with counts per source
    """
    loader = FeedLoader(db_session)

    counts = {
        "approvals": loader.load_from_approvals(),
        "feedback": loader.load_from_feedback(),
        "gold": loader.load_from_goldsets(),
    }

    logger.info(f"Feed load complete: {counts}")
    return counts
