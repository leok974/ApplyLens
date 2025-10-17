"""Core agent definition and contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass
class Agent:
    """Core agent definition with typed contracts.
    
    An agent consists of:
    - name: unique identifier
    - describe: function returning agent metadata
    - plan: function that creates an execution plan from parameters
    - execute: function that runs the plan and returns results
    """
    
    name: str
    describe: Callable[[], dict]
    plan: Callable[[dict], dict]
    execute: Callable[[dict], dict]
