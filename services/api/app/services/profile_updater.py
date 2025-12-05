# app/services/profile_updater.py
"""
Profile updater service for merging resume contact info into user profiles.

Handles the business logic of updating ResumeProfile models with parsed contact data.
"""

import logging

from app.services.resume_profile_parser import ParsedResumeContact

logger = logging.getLogger(__name__)


def merge_resume_contact_into_profile(
    profile,  # ResumeProfile model instance
    parsed: ParsedResumeContact,
    *,
    overwrite_existing: bool = False,
):
    """
    Merge parsed resume contact info into an existing ResumeProfile.
    If overwrite_existing=False, we only fill empty fields.

    Args:
        profile: ResumeProfile instance to update
        parsed: ParsedResumeContact with extracted data
        overwrite_existing: If True, replace existing values; if False, only fill nulls

    Returns:
        Updated profile instance (mutated in place)
    """

    # Name
    if parsed.full_name:
        if overwrite_existing or not getattr(profile, "name", None):
            profile.name = parsed.full_name
            logger.debug(f"Updated profile name: {parsed.full_name}")

    # Email
    if parsed.email:
        if overwrite_existing or not getattr(profile, "email", None):
            profile.email = parsed.email
            logger.debug(f"Updated profile email: {parsed.email}")

    # Phone
    if parsed.phone:
        if overwrite_existing or not getattr(profile, "phone", None):
            profile.phone = parsed.phone
            logger.debug(f"Updated profile phone: {parsed.phone}")

    # LinkedIn
    if parsed.linkedin:
        if overwrite_existing or not getattr(profile, "linkedin", None):
            profile.linkedin = parsed.linkedin
            logger.debug(f"Updated profile LinkedIn: {parsed.linkedin}")

    # Years of experience (NEW)
    if parsed.years_experience is not None:
        current = getattr(profile, "experience_years", None)
        if overwrite_existing or current is None:
            profile.experience_years = parsed.years_experience
            logger.debug(f"Updated profile experience_years: {parsed.years_experience}")

    return profile
