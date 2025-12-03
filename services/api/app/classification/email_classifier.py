"""
Email classification system for ApplyLens.

Combines high-precision rules, heuristics, and ML models to categorize emails
and determine if they represent real job opportunities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal, Protocol, Any

from app.models import Email
from app.config import get_settings


Category = Literal[
    "recruiter_outreach",
    "interview_invite",
    "offer",
    "rejection",
    "application_confirmation",
    "job_alert_digest",
    "newsletter_marketing",
    "company_update",
    "receipt_invoice",
    "security_auth",
    "personal_other",
]


@dataclass
class ClassificationResult:
    """Result from email classification."""

    category: Category
    is_real_opportunity: bool
    confidence: float
    model_version: str
    source: Literal["rule", "heuristic", "ml_shadow", "ml_live"]


class EmailClassifier(Protocol):
    """Interface for email classifiers (heuristic-only, ML-only, or hybrid)."""

    def classify(self, email: Email) -> ClassificationResult:
        """Classify an email and return the result."""
        ...


def _apply_high_precision_rules(email: Email) -> Optional[ClassificationResult]:
    """
    Apply hard rules for obvious categories (security codes, receipts, etc.).

    These rules have very high precision and bypass ML models.
    """
    subject = (email.subject or "").lower()
    sender = (email.from_address or "").lower()
    snippet = (email.snippet or "").lower()

    # Security / Authentication emails
    security_keywords = [
        "verification code",
        "2-step",
        "two-factor",
        "2fa",
        "verify your",
        "reset your password",
        "security alert",
        "unusual activity",
    ]
    security_senders = ["no-reply@auth", "security@", "noreply@"]

    if any(k in subject or k in snippet for k in security_keywords) or any(
        s in sender for s in security_senders
    ):
        return ClassificationResult(
            category="security_auth",
            is_real_opportunity=False,
            confidence=0.99,
            model_version="rules_v1",
            source="rule",
        )

    # Receipt / Invoice / Payment confirmation
    receipt_keywords = [
        "receipt",
        "invoice",
        "payment confirmation",
        "order confirmation",
        "purchase confirmation",
        "your order",
        "payment received",
    ]
    receipt_senders = [
        "@stripe.com",
        "@paypal.com",
        "@square.com",
        "billing@",
        "receipts@",
    ]

    if any(k in subject or k in snippet for k in receipt_keywords) or any(
        s in sender for s in receipt_senders
    ):
        return ClassificationResult(
            category="receipt_invoice",
            is_real_opportunity=False,
            confidence=0.98,
            model_version="rules_v1",
            source="rule",
        )

    # Job alert digests from known aggregators
    job_alert_senders = [
        "jobalerts@linkedin.com",
        "noreply@indeed.com",
        "@glassdoor.com",
        "@ziprecruiter.com",
        "jobs-noreply@",
    ]
    job_alert_subjects = [
        "job alert",
        "recommended jobs",
        "jobs matching",
        "new jobs for you",
        "daily job digest",
    ]

    if any(s in sender for s in job_alert_senders) or any(
        k in subject for k in job_alert_subjects
    ):
        return ClassificationResult(
            category="job_alert_digest",
            is_real_opportunity=False,  # Aggregator emails, not direct opportunities
            confidence=0.95,
            model_version="rules_v1",
            source="rule",
        )

    return None


class HybridEmailClassifier:
    """
    Combines rules, heuristics, and ML model prediction.

    Priority order:
    1. High-precision hard rules (security, receipts, known aggregators)
    2. ML model predictions (if loaded and enabled)
    3. Fallback to heuristics
    """

    def __init__(
        self, ml_model: Any | None = None, vectorizer: Any | None = None
    ) -> None:
        self.ml_model = ml_model
        self.vectorizer = vectorizer

        settings = get_settings()
        self.model_version = getattr(
            settings, "EMAIL_CLASSIFIER_MODEL_VERSION", "heuristic_v1"
        )
        self.mode: Literal["heuristic", "ml_shadow", "ml_live"] = getattr(
            settings, "EMAIL_CLASSIFIER_MODE", "heuristic"
        )

    def classify(self, email: Email) -> ClassificationResult:
        """Classify an email using the hybrid approach."""
        # 1) Hard rules (highest priority)
        rule_result = _apply_high_precision_rules(email)
        if rule_result is not None:
            return rule_result

        # 2) Fallback to heuristic-only if ML not loaded
        if self.ml_model is None or self.vectorizer is None:
            return self._heuristic_only(email)

        # 3) ML pipeline
        ml_result = self._ml_predict(email)

        # If we're in shadow mode, we use heuristic as the live label,
        # but still log the ML result separately (caller's responsibility)
        if self.mode == "ml_shadow":
            return self._heuristic_only(email)

        # Live ML
        return ml_result

    def _heuristic_only(self, email: Email) -> ClassificationResult:
        """
        Your existing heuristic pipeline wrapped into the new interface.

        This is a simplified version - replace with your actual heuristics.
        """
        subject = (email.subject or "").lower()
        snippet = (email.snippet or "").lower()

        # Opportunity signals
        opportunity_keywords = [
            "interview",
            "opportunity",
            "phone screen",
            "schedule",
            "round",
            "recruiter",
            "hiring",
            "position",
            "role at",
            "join our team",
            "application",
        ]

        # Rejection signals
        rejection_keywords = [
            "unfortunately",
            "not moving forward",
            "decided to pursue",
            "other candidates",
            "not a fit",
        ]

        # Check for opportunities
        opp_score = sum(1 for k in opportunity_keywords if k in subject or k in snippet)

        # Check for rejections
        if any(k in subject or k in snippet for k in rejection_keywords):
            return ClassificationResult(
                category="rejection",
                is_real_opportunity=False,
                confidence=0.75,
                model_version="heuristic_v1",
                source="heuristic",
            )

        # Interview invites (high priority opportunity)
        if any(
            k in subject or k in snippet
            for k in ["interview", "phone screen", "schedule a call"]
        ):
            return ClassificationResult(
                category="interview_invite",
                is_real_opportunity=True,
                confidence=0.8,
                model_version="heuristic_v1",
                source="heuristic",
            )

        # General opportunity
        if opp_score >= 2:
            return ClassificationResult(
                category="recruiter_outreach",
                is_real_opportunity=True,
                confidence=0.6 + (opp_score * 0.05),
                model_version="heuristic_v1",
                source="heuristic",
            )

        # Default: probably marketing/newsletter
        return ClassificationResult(
            category="newsletter_marketing",
            is_real_opportunity=False,
            confidence=0.5,
            model_version="heuristic_v1",
            source="heuristic",
        )

    def _ml_predict(self, email: Email) -> ClassificationResult:
        """Make prediction using the loaded ML model."""
        text = self._build_text(email)
        features = self.vectorizer.transform([text])
        proba = self.ml_model.predict_proba(features)[0]

        # Assuming binary classifier: proba[1] is "is_real_opportunity"
        opp_prob = float(proba[1])
        is_opp = opp_prob >= 0.5

        # For v1, keep category simple: opportunity vs newsletter_marketing
        # Later versions can use a multi-class category model
        category: Category
        if is_opp:
            # Could refine this further with a second model or rules
            category = "recruiter_outreach"
        else:
            category = "newsletter_marketing"

        return ClassificationResult(
            category=category,
            is_real_opportunity=is_opp,
            confidence=opp_prob,
            model_version=self.model_version,
            source="ml_live" if self.mode == "ml_live" else "ml_shadow",
        )

    @staticmethod
    def _build_text(email: Email) -> str:
        """Build text representation of email for ML features."""
        parts = [
            email.subject or "",
            email.snippet or "",
            email.from_address or "",
        ]
        # You can add body text if available
        return "\n".join(parts)


def get_classifier() -> HybridEmailClassifier:
    """
    Factory to load a classifier with ML artifacts.

    Used as a FastAPI dependency or called directly in workers.
    Falls back to heuristics-only if ML models aren't available.
    """
    import os

    settings = get_settings()

    model_path = getattr(
        settings, "EMAIL_CLASSIFIER_MODEL_PATH", "models/email_opp_model.joblib"
    )
    vec_path = getattr(
        settings,
        "EMAIL_CLASSIFIER_VECTORIZER_PATH",
        "models/email_opp_vectorizer.joblib",
    )

    # Check if ML artifacts exist
    if not (os.path.exists(model_path) and os.path.exists(vec_path)):
        # ML artifacts not present, fall back to heuristics-only
        return HybridEmailClassifier(ml_model=None, vectorizer=None)

    # Lazy import to avoid import cost if not configured
    try:
        import joblib

        ml_model = joblib.load(model_path)
        vectorizer = joblib.load(vec_path)
        return HybridEmailClassifier(ml_model=ml_model, vectorizer=vectorizer)
    except Exception as e:
        # If loading fails, fall back to heuristics
        import logging

        logging.warning(
            f"Failed to load ML classifier, falling back to heuristics: {e}"
        )
        return HybridEmailClassifier(ml_model=None, vectorizer=None)
