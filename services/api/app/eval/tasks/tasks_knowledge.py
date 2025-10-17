"""
Golden tasks for knowledge.update agent.

These are representative test cases covering:
- Knowledge base sync
- Synonym preservation
- Config updates
- Conflict resolution
"""
from typing import List
from app.eval.models import EvalTask, EvalSuite


def get_knowledge_tasks() -> List[EvalTask]:
    """Get all knowledge.update eval tasks."""
    return [
        # Sync tasks
        EvalTask(
            id="knowledge.sync.001",
            agent="knowledge.update",
            category="sync",
            objective="Sync 100 knowledge base entries from source",
            context={
                "source": "elasticsearch",
                "target": "bigquery",
                "entry_count": 100,
                "has_conflicts": False,
                "synonyms_present": True,
            },
            expected_output={
                "items_synced": 100,
                "synonyms_preserved": True,
                "conflicts_resolved": 0,
                "duration_ms": 5000,
            },
            invariants=["sync_completion"],
            difficulty="easy",
            tags=["sync", "baseline"],
        ),
        
        EvalTask(
            id="knowledge.sync.002",
            agent="knowledge.update",
            category="sync",
            objective="Sync knowledge base with conflicts",
            context={
                "source": "elasticsearch",
                "target": "bigquery",
                "entry_count": 50,
                "has_conflicts": True,
                "conflict_count": 5,
                "synonyms_present": True,
            },
            expected_output={
                "items_synced": 50,
                "synonyms_preserved": True,
                "conflicts_resolved": 5,
                "duration_ms": 8000,
            },
            invariants=["sync_completion"],
            difficulty="medium",
            tags=["sync", "conflicts"],
        ),
        
        # Synonym preservation
        EvalTask(
            id="knowledge.synonym.001",
            agent="knowledge.update",
            category="synonym_preservation",
            objective="Ensure synonyms are preserved during sync",
            context={
                "source": "elasticsearch",
                "target": "bigquery",
                "entry_count": 30,
                "has_conflicts": False,
                "synonyms_present": True,
                "synonym_groups": [
                    ["meeting", "call", "session"],
                    ["urgent", "critical", "important"],
                    ["invoice", "bill", "payment"],
                ],
            },
            expected_output={
                "items_synced": 30,
                "synonyms_preserved": True,
                "conflicts_resolved": 0,
                "synonym_groups_intact": 3,
            },
            invariants=["sync_completion"],
            difficulty="medium",
            tags=["synonyms", "data_quality"],
        ),
        
        # Config updates
        EvalTask(
            id="knowledge.config.001",
            agent="knowledge.update",
            category="update",
            objective="Update knowledge base configuration",
            context={
                "config_type": "synonym_list",
                "changes": [
                    {"action": "add", "group": ["deadline", "due date"]},
                    {"action": "remove", "term": "obsolete_term"},
                ],
                "validate_before_apply": True,
            },
            expected_output={
                "items_synced": 2,
                "synonyms_preserved": True,
                "conflicts_resolved": 0,
                "config_updated": True,
            },
            invariants=["sync_completion"],
            difficulty="easy",
            tags=["config", "update"],
        ),
        
        # Large batch sync
        EvalTask(
            id="knowledge.sync.003",
            agent="knowledge.update",
            category="sync",
            objective="Sync large batch of 1000 entries",
            context={
                "source": "elasticsearch",
                "target": "bigquery",
                "entry_count": 1000,
                "has_conflicts": True,
                "conflict_count": 20,
                "synonyms_present": True,
            },
            expected_output={
                "items_synced": 1000,
                "synonyms_preserved": True,
                "conflicts_resolved": 20,
                "duration_ms": 30000,
            },
            invariants=["sync_completion"],
            difficulty="hard",
            tags=["sync", "large_batch", "performance"],
        ),
        
        # Edge case: empty sync
        EvalTask(
            id="knowledge.edge.001",
            agent="knowledge.update",
            category="edge_case",
            objective="Handle empty knowledge base sync",
            context={
                "source": "elasticsearch",
                "target": "bigquery",
                "entry_count": 0,
                "has_conflicts": False,
                "synonyms_present": False,
            },
            expected_output={
                "items_synced": 0,
                "synonyms_preserved": True,
                "conflicts_resolved": 0,
                "duration_ms": 100,
            },
            invariants=[],
            difficulty="easy",
            tags=["edge_case"],
        ),
        
        # Conflict resolution
        EvalTask(
            id="knowledge.conflict.001",
            agent="knowledge.update",
            category="conflict_resolution",
            objective="Resolve conflicts with last-write-wins strategy",
            context={
                "source": "elasticsearch",
                "target": "bigquery",
                "entry_count": 20,
                "has_conflicts": True,
                "conflict_count": 10,
                "conflict_strategy": "last_write_wins",
                "synonyms_present": False,
            },
            expected_output={
                "items_synced": 20,
                "synonyms_preserved": True,
                "conflicts_resolved": 10,
                "strategy_used": "last_write_wins",
            },
            invariants=["sync_completion"],
            difficulty="medium",
            tags=["conflicts", "strategy"],
        ),
    ]


def get_knowledge_suite() -> EvalSuite:
    """Get the complete knowledge.update eval suite."""
    suite = EvalSuite(
        name="knowledge_update_v1",
        agent="knowledge.update",
        version="1.0",
        tasks=get_knowledge_tasks(),
        invariants=["sync_completion"],
    )
    return suite
