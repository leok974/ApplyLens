"""Learning loop API endpoints for the Companion extension."""

import logging
import os
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException, status

from app.models_learning import LearningProfileResponse, LearningSyncRequest, StyleHint
from app.models_learning_db import FormProfile, AutofillEvent, GenStyle
from app.core.metrics import learning_sync_counter
from app.db import get_db
from app.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/extension/learning", tags=["learning"])

DEV_MODE = os.getenv("APPLYLENS_DEV", "1") == "1"


def dev_only():
    """Guard for dev-only endpoints."""
    if not DEV_MODE:
        raise HTTPException(status_code=403, detail="Dev-only endpoint")
    return True


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def learning_sync(
    payload: LearningSyncRequest,
    db: Session = Depends(get_db),
    _dev: bool = Depends(dev_only),
):
    """Ingest anonymized learning events from the Companion extension.

    Phase 2.0: Persist events to autofill_events table and update form_profiles.

    Args:
        payload: Batch of learning events from the extension
        db: Database session
        _dev: Dev-mode guard

    Returns:
        202 Accepted with confirmation
    """
    # Check if we're using PostgreSQL (skip persistence on SQLite)
    is_postgres = "postgresql" in settings.DATABASE_URL.lower()

    if not is_postgres:
        # Phase 1.5 behavior: Just log metrics on SQLite
        learning_sync_counter.labels(status="sqlite_skip").inc()
        return {"status": "accepted", "persisted": False, "reason": "sqlite"}

    try:
        # Generate a temporary user_id for Phase 2.0
        # Phase 3.0 will use actual authenticated user_id
        temp_user_id = uuid.uuid4()

        # Persist each event to database
        events_created = 0
        for event in payload.events:
            db_event = AutofillEvent(
                user_id=temp_user_id,
                host=event.host,
                schema_hash=event.schema_hash,
                suggested_map=event.suggested_map,
                final_map=event.final_map,
                gen_style_id=event.gen_style_id,
                edit_stats=event.edit_stats.dict(),
                duration_ms=event.duration_ms,
                validation_errors=event.validation_errors,
                status=event.status,
                application_id=uuid.UUID(event.application_id)
                if event.application_id
                else None,
            )
            db.add(db_event)
            events_created += 1

        # Update or create form profile
        profile = (
            db.query(FormProfile)
            .filter(
                FormProfile.host == payload.host,
                FormProfile.schema_hash == payload.schema_hash,
            )
            .first()
        )

        if profile:
            # Update existing profile
            profile.last_seen_at = datetime.utcnow()
            # TODO: Recalculate aggregate stats from all events
        else:
            # Create new profile
            profile = FormProfile(
                host=payload.host,
                schema_hash=payload.schema_hash,
                fields={},  # Will be populated by aggregation job
                last_seen_at=datetime.utcnow(),
            )
            db.add(profile)

        db.commit()
        learning_sync_counter.labels(status="persisted").inc()

        return {"status": "accepted", "persisted": True, "events_saved": events_created}

    except Exception as e:
        db.rollback()
        learning_sync_counter.labels(status="error").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist learning events: {str(e)}",
        )


@router.get("/profile", response_model=LearningProfileResponse)
async def learning_profile(
    host: str,
    schema_hash: str,
    db: Session = Depends(get_db),
    _dev: bool = Depends(dev_only),
):
    """Return canonical mapping + style hints for a host+schema pair.

    Phase 2.1: Query form_profiles table for aggregated learned mappings.

    Args:
        host: Hostname (e.g., "greenhouse.io")
        schema_hash: Hash of form schema
        db: Database session
        _dev: Dev-mode guard

    Returns:
        Form profile with canonical mappings and style hints
    """
    # Check if we're using PostgreSQL
    is_postgres = "postgresql" in settings.DATABASE_URL.lower()

    if not is_postgres:
        # Phase 1.5 behavior: Return empty profile on SQLite
        return LearningProfileResponse(host=host, schema_hash=schema_hash)

    # Query database for existing profile
    profile = (
        db.query(FormProfile)
        .filter(FormProfile.host == host, FormProfile.schema_hash == schema_hash)
        .first()
    )

    if not profile:
        # No profile exists yet - return empty
        return LearningProfileResponse(host=host, schema_hash=schema_hash)

    # Safety guard: Reject low-confidence profiles from noisy or early data
    # Low success rate (<60%) or high edit distance (>500 chars) indicates
    # the profile hasn't stabilized yet and shouldn't be used for recommendations
    success_rate = profile.success_rate or 0.0
    avg_edit_chars = profile.avg_edit_chars or 0.0

    if success_rate < 0.6 or avg_edit_chars > 500:
        logger.info(
            f"Rejecting low-confidence profile for {host}/{schema_hash}: "
            f"success_rate={success_rate:.2f}, avg_edit_chars={avg_edit_chars:.1f}"
        )
        return LearningProfileResponse(host=host, schema_hash=schema_hash)

    # Pick best GenStyle for this host/schema based on prior_weight
    # The aggregator updates prior_weight based on edit distance
    style = db.query(GenStyle).order_by(GenStyle.prior_weight.desc()).first()

    style_hint = None
    if style:
        # Confidence based on number of events for this form
        event_count = (
            db.query(func.count(AutofillEvent.id))
            .filter(
                AutofillEvent.host == host,
                AutofillEvent.schema_hash == schema_hash,
                AutofillEvent.status == "ok",
            )
            .scalar()
        )

        # Simple confidence: more samples = higher confidence
        # 10+ events = full confidence
        confidence = min((event_count or 0) / 10.0, 1.0)

        style_hint = StyleHint(gen_style_id=style.id, confidence=confidence)

    return LearningProfileResponse(
        host=host,
        schema_hash=schema_hash,
        canonical_map=profile.fields or {},
        style_hint=style_hint,
    )
