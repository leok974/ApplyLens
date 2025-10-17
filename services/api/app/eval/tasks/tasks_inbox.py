"""
Golden tasks for inbox.triage agent.

These are representative test cases covering:
- Phishing detection
- Risk scoring
- Email categorization
- Offer detection
- Spam filtering
"""
from typing import List
from app.eval.models import EvalTask, EvalSuite


def get_inbox_tasks() -> List[EvalTask]:
    """Get all inbox.triage eval tasks."""
    return [
        # Phishing detection tasks
        EvalTask(
            id="inbox.phishing.001",
            agent="inbox.triage",
            category="phishing_detection",
            objective="Analyze this suspicious email for phishing indicators",
            context={
                "subject": "Urgent: Verify your account immediately",
                "sender": "noreply@secure-bank-verify.net",
                "sender_display": "Bank Security Team",
                "body": """Dear Customer,
                
Your account has been flagged for suspicious activity. Please verify your identity immediately by clicking the link below:

http://verify-account-now.suspicious-domain.com/login

Failure to verify within 24 hours will result in account suspension.

Bank Security Team""",
                "has_links": True,
                "domain_age_days": 3,
                "sender_in_contacts": False,
            },
            expected_output={
                "risk_level": "high",
                "is_phishing": True,
                "category": "phishing",
                "confidence": 0.95,
            },
            invariants=["no_false_negatives_phishing"],
            difficulty="easy",
            tags=["phishing", "red_team", "critical"],
        ),
        
        EvalTask(
            id="inbox.phishing.002",
            agent="inbox.triage",
            category="phishing_detection",
            objective="Check if this email is a legitimate security alert or phishing",
            context={
                "subject": "Security Alert: New login from Windows device",
                "sender": "no-reply@accounts.google.com",
                "sender_display": "Google",
                "body": """Hi there,

We noticed a new sign-in to your Google Account on a Windows device. If this was you, you don't need to do anything. If not, we'll help you secure your account.

Check activity: https://myaccount.google.com/notifications

The Google Accounts team""",
                "has_links": True,
                "domain_age_days": 5000,
                "sender_in_contacts": False,
                "spf_pass": True,
                "dkim_pass": True,
            },
            expected_output={
                "risk_level": "low",
                "is_phishing": False,
                "category": "notification",
                "confidence": 0.90,
            },
            invariants=[],
            difficulty="medium",
            tags=["phishing", "false_positive_test"],
        ),
        
        # Risk scoring tasks
        EvalTask(
            id="inbox.risk.001",
            agent="inbox.triage",
            category="risk_scoring",
            objective="Assess risk level of this email with urgent payment request",
            context={
                "subject": "URGENT: Invoice payment required",
                "sender": "billing@unknown-company.biz",
                "body": "Your invoice is overdue. Pay immediately to avoid penalties. Wire transfer details: ...",
                "has_attachments": True,
                "attachment_types": [".pdf", ".exe"],
                "sender_in_contacts": False,
                "urgency_keywords": ["urgent", "immediately", "overdue"],
            },
            expected_output={
                "risk_level": "high",
                "is_phishing": True,
                "category": "financial_scam",
                "confidence": 0.88,
            },
            invariants=["no_false_negatives_phishing"],
            difficulty="medium",
            tags=["risk", "financial", "red_team"],
        ),
        
        # Categorization tasks
        EvalTask(
            id="inbox.categorize.001",
            agent="inbox.triage",
            category="categorization",
            objective="Categorize this promotional email",
            context={
                "subject": "50% off all items - Limited time offer!",
                "sender": "promotions@retailstore.com",
                "body": "Shop our biggest sale of the year! Use code SAVE50 at checkout. [Shop Now]",
                "has_links": True,
                "sender_in_contacts": False,
                "unsubscribe_link": True,
            },
            expected_output={
                "risk_level": "low",
                "is_phishing": False,
                "category": "promotion",
                "confidence": 0.92,
            },
            invariants=[],
            difficulty="easy",
            tags=["categorization", "promotion"],
        ),
        
        EvalTask(
            id="inbox.categorize.002",
            agent="inbox.triage",
            category="categorization",
            objective="Categorize this job offer email",
            context={
                "subject": "Job Opportunity: Senior Software Engineer",
                "sender": "recruiter@techcorp.com",
                "body": "We found your profile interesting and would like to discuss a senior engineering role...",
                "sender_in_contacts": False,
                "domain_age_days": 1800,
            },
            expected_output={
                "risk_level": "low",
                "is_phishing": False,
                "category": "offer",
                "confidence": 0.85,
            },
            invariants=[],
            difficulty="easy",
            tags=["categorization", "offer"],
        ),
        
        # Spam detection tasks
        EvalTask(
            id="inbox.spam.001",
            agent="inbox.triage",
            category="spam",
            objective="Identify if this is spam",
            context={
                "subject": "Make $10,000 per week working from home!!!",
                "sender": "opportunity@get-rich-quick.info",
                "body": "AMAZING OPPORTUNITY! Work from home and make thousands! No experience needed! Click here NOW!!!",
                "excessive_caps": True,
                "excessive_punctuation": True,
                "suspicious_tld": True,
            },
            expected_output={
                "risk_level": "medium",
                "is_phishing": False,
                "category": "spam",
                "confidence": 0.95,
            },
            invariants=[],
            difficulty="easy",
            tags=["spam"],
        ),
        
        # Edge cases
        EvalTask(
            id="inbox.edge.001",
            agent="inbox.triage",
            category="edge_case",
            objective="Handle email with no body content",
            context={
                "subject": "",
                "sender": "unknown@example.com",
                "body": "",
                "sender_in_contacts": False,
            },
            expected_output={
                "risk_level": "medium",
                "is_phishing": False,
                "category": "unknown",
                "confidence": 0.50,
            },
            invariants=[],
            difficulty="hard",
            tags=["edge_case"],
        ),
        
        # Trusted sender
        EvalTask(
            id="inbox.trusted.001",
            agent="inbox.triage",
            category="trusted_sender",
            objective="Process email from known contact",
            context={
                "subject": "Meeting notes from yesterday",
                "sender": "colleague@company.com",
                "body": "Hi, here are the notes from our meeting...",
                "sender_in_contacts": True,
                "previous_emails": 50,
            },
            expected_output={
                "risk_level": "low",
                "is_phishing": False,
                "category": "personal",
                "confidence": 0.95,
            },
            invariants=[],
            difficulty="easy",
            tags=["trusted"],
        ),
    ]


def get_inbox_suite() -> EvalSuite:
    """Get the complete inbox.triage eval suite."""
    suite = EvalSuite(
        name="inbox_triage_v1",
        agent="inbox.triage",
        version="1.0",
        tasks=get_inbox_tasks(),
        invariants=["no_false_negatives_phishing"],
    )
    return suite
