"""Active learning models for labeled examples and training data.

Stores labeled examples from multiple sources:
- Approvals (user decisions on agent actions)
- Feedback API (thumbs up/down + notes)
- Gold sets (curated test cases)
- Synthetic tasks (generated examples)
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, Index
from sqlalchemy.sql import func

from .db import Base


class LabeledExample(Base):
    """Labeled training examples for active learning.
    
    Aggregates labeled data from multiple sources to train
    and improve agent heuristics, rules, and decision thresholds.
    """
    
    __tablename__ = "labeled_examples"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Agent context
    agent = Column(String(64), nullable=False, index=True)  # inbox_triage, knowledge_update, etc.
    key = Column(String(256), nullable=False, index=True)  # thread_id, rule_id, task_id
    
    # Labeled data
    payload = Column(JSON, nullable=False)  # Feature snapshot: {spf, dkim, keywords, etc.}
    label = Column(String(64), nullable=False, index=True)  # High-Risk, Offer, Safe, etc.
    
    # Provenance
    source = Column(String(32), nullable=False, index=True)  # approvals|feedback|gold|synthetic
    source_id = Column(String(128), nullable=True)  # Original record ID (approval_id, feedback_id, etc.)
    
    # Versioning
    version = Column(String(16), nullable=False, default="v1")  # Schema version for reproducibility
    
    # Metadata
    confidence = Column(Integer, nullable=True)  # 0-100 confidence in label (if available)
    notes = Column(String(1024), nullable=True)  # Human notes/rationale
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('ix_labeled_examples_agent_source', 'agent', 'source'),
        Index('ix_labeled_examples_agent_label', 'agent', 'label'),
        Index('ix_labeled_examples_created_at_desc', created_at.desc()),
    )
    
    def __repr__(self):
        return f"<LabeledExample(agent={self.agent}, label={self.label}, source={self.source})>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "agent": self.agent,
            "key": self.key,
            "payload": self.payload,
            "label": self.label,
            "source": self.source,
            "source_id": self.source_id,
            "version": self.version,
            "confidence": self.confidence,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
