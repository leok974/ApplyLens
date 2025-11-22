# Dev-only risk assessment endpoints for E2E testing
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import os

# Security prefix router (for /security/rescan)
router = APIRouter(prefix="/security", tags=["security", "dev"])

# No-prefix router for /emails paths that tests expect
emails_risk_router = APIRouter(tags=["emails", "dev"])


def require_dev():
    """Ensure dev routes are only accessible when ALLOW_DEV_ROUTES=1"""
    if os.getenv("ALLOW_DEV_ROUTES") != "1":
        raise HTTPException(status_code=403, detail="Dev routes disabled")


class RiskRescanRequest(BaseModel):
    email_id: str


class RiskResponse(BaseModel):
    ok: bool
    email_id: str
    suspicious: bool
    risk_score: int
    flags: list[str]
    evidence: list[str]
    version: str


@router.post(
    "/rescan", response_model=RiskResponse, dependencies=[Depends(require_dev)]
)
def rescan_risk(payload: RiskRescanRequest):
    """Dev stub for email risk rescanning - returns mock data for testing"""
    # Return test case data based on email_id pattern
    # tc1 = high risk, tc2 = medium, tc3 = low
    if "tc1" in payload.email_id.lower():
        return RiskResponse(
            ok=True,
            email_id=payload.email_id,
            suspicious=True,
            risk_score=95,
            flags=["suspicious_link", "urgency_language", "external_sender"],
            evidence=[
                "Contains link to unverified domain",
                "Uses urgent call-to-action language",
                "Sender not in organization",
            ],
            version="dev-stub",
        )
    elif "tc2" in payload.email_id.lower():
        return RiskResponse(
            ok=True,
            email_id=payload.email_id,
            suspicious=True,
            risk_score=65,
            flags=["suspicious_link"],
            evidence=["Contains link that may be phishing"],
            version="dev-stub",
        )
    else:
        return RiskResponse(
            ok=True,
            email_id=payload.email_id,
            suspicious=False,
            risk_score=12,
            flags=[],
            evidence=[],
            version="dev-stub",
        )


@router.get(
    "/emails/{email_id}/risk",
    response_model=RiskResponse,
    dependencies=[Depends(require_dev)],
)
def get_email_risk(email_id: str):
    """Dev stub for getting email risk assessment (legacy /security/emails path)"""
    # Reuse same logic as rescan
    return rescan_risk(RiskRescanRequest(email_id=email_id))


# === Emails risk endpoints (no prefix - matches test expectations) ===


@emails_risk_router.get(
    "/emails/{email_id}/risk-advice", dependencies=[Depends(require_dev)]
)
def get_risk_advice(email_id: str):
    """Dev stub for risk advice endpoint - returns detailed explanations"""
    # Return realistic risk advice for test fixture tc1-brand-mismatch
    if "tc1" in email_id.lower() or "brand" in email_id.lower():
        return {
            "suspicious": True,
            "suspicion_score": 85,
            "explanations": [
                "Brand mismatch: email mentions 'Prometric' but sender domain is careers-finetunelearning.com",
                "Suspicious SPF: neutral result indicates sender IP not authorized",
                "DMARC policy missing: no protection against spoofing",
            ],
            "recommended_actions": ["quarantine", "report_phishing"],
            "version": "dev-stub",
        }

    # Default low-risk response
    return {
        "suspicious": False,
        "suspicion_score": 5,
        "explanations": [],
        "recommended_actions": [],
        "version": "dev-stub",
    }


@emails_risk_router.post(
    "/emails/{email_id}/risk-feedback", dependencies=[Depends(require_dev)]
)
def submit_risk_feedback(email_id: str, verdict: dict):
    """Dev stub for risk feedback submission"""
    return {
        "ok": True,
        "email_id": email_id,
        "feedback_recorded": True,
        "verdict": verdict,
        "version": "dev-stub",
    }
