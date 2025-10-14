"""
Email logic module

Business logic for email classification, policy evaluation, and automation.
"""

from .classify import (
    calculate_risk_score,
    classify_batch,
    classify_email,
    extract_expiry_date,
    extract_profile_tags,
    weak_category,
)
from .policy import (
    DEFAULT_POLICIES,
    PolicyEngine,
    create_default_engine,
    load_policies_from_file,
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
