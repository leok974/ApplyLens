from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class EmailOut(BaseModel):
    id: int
    thread_id: str
    from_addr: str
    subject: str
    label: str
    received_at: datetime

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
