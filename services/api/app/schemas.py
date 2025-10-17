from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EmailOut(BaseModel):
    id: int
    gmail_id: Optional[str] = None
    thread_id: Optional[str] = None
    subject: Optional[str] = None
    sender: Optional[str] = None
    recipient: Optional[str] = None
    received_at: Optional[datetime] = None
    owner_email: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    category: Optional[str] = None

    class Config:
        from_attributes = True


# Security Policy Schemas
class AutoUnsubscribeConfig(BaseModel):
    enabled: bool
    threshold: int


class SecurityPoliciesIn(BaseModel):
    auto_quarantine_high_risk: bool
    auto_archive_expired_promos: bool
    auto_unsubscribe_inactive: Optional[AutoUnsubscribeConfig] = None


class SecurityPoliciesOut(BaseModel):
    autoQuarantineHighRisk: bool
    autoArchiveExpiredPromos: bool
    autoUnsubscribeInactive: dict
