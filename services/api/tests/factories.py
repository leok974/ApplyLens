"""
Factory classes for creating test data.

Uses factory_boy and faker to generate realistic test objects
without manual data entry.

Usage:
    from tests.factories import EmailFactory, PolicyFactory
    
    # Create an email with default values
    email = EmailFactory()
    
    # Create an email with custom values
    email = EmailFactory(subject="Test Email", sender="hr@company.com")
    
    # Create multiple emails
    emails = EmailFactory.create_batch(5)
"""

import factory
from factory import fuzzy
from datetime import datetime, timedelta
from typing import Optional

from app.models import Email, Policy, ActionType
from app.models.personalization import UserWeight


class EmailFactory(factory.Factory):
    """Factory for creating Email test objects."""
    
    class Meta:
        model = Email
    
    id = factory.Sequence(lambda n: n + 1000)
    gmail_id = factory.LazyAttribute(lambda obj: f"gmail_{obj.id}_{factory.Faker('uuid4')}")
    thread_id = factory.LazyAttribute(lambda obj: f"thread_{factory.Faker('uuid4')}")
    subject = factory.Faker("sentence", nb_words=6)
    body_text = factory.Faker("paragraph", nb_sentences=5)
    sender = factory.LazyFunction(lambda: f"{factory.Faker('first_name')().lower()}@{factory.Faker('domain_name')()}")
    recipient = "me@example.com"
    received_at = factory.LazyFunction(lambda: datetime.now() - timedelta(days=factory.Faker('random_int', min=0, max=30)()))
    
    # Application fields
    company = factory.Faker("company")
    role = factory.Faker("job")
    source = factory.fuzzy.FuzzyChoice(["linkedin", "indeed", "company_site", "referral"])
    source_confidence = fuzzy.FuzzyFloat(0.5, 1.0)
    
    # Categorization
    category = factory.fuzzy.FuzzyChoice(["personal", "promotions", "bills", "security", "applications"])
    risk_score = fuzzy.FuzzyFloat(0, 30)  # Default to low risk
    quarantined = False
    
    # Optional fields default to None
    labels = None
    label_heuristics = None
    raw = None
    features_json = None
    ml_features = None
    ml_scores = None
    amount_cents = None
    due_date = None
    event_start_at = None
    event_location = None
    application_id = None
    profile_tags = None
    expires_at = None
    flags = []
    
    # Reply metrics
    first_user_reply_at = None
    last_user_reply_at = None
    user_reply_count = 0


class HighRiskEmailFactory(EmailFactory):
    """Factory for creating high-risk emails for security testing."""
    
    risk_score = fuzzy.FuzzyFloat(70, 100)
    quarantined = True
    flags = factory.LazyFunction(lambda: [
        {"signal": "suspicious_link", "evidence": "http://phishing.com", "weight": 0.8},
        {"signal": "urgency_keyword", "evidence": "URGENT ACTION REQUIRED", "weight": 0.6}
    ])
    category = "security"


class ApplicationEmailFactory(EmailFactory):
    """Factory for creating application-related emails."""
    
    category = "applications"
    company = factory.Faker("company")
    role = factory.Faker("job")
    source = factory.fuzzy.FuzzyChoice(["linkedin", "indeed", "company_site"])
    source_confidence = fuzzy.FuzzyFloat(0.7, 1.0)
    subject = factory.LazyAttribute(lambda obj: f"Application for {obj.role} at {obj.company}")


class PolicyFactory(factory.Factory):
    """Factory for creating Policy test objects."""
    
    class Meta:
        model = Policy
    
    id = factory.Sequence(lambda n: n + 100)
    name = factory.LazyAttribute(lambda obj: f"Test Policy {obj.id}")
    description = factory.Faker("sentence")
    condition = "category:promotions"
    action = factory.fuzzy.FuzzyChoice(list(ActionType))
    confidence_threshold = fuzzy.FuzzyFloat(0.5, 0.9)
    priority = fuzzy.FuzzyInteger(1, 100)
    enabled = True
    dry_run = False
    user_email = None
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)


class LabelPolicyFactory(PolicyFactory):
    """Factory for label action policies."""
    
    action = ActionType.label_email
    condition = "category:promotions"
    confidence_threshold = 0.7


class ArchivePolicyFactory(PolicyFactory):
    """Factory for archive action policies."""
    
    action = ActionType.archive_email
    condition = "category:newsletters"
    confidence_threshold = 0.8


class UserWeightFactory(factory.Factory):
    """Factory for creating UserWeight test objects."""
    
    class Meta:
        model = UserWeight
    
    id = factory.Sequence(lambda n: n + 500)
    user_id = "test@example.com"
    feature = factory.LazyAttribute(lambda obj: f"contains:{factory.Faker('word')()}")
    weight = fuzzy.FuzzyFloat(-5.0, 5.0)
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)


class PositiveWeightFactory(UserWeightFactory):
    """Factory for positive user weights (user likes these)."""
    
    weight = fuzzy.FuzzyFloat(1.0, 5.0)


class NegativeWeightFactory(UserWeightFactory):
    """Factory for negative user weights (user dislikes these)."""
    
    weight = fuzzy.FuzzyFloat(-5.0, -1.0)


# Convenience functions for common patterns

def create_email_with_weights(user_id: str, positive_features: list[str], negative_features: list[str] = None) -> tuple[Email, list[UserWeight]]:
    """
    Create an email and associated user weights for testing personalization.
    
    Args:
        user_id: User email address
        positive_features: List of features with positive weights
        negative_features: Optional list of features with negative weights
    
    Returns:
        Tuple of (email, list of user_weights)
    """
    email = EmailFactory()
    
    weights = []
    for feature in positive_features:
        weights.append(PositiveWeightFactory(user_id=user_id, feature=feature))
    
    if negative_features:
        for feature in negative_features:
            weights.append(NegativeWeightFactory(user_id=user_id, feature=feature))
    
    return email, weights


def create_policy_with_emails(n_emails: int = 3, **policy_kwargs) -> tuple[Policy, list[Email]]:
    """
    Create a policy and matching emails for testing policy execution.
    
    Args:
        n_emails: Number of emails to create
        **policy_kwargs: Additional arguments for PolicyFactory
    
    Returns:
        Tuple of (policy, list of emails)
    """
    policy = PolicyFactory(**policy_kwargs)
    emails = EmailFactory.create_batch(n_emails)
    
    return policy, emails
