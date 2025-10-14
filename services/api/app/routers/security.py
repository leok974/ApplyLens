# services/api/app/routers/security.py
import asyncio
import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Email
from app.security.analyzer import BlocklistProvider, EmailRiskAnalyzer, RiskAnalysis
from app.security.events import BUS

router = APIRouter(prefix="/security", tags=["security"])

# Initialize blocklist provider and analyzer
BLOCKLISTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "security", "blocklists.json"
)
try:
    BLOCKLIST_PROVIDER = BlocklistProvider(BLOCKLISTS_PATH)
    ANALYZER = EmailRiskAnalyzer(blocklists=BLOCKLIST_PROVIDER)
except Exception as e:
    print(f"Warning: Could not load blocklists from {BLOCKLISTS_PATH}: {e}")
    ANALYZER = EmailRiskAnalyzer()


@router.post("/rescan/{email_id}")
def rescan_email(email_id: str, db: Session = Depends(get_db)):
    """
    Rescan an email for security risks and update its risk score, flags, and quarantine status.
    """
    # Fetch email from database
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail=f"Email {email_id} not found")

    # Build inputs for analyzer
    # Extract headers from raw Gmail API response
    headers_dict = {}
    if email.raw and isinstance(email.raw, dict):
        payload = email.raw.get("payload", {})
        headers_list = payload.get("headers", [])
        headers_dict = {
            h["name"]: h["value"] for h in headers_list if isinstance(h, dict)
        }

    # Parse from field
    from_parts = email.sender.split("<") if email.sender else []
    from_name = from_parts[0].strip().strip('"') if len(from_parts) > 1 else ""
    from_email = (
        from_parts[1].rstrip(">") if len(from_parts) > 1 else (email.sender or "")
    )

    # Analyze
    result: RiskAnalysis = ANALYZER.analyze(
        headers=headers_dict,
        from_name=from_name,
        from_email=from_email,
        subject=email.subject or "",
        body_text=email.body_text or "",
        body_html=None,  # Could extract from raw if needed
        urls_visible_text_pairs=None,  # Auto-extract from body
        attachments=[],  # Could parse from payload parts if needed
        domain_first_seen_days_ago=None,  # Could compute from domain age
    )

    # Update email record with JSONB flags
    email.risk_score = float(result.risk_score)  # risk_score is Float in model
    email.flags = [f.dict() for f in result.flags]  # JSONB accepts list directly
    email.quarantined = result.quarantined

    db.commit()
    db.refresh(email)

    return {
        "status": "ok",
        "email_id": email_id,
        "risk_score": result.risk_score,
        "quarantined": result.quarantined,
        "flags": [f.dict() for f in result.flags],
    }


@router.get("/stats")
def get_security_stats(db: Session = Depends(get_db)):
    """
    Get overall security statistics across all emails.
    """
    from sqlalchemy import func

    # Count quarantined emails
    quarantined = db.query(func.count(Email.id)).filter(Email.quarantined).scalar() or 0

    # Average risk score
    average_risk = (
        db.query(func.avg(Email.risk_score))
        .filter(Email.risk_score.isnot(None))
        .scalar()
    )
    average_risk = float(average_risk) if average_risk is not None else 0.0

    # High risk count (score >= 50)
    high_risk = (
        db.query(func.count(Email.id)).filter(Email.risk_score >= 50).scalar() or 0
    )

    return {
        "total_quarantined": quarantined,
        "average_risk_score": round(average_risk, 2),
        "high_risk_count": high_risk,
    }


@router.post("/bulk/rescan")
def bulk_rescan(email_ids: list[str], db: Session = Depends(get_db)):
    """
    Rescan multiple emails for security risks.
    Returns count of successfully rescanned emails.
    """
    updated = 0

    for eid in email_ids:
        try:
            email = db.query(Email).filter(Email.id == eid).first()
            if not email:
                continue

            # Extract headers from raw
            headers_dict = {}
            if email.raw and isinstance(email.raw, dict):
                payload = email.raw.get("payload", {})
                headers_list = payload.get("headers", [])
                headers_dict = {
                    h["name"]: h["value"] for h in headers_list if isinstance(h, dict)
                }

            # Parse from field
            from_parts = email.sender.split("<") if email.sender else []
            from_name = from_parts[0].strip().strip('"') if len(from_parts) > 1 else ""
            from_email = (
                from_parts[1].rstrip(">")
                if len(from_parts) > 1
                else (email.sender or "")
            )

            # Analyze
            result = ANALYZER.analyze(
                headers=headers_dict,
                from_name=from_name,
                from_email=from_email,
                subject=email.subject or "",
                body_text=email.body_text or "",
                body_html=None,
                urls_visible_text_pairs=None,
                attachments=[],
                domain_first_seen_days_ago=None,
            )

            # Update
            email.risk_score = float(result.risk_score)
            email.flags = [f.dict() for f in result.flags]
            email.quarantined = result.quarantined
            updated += 1
        except Exception as e:
            print(f"Error rescanning email {eid}: {e}")
            continue

    db.commit()
    return {"updated": updated, "total": len(email_ids)}


@router.post("/bulk/quarantine")
def bulk_quarantine(email_ids: list[str], db: Session = Depends(get_db)):
    """
    Quarantine multiple emails by ID.
    Returns count of quarantined emails.
    """
    count = 0
    for eid in email_ids:
        email = db.query(Email).filter(Email.id == eid).first()
        if email:
            email.quarantined = True
            count += 1

    db.commit()
    return {"quarantined": count, "total": len(email_ids)}


@router.post("/bulk/release")
def bulk_release(email_ids: list[str], db: Session = Depends(get_db)):
    """
    Release multiple emails from quarantine.
    Returns count of released emails.
    """
    count = 0
    for eid in email_ids:
        email = db.query(Email).filter(Email.id == eid).first()
        if email:
            email.quarantined = False
            count += 1

    db.commit()
    return {"released": count, "total": len(email_ids)}


@router.get("/events")
async def security_events(request: Request):
    """
    Server-Sent Events (SSE) endpoint for real-time security notifications.

    Streams events like:
    - High-risk email detected
    - Bulk quarantine operations
    - Policy changes

    Usage:
        const es = new EventSource('/api/security/events', { withCredentials: true });
        es.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Security event:', data);
        };
    """
    q = BUS.subscribe()

    async def event_generator():
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                try:
                    # Wait for event with timeout (for keepalive)
                    evt = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"data: {json.dumps(evt)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield ": keepalive\n\n"
        finally:
            # Clean up subscription
            BUS.unsubscribe(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
