"""
Core models for evaluation harness.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field


class EvalTask(BaseModel):
    """A single evaluation task/test case."""
    
    id: str  # e.g., "inbox.phishing.001"
    agent: str  # e.g., "inbox.triage"
    category: str  # e.g., "phishing_detection"
    objective: str  # Task description for the agent
    context: Dict[str, Any] = {}  # Input context (email content, etc.)
    expected_output: Optional[Dict[str, Any]] = None  # Gold standard output
    invariants: List[str] = []  # Invariant IDs that must pass
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    tags: List[str] = []  # e.g., ["red_team", "regression"]
    
    class Config:
        schema_extra = {
            "example": {
                "id": "inbox.phishing.001",
                "agent": "inbox.triage",
                "category": "phishing_detection",
                "objective": "Analyze this suspicious email for phishing indicators",
                "context": {
                    "subject": "Urgent: Verify your account",
                    "sender": "noreply@suspicious-domain.com",
                    "body": "Click here to verify..."
                },
                "expected_output": {
                    "risk_level": "high",
                    "is_phishing": True
                },
                "invariants": ["no_false_negatives_phishing"],
                "difficulty": "medium",
                "tags": ["phishing", "red_team"]
            }
        }


class EvalResult(BaseModel):
    """Result from evaluating a single task."""
    
    task_id: str
    agent: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Execution
    success: bool  # Did the agent complete without errors?
    output: Optional[Dict[str, Any]] = None  # Agent's actual output
    error: Optional[str] = None
    latency_ms: float
    cost_weight: float  # Relative cost (1.0 = baseline)
    
    # Scoring
    quality_score: float  # 0-100, from judge
    judge_reasoning: str  # Why this score?
    passed_invariants: List[str] = []
    failed_invariants: List[str] = []
    
    # Metadata
    difficulty: str
    tags: List[str] = []


class Judge(BaseModel):
    """A judge that scores agent outputs."""
    
    name: str  # e.g., "risk_accuracy_judge"
    agent: str  # Which agent this judges
    categories: List[str] = []  # Categories it can judge
    
    # Judge behavior
    use_llm: bool = False  # True = use LLM, False = use mock/heuristic
    scoring_rubric: Optional[str] = None  # How to score (for LLM judges)
    
    def score(self, task: EvalTask, output: Dict[str, Any]) -> tuple[float, str]:
        """
        Score an agent output.
        
        Returns:
            (score: 0-100, reasoning: str)
        """
        raise NotImplementedError("Subclasses must implement score()")


class Invariant(BaseModel):
    """A must-never-regress rule."""
    
    id: str  # e.g., "no_false_negatives_phishing"
    name: str
    agent: str
    description: str
    severity: Literal["critical", "high", "medium", "low"] = "high"
    
    def check(self, task: EvalTask, output: Dict[str, Any]) -> tuple[bool, str]:
        """
        Check if invariant holds.
        
        Returns:
            (passed: bool, reason: str)
        """
        raise NotImplementedError("Subclasses must implement check()")


class EvalSuite(BaseModel):
    """A collection of eval tasks."""
    
    name: str  # e.g., "inbox_triage_v1"
    agent: str
    version: str = "1.0"
    tasks: List[EvalTask] = []
    invariants: List[str] = []  # Invariant IDs
    
    def add_task(self, task: EvalTask) -> None:
        """Add a task to the suite."""
        self.tasks.append(task)
    
    def get_task(self, task_id: str) -> Optional[EvalTask]:
        """Get task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None


class EvalRun(BaseModel):
    """Results from running an eval suite."""
    
    run_id: str
    suite_name: str
    agent: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Results
    results: List[EvalResult] = []
    
    # Aggregated metrics
    total_tasks: int = 0
    success_rate: float = 0.0
    avg_quality_score: float = 0.0
    avg_latency_ms: float = 0.0
    total_cost_weight: float = 0.0
    
    # Invariants
    invariants_passed: int = 0
    invariants_failed: int = 0
    failed_invariant_ids: List[str] = []
    
    # Breakdown by difficulty
    quality_by_difficulty: Dict[str, float] = {}
    
    def add_result(self, result: EvalResult) -> None:
        """Add a result and update aggregates."""
        self.results.append(result)
        self._recompute_metrics()
    
    def _recompute_metrics(self) -> None:
        """Recompute aggregate metrics."""
        if not self.results:
            return
        
        self.total_tasks = len(self.results)
        self.success_rate = sum(1 for r in self.results if r.success) / self.total_tasks
        self.avg_quality_score = sum(r.quality_score for r in self.results) / self.total_tasks
        self.avg_latency_ms = sum(r.latency_ms for r in self.results) / self.total_tasks
        self.total_cost_weight = sum(r.cost_weight for r in self.results)
        
        # Invariants
        all_passed = [inv for r in self.results for inv in r.passed_invariants]
        all_failed = [inv for r in self.results for inv in r.failed_invariants]
        self.invariants_passed = len(all_passed)
        self.invariants_failed = len(all_failed)
        self.failed_invariant_ids = list(set(all_failed))
        
        # By difficulty
        by_diff: Dict[str, List[float]] = {}
        for r in self.results:
            if r.difficulty not in by_diff:
                by_diff[r.difficulty] = []
            by_diff[r.difficulty].append(r.quality_score)
        
        self.quality_by_difficulty = {
            diff: sum(scores) / len(scores)
            for diff, scores in by_diff.items()
        }
    
    def to_jsonl_record(self) -> Dict[str, Any]:
        """Export as JSONL record for trend analysis."""
        return {
            "run_id": self.run_id,
            "suite_name": self.suite_name,
            "agent": self.agent,
            "timestamp": self.timestamp.isoformat(),
            "total_tasks": self.total_tasks,
            "success_rate": self.success_rate,
            "avg_quality_score": self.avg_quality_score,
            "avg_latency_ms": self.avg_latency_ms,
            "total_cost_weight": self.total_cost_weight,
            "invariants_passed": self.invariants_passed,
            "invariants_failed": self.invariants_failed,
            "failed_invariant_ids": self.failed_invariant_ids,
            "quality_by_difficulty": self.quality_by_difficulty,
        }
