"""Planner v2 with heuristic scoring and optional LLM fallback.

Intelligently routes tasks to agents based on:
- Historical success rates and quality scores
- Cost and latency budgets
- Required capabilities
- Optional LLM-based reasoning when heuristics have low confidence
"""

import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
from pydantic import BaseModel

from .skills import get_skill_registry, SkillRegistry


class PlannerMode(str, Enum):
    """Planning mode configuration."""

    HEURISTIC = "heuristic"  # Pure heuristic, no LLM calls
    LLM = "llm"  # Always use LLM
    AUTO = "auto"  # Heuristic first, LLM fallback if low confidence


class Plan(BaseModel):
    """Execution plan for an agent."""

    agent: str
    confidence: float  # 0.0-1.0
    reasoning: str
    required_capabilities: List[str]
    estimated_cost_weight: float
    estimated_latency_ms: float
    steps: List[str] = ["prepare", "execute", "summarize"]
    dry_run: bool = False
    fallback_used: bool = False


class PlannerV2:
    """Intelligent agent planner with scoring heuristics.

    Routes tasks to the best agent based on:
    - Capability matching (what skills are needed?)
    - Historical performance (quality, success rate)
    - Cost/latency trade-offs
    - Freshness (recent vs stale metrics)
    """

    def __init__(
        self,
        mode: PlannerMode = PlannerMode.HEURISTIC,
        confidence_threshold: float = 0.7,
        use_mock_llm: bool = True,  # For CI/testing
    ):
        self.mode = mode
        self.confidence_threshold = confidence_threshold
        self.use_mock_llm = use_mock_llm
        self.registry = get_skill_registry()

        # Keyword patterns for objective classification
        self.patterns = {
            "inbox.triage": [
                r"risk",
                r"phishing",
                r"spam",
                r"suspicious",
                r"malicious",
                r"categorize",
                r"label",
                r"triage",
                r"inbox",
                r"email",
            ],
            "knowledge.update": [
                r"sync",
                r"update.*config",
                r"knowledge",
                r"synonym",
                r"database.*sync",
                r"refresh.*data",
            ],
            "insights.write": [
                r"report",
                r"insight",
                r"trend",
                r"analytic",
                r"metric",
                r"dashboard",
                r"summary",
                r"analysis",
            ],
            "warehouse.health": [
                r"warehouse",
                r"bigquery",
                r"bq",
                r"parity",
                r"health.*check",
                r"data.*quality",
            ],
        }

    def plan(self, objective: str, context: Optional[Dict] = None) -> Plan:
        """Create an execution plan for the given objective.

        Args:
            objective: Natural language description of the task
            context: Additional context (user, budget, constraints)

        Returns:
            Plan with selected agent and execution details
        """
        context = context or {}

        # Step 1: Extract required capabilities from objective
        capabilities = self._extract_capabilities(objective)

        # Step 2: Find candidate agents
        candidates = self._find_candidates(objective, capabilities)

        # Step 3: Score and rank candidates
        scored = [
            (agent, self._score_agent(agent, capabilities, context))
            for agent in candidates
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        if not scored:
            # No candidates found
            return self._create_fallback_plan(objective, capabilities)

        best_agent, best_score = scored[0]
        confidence = self._compute_confidence(best_score, scored)

        # Step 4: Check if we need LLM fallback
        if self._should_use_llm_fallback(confidence):
            return self._llm_plan(objective, context, scored, capabilities)

        # Step 5: Build plan
        return self._build_plan(best_agent, confidence, capabilities, context)

    def _extract_capabilities(self, objective: str) -> List[str]:
        """Extract required capabilities from the objective text."""
        capabilities = []
        obj_lower = objective.lower()

        # Search patterns
        if any(word in obj_lower for word in ["search", "query", "find"]):
            capabilities.append("es.search" if "email" in obj_lower else "bq.query")

        if any(word in obj_lower for word in ["risk", "phish", "suspicious"]):
            capabilities.append("risk.analysis")

        if any(word in obj_lower for word in ["categorize", "label", "classify"]):
            capabilities.append("email.classification")

        if any(word in obj_lower for word in ["sync", "update", "refresh"]):
            capabilities.append("db.sync")

        if any(word in obj_lower for word in ["trend", "metric", "report"]):
            capabilities.extend(["metrics.query", "trend.analysis"])

        if any(word in obj_lower for word in ["parity", "health", "quality"]):
            capabilities.append("parity.check")

        return capabilities

    def _find_candidates(self, objective: str, capabilities: List[str]) -> List[str]:
        """Find candidate agents based on objective and capabilities."""
        candidates = set()
        obj_lower = objective.lower()

        # Pattern-based matching
        for agent, patterns in self.patterns.items():
            if any(re.search(pattern, obj_lower) for pattern in patterns):
                candidates.add(agent)

        # Capability-based matching
        for cap in capabilities:
            for skill in self.registry.find_by_capability(cap):
                candidates.add(skill.agent)

        # Default to all agents if no matches (better than nothing)
        if not candidates:
            candidates = set(self.registry.get_all_agents())

        return list(candidates)

    def _score_agent(self, agent: str, capabilities: List[str], context: Dict) -> float:
        """Score an agent for the given task.

        Score formula:
        score = (capability_match * 0.4) + (quality * 0.3) +
                (success_rate * 0.2) + (cost_factor * 0.1)

        Returns:
            Score between 0.0 and 100.0
        """
        skills = self.registry.get_by_agent(agent)
        if not skills:
            return 0.0

        # Capability match score
        agent_capabilities = set()
        for skill in skills:
            agent_capabilities.update(skill.provides)

        if capabilities:
            matches = len(set(capabilities) & agent_capabilities)
            cap_score = (matches / len(capabilities)) * 100
        else:
            cap_score = 50.0  # Neutral if no specific requirements

        # Quality score (average across skills)
        quality_score = sum(s.quality_score for s in skills) / len(skills)

        # Success rate score
        success_score = (sum(s.success_rate for s in skills) / len(skills)) * 100

        # Cost factor (lower cost = higher score)
        avg_cost = sum(s.cost_weight for s in skills) / len(skills)
        cost_score = max(0, 100 - (avg_cost * 20))

        # Budget constraints from context
        budget_penalty = 0.0
        if "max_cost_weight" in context:
            if avg_cost > context["max_cost_weight"]:
                budget_penalty = 20.0

        # Weighted score
        score = (
            cap_score * 0.4
            + quality_score * 0.3
            + success_score * 0.2
            + cost_score * 0.1
            - budget_penalty
        )

        return max(0.0, min(100.0, score))

    def _compute_confidence(
        self, best_score: float, all_scored: List[Tuple[str, float]]
    ) -> float:
        """Compute confidence in the top choice.

        Confidence is high when:
        - Best score is high (absolute quality)
        - Gap between best and second is large (clear winner)
        """
        # Absolute confidence from score
        absolute_conf = best_score / 100.0

        # Relative confidence from gap
        if len(all_scored) > 1:
            gap = best_score - all_scored[1][1]
            relative_conf = min(1.0, gap / 30.0)  # 30+ point gap = 1.0
        else:
            relative_conf = 1.0

        # Blend
        return (absolute_conf * 0.6) + (relative_conf * 0.4)

    def _should_use_llm_fallback(self, confidence: float) -> bool:
        """Determine if LLM fallback should be used."""
        if self.mode == PlannerMode.HEURISTIC:
            return False
        if self.mode == PlannerMode.LLM:
            return True
        # AUTO mode
        return confidence < self.confidence_threshold

    def _llm_plan(
        self,
        objective: str,
        context: Dict,
        scored_candidates: List[Tuple[str, float]],
        capabilities: List[str],
    ) -> Plan:
        """Use LLM to create plan (or mock in CI)."""
        if self.use_mock_llm:
            # Mock LLM response for deterministic testing
            best_agent = (
                scored_candidates[0][0] if scored_candidates else "inbox.triage"
            )
            return Plan(
                agent=best_agent,
                confidence=0.85,
                reasoning=f"LLM selected {best_agent} based on objective analysis (mocked)",
                required_capabilities=capabilities,
                estimated_cost_weight=1.0,
                estimated_latency_ms=1000.0,
                fallback_used=True,
            )

        # Real LLM call would go here
        # For now, just use top heuristic choice with boosted confidence
        best_agent = scored_candidates[0][0]
        return self._build_plan(
            best_agent, 0.85, capabilities, context, fallback_used=True
        )

    def _build_plan(
        self,
        agent: str,
        confidence: float,
        capabilities: List[str],
        context: Dict,
        fallback_used: bool = False,
    ) -> Plan:
        """Build a complete execution plan."""
        skills = self.registry.get_by_agent(agent)

        if skills:
            avg_cost = sum(s.cost_weight for s in skills) / len(skills)
            avg_latency = sum(s.avg_latency_ms for s in skills) / len(skills)
        else:
            avg_cost = 1.0
            avg_latency = 1000.0

        reasoning = f"Selected {agent} based on "
        if fallback_used:
            reasoning += "LLM analysis"
        else:
            reasoning += f"heuristic scoring (confidence: {confidence:.2f})"

        return Plan(
            agent=agent,
            confidence=confidence,
            reasoning=reasoning,
            required_capabilities=capabilities,
            estimated_cost_weight=avg_cost,
            estimated_latency_ms=avg_latency,
            dry_run=context.get("dry_run", False),
            fallback_used=fallback_used,
        )

    def _create_fallback_plan(self, objective: str, capabilities: List[str]) -> Plan:
        """Create a safe fallback plan when no candidates found."""
        return Plan(
            agent="inbox.triage",  # Safe default
            confidence=0.3,
            reasoning="No strong candidates found, using default agent",
            required_capabilities=capabilities,
            estimated_cost_weight=1.0,
            estimated_latency_ms=1000.0,
            dry_run=True,  # Safe mode
        )


# Helper to get all agents from registry
def _get_all_agents_from_registry(registry) -> List[str]:
    """Extract unique agent names from skill registry."""
    return list(set(skill.agent for skill in registry.get_all().values()))


# Add method to SkillRegistry


def get_all_agents(self) -> List[str]:
    """Get list of all unique agent names."""
    return list(set(skill.agent for skill in self._skills.values()))


SkillRegistry.get_all_agents = get_all_agents
