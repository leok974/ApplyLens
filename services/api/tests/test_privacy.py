"""
Tests for PII scanning, consent management, and compliance.
"""

import pytest
from datetime import datetime, timedelta

from app.security.pii_scan import (
    PIIScanner,
    PIIRedactor,
    PIIAccessTracker,
    PIIType,
)
from app.security.consent_log import (
    ConsentManager,
    ConsentType,
    ConsentStatus,
    DataSubjectRight,
    ConsentRecord,
    DataSubjectRequest,
)


class TestPIIScanner:
    """Test PII scanner."""

    @pytest.fixture
    def scanner(self):
        """Create PII scanner."""
        return PIIScanner()

    def test_email_detection(self, scanner):
        """Test email address detection."""
        text = "Contact me at user@example.com or admin@test.org"

        result = scanner.scan(text, redact=False)

        assert result.has_pii is True
        assert PIIType.EMAIL in result.pii_types_found
        assert len([m for m in result.matches if m.pii_type == PIIType.EMAIL]) == 2

    def test_phone_detection(self, scanner):
        """Test phone number detection."""
        text = "Call me at (555) 123-4567 or 555-987-6543"

        result = scanner.scan(text, redact=False)

        assert result.has_pii is True
        assert PIIType.PHONE in result.pii_types_found
        assert len([m for m in result.matches if m.pii_type == PIIType.PHONE]) == 2

    def test_ssn_detection(self, scanner):
        """Test SSN detection."""
        text = "My SSN is 123-45-6789"

        result = scanner.scan(text, redact=False)

        assert result.has_pii is True
        assert PIIType.SSN in result.pii_types_found

    def test_credit_card_detection(self, scanner):
        """Test credit card detection."""
        text = "Card number: 4532015112830366"

        result = scanner.scan(text, redact=False)

        assert result.has_pii is True
        assert PIIType.CREDIT_CARD in result.pii_types_found

    def test_ip_address_detection(self, scanner):
        """Test IP address detection."""
        text = "Server IP: 192.168.1.100"

        result = scanner.scan(text, redact=False)

        assert result.has_pii is True
        assert PIIType.IP_ADDRESS in result.pii_types_found

    def test_api_key_detection(self, scanner):
        """Test API key detection."""
        text = "API_KEY=sk_test_abcdefgh1234567890"

        result = scanner.scan(text, redact=False)

        assert result.has_pii is True
        assert PIIType.API_KEY in result.pii_types_found

    def test_password_detection(self, scanner):
        """Test password detection."""
        text = "password: secret123456"

        result = scanner.scan(text, redact=False)

        assert result.has_pii is True
        assert PIIType.PASSWORD in result.pii_types_found

    def test_redaction(self, scanner):
        """Test PII redaction."""
        text = "Email me at user@example.com"

        result = scanner.scan(text, redact=True)

        assert "[EMAIL_REDACTED]" in result.redacted_text
        assert "user@example.com" not in result.redacted_text

    def test_multiple_pii_types(self, scanner):
        """Test detection of multiple PII types."""
        text = "Contact user@example.com at 555-123-4567"

        result = scanner.scan(text, redact=True)

        assert len(result.matches) == 2
        assert PIIType.EMAIL in result.pii_types_found
        assert PIIType.PHONE in result.pii_types_found
        assert "[EMAIL_REDACTED]" in result.redacted_text
        assert "[PHONE_REDACTED]" in result.redacted_text

    def test_scan_dict(self, scanner):
        """Test scanning dictionary values."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "555-123-4567",
            "nested": {"contact": "admin@test.org"},
        }

        redacted, matches = scanner.scan_dict(data, redact=True)

        assert len(matches) >= 2  # At least 2 emails
        assert "[EMAIL_REDACTED]" in redacted["email"]
        assert "[PHONE_REDACTED]" in redacted["phone"]
        assert "[EMAIL_REDACTED]" in redacted["nested"]["contact"]

    def test_no_pii(self, scanner):
        """Test text with no PII."""
        text = "This is a normal message with no PII."

        result = scanner.scan(text, redact=False)

        assert result.has_pii is False
        assert len(result.matches) == 0

    def test_luhn_validation(self, scanner):
        """Test Luhn algorithm for credit card validation."""
        # Valid card number
        assert scanner.validate_luhn("4532015112830366") is True

        # Invalid card number
        assert scanner.validate_luhn("1234567890123456") is False


class TestPIIRedactor:
    """Test PII redactor."""

    @pytest.fixture
    def redactor(self):
        """Create PII redactor."""
        return PIIRedactor()

    def test_redact_log_message(self, redactor):
        """Test redacting log messages."""
        message = "User user@example.com logged in from 192.168.1.100"

        redacted = redactor.redact_log_message(message)

        assert "[EMAIL_REDACTED]" in redacted
        assert "[IP_REDACTED]" in redacted
        assert "user@example.com" not in redacted

    def test_redact_api_response(self, redactor):
        """Test redacting API responses."""
        response = {"user": {"email": "user@example.com", "phone": "555-123-4567"}}

        redacted = redactor.redact_api_response(response)

        assert "[EMAIL_REDACTED]" in redacted["user"]["email"]
        assert "[PHONE_REDACTED]" in redacted["user"]["phone"]

    def test_redaction_stats(self, redactor):
        """Test redaction statistics."""
        redactor.redact_log_message("Email: user@example.com")
        redactor.redact_log_message("Phone: 555-123-4567")

        stats = redactor.get_stats()

        assert stats["total_redactions"] >= 2


class TestPIIAccessTracker:
    """Test PII access tracker."""

    @pytest.fixture
    def tracker(self):
        """Create PII access tracker."""
        return PIIAccessTracker()

    def test_log_access(self, tracker):
        """Test logging PII access."""
        tracker.log_access(
            user_id="user123",
            action="view",
            pii_type=PIIType.EMAIL,
            resource_id="email456",
            resource_type="email",
            justification="Customer support ticket",
        )

        logs = tracker.get_access_logs(user_id="user123")

        assert len(logs) == 1
        assert logs[0].action == "view"
        assert logs[0].pii_type == PIIType.EMAIL

    def test_filter_by_resource(self, tracker):
        """Test filtering access logs by resource."""
        tracker.log_access("user1", "view", PIIType.EMAIL, "res1", "email")
        tracker.log_access("user2", "export", PIIType.EMAIL, "res2", "email")

        logs = tracker.get_access_logs(resource_id="res1")

        assert len(logs) == 1
        assert logs[0].resource_id == "res1"


class TestConsentManager:
    """Test consent manager."""

    @pytest.fixture
    def manager(self):
        """Create consent manager."""
        return ConsentManager()

    def test_grant_consent(self, manager):
        """Test granting consent."""
        record = manager.grant_consent(
            user_id="user123",
            consent_type=ConsentType.ANALYTICS,
            version="1.0",
        )

        assert record.status == ConsentStatus.GRANTED
        assert record.is_active is True

    def test_withdraw_consent(self, manager):
        """Test withdrawing consent."""
        manager.grant_consent("user123", ConsentType.ANALYTICS)

        success = manager.withdraw_consent("user123", ConsentType.ANALYTICS)

        assert success is True
        assert manager.check_consent("user123", ConsentType.ANALYTICS) is False

    def test_check_consent(self, manager):
        """Test checking consent status."""
        manager.grant_consent("user123", ConsentType.MARKETING)

        has_consent = manager.check_consent("user123", ConsentType.MARKETING)

        assert has_consent is True

        # Check consent that wasn't granted
        has_analytics = manager.check_consent("user123", ConsentType.ANALYTICS)
        assert has_analytics is False

    def test_consent_expiration(self, manager):
        """Test consent expiration."""
        # Grant consent that expires in 1 second
        record = manager.grant_consent(
            user_id="user123",
            consent_type=ConsentType.MARKETING,
            expires_days=-1,  # Already expired
        )

        assert record.is_active is False

    def test_get_user_consents(self, manager):
        """Test getting all user consents."""
        manager.grant_consent("user123", ConsentType.ANALYTICS)
        manager.grant_consent("user123", ConsentType.MARKETING)

        consents = manager.get_user_consents("user123")

        assert len(consents) == 2
        consent_types = {c.consent_type for c in consents}
        assert ConsentType.ANALYTICS in consent_types
        assert ConsentType.MARKETING in consent_types

    def test_submit_dsr_request(self, manager):
        """Test submitting data subject request."""
        request = manager.submit_dsr_request(
            user_id="user123",
            user_email="user@example.com",
            right_type=DataSubjectRight.ACCESS,
        )

        assert request.request_id.startswith("DSR-")
        assert request.status == "pending"
        assert request.right_type == DataSubjectRight.ACCESS

    def test_process_dsr_request(self, manager):
        """Test processing DSR request."""
        request = manager.submit_dsr_request(
            user_id="user123",
            user_email="user@example.com",
            right_type=DataSubjectRight.PORTABILITY,
        )

        success = manager.process_dsr_request(
            request.request_id,
            status="completed",
            data_export_url="https://example.com/export/user123.zip",
        )

        assert success is True
        assert request.status == "completed"
        assert request.completed_at is not None

    def test_overdue_requests(self, manager):
        """Test detecting overdue requests."""
        request = manager.submit_dsr_request(
            user_id="user123",
            user_email="user@example.com",
            right_type=DataSubjectRight.ERASURE,
        )

        # Simulate old request
        request.requested_at = datetime.utcnow() - timedelta(days=35)

        overdue = manager.get_overdue_requests()

        assert len(overdue) == 1
        assert overdue[0].request_id == request.request_id

    def test_retention_policy(self, manager):
        """Test retention policy lookup."""
        policy = manager.get_retention_policy("email_content")

        assert policy is not None
        assert policy.retention_days == 365
        assert policy.legal_basis == "consent"

    def test_should_delete(self, manager):
        """Test data deletion check."""
        # Recent data
        recent = datetime.utcnow() - timedelta(days=30)
        assert manager.should_delete("email_content", recent) is False

        # Old data (> 365 days)
        old = datetime.utcnow() - timedelta(days=400)
        assert manager.should_delete("email_content", old) is True

    def test_generate_consent_report(self, manager):
        """Test generating consent report."""
        manager.grant_consent("user1", ConsentType.ANALYTICS)
        manager.grant_consent("user2", ConsentType.MARKETING)
        manager.submit_dsr_request(
            "user3", "user3@example.com", DataSubjectRight.ACCESS
        )

        report = manager.generate_consent_report()

        assert "Consent & Privacy Report" in report
        assert "Total Users with Consent Records" in report
        assert "Data Subject Requests" in report


class TestConsentRecord:
    """Test consent record model."""

    def test_record_creation(self):
        """Test creating a consent record."""
        record = ConsentRecord(
            user_id="user123",
            consent_type=ConsentType.ANALYTICS,
            status=ConsentStatus.GRANTED,
            granted_at=datetime.utcnow(),
            version="1.0",
        )

        assert record.user_id == "user123"
        assert record.consent_type == ConsentType.ANALYTICS
        assert record.is_active is True

    def test_inactive_record(self):
        """Test inactive consent record."""
        record = ConsentRecord(
            user_id="user123",
            consent_type=ConsentType.MARKETING,
            status=ConsentStatus.WITHDRAWN,
            version="1.0",
        )

        assert record.is_active is False


class TestDataSubjectRequest:
    """Test DSR model."""

    def test_request_creation(self):
        """Test creating DSR."""
        request = DataSubjectRequest(
            request_id="DSR-12345678",
            user_id="user123",
            user_email="user@example.com",
            right_type=DataSubjectRight.ACCESS,
        )

        assert request.request_id == "DSR-12345678"
        assert request.status == "pending"

    def test_is_overdue(self):
        """Test overdue detection."""
        request = DataSubjectRequest(
            request_id="DSR-12345678",
            user_id="user123",
            user_email="user@example.com",
            right_type=DataSubjectRight.ERASURE,
        )

        # Recent request
        assert request.is_overdue is False

        # Old request
        request.requested_at = datetime.utcnow() - timedelta(days=35)
        assert request.is_overdue is True

        # Completed request (not overdue)
        request.status = "completed"
        assert request.is_overdue is False
