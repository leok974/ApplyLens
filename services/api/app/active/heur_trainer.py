"""Heuristic trainer for active learning.

Trains simple deterministic models on labeled examples to update planner configs.
Supports per-agent feature extraction and training strategies.

Design:
- Feature extractors convert payloads to numeric vectors
- Deterministic trainers (logistic regression, decision trees)
- Output: Config bundle (JSON) with updated thresholds/weights
- No external LLM calls - all local computation
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import Counter

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler
import numpy as np

from app.models_al import LabeledExample

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Extract numeric features from agent payloads."""
    
    @staticmethod
    def extract_inbox_triage(payload: Dict[str, Any]) -> List[float]:
        """Extract features for inbox_triage agent.
        
        Features:
        - risk_score (0-100)
        - has_spf_fail (0/1)
        - has_dkim_fail (0/1)
        - suspicious_keywords_count
        - attachment_count
        - sender_domain_age_days
        - recipient_count
        """
        return [
            payload.get("risk_score", 0),
            1 if payload.get("spf_fail") else 0,
            1 if payload.get("dkim_fail") else 0,
            len(payload.get("suspicious_keywords", [])),
            len(payload.get("attachments", [])),
            payload.get("sender_domain_age_days", 0),
            payload.get("recipient_count", 1)
        ]
    
    @staticmethod
    def extract_insights_writer(payload: Dict[str, Any]) -> List[float]:
        """Extract features for insights_writer agent.
        
        Features:
        - pattern_strength (0-100)
        - data_points_count
        - confidence_score (0-100)
        - statistical_significance (0-1)
        - novelty_score (0-100)
        """
        return [
            payload.get("pattern_strength", 0),
            payload.get("data_points_count", 0),
            payload.get("confidence_score", 0),
            payload.get("statistical_significance", 0),
            payload.get("novelty_score", 0)
        ]
    
    @staticmethod
    def extract_knowledge_update(payload: Dict[str, Any]) -> List[float]:
        """Extract features for knowledge_update agent.
        
        Features:
        - similarity_score (0-100)
        - frequency_delta
        - co_occurrence_count
        - context_overlap_ratio (0-1)
        """
        return [
            payload.get("similarity_score", 0),
            payload.get("frequency_delta", 0),
            payload.get("co_occurrence_count", 0),
            payload.get("context_overlap_ratio", 0)
        ]
    
    @staticmethod
    def extract_for_agent(agent: str, payload: Dict[str, Any]) -> Optional[List[float]]:
        """Extract features for specified agent."""
        extractors = {
            "inbox_triage": FeatureExtractor.extract_inbox_triage,
            "insights_writer": FeatureExtractor.extract_insights_writer,
            "knowledge_update": FeatureExtractor.extract_knowledge_update
        }
        
        extractor = extractors.get(agent)
        if not extractor:
            logger.warning(f"No feature extractor for agent: {agent}")
            return None
        
        return extractor(payload)


class HeuristicTrainer:
    """Train deterministic models on labeled examples."""
    
    def __init__(self, db_session):
        self.db = db_session
        self.scaler = StandardScaler()
    
    def train_for_agent(
        self,
        agent: str,
        min_examples: int = 50,
        model_type: str = "logistic"
    ) -> Optional[Dict[str, Any]]:
        """Train a model for specified agent.
        
        Args:
            agent: Agent name (inbox_triage, insights_writer, etc.)
            min_examples: Minimum labeled examples required
            model_type: "logistic" or "tree"
        
        Returns:
            Config bundle dict with updated params, or None if insufficient data
        """
        # Fetch labeled examples
        examples = self.db.query(LabeledExample).filter_by(agent=agent).all()
        
        if len(examples) < min_examples:
            logger.info(f"Insufficient examples for {agent}: {len(examples)} < {min_examples}")
            return None
        
        # Extract features and labels
        X = []
        y = []
        
        for ex in examples:
            features = FeatureExtractor.extract_for_agent(agent, ex.payload)
            if features is None:
                continue
            
            X.append(features)
            y.append(ex.label)
        
        if len(X) == 0:
            logger.warning(f"No valid features extracted for {agent}")
            return None
        
        X = np.array(X)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        if model_type == "logistic":
            model = LogisticRegression(random_state=42, max_iter=1000)
        elif model_type == "tree":
            model = DecisionTreeClassifier(random_state=42, max_depth=5)
        else:
            raise ValueError(f"Unknown model_type: {model_type}")
        
        model.fit(X_scaled, y)
        
        # Generate config bundle
        bundle = self._generate_bundle(agent, model, X, y, examples)
        
        logger.info(f"Trained {model_type} for {agent}: {len(X)} examples, accuracy={bundle['accuracy']:.2f}")
        
        return bundle
    
    def _generate_bundle(
        self,
        agent: str,
        model,
        X: np.ndarray,
        y: List[str],
        examples: List[LabeledExample]
    ) -> Dict[str, Any]:
        """Generate config bundle from trained model."""
        # Calculate accuracy
        predictions = model.predict(self.scaler.transform(X))
        accuracy = np.mean(predictions == y)
        
        # Extract feature importances (if available)
        feature_importances = None
        if hasattr(model, "feature_importances_"):
            feature_importances = model.feature_importances_.tolist()
        elif hasattr(model, "coef_"):
            # For logistic regression, use absolute coefficients
            feature_importances = np.abs(model.coef_[0]).tolist()
        
        # Analyze label distribution
        label_counts = Counter(y)
        
        # Generate thresholds based on model
        thresholds = self._extract_thresholds(agent, model, feature_importances)
        
        return {
            "agent": agent,
            "version": "v1",
            "created_at": datetime.utcnow().isoformat(),
            "training_count": len(examples),
            "accuracy": float(accuracy),
            "label_distribution": dict(label_counts),
            "feature_importances": feature_importances,
            "thresholds": thresholds,
            "model_type": model.__class__.__name__,
            "sources_used": list({ex.source for ex in examples})
        }
    
    def _extract_thresholds(
        self,
        agent: str,
        model,
        feature_importances: Optional[List[float]]
    ) -> Dict[str, Any]:
        """Extract threshold recommendations from model."""
        if agent == "inbox_triage":
            # For logistic regression, use decision boundary
            if hasattr(model, "intercept_"):
                intercept = float(model.intercept_[0])
                coeffs = model.coef_[0].tolist()
                
                # Calculate recommended risk_score threshold
                # Assuming first feature is risk_score
                if len(coeffs) > 0 and coeffs[0] != 0:
                    risk_threshold = -intercept / coeffs[0]
                    risk_threshold = max(0, min(100, risk_threshold))  # Clamp to [0,100]
                else:
                    risk_threshold = 50.0  # Default
                
                return {
                    "risk_score_threshold": round(risk_threshold, 1),
                    "spf_dkim_weight": round(abs(coeffs[1] + coeffs[2]), 2) if len(coeffs) > 2 else 1.0
                }
        
        elif agent == "insights_writer":
            if hasattr(model, "intercept_"):
                intercept = float(model.intercept_[0])
                coeffs = model.coef_[0].tolist()
                
                # Pattern strength threshold
                if len(coeffs) > 0 and coeffs[0] != 0:
                    pattern_threshold = -intercept / coeffs[0]
                    pattern_threshold = max(0, min(100, pattern_threshold))
                else:
                    pattern_threshold = 70.0
                
                return {
                    "pattern_strength_threshold": round(pattern_threshold, 1),
                    "min_data_points": 10
                }
        
        elif agent == "knowledge_update":
            if hasattr(model, "intercept_"):
                intercept = float(model.intercept_[0])
                coeffs = model.coef_[0].tolist()
                
                # Similarity threshold
                if len(coeffs) > 0 and coeffs[0] != 0:
                    similarity_threshold = -intercept / coeffs[0]
                    similarity_threshold = max(0, min(100, similarity_threshold))
                else:
                    similarity_threshold = 80.0
                
                return {
                    "similarity_threshold": round(similarity_threshold, 1),
                    "min_co_occurrence": 3
                }
        
        # Default fallback
        return {}
    
    def generate_diff(
        self,
        agent: str,
        old_bundle: Optional[Dict[str, Any]],
        new_bundle: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate diff between old and new config bundles.
        
        Returns:
            Diff dict with changes, additions, and removals
        """
        if old_bundle is None:
            return {
                "type": "initial",
                "changes": [],
                "additions": list(new_bundle["thresholds"].keys()),
                "removals": [],
                "summary": f"Initial config for {agent}"
            }
        
        old_thresholds = old_bundle.get("thresholds", {})
        new_thresholds = new_bundle["thresholds"]
        
        changes = []
        additions = []
        removals = []
        
        # Find changes and additions
        for key, new_val in new_thresholds.items():
            if key not in old_thresholds:
                additions.append(key)
            elif old_thresholds[key] != new_val:
                old_val = old_thresholds[key]
                delta = new_val - old_val if isinstance(new_val, (int, float)) else None
                changes.append({
                    "param": key,
                    "old": old_val,
                    "new": new_val,
                    "delta": delta
                })
        
        # Find removals
        for key in old_thresholds:
            if key not in new_thresholds:
                removals.append(key)
        
        summary = f"{len(changes)} changes, {len(additions)} additions, {len(removals)} removals"
        
        return {
            "type": "update",
            "changes": changes,
            "additions": additions,
            "removals": removals,
            "summary": summary,
            "accuracy_delta": new_bundle["accuracy"] - old_bundle.get("accuracy", 0)
        }
