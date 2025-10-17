"""Judge reliability weighting for active learning.

Assigns reliability weights to LLM judges based on:
- Calibration error (predicted confidence vs actual accuracy)
- Agreement with human labels
- Recent performance with exponential decay

Design:
- Nightly weight updates per agent
- Stores weights in runtime_settings
- Used to weight judge votes in evaluation
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

import numpy as np

from app.models import RuntimeSetting
from app.models_al import LabeledExample
from app.eval.models import EvaluationResult

logger = logging.getLogger(__name__)


class JudgeWeights:
    """Manage reliability weights for LLM judges."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def update_weights_for_agent(
        self,
        agent: str,
        lookback_days: int = 30,
        decay_halflife_days: float = 7.0
    ) -> Dict[str, float]:
        """Update judge reliability weights for an agent.
        
        Args:
            agent: Agent name (inbox_triage, etc.)
            lookback_days: How many days to look back
            decay_halflife_days: Exponential decay half-life
        
        Returns:
            Dict of judge_name -> weight (0-1)
        """
        since = datetime.utcnow() - timedelta(days=lookback_days)
        
        # Fetch evaluation results with judge scores
        eval_results = (
            self.db.query(EvaluationResult)
            .filter(
                EvaluationResult.agent == agent,
                EvaluationResult.created_at >= since,
                EvaluationResult.judge_scores.isnot(None)
            )
            .all()
        )
        
        if not eval_results:
            logger.info(f"No eval results for {agent}, using default weights")
            return self._get_default_weights()
        
        # Fetch labeled examples for validation
        labeled = (
            self.db.query(LabeledExample)
            .filter(
                LabeledExample.agent == agent,
                LabeledExample.created_at >= since,
                LabeledExample.source.in_(["approvals", "gold"])  # High-confidence labels
            )
            .all()
        )
        
        # Build key -> label mapping
        label_map = {ex.key: ex.label for ex in labeled}
        
        # Calculate per-judge metrics
        judge_metrics = defaultdict(lambda: {
            "predictions": [],
            "actuals": [],
            "confidences": [],
            "timestamps": []
        })
        
        for result in eval_results:
            if result.task_key not in label_map:
                continue
            
            actual_label = label_map[result.task_key]
            
            # Parse judge scores
            judge_scores = result.judge_scores
            if isinstance(judge_scores, str):
                judge_scores = json.loads(judge_scores)
            
            for judge_name, score_data in judge_scores.items():
                predicted_label = score_data.get("verdict")
                confidence = score_data.get("confidence", 50) / 100.0  # Normalize to 0-1
                
                if predicted_label:
                    judge_metrics[judge_name]["predictions"].append(predicted_label)
                    judge_metrics[judge_name]["actuals"].append(actual_label)
                    judge_metrics[judge_name]["confidences"].append(confidence)
                    judge_metrics[judge_name]["timestamps"].append(result.created_at)
        
        # Calculate weights per judge
        weights = {}
        now = datetime.utcnow()
        
        for judge_name, metrics in judge_metrics.items():
            if len(metrics["predictions"]) < 5:
                # Insufficient data, use default
                weights[judge_name] = 0.5
                continue
            
            # Calculate agreement rate with exponential time decay
            agreements = np.array([
                1.0 if pred == actual else 0.0
                for pred, actual in zip(metrics["predictions"], metrics["actuals"])
            ])
            
            # Calculate time decay weights
            time_deltas = [(now - ts).total_seconds() / 86400.0 for ts in metrics["timestamps"]]  # Days
            decay_weights = np.exp(-np.array(time_deltas) * np.log(2) / decay_halflife_days)
            
            # Weighted agreement rate
            weighted_agreement = np.average(agreements, weights=decay_weights)
            
            # Calculate calibration error
            confidences = np.array(metrics["confidences"])
            calibration_error = np.abs(confidences - agreements).mean()
            
            # Combined weight: agreement rate minus calibration penalty
            weight = weighted_agreement - (0.5 * calibration_error)
            weight = max(0.1, min(1.0, weight))  # Clamp to [0.1, 1.0]
            
            weights[judge_name] = round(weight, 3)
            
            logger.info(
                f"Judge {judge_name} for {agent}: "
                f"agreement={weighted_agreement:.2f}, "
                f"calibration_error={calibration_error:.2f}, "
                f"weight={weight:.3f}"
            )
        
        # Store in runtime_settings
        self._save_weights(agent, weights)
        
        return weights
    
    def _get_default_weights(self) -> Dict[str, float]:
        """Return default weights for judges."""
        return {
            "gpt-4": 0.8,
            "gpt-3.5-turbo": 0.6,
            "claude-3-opus": 0.8,
            "claude-3-sonnet": 0.7
        }
    
    def _save_weights(self, agent: str, weights: Dict[str, float]):
        """Save weights to runtime_settings."""
        key = f"judge_weights.{agent}"
        
        setting = self.db.query(RuntimeSetting).filter_by(key=key).first()
        
        if setting:
            setting.value = json.dumps(weights)
            setting.updated_at = datetime.utcnow()
        else:
            setting = RuntimeSetting(
                key=key,
                value=json.dumps(weights),
                category="active_learning"
            )
            self.db.add(setting)
        
        self.db.commit()
        logger.info(f"Saved judge weights for {agent}: {weights}")
    
    def get_weights(self, agent: str) -> Dict[str, float]:
        """Retrieve current judge weights for an agent.
        
        Args:
            agent: Agent name
        
        Returns:
            Dict of judge_name -> weight, or defaults if not found
        """
        key = f"judge_weights.{agent}"
        setting = self.db.query(RuntimeSetting).filter_by(key=key).first()
        
        if setting and setting.value:
            try:
                return json.loads(setting.value)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in judge weights for {agent}")
        
        return self._get_default_weights()
    
    def update_all_agents(self, lookback_days: int = 30) -> Dict[str, Dict[str, float]]:
        """Update judge weights for all active agents.
        
        Returns:
            Dict of agent -> weights
        """
        # Get distinct agents from labeled examples
        agents = (
            self.db.query(LabeledExample.agent)
            .distinct()
            .all()
        )
        
        agents = [a[0] for a in agents]
        
        results = {}
        for agent in agents:
            try:
                weights = self.update_weights_for_agent(agent, lookback_days=lookback_days)
                results[agent] = weights
            except Exception as e:
                logger.error(f"Failed to update weights for {agent}: {e}")
                results[agent] = self._get_default_weights()
        
        return results


def nightly_update_weights(db_session):
    """Nightly job to update all judge weights.
    
    Should be called by scheduler (e.g., APScheduler or cron).
    """
    logger.info("Starting nightly judge weight update")
    
    weights_mgr = JudgeWeights(db_session)
    results = weights_mgr.update_all_agents(lookback_days=30)
    
    logger.info(f"Updated weights for {len(results)} agents")
    
    for agent, weights in results.items():
        logger.info(f"  {agent}: {weights}")
    
    return results
