"""
Email logic module

Business logic for email classification, policy evaluation, and automation.
"""

from .classify import (
    weak_category,
    calculate_risk_score,
    extract_expiry_date,
    extract_profile_tags,
    classify_email,
    classify_batch,
)

from .policy import (
    PolicyEngine,
    create_default_engine,
    load_policies_from_file,
    DEFAULT_POLICIES,
)

__all__ = [
    # Classification
    "weak_category",
    "calculate_risk_score",
    "extract_expiry_date",
    "extract_profile_tags",
    "classify_email",
    "classify_batch",
    # Policy
    "PolicyEngine",
    "create_default_engine",
    "load_policies_from_file",
    "DEFAULT_POLICIES",
]
