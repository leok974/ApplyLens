from fastapi import APIRouter, Depends, HTTPException, Query
from prometheus_client import Counter
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..deps.user import get_current_user_email
from ..es import es
from ..schemas import EmailOut

router = APIRouter(prefix="/emails", tags=["emails"])

# Prometheus metrics for risk advice
email_risk_served_total = Counter(
    "applylens_email_risk_served_total", "Email risk advice served", ["level"]
)


@router.get("/", response_model=list[EmailOut])
def list_emails(
    limit: int = Query(
        50, ge=1, le=500, description="Maximum number of emails to return"
    ),
    offset: int = Query(0, ge=0, description="Number of emails to skip"),
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """List emails for the current user, newest first."""
    rows = (
        db.query(models.Email)
        .filter(models.Email.owner_email == user_email)
        .order_by(models.Email.received_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows


@router.get("/{email_id}/risk-advice")
def get_risk_advice(email_id: str):
    """
    Get suspicious email risk assessment with actionable guidance.

    Returns phishing detection scores, explanations, and agentic verification steps
    computed by the applylens_emails_v3 ingest pipeline.
    """
    if not es:
        raise HTTPException(status_code=503, detail="Elasticsearch not available")

    try:
        doc = es.get(
            index="gmail_emails",
            id=email_id,
            _source_includes=[
                "suspicious",
                "suspicion_score",
                "explanations",
                "suggested_actions",
                "verify_checks",
            ],
        )

        src = doc.get("_source", {})

        # Extract fields with defaults
        suspicious = src.get("suspicious", False)
        score = src.get("suspicion_score", 0)
        explanations = src.get("explanations", [])
        suggested_actions = src.get(
            "suggested_actions", ["Wait to share any personal details until verified."]
        )
        verify_checks = src.get(
            "verify_checks",
            [
                "Request official posting link.",
                "Ask for a calendar invite from corporate domain.",
            ],
        )

        # Determine risk level for metrics
        if suspicious:
            level = "suspicious"
        elif score >= 25:
            level = "warn"
        else:
            level = "ok"

        email_risk_served_total.labels(level=level).inc()

        return {
            "suspicious": suspicious,
            "suspicion_score": score,
            "explanations": explanations,
            "suggested_actions": suggested_actions,
            "verify_checks": verify_checks,
        }

    except Exception as e:
        if "index_not_found" in str(e).lower() or "not_found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Email {email_id} not found")
        raise HTTPException(
            status_code=500, detail=f"Error fetching risk advice: {str(e)}"
        )
