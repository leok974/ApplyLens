"""
Phase 6: Personalization models for per-user learning and policy analytics.
"""

from datetime import datetime

from sqlalchemy import (Column, DateTime, Float, Integer, String,
                        UniqueConstraint)

from ..db import Base


class UserWeight(Base):
    """
    Per-user feature weights learned online from approve/reject feedback.

    Features can be:
    - category:<cat> (e.g., category:promo, category:event)
    - sender_domain:<domain> (e.g., sender_domain:bestbuy.com)
    - listid:<list_id> (e.g., listid:github-notifications)
    - contains:<token> (e.g., contains:invoice, contains:meetup)

    Weights are updated using online gradient descent:
    w ← w + η * y * x
    where y=+1 for approve, y=-1 for reject, x=1 for feature presence
    """

    __tablename__ = "user_weights"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    feature = Column(String, nullable=False)  # e.g., 'sender_domain:bestbuy.com'
    weight = Column(Float, default=0.0)  # learned weight
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "feature", name="uq_user_feature"),)

    def __repr__(self):
        return f"<UserWeight(user={self.user_id}, feature={self.feature}, weight={self.weight:.3f})>"


class PolicyStats(Base):
    """
    Per-user, per-policy performance statistics.

    Tracks:
    - How many times the policy fired (proposed actions)
    - How many proposals were approved
    - How many were rejected
    - Precision (approved/fired)
    - Estimated recall (approved/(approved+should_have))
    """

    __tablename__ = "policy_stats"

    id = Column(Integer, primary_key=True)
    policy_id = Column(Integer, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)

    # Counters
    fired = Column(Integer, default=0)  # Total times policy fired
    approved = Column(Integer, default=0)  # User approved proposals
    rejected = Column(Integer, default=0)  # User rejected proposals

    # Metrics
    precision = Column(Float, default=0.0)  # approved/fired
    recall = Column(Float, default=0.0)  # approved/(approved+should_have) — estimated

    # Window
    window_days = Column(Integer, default=30)  # Stats computed over this window
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("policy_id", "user_id", name="uq_pol_user"),)

    def __repr__(self):
        return f"<PolicyStats(policy={self.policy_id}, user={self.user_id}, precision={self.precision:.2f})>"
