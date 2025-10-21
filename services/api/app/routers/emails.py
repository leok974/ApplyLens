from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from elasticsearch import BadRequestError, NotFoundError
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
email_risk_feedback_total = Counter(
    "applylens_email_risk_feedback_total", "Email risk feedback submitted", ["verdict"]
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
def get_risk_advice(email_id: str, index: str | None = None):
    """
    Get suspicious email risk assessment with actionable guidance.

    Returns phishing detection scores, explanations, and agentic verification steps
    computed by the applylens_emails_v3 ingest pipeline.

    Args:
        email_id: Email document ID
        index: Optional index name (defaults to 'gmail_emails' alias)
    """
    if not es:
        raise HTTPException(status_code=503, detail="Elasticsearch not available")

    # Default to alias, allow override via query param
    idx = index or "gmail_emails"

    try:
        # Try direct get from specified index/alias
        doc = es.get(
            index=idx,
            id=email_id,
            _source_includes=[
                "from",
                "reply_to",
                "subject",
                "suspicious",
                "suspicion_score",
                "explanations",
                "suggested_actions",
                "verify_checks",
                "labels_norm",
                "headers_authentication_results",
                "received_at",
            ],
        )
    except (NotFoundError, BadRequestError):
        # Fallback: scan all gmail_emails-* indices for the document
        # BadRequestError happens when alias points to multiple indices
        try:
            r = es.search(
                index="gmail_emails-*",
                size=1,
                query={"ids": {"values": [email_id]}},
            )
            if r["hits"]["hits"]:
                doc = {"_source": r["hits"]["hits"][0]["_source"]}
            else:
                raise HTTPException(
                    status_code=404, detail=f"Email {email_id} not found"
                )
        except HTTPException:
            raise
        except Exception as search_err:
            raise HTTPException(
                status_code=500,
                detail=f"Error searching for email: {str(search_err)}",
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching email: {str(e)}")

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

    # Emit Prometheus counter
    email_risk_served_total.labels(level=level).inc()

    return {
        "suspicious": suspicious,
        "suspicion_score": score,
        "explanations": explanations,
        "suggested_actions": suggested_actions,
        "verify_checks": verify_checks,
        "from": src.get("from"),
        "reply_to": src.get("reply_to"),
        "subject": src.get("subject"),
        "received_at": src.get("received_at"),
    }


@router.post("/{email_id}/risk-feedback")
def risk_feedback(email_id: str, body: dict):
    """
    Submit user feedback on email risk assessment for training and refinement.

    Body: { verdict: "scam"|"legit"|"unsure", note?: str }

    - Updates email labels in Elasticsearch
    - Increments Prometheus metrics: applylens_email_risk_feedback_total{verdict=...}
    - Helps improve phishing detection heuristics over time
    """
    if not es:
        raise HTTPException(status_code=503, detail="Elasticsearch not available")

    verdict = (body or {}).get("verdict", "unsure")
    note = (body or {}).get("note", "")

    if verdict not in ["scam", "legit", "unsure"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid verdict. Must be 'scam', 'legit', or 'unsure'",
        )

    try:
        # Fetch current labels
        doc = es.get(
            index="gmail_emails", id=email_id, _source_includes=["labels_norm"]
        )
        labels = doc.get("_source", {}).get("labels_norm", [])
        if not isinstance(labels, list):
            labels = []

        # Update labels based on verdict
        if verdict == "scam":
            if "suspicious" not in labels:
                labels.append("suspicious")
            if "user_confirmed_scam" not in labels:
                labels.append("user_confirmed_scam")
        elif verdict == "legit":
            # Remove suspicious label if present
            labels = [label for label in labels if label != "suspicious"]
            if "user_confirmed_legit" not in labels:
                labels.append("user_confirmed_legit")

        # Update document
        es.update(
            index="gmail_emails",
            id=email_id,
            doc={
                "labels_norm": labels,
                "user_feedback_verdict": verdict,
                "user_feedback_note": note,
                "user_feedback_at": "now",
            },
        )

        # Increment metrics
        email_risk_feedback_total.labels(verdict=verdict).inc()

        return {"ok": True, "verdict": verdict, "labels": labels}

    except Exception as e:
        if "index_not_found" in str(e).lower() or "not_found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Email {email_id} not found")
        raise HTTPException(
            status_code=500, detail=f"Error submitting feedback: {str(e)}"
        )


@router.post("/{email_id}/prime-advice")
async def prime_advice(
    email_id: str, index: str | None = None, background_tasks: BackgroundTasks = None
):
    """
    Prime risk advice cache for instant UI loading (agentic nudge).

    Fire-and-forget endpoint to pre-compute risk advice for high-risk emails.
    Can be called from UI after message open or via scheduled cron sweep.

    Args:
        email_id: Email document ID
        index: Optional index name (defaults to 'gmail_emails' alias)
        background_tasks: FastAPI background tasks
    """

    def _prime():
        """Background task to pre-compute and cache risk advice"""
        try:
            # Call get_risk_advice internally (metrics will be emitted)
            get_risk_advice(email_id=email_id, index=index)
        except Exception:
            # Silent fail - this is best-effort caching
            pass

    if background_tasks:
        background_tasks.add_task(_prime)

    return {"ok": True, "primed": email_id}


@router.get("/risk/summary-24h")
async def risk_summary_24h():
    """
    Get 24-hour risk summary for dashboards/monitoring.

    Returns:
    - high: count of emails with suspicion_score >= 40
    - warn: count of emails with 25 <= suspicion_score < 40
    - low: count of emails with suspicion_score < 25
    - top_reasons: top 5 phishing signals detected

    Useful for Grafana JSON datasource panels, Kibana Canvas, or CLI monitoring.
    """
    if not es:
        raise HTTPException(
            status_code=503, detail="Elasticsearch connection not available"
        )

    try:
        body = {
            "size": 0,
            "query": {"range": {"received_at": {"gte": "now-24h"}}},
            "aggs": {
                "high": {"filter": {"range": {"suspicion_score": {"gte": 40}}}},
                "warn": {
                    "filter": {"range": {"suspicion_score": {"gte": 25, "lt": 40}}}
                },
                "low": {"filter": {"range": {"suspicion_score": {"lt": 25}}}},
                "top_reasons": {"terms": {"field": "explanations.keyword", "size": 5}},
            },
        }

        r = es.search(index="gmail_emails-*", body=body)
        agg = r["aggregations"]

        return {
            "high": agg["high"]["doc_count"],
            "warn": agg["warn"]["doc_count"],
            "low": agg["low"]["doc_count"],
            "top_reasons": [
                {"key": b["key"], "count": b["doc_count"]}
                for b in agg["top_reasons"]["buckets"]
            ],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching risk summary: {str(e)}"
        )
