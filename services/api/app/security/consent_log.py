"""
GDPR/CCPA consent tracking and data privacy management.

Manages user consent for data processing and tracks data retention.
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field


class ConsentType(str, Enum):
    """Types of user consent."""
    ESSENTIAL = "essential"  # Required for service
    ANALYTICS = "analytics"  # Analytics tracking
    MARKETING = "marketing"  # Marketing communications
    PERSONALIZATION = "personalization"  # Personalized features
    THIRD_PARTY = "third_party"  # Third-party data sharing


class ConsentStatus(str, Enum):
    """Status of consent."""
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class DataSubjectRight(str, Enum):
    """GDPR data subject rights."""
    ACCESS = "access"  # Right to access (Art. 15)
    RECTIFICATION = "rectification"  # Right to rectification (Art. 16)
    ERASURE = "erasure"  # Right to erasure (Art. 17)
    RESTRICT = "restrict"  # Right to restrict processing (Art. 18)
    PORTABILITY = "portability"  # Right to data portability (Art. 20)
    OBJECT = "object"  # Right to object (Art. 21)


class ConsentRecord(BaseModel):
    """Record of user consent."""
    user_id: str
    consent_type: ConsentType
    status: ConsentStatus
    granted_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    version: str = "1.0"  # Privacy policy version
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    @property
    def is_active(self) -> bool:
        """Check if consent is currently active."""
        if self.status != ConsentStatus.GRANTED:
            return False
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        
        return True


class DataSubjectRequest(BaseModel):
    """Data subject rights request (GDPR/CCPA)."""
    request_id: str
    user_id: str
    user_email: str
    right_type: DataSubjectRight
    status: str = "pending"  # pending, in_progress, completed, denied
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    # For portability requests
    data_export_url: Optional[str] = None
    
    @property
    def is_overdue(self) -> bool:
        """Check if request is overdue (30 days for GDPR)."""
        deadline = self.requested_at + timedelta(days=30)
        return datetime.utcnow() > deadline and self.status != "completed"


class DataRetentionPolicy(BaseModel):
    """Data retention policy for different data types."""
    data_type: str
    retention_days: int
    legal_basis: str  # contract, legal_obligation, consent, etc.
    description: str
    
    def get_deletion_date(self, created_at: datetime) -> datetime:
        """Calculate when data should be deleted."""
        return created_at + timedelta(days=self.retention_days)


class ConsentManager:
    """
    Manages user consent for GDPR/CCPA compliance.
    
    Tracks consent status, handles withdrawals, and manages
    data subject rights requests.
    """
    
    # Default retention policies
    DEFAULT_RETENTION_POLICIES = [
        DataRetentionPolicy(
            data_type="user_profile",
            retention_days=2555,  # 7 years (legal requirement)
            legal_basis="contract",
            description="User account and profile data",
        ),
        DataRetentionPolicy(
            data_type="email_content",
            retention_days=365,  # 1 year
            legal_basis="consent",
            description="Email messages and attachments",
        ),
        DataRetentionPolicy(
            data_type="analytics_events",
            retention_days=90,  # 90 days
            legal_basis="legitimate_interest",
            description="Usage analytics and metrics",
        ),
        DataRetentionPolicy(
            data_type="audit_logs",
            retention_days=2555,  # 7 years (compliance)
            legal_basis="legal_obligation",
            description="Security and compliance audit logs",
        ),
        DataRetentionPolicy(
            data_type="marketing_data",
            retention_days=730,  # 2 years
            legal_basis="consent",
            description="Marketing preferences and campaign data",
        ),
    ]
    
    def __init__(self):
        self.consent_records: Dict[str, List[ConsentRecord]] = {}
        self.dsr_requests: List[DataSubjectRequest] = []
        self.retention_policies = {p.data_type: p for p in self.DEFAULT_RETENTION_POLICIES}
    
    def grant_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        version: str = "1.0",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expires_days: Optional[int] = None,
    ) -> ConsentRecord:
        """
        Grant user consent.
        
        Args:
            user_id: User ID
            consent_type: Type of consent
            version: Privacy policy version
            ip_address: User's IP address
            user_agent: User's browser/app
            expires_days: Days until consent expires (None = no expiration)
        
        Returns:
            Consent record
        """
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        record = ConsentRecord(
            user_id=user_id,
            consent_type=consent_type,
            status=ConsentStatus.GRANTED,
            granted_at=datetime.utcnow(),
            expires_at=expires_at,
            version=version,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        if user_id not in self.consent_records:
            self.consent_records[user_id] = []
        
        self.consent_records[user_id].append(record)
        
        return record
    
    def withdraw_consent(self, user_id: str, consent_type: ConsentType) -> bool:
        """
        Withdraw user consent.
        
        Args:
            user_id: User ID
            consent_type: Type of consent to withdraw
        
        Returns:
            True if consent was withdrawn
        """
        if user_id not in self.consent_records:
            return False
        
        withdrawn = False
        for record in self.consent_records[user_id]:
            if record.consent_type == consent_type and record.status == ConsentStatus.GRANTED:
                record.status = ConsentStatus.WITHDRAWN
                record.withdrawn_at = datetime.utcnow()
                withdrawn = True
        
        return withdrawn
    
    def check_consent(self, user_id: str, consent_type: ConsentType) -> bool:
        """
        Check if user has active consent.
        
        Args:
            user_id: User ID
            consent_type: Type of consent to check
        
        Returns:
            True if user has active consent
        """
        if user_id not in self.consent_records:
            return False
        
        for record in self.consent_records[user_id]:
            if record.consent_type == consent_type and record.is_active:
                return True
        
        return False
    
    def get_user_consents(self, user_id: str) -> List[ConsentRecord]:
        """Get all consent records for a user."""
        return self.consent_records.get(user_id, [])
    
    def submit_dsr_request(
        self,
        user_id: str,
        user_email: str,
        right_type: DataSubjectRight,
    ) -> DataSubjectRequest:
        """
        Submit a data subject rights request.
        
        Args:
            user_id: User ID
            user_email: User email
            right_type: Type of right being exercised
        
        Returns:
            DSR request
        """
        import uuid
        request_id = f"DSR-{uuid.uuid4().hex[:8].upper()}"
        
        request = DataSubjectRequest(
            request_id=request_id,
            user_id=user_id,
            user_email=user_email,
            right_type=right_type,
        )
        
        self.dsr_requests.append(request)
        
        return request
    
    def process_dsr_request(
        self,
        request_id: str,
        status: str,
        notes: Optional[str] = None,
        data_export_url: Optional[str] = None,
    ) -> bool:
        """
        Process a DSR request.
        
        Args:
            request_id: Request ID
            status: New status (in_progress, completed, denied)
            notes: Processing notes
            data_export_url: URL for data export (for portability requests)
        
        Returns:
            True if request was processed
        """
        for request in self.dsr_requests:
            if request.request_id == request_id:
                request.status = status
                request.notes = notes
                request.data_export_url = data_export_url
                
                if status == "completed":
                    request.completed_at = datetime.utcnow()
                
                return True
        
        return False
    
    def get_overdue_requests(self) -> List[DataSubjectRequest]:
        """Get overdue DSR requests (>30 days)."""
        return [req for req in self.dsr_requests if req.is_overdue]
    
    def get_retention_policy(self, data_type: str) -> Optional[DataRetentionPolicy]:
        """Get retention policy for a data type."""
        return self.retention_policies.get(data_type)
    
    def should_delete(self, data_type: str, created_at: datetime) -> bool:
        """
        Check if data should be deleted based on retention policy.
        
        Args:
            data_type: Type of data
            created_at: When data was created
        
        Returns:
            True if data should be deleted
        """
        policy = self.get_retention_policy(data_type)
        if not policy:
            return False
        
        deletion_date = policy.get_deletion_date(created_at)
        return datetime.utcnow() >= deletion_date
    
    def generate_consent_report(self) -> str:
        """Generate consent status report."""
        total_users = len(self.consent_records)
        
        consent_by_type = {}
        for consent_type in ConsentType:
            count = 0
            for records in self.consent_records.values():
                for record in records:
                    if record.consent_type == consent_type and record.is_active:
                        count += 1
            consent_by_type[consent_type.value] = count
        
        pending_requests = len([r for r in self.dsr_requests if r.status == "pending"])
        overdue_requests = len(self.get_overdue_requests())
        
        report = f"""# Consent & Privacy Report

**Generated:** {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}

## Consent Summary

- **Total Users with Consent Records:** {total_users}

### Active Consents by Type

"""
        
        for consent_type, count in consent_by_type.items():
            report += f"- **{consent_type}:** {count} users\n"
        
        report += f"""

## Data Subject Requests

- **Pending Requests:** {pending_requests}
- **Overdue Requests:** {overdue_requests}

"""
        
        if overdue_requests > 0:
            report += "### Overdue Requests\n\n"
            for request in self.get_overdue_requests():
                days_overdue = (datetime.utcnow() - request.requested_at).days - 30
                report += f"- {request.request_id}: {request.right_type.value} ({days_overdue} days overdue)\n"
        
        report += """

## Retention Policies

"""
        
        for policy in self.retention_policies.values():
            report += f"""
### {policy.data_type}

- **Retention:** {policy.retention_days} days
- **Legal Basis:** {policy.legal_basis}
- **Description:** {policy.description}
"""
        
        return report


# Global instance
_consent_manager = None


def get_consent_manager() -> ConsentManager:
    """Get global consent manager instance."""
    global _consent_manager
    if _consent_manager is None:
        _consent_manager = ConsentManager()
    return _consent_manager
