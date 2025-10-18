"""
PII scanner with automatic detection and redaction.

Detects and redacts personally identifiable information (PII) in logs,
database fields, and API responses.
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class PIIType(str, Enum):
    """Types of PII that can be detected."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    API_KEY = "api_key"
    PASSWORD = "password"
    NAME = "name"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"


class PIIMatch(BaseModel):
    """A detected PII match."""
    pii_type: PIIType
    matched_text: str
    start_pos: int
    end_pos: int
    confidence: float = 1.0  # 0.0 to 1.0
    context: Optional[str] = None


class PIIScanResult(BaseModel):
    """Result of a PII scan."""
    original_text: str
    redacted_text: str
    matches: List[PIIMatch] = Field(default_factory=list)
    scan_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def has_pii(self) -> bool:
        """Check if PII was detected."""
        return len(self.matches) > 0
    
    @property
    def pii_types_found(self) -> Set[PIIType]:
        """Get set of PII types found."""
        return {match.pii_type for match in self.matches}


class PIIScanner:
    """
    Scans text for PII using regex patterns and returns redacted version.
    
    Supports multiple PII types with configurable patterns and redaction.
    """
    
    # Regex patterns for PII detection
    PATTERNS = {
        PIIType.EMAIL: re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            re.IGNORECASE
        ),
        PIIType.PHONE: re.compile(
            r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b'
        ),
        PIIType.SSN: re.compile(
            r'\b(?!000|666|9\d{2})([0-9]{3})[-]?(?!00)([0-9]{2})[-]?(?!0000)([0-9]{4})\b'
        ),
        PIIType.CREDIT_CARD: re.compile(
            r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12})\b'
        ),
        PIIType.IP_ADDRESS: re.compile(
            r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ),
        PIIType.API_KEY: re.compile(
            r'\b(?:api[_-]?key|apikey|access[_-]?token|secret[_-]?key)[:\s=]+["\']?([A-Za-z0-9_\-]{20,})["\']?\b',
            re.IGNORECASE
        ),
        PIIType.PASSWORD: re.compile(
            r'\b(?:password|passwd|pwd)[:\s=]+["\']?([^\s"\']{6,})["\']?\b',
            re.IGNORECASE
        ),
        PIIType.DATE_OF_BIRTH: re.compile(
            r'\b(?:dob|date[_\s]of[_\s]birth)[:\s=]+["\']?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})["\']?\b',
            re.IGNORECASE
        ),
    }
    
    # Redaction templates
    REDACTIONS = {
        PIIType.EMAIL: "[EMAIL_REDACTED]",
        PIIType.PHONE: "[PHONE_REDACTED]",
        PIIType.SSN: "[SSN_REDACTED]",
        PIIType.CREDIT_CARD: "[CREDIT_CARD_REDACTED]",
        PIIType.IP_ADDRESS: "[IP_REDACTED]",
        PIIType.API_KEY: "[API_KEY_REDACTED]",
        PIIType.PASSWORD: "[PASSWORD_REDACTED]",
        PIIType.NAME: "[NAME_REDACTED]",
        PIIType.ADDRESS: "[ADDRESS_REDACTED]",
        PIIType.DATE_OF_BIRTH: "[DOB_REDACTED]",
    }
    
    def __init__(self, enabled_types: Optional[List[PIIType]] = None):
        """
        Initialize PII scanner.
        
        Args:
            enabled_types: List of PII types to scan for.
                          If None, scan for all types.
        """
        if enabled_types is None:
            self.enabled_types = list(PIIType)
        else:
            self.enabled_types = enabled_types
    
    def scan(self, text: str, redact: bool = True) -> PIIScanResult:
        """
        Scan text for PII and optionally redact it.
        
        Args:
            text: Text to scan
            redact: Whether to redact detected PII
        
        Returns:
            PIIScanResult with matches and redacted text
        """
        matches: List[PIIMatch] = []
        redacted_text = text
        
        # Scan for each enabled PII type
        for pii_type in self.enabled_types:
            if pii_type not in self.PATTERNS:
                continue
            
            pattern = self.PATTERNS[pii_type]
            
            for match in pattern.finditer(text):
                matches.append(PIIMatch(
                    pii_type=pii_type,
                    matched_text=match.group(0),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    context=self._get_context(text, match.start(), match.end()),
                ))
        
        # Sort matches by position (reverse order for redaction)
        matches.sort(key=lambda m: m.start_pos, reverse=True)
        
        # Redact if requested
        if redact:
            for match in matches:
                redaction = self.REDACTIONS.get(match.pii_type, "[REDACTED]")
                redacted_text = (
                    redacted_text[:match.start_pos] +
                    redaction +
                    redacted_text[match.end_pos:]
                )
        
        return PIIScanResult(
            original_text=text,
            redacted_text=redacted_text,
            matches=sorted(matches, key=lambda m: m.start_pos),
        )
    
    def scan_dict(self, data: Dict, redact: bool = True) -> Tuple[Dict, List[PIIMatch]]:
        """
        Scan dictionary values for PII.
        
        Args:
            data: Dictionary to scan
            redact: Whether to redact detected PII
        
        Returns:
            Tuple of (redacted_dict, all_matches)
        """
        redacted_data = {}
        all_matches = []
        
        for key, value in data.items():
            if isinstance(value, str):
                result = self.scan(value, redact=redact)
                redacted_data[key] = result.redacted_text
                all_matches.extend(result.matches)
            elif isinstance(value, dict):
                redacted_nested, nested_matches = self.scan_dict(value, redact=redact)
                redacted_data[key] = redacted_nested
                all_matches.extend(nested_matches)
            elif isinstance(value, list):
                redacted_list = []
                for item in value:
                    if isinstance(item, str):
                        result = self.scan(item, redact=redact)
                        redacted_list.append(result.redacted_text)
                        all_matches.extend(result.matches)
                    else:
                        redacted_list.append(item)
                redacted_data[key] = redacted_list
            else:
                redacted_data[key] = value
        
        return redacted_data, all_matches
    
    def _get_context(self, text: str, start: int, end: int, window: int = 20) -> str:
        """Get context around a match."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        
        context = text[context_start:context_end]
        
        # Add ellipsis if truncated
        if context_start > 0:
            context = "..." + context
        if context_end < len(text):
            context = context + "..."
        
        return context
    
    def validate_luhn(self, number: str) -> bool:
        """
        Validate credit card number using Luhn algorithm.
        
        Used to reduce false positives for credit card detection.
        """
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        
        return checksum % 10 == 0


class PIIRedactor:
    """
    High-level PII redaction for logs and API responses.
    
    Automatically redacts PII in logging calls and API responses.
    """
    
    def __init__(self):
        self.scanner = PIIScanner()
        self.redaction_count = 0
    
    def redact_log_message(self, message: str) -> str:
        """
        Redact PII from log message.
        
        Args:
            message: Log message
        
        Returns:
            Redacted log message
        """
        result = self.scanner.scan(message, redact=True)
        
        if result.has_pii:
            self.redaction_count += len(result.matches)
        
        return result.redacted_text
    
    def redact_api_response(self, response: Dict) -> Dict:
        """
        Redact PII from API response.
        
        Args:
            response: API response dictionary
        
        Returns:
            Redacted response
        """
        redacted, matches = self.scanner.scan_dict(response, redact=True)
        
        if matches:
            self.redaction_count += len(matches)
        
        return redacted
    
    def get_stats(self) -> Dict:
        """Get redaction statistics."""
        return {
            "total_redactions": self.redaction_count,
        }


class PIIAuditLog(BaseModel):
    """Audit log entry for PII access."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    action: str  # view, export, delete
    pii_type: PIIType
    resource_id: str
    resource_type: str  # user, email, document, etc.
    justification: Optional[str] = None
    ip_address: Optional[str] = None


class PIIAccessTracker:
    """
    Track access to PII data for compliance auditing.
    
    Logs all access to PII fields for GDPR/CCPA compliance.
    """
    
    def __init__(self):
        self.audit_logs: List[PIIAuditLog] = []
    
    def log_access(
        self,
        user_id: str,
        action: str,
        pii_type: PIIType,
        resource_id: str,
        resource_type: str,
        justification: Optional[str] = None,
        ip_address: Optional[str] = None,
    ):
        """Log PII access."""
        entry = PIIAuditLog(
            user_id=user_id,
            action=action,
            pii_type=pii_type,
            resource_id=resource_id,
            resource_type=resource_type,
            justification=justification,
            ip_address=ip_address,
        )
        
        self.audit_logs.append(entry)
    
    def get_access_logs(
        self,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        days: int = 30,
    ) -> List[PIIAuditLog]:
        """
        Get PII access logs.
        
        Args:
            user_id: Filter by user ID
            resource_id: Filter by resource ID
            days: Number of days to look back
        
        Returns:
            List of audit log entries
        """
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        logs = [
            log for log in self.audit_logs
            if log.timestamp >= cutoff
        ]
        
        if user_id:
            logs = [log for log in logs if log.user_id == user_id]
        
        if resource_id:
            logs = [log for log in logs if log.resource_id == resource_id]
        
        return logs


# Global instances
_pii_scanner = None
_pii_redactor = None
_pii_access_tracker = None


def get_pii_scanner() -> PIIScanner:
    """Get global PII scanner instance."""
    global _pii_scanner
    if _pii_scanner is None:
        _pii_scanner = PIIScanner()
    return _pii_scanner


def get_pii_redactor() -> PIIRedactor:
    """Get global PII redactor instance."""
    global _pii_redactor
    if _pii_redactor is None:
        _pii_redactor = PIIRedactor()
    return _pii_redactor


def get_pii_access_tracker() -> PIIAccessTracker:
    """Get global PII access tracker instance."""
    global _pii_access_tracker
    if _pii_access_tracker is None:
        _pii_access_tracker = PIIAccessTracker()
    return _pii_access_tracker
