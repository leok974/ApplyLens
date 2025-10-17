"""Agent skill registry for planning and routing.

Skills define what capabilities each agent provides and at what cost/quality trade-off.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class Skill(BaseModel):
    """A capability that an agent provides.
    
    Attributes:
        name: Unique skill identifier (e.g., "inbox.risk_scoring")
        agent: Agent that provides this skill
        provides: List of capabilities (e.g., ["es.search", "risk.analysis"])
        cost_weight: Relative cost multiplier (1.0 = baseline)
        quality_score: Historical quality metric (0-100)
        avg_latency_ms: Average execution time
        success_rate: Historical success rate (0.0-1.0)
    """
    name: str
    agent: str
    provides: List[str] = Field(default_factory=list)
    cost_weight: float = 1.0
    quality_score: float = 85.0
    avg_latency_ms: float = 1000.0
    success_rate: float = 0.95


class SkillRegistry:
    """Registry of agent skills for intelligent routing."""
    
    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._initialize_default_skills()
    
    def _initialize_default_skills(self):
        """Initialize skills for existing agents."""
        # Inbox Triage Agent
        self.register(Skill(
            name="inbox.risk_scoring",
            agent="inbox.triage",
            provides=["risk.analysis", "phishing.detection", "es.search"],
            cost_weight=1.2,
            quality_score=88.0,
            avg_latency_ms=800.0,
            success_rate=0.94
        ))
        
        self.register(Skill(
            name="inbox.categorization",
            agent="inbox.triage",
            provides=["email.classification", "label.assignment"],
            cost_weight=0.8,
            quality_score=90.0,
            avg_latency_ms=600.0,
            success_rate=0.96
        ))
        
        # Knowledge Updater Agent
        self.register(Skill(
            name="knowledge.sync",
            agent="knowledge.update",
            provides=["db.sync", "config.update", "diff.analysis"],
            cost_weight=0.5,
            quality_score=92.0,
            avg_latency_ms=1200.0,
            success_rate=0.98
        ))
        
        # Insights Writer Agent
        self.register(Skill(
            name="insights.analysis",
            agent="insights.write",
            provides=["metrics.query", "trend.analysis", "report.generation"],
            cost_weight=1.5,
            quality_score=85.0,
            avg_latency_ms=1500.0,
            success_rate=0.92
        ))
        
        # Warehouse Health Agent
        self.register(Skill(
            name="warehouse.monitoring",
            agent="warehouse.health",
            provides=["bq.query", "parity.check", "health.report"],
            cost_weight=1.8,
            quality_score=87.0,
            avg_latency_ms=2000.0,
            success_rate=0.93
        ))
    
    def register(self, skill: Skill) -> None:
        """Register a new skill."""
        self._skills[skill.name] = skill
    
    def get(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        return self._skills.get(name)
    
    def get_by_agent(self, agent: str) -> List[Skill]:
        """Get all skills provided by an agent."""
        return [s for s in self._skills.values() if s.agent == agent]
    
    def find_by_capability(self, capability: str) -> List[Skill]:
        """Find all skills that provide a specific capability."""
        return [s for s in self._skills.values() if capability in s.provides]
    
    def get_all(self) -> Dict[str, Skill]:
        """Get all registered skills."""
        return self._skills.copy()
    
    def update_metrics(
        self,
        skill_name: str,
        quality_score: Optional[float] = None,
        avg_latency_ms: Optional[float] = None,
        success_rate: Optional[float] = None
    ) -> None:
        """Update skill metrics based on recent performance."""
        skill = self._skills.get(skill_name)
        if not skill:
            return
        
        if quality_score is not None:
            skill.quality_score = quality_score
        if avg_latency_ms is not None:
            skill.avg_latency_ms = avg_latency_ms
        if success_rate is not None:
            skill.success_rate = success_rate


# Global registry instance
_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """Get or create the global skill registry."""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry


def reset_skill_registry() -> None:
    """Reset the global registry (useful for testing)."""
    global _registry
    _registry = None
