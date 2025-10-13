"""
Unit tests for confidence estimation with user weight learning.

Tests that confidence scores are adjusted based on user's learned preferences.
"""
import pytest
from sqlalchemy.orm import Session

from app.routers.actions import estimate_confidence
from app.models import UserWeight, Policy, ActionType, Email
from app.db import get_db


def test_confidence_bump_from_user_weights():
    """Test that positive user weights increase confidence scores."""
    db = next(get_db())
    
    # Seed positive weights for meetup-related features
    # User has historically approved emails with "meetup" in subject
    uw1 = UserWeight(user_id="test@example.com", feature="contains:meetup", weight=3.0)
    uw2 = UserWeight(user_id="test@example.com", feature="category:promo", weight=2.0)
    db.add(uw1)
    db.add(uw2)
    db.commit()
    
    # Create test email with meetup in subject
    email = Email(
        id=999,
        subject="Local Meetup tonight",
        category="promo",
        sender_domain="events.example.com",
        risk_score=10,
        quarantined=False
    )
    
    # Create test policy
    policy = Policy(
        id=1,
        name="Test Policy",
        condition="category:promo",
        action=ActionType.label_email,
        confidence_threshold=0.7,
        priority=50,
        enabled=True
    )
    
    # Features and aggregations
    feats = {"category": "promo", "risk_score": 10}
    aggs = {"promo_ratio": 0.7}  # Above 0.6 threshold for +0.1 bump
    neighbors = []
    
    # Mock user object
    class MockUser:
        email = "test@example.com"
    
    user = MockUser()
    
    # Calculate confidence with user weights
    conf = estimate_confidence(
        policy=policy,
        feats=feats,
        aggs=aggs,
        neighbors=neighbors,
        db=db,
        user=user,
        email=email
    )
    
    # Base: 0.7 (policy threshold)
    # + 0.1 (promo_ratio > 0.6)
    # + bump from weights: 0.05 * (3.0 + 2.0) = 0.25, capped at 0.15
    # Expected: 0.7 + 0.1 + 0.15 = 0.95
    # But capped at 0.99, so should be close to 0.95
    
    assert conf > 0.85, f"Expected confidence > 0.85 with positive weights, got {conf}"
    assert conf <= 0.99, f"Confidence should be capped at 0.99, got {conf}"
    
    # Cleanup
    db.query(UserWeight).filter(UserWeight.user_id == "test@example.com").delete()
    db.commit()


def test_confidence_without_user_weights():
    """Test baseline confidence when no user weights exist."""
    db = next(get_db())
    
    # Ensure no weights for this user
    db.query(UserWeight).filter(UserWeight.user_id == "test2@example.com").delete()
    db.commit()
    
    email = Email(
        id=1000,
        subject="Regular email",
        category="personal",
        sender_domain="example.com",
        risk_score=20,
        quarantined=False
    )
    
    policy = Policy(
        id=2,
        name="Test Policy 2",
        condition="category:personal",
        action=ActionType.label_email,
        confidence_threshold=0.75,
        priority=50,
        enabled=True
    )
    
    feats = {"category": "personal", "risk_score": 20}
    aggs = {}
    neighbors = []
    
    class MockUser:
        email = "test2@example.com"
    
    conf = estimate_confidence(
        policy=policy,
        feats=feats,
        aggs=aggs,
        neighbors=neighbors,
        db=db,
        user=MockUser(),
        email=email
    )
    
    # Should be close to policy threshold (0.75) with no bumps
    assert 0.74 <= conf <= 0.76, f"Expected baseline confidence ~0.75, got {conf}"


def test_confidence_negative_weights():
    """Test that negative user weights decrease confidence scores."""
    db = next(get_db())
    
    # Seed negative weights (user has rejected similar emails)
    uw = UserWeight(user_id="test3@example.com", feature="contains:newsletter", weight=-4.0)
    db.add(uw)
    db.commit()
    
    email = Email(
        id=1001,
        subject="Weekly Newsletter Update",
        category="promo",
        sender_domain="news.example.com",
        risk_score=15,
        quarantined=False
    )
    
    policy = Policy(
        id=3,
        name="Test Policy 3",
        condition="category:promo",
        action=ActionType.archive_email,
        confidence_threshold=0.7,
        priority=50,
        enabled=True
    )
    
    feats = {"category": "promo", "risk_score": 15}
    aggs = {}
    neighbors = []
    
    class MockUser:
        email = "test3@example.com"
    
    conf = estimate_confidence(
        policy=policy,
        feats=feats,
        aggs=aggs,
        neighbors=neighbors,
        db=db,
        user=MockUser(),
        email=email
    )
    
    # Base: 0.7
    # Negative bump: 0.05 * (-4.0) = -0.2, capped at -0.15
    # Expected: 0.7 - 0.15 = 0.55
    
    assert 0.50 <= conf <= 0.60, f"Expected lowered confidence ~0.55, got {conf}"
    
    # Cleanup
    db.query(UserWeight).filter(UserWeight.user_id == "test3@example.com").delete()
    db.commit()


def test_confidence_high_risk_override():
    """Test that high risk scores override other factors."""
    db = next(get_db())
    
    email = Email(
        id=1002,
        subject="Suspicious attachment",
        category="unknown",
        sender_domain="suspicious.com",
        risk_score=85,  # High risk
        quarantined=False
    )
    
    policy = Policy(
        id=4,
        name="High Risk Policy",
        condition="risk_score >= 80",
        action=ActionType.quarantine_attachment,
        confidence_threshold=0.7,
        priority=10,
        enabled=True
    )
    
    feats = {"category": "unknown", "risk_score": 85}
    aggs = {}
    neighbors = []
    
    class MockUser:
        email = "test4@example.com"
    
    conf = estimate_confidence(
        policy=policy,
        feats=feats,
        aggs=aggs,
        neighbors=neighbors,
        db=db,
        user=MockUser(),
        email=email
    )
    
    # High risk should result in confidence = 0.95
    assert conf >= 0.94, f"Expected high confidence for high risk, got {conf}"


def test_confidence_without_db_params():
    """Test that confidence estimation works without db/user/email (baseline only)."""
    policy = Policy(
        id=5,
        name="Basic Policy",
        condition="category:work",
        action=ActionType.label_email,
        confidence_threshold=0.8,
        priority=50,
        enabled=True
    )
    
    feats = {"category": "work", "risk_score": 30}
    aggs = {}
    neighbors = []
    
    # Call without db, user, email - should use baseline only
    conf = estimate_confidence(
        policy=policy,
        feats=feats,
        aggs=aggs,
        neighbors=neighbors,
        db=None,
        user=None,
        email=None
    )
    
    # Should match policy threshold
    assert conf == 0.8, f"Expected baseline confidence = 0.8, got {conf}"
