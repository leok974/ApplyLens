"""
Golden tests for Inbox Triage Agent.

Tests with mocked Gmail provider to verify risk scoring and triage logic.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.agents.inbox_triage import InboxTriageAgent, RiskScorer


class MockGmailProvider:
    """Mock Gmail provider for testing."""

    def __init__(self, mock_emails):
        self.mock_emails = mock_emails

    def search_recent(self, query: str, max_results: int = 10):
        """Return mock emails."""
        return self.mock_emails[:max_results]


class MockProviderFactory:
    """Mock provider factory."""

    def __init__(self, gmail_provider):
        self._gmail = gmail_provider

    def gmail(self):
        return self._gmail


# ============================================================================
# Test Data - Golden Email Samples
# ============================================================================

GOLDEN_EMAILS = {
    "phishing_urgent": {
        "id": "email_001",
        "from": "security@paypal-verify.tk",
        "subject": "URGENT: Verify Your Account Now",
        "snippet": "Your account will be suspended unless you verify your billing information. Click here immediately to confirm your password.",
        "date": "2025-10-17T10:00:00Z",
        "labels": [],
    },
    "spam_prize": {
        "id": "email_002",
        "from": "winner@prize-claim.ru",
        "subject": "Congratulations! You won $1,000,000",
        "snippet": "Click below to claim your prize. Act now before it expires!",
        "date": "2025-10-17T09:00:00Z",
        "labels": ["SPAM"],
    },
    "legit_github": {
        "id": "email_003",
        "from": "notifications@github.com",
        "subject": "Pull request merged #123",
        "snippet": "Your pull request has been successfully merged into main branch.",
        "date": "2025-10-17T08:00:00Z",
        "labels": ["CATEGORY_UPDATES"],
    },
    "promo_newsletter": {
        "id": "email_004",
        "from": "newsletter@shop.com",
        "subject": "Weekend Sale - 50% Off",
        "snippet": "Check out our latest deals this weekend only.",
        "date": "2025-10-17T07:00:00Z",
        "labels": ["CATEGORY_PROMOTIONS"],
    },
    "suspicious_billing": {
        "id": "email_005",
        "from": "billing@services-update.cn",
        "subject": "Your billing information expired",
        "snippet": "Please verify your account to avoid suspension. Urgent action required.",
        "date": "2025-10-17T06:00:00Z",
        "labels": [],
    },
}


# ============================================================================
# Risk Scoring Tests
# ============================================================================


def test_risk_scorer_phishing():
    """Test risk scoring for obvious phishing attempt."""
    email = GOLDEN_EMAILS["phishing_urgent"]
    result = RiskScorer.score(email)

    print("\n[TEST] Phishing Email Risk Scoring")
    print(f"  Email: {email['subject']}")
    print(f"  Risk Score: {result['risk_score']}")
    print(f"  Risk Level: {result['risk_level']}")
    print(f"  Reasons: {result['reasons']}")

    assert (
        result["risk_score"] >= 80
    ), f"Expected high risk score, got {result['risk_score']}"
    assert (
        result["risk_level"] == "CRITICAL"
    ), f"Expected CRITICAL, got {result['risk_level']}"
    assert "suspicious TLD" in result["reasons"]
    assert result["suggested_action"] == "quarantine"
    print("  ✓ PASSED")


def test_risk_scorer_spam():
    """Test risk scoring for spam with Gmail label."""
    email = GOLDEN_EMAILS["spam_prize"]
    result = RiskScorer.score(email)

    print("\n[TEST] Spam Email Risk Scoring")
    print(f"  Email: {email['subject']}")
    print(f"  Risk Score: {result['risk_score']}")
    print(f"  Risk Level: {result['risk_level']}")

    assert (
        result["risk_score"] >= 60
    ), f"Expected high risk score, got {result['risk_score']}"
    assert result["risk_level"] in ["HIGH", "CRITICAL"], f"Got {result['risk_level']}"
    assert "Gmail marked as spam" in result["reasons"]
    print("  ✓ PASSED")


def test_risk_scorer_legit():
    """Test risk scoring for legitimate email."""
    email = GOLDEN_EMAILS["legit_github"]
    result = RiskScorer.score(email)

    print("\n[TEST] Legitimate Email Risk Scoring")
    print(f"  Email: {email['subject']}")
    print(f"  Risk Score: {result['risk_score']}")
    print(f"  Risk Level: {result['risk_level']}")

    assert (
        result["risk_score"] < 30
    ), f"Expected low risk score, got {result['risk_score']}"
    assert result["risk_level"] in ["SAFE", "LOW"], f"Got {result['risk_level']}"
    print("  ✓ PASSED")


def test_risk_scorer_promo():
    """Test risk scoring for promotional email."""
    email = GOLDEN_EMAILS["promo_newsletter"]
    result = RiskScorer.score(email)

    print("\n[TEST] Promotional Email Risk Scoring")
    print(f"  Email: {email['subject']}")
    print(f"  Risk Score: {result['risk_score']}")
    print(f"  Risk Level: {result['risk_level']}")

    assert (
        result["risk_score"] < 40
    ), f"Expected medium-low risk, got {result['risk_score']}"
    print("  ✓ PASSED")


# ============================================================================
# Agent Execution Tests
# ============================================================================


def test_inbox_triage_dry_run():
    """Test inbox triage in dry-run mode."""
    print("\n[TEST] Inbox Triage - Dry Run Mode")

    # Setup mock provider
    mock_emails = list(GOLDEN_EMAILS.values())
    mock_gmail = MockGmailProvider(mock_emails)
    mock_factory = MockProviderFactory(mock_gmail)

    # Create agent
    agent = InboxTriageAgent(provider_factory=mock_factory)

    # Create plan
    plan = agent.plan(
        objective="Triage inbox emails",
        params={
            "max_emails": 10,
            "hours_back": 24,
            "apply_labels": True,
            "quarantine_threshold": 80,
        },
    )

    # Add dry_run flag
    plan["dry_run"] = True

    # Execute
    result = agent.execute(plan)

    print(f"  Total emails: {result['total_emails']}")
    print(f"  By risk level: {result['by_risk_level']}")
    print(f"  High risk count: {result['high_risk_count']}")
    print(f"  Quarantined: {result['quarantined_count']}")
    print(f"  Actions taken: {result['actions_count']}")
    print(f"  Dry run: {result['dry_run']}")

    assert result["total_emails"] == len(mock_emails)
    assert result["high_risk_count"] >= 2, "Should detect at least 2 high-risk emails"
    assert result["dry_run"] is True
    assert result["actions_count"] == 0, "No actions should be taken in dry run"
    print("  ✓ PASSED")


def test_inbox_triage_live_mode():
    """Test inbox triage in live mode (still mocked)."""
    print("\n[TEST] Inbox Triage - Live Mode (Mocked)")

    # Setup mock provider
    mock_emails = list(GOLDEN_EMAILS.values())
    mock_gmail = MockGmailProvider(mock_emails)
    mock_factory = MockProviderFactory(mock_gmail)

    # Create agent
    agent = InboxTriageAgent(provider_factory=mock_factory)

    # Create plan
    plan = agent.plan(
        objective="Triage inbox emails",
        params={
            "max_emails": 10,
            "hours_back": 24,
            "apply_labels": False,  # Don't apply labels (would be denied by approvals)
            "quarantine_threshold": 80,
        },
    )

    # Set live mode
    plan["dry_run"] = False

    # Execute
    result = agent.execute(plan)

    print(f"  Total emails: {result['total_emails']}")
    print(f"  High risk count: {result['high_risk_count']}")
    print(f"  Quarantined: {result['quarantined_count']}")
    print(f"  Actions taken: {result['actions_count']}")

    assert result["total_emails"] == len(mock_emails)
    assert result["high_risk_count"] >= 2
    # Quarantine actions should be denied by Approvals.allow()
    assert (
        result["quarantined_count"] == 0
    ), "Quarantine should be denied without approval"
    print("  ✓ PASSED")


def test_inbox_triage_report_generation():
    """Test triage report artifact generation."""
    print("\n[TEST] Inbox Triage - Report Generation")

    # Setup mock provider
    mock_emails = [
        GOLDEN_EMAILS["phishing_urgent"],
        GOLDEN_EMAILS["spam_prize"],
        GOLDEN_EMAILS["legit_github"],
    ]
    mock_gmail = MockGmailProvider(mock_emails)
    mock_factory = MockProviderFactory(mock_gmail)

    # Create agent
    agent = InboxTriageAgent(provider_factory=mock_factory)

    # Create plan
    plan = agent.plan(objective="Triage inbox", params={"max_emails": 10})
    plan["dry_run"] = True

    # Execute
    result = agent.execute(plan)

    # Check artifacts were created
    assert "artifacts" in result
    assert "report" in result["artifacts"]
    assert "results_json" in result["artifacts"]

    print(f"  Report path: {result['artifacts']['report']}")
    print(f"  JSON path: {result['artifacts']['results_json']}")
    print("  ✓ PASSED")


def test_inbox_triage_risk_distribution():
    """Test risk distribution across email types."""
    print("\n[TEST] Inbox Triage - Risk Distribution")

    # Setup mock provider with all email types
    mock_emails = list(GOLDEN_EMAILS.values())
    mock_gmail = MockGmailProvider(mock_emails)
    mock_factory = MockProviderFactory(mock_gmail)

    # Create agent
    agent = InboxTriageAgent(provider_factory=mock_factory)

    # Create plan
    plan = agent.plan(objective="Triage all emails", params={"max_emails": 100})
    plan["dry_run"] = True

    # Execute
    result = agent.execute(plan)

    by_risk = result["by_risk_level"]
    print("  Risk distribution:")
    for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "SAFE"]:
        count = by_risk.get(level, 0)
        if count > 0:
            print(f"    {level}: {count}")

    # Verify we have different risk levels
    critical_high = by_risk.get("CRITICAL", 0) + by_risk.get("HIGH", 0)
    safe_low = by_risk.get("SAFE", 0) + by_risk.get("LOW", 0)

    assert critical_high >= 2, "Should have critical/high risk emails"
    assert safe_low >= 1, "Should have safe/low risk emails"
    print("  ✓ PASSED")


# ============================================================================
# Main Test Runner
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Inbox Triage Agent - Golden Tests")
    print("=" * 70)

    print("\n--- Risk Scoring Tests ---")
    test_risk_scorer_phishing()
    test_risk_scorer_spam()
    test_risk_scorer_legit()
    test_risk_scorer_promo()

    print("\n--- Agent Execution Tests ---")
    test_inbox_triage_dry_run()
    test_inbox_triage_live_mode()
    test_inbox_triage_report_generation()
    test_inbox_triage_risk_distribution()

    print("\n" + "=" * 70)
    print("✓ ALL GOLDEN TESTS PASSED")
    print("=" * 70 + "\n")
