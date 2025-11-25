"""Uncertainty sampler for active learning.

Identifies edge cases for human review based on:
- Ensemble disagreement (variance in judge predictions)
- Low confidence predictions
- High-stakes decisions

Design:
- Sample candidates with highest uncertainty
- Populate review queue for human labeling
- Prioritize by risk/impact
"""

import logging
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from collections import Counter
import json

import numpy as np

from app.models_al import LabeledExample
from app.eval.models import EvalResult

logger = logging.getLogger(__name__)


class UncertaintySampler:
    """Sample uncertain predictions for human review."""

    def __init__(self, db_session):
        self.db = db_session

    def calculate_uncertainty(
        self, judge_scores: Dict[str, Dict], judge_weights: Dict[str, float]
    ) -> Tuple[float, str]:
        """Calculate uncertainty score from judge ensemble.

        Args:
            judge_scores: Dict of judge_name -> {verdict, confidence}
            judge_weights: Dict of judge_name -> reliability weight

        Returns:
            (uncertainty_score, method) where method is "disagreement", "low_confidence", or "weighted_variance"
        """
        if not judge_scores:
            return 1.0, "no_judges"

        verdicts = []
        confidences = []
        weights = []

        for judge_name, score_data in judge_scores.items():
            verdict = score_data.get("verdict")
            confidence = score_data.get("confidence", 50) / 100.0  # Normalize to 0-1
            weight = judge_weights.get(judge_name, 0.5)

            if verdict:
                verdicts.append(verdict)
                confidences.append(confidence)
                weights.append(weight)

        if len(verdicts) == 0:
            return 1.0, "no_verdicts"

        # Method 1: Disagreement - multiple distinct verdicts
        verdict_counts = Counter(verdicts)
        if len(verdict_counts) > 1:
            # Entropy-based disagreement
            total = len(verdicts)
            entropy = -sum(
                (count / total) * np.log2(count / total)
                for count in verdict_counts.values()
            )
            max_entropy = np.log2(len(verdict_counts))
            disagreement = entropy / max_entropy if max_entropy > 0 else 0

            return disagreement, "disagreement"

        # Method 2: Low confidence
        weighted_confidence = np.average(confidences, weights=weights)
        if weighted_confidence < 0.6:
            uncertainty = 1.0 - weighted_confidence
            return uncertainty, "low_confidence"

        # Method 3: Weighted variance
        confidence_variance = np.average(
            [(c - weighted_confidence) ** 2 for c in confidences], weights=weights
        )
        uncertainty = min(1.0, confidence_variance * 4)  # Scale to [0, 1]

        return uncertainty, "weighted_variance"

    def sample_for_review(
        self,
        agent: str,
        lookback_days: int = 7,
        min_uncertainty: float = 0.5,
        top_n: int = 50,
    ) -> List[Dict]:
        """Sample uncertain predictions for human review.

        Args:
            agent: Agent name (inbox_triage, etc.)
            lookback_days: How many days to look back
            min_uncertainty: Minimum uncertainty threshold
            top_n: Max candidates to return

        Returns:
            List of candidate dicts with task_key, uncertainty, method, payload
        """
        since = datetime.utcnow() - timedelta(days=lookback_days)

        # Fetch recent evaluation results
        eval_results = (
            self.db.query(EvalResult)
            .filter(
                EvalResult.agent == agent,
                EvalResult.created_at >= since,
                EvalResult.judge_scores.isnot(None),
            )
            .all()
        )

        if not eval_results:
            logger.info(f"No eval results for {agent} in last {lookback_days} days")
            return []

        # Filter out already-labeled examples
        labeled_keys = {
            ex.key
            for ex in self.db.query(LabeledExample.key)
            .filter(LabeledExample.agent == agent)
            .all()
        }

        # Load judge weights
        from app.active.weights import JudgeWeights

        weights_mgr = JudgeWeights(self.db)
        judge_weights = weights_mgr.get_weights(agent)

        # Calculate uncertainty for each result
        candidates = []

        for result in eval_results:
            if result.task_key in labeled_keys:
                continue  # Already labeled

            # Parse judge scores
            judge_scores = result.judge_scores
            if isinstance(judge_scores, str):
                judge_scores = json.loads(judge_scores)

            uncertainty, method = self.calculate_uncertainty(
                judge_scores, judge_weights
            )

            if uncertainty >= min_uncertainty:
                candidates.append(
                    {
                        "task_key": result.task_key,
                        "agent": agent,
                        "uncertainty": round(uncertainty, 3),
                        "method": method,
                        "judge_scores": judge_scores,
                        "payload": result.task_input,
                        "created_at": result.created_at.isoformat(),
                        "eval_result_id": result.id,
                    }
                )

        # Sort by uncertainty descending
        candidates.sort(key=lambda x: x["uncertainty"], reverse=True)

        # Return top N
        top_candidates = candidates[:top_n]

        logger.info(
            f"Sampled {len(top_candidates)} uncertain predictions for {agent} "
            f"(out of {len(eval_results)} total, {len(labeled_keys)} already labeled)"
        )

        return top_candidates

    def sample_all_agents(
        self,
        lookback_days: int = 7,
        min_uncertainty: float = 0.5,
        top_n_per_agent: int = 20,
    ) -> Dict[str, List[Dict]]:
        """Sample uncertain predictions for all agents.

        Returns:
            Dict of agent -> list of candidates
        """
        # Get distinct agents from eval results
        agents = self.db.query(EvalResult.agent).distinct().all()

        agents = [a[0] for a in agents]

        results = {}
        for agent in agents:
            try:
                candidates = self.sample_for_review(
                    agent,
                    lookback_days=lookback_days,
                    min_uncertainty=min_uncertainty,
                    top_n=top_n_per_agent,
                )
                if candidates:
                    results[agent] = candidates
            except Exception as e:
                logger.error(f"Failed to sample for {agent}: {e}")

        return results

    def get_review_queue_stats(self) -> Dict[str, int]:
        """Get statistics on review queue.

        Returns:
            Dict with total unlabeled, by_agent, by_uncertainty_range
        """
        # Count unlabeled eval results
        total = self.db.query(EvalResult).count()

        labeled_count = self.db.query(LabeledExample).count()

        # Approximate unlabeled (rough estimate)
        unlabeled = total - labeled_count

        # Count by agent
        by_agent = {}
        agents = self.db.query(EvalResult.agent).distinct().all()

        for (agent,) in agents:
            agent_total = (
                self.db.query(EvalResult).filter(EvalResult.agent == agent).count()
            )
            agent_labeled = (
                self.db.query(LabeledExample)
                .filter(LabeledExample.agent == agent)
                .count()
            )
            by_agent[agent] = agent_total - agent_labeled

        return {
            "total_unlabeled": max(0, unlabeled),
            "by_agent": by_agent,
            "total_eval_results": total,
            "total_labeled": labeled_count,
        }


def daily_sample_review_queue(
    db_session, top_n_per_agent: int = 20
) -> Dict[str, List[Dict]]:
    """Daily job to sample review queue candidates.

    Should be called by scheduler.

    Returns:
        Dict of agent -> candidates (can be stored or emailed to reviewers)
    """
    logger.info("Starting daily review queue sampling")

    sampler = UncertaintySampler(db_session)
    candidates = sampler.sample_all_agents(
        lookback_days=7, min_uncertainty=0.5, top_n_per_agent=top_n_per_agent
    )

    total_candidates = sum(len(c) for c in candidates.values())
    logger.info(
        f"Sampled {total_candidates} candidates across {len(candidates)} agents"
    )

    for agent, agent_candidates in candidates.items():
        logger.info(f"  {agent}: {len(agent_candidates)} candidates")

    return candidates
