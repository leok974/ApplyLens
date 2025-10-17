"""
Golden task collections for all agents.
"""
from .tasks_inbox import get_inbox_suite, get_inbox_tasks
from .tasks_knowledge import get_knowledge_suite, get_knowledge_tasks
from .tasks_insights import get_insights_suite, get_insights_tasks
from .tasks_warehouse import get_warehouse_suite, get_warehouse_tasks

__all__ = [
    "get_inbox_suite",
    "get_inbox_tasks",
    "get_knowledge_suite",
    "get_knowledge_tasks",
    "get_insights_suite",
    "get_insights_tasks",
    "get_warehouse_suite",
    "get_warehouse_tasks",
]
