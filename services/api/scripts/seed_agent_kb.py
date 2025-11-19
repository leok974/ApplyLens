"""
Seed the agent_kb Elasticsearch index with knowledge base documents.

Run: python scripts/seed_agent_kb.py

Populates the knowledge base with:
- Phishing detection patterns
- Job search tips and best practices
- Email security guidance
- Application tracking advice
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.es import ES_URL, ES_ENABLED
from elasticsearch import Elasticsearch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Knowledge base documents
KB_DOCUMENTS = [
    {
        "id": "phishing-001",
        "title": "Common Phishing Red Flags",
        "content": """
        Phishing emails often exhibit these warning signs:
        - Urgent language ("act now", "verify immediately", "account suspended")
        - Generic greetings ("Dear Customer" instead of your name)
        - Suspicious sender domains (slight misspellings of legitimate companies)
        - Requests for sensitive information (passwords, SSN, credit cards)
        - Unexpected attachments or links
        - Poor grammar and spelling errors
        - Threatening consequences if you don't comply
        - Too-good-to-be-true offers or prizes

        Always verify sender authenticity before clicking links or providing information.
        """,
        "category": "security",
        "tags": ["phishing", "security", "fraud-detection"],
    },
    {
        "id": "phishing-002",
        "title": "Suspicious Domain Patterns",
        "content": """
        Watch for these domain red flags:
        - Homoglyph attacks (using similar-looking characters like "g00gle.com" with zeros)
        - Extra subdomains (e.g., "paypal-security.suspicious-domain.com")
        - Unusual TLDs (.tk, .ml, .ga often used by scammers)
        - Recently registered domains (less than 30 days old)
        - Domains with many hyphens or numbers
        - Missing HTTPS or invalid SSL certificates

        Legitimate companies use consistent, well-established domains.
        """,
        "category": "security",
        "tags": ["phishing", "domains", "security"],
    },
    {
        "id": "job-search-001",
        "title": "Job Application Best Practices",
        "content": """
        Optimize your job application tracking:
        - Keep a spreadsheet of all applications (company, position, date, status)
        - Set up email filters to organize recruiter responses
        - Follow up 1-2 weeks after applying if no response
        - Save job descriptions (they may be removed later)
        - Track interview stages and next steps
        - Set reminders for follow-up deadlines
        - Note recruiter names and contact information
        - Document salary discussions and negotiations

        Staying organized increases your success rate and prevents missed opportunities.
        """,
        "category": "job-search",
        "tags": ["applications", "organization", "tracking"],
    },
    {
        "id": "job-search-002",
        "title": "Identifying Legitimate Job Offers",
        "content": """
        Red flags in job offers:
        - Requests for payment or financial information upfront
        - Vague job descriptions or responsibilities
        - Promises of high pay for minimal work
        - Communication only through personal email (not company domain)
        - Immediate job offers without interview
        - Requests to use your personal bank account
        - Poor grammar and unprofessional language
        - No company website or verifiable business information

        Always research the company and verify legitimacy before proceeding.
        """,
        "category": "job-search",
        "tags": ["fraud", "job-offers", "security"],
    },
    {
        "id": "email-security-001",
        "title": "Email Security Hygiene",
        "content": """
        Protect your inbox:
        - Use unique passwords for each account
        - Enable two-factor authentication (2FA)
        - Regularly review connected apps and permissions
        - Be cautious with email forwarding rules
        - Don't click links in unsolicited emails
        - Verify sender identity for sensitive requests
        - Keep software and browsers updated
        - Use email filters to block spam and phishing
        - Report suspicious emails to your provider
        - Regularly clean up old emails and attachments

        Prevention is easier than recovery from a breach.
        """,
        "category": "security",
        "tags": ["email-security", "best-practices", "prevention"],
    },
    {
        "id": "recruiter-001",
        "title": "Understanding Recruiter Emails",
        "content": """
        Legitimate recruiter emails typically:
        - Come from company domain or verified recruiting platform
        - Include specific job details and requirements
        - Reference your resume or LinkedIn profile
        - Provide clear next steps and timelines
        - Include recruiter's full name and contact information
        - Link to official company career page
        - Have professional formatting and language

        Scam recruiter emails often:
        - Use generic personal email addresses
        - Make vague or unrealistic promises
        - Request personal financial information
        - Push for immediate decisions
        - Have grammatical errors or poor formatting
        """,
        "category": "job-search",
        "tags": ["recruiters", "communication", "verification"],
    },
    {
        "id": "application-tracking-001",
        "title": "Email Organization for Job Seekers",
        "content": """
        Effective email management during job search:
        - Create folders: "Applications Sent", "Responses", "Interviews", "Offers", "Rejections"
        - Use labels/tags to categorize by company or position type
        - Set up filters to auto-sort recruiter emails
        - Star or flag time-sensitive messages
        - Archive old applications after 60-90 days
        - Keep a "Follow-up" folder with action items
        - Save important attachments to cloud storage
        - Create templates for common responses

        Good organization helps you respond quickly and professionally.
        """,
        "category": "job-search",
        "tags": ["organization", "email-management", "productivity"],
    },
    {
        "id": "interview-001",
        "title": "Interview Follow-up Etiquette",
        "content": """
        After interviews:
        - Send thank-you email within 24 hours
        - Reference specific discussion points from interview
        - Reiterate your interest in the position
        - Include any additional information requested
        - Keep it concise (3-4 paragraphs)
        - Proofread carefully before sending
        - Follow up on timeline if no response after stated period
        - Maintain professional tone even if declined

        Prompt, thoughtful follow-up demonstrates professionalism and interest.
        """,
        "category": "job-search",
        "tags": ["interviews", "follow-up", "communication"],
    },
]


def seed_knowledge_base():
    """Seed the agent_kb index with documents."""
    # Create ES client (es global may be None if not initialized yet)
    es_client = Elasticsearch(ES_URL) if ES_ENABLED else None
    if not es_client:
        logger.error("Elasticsearch client not available")
        return False

    logger.info(f"Seeding {len(KB_DOCUMENTS)} documents to agent_kb index...")

    success_count = 0
    for doc in KB_DOCUMENTS:
        try:
            es_client.index(
                index="agent_kb",
                id=doc["id"],
                document=doc,
            )
            logger.info(f"✓ Indexed: {doc['id']} - {doc['title']}")
            success_count += 1
        except Exception as e:
            logger.error(f"✗ Failed to index {doc['id']}: {e}")

    logger.info(
        f"\n✓ Seeded {success_count}/{len(KB_DOCUMENTS)} documents successfully"
    )

    # Refresh index to make documents immediately searchable
    try:
        es_client.indices.refresh(index="agent_kb")
        logger.info("✓ Refreshed agent_kb index")
    except Exception as e:
        logger.warning(f"Failed to refresh index: {e}")

    return success_count == len(KB_DOCUMENTS)


def verify_seeding():
    """Verify that documents were indexed correctly."""
    es_client = Elasticsearch(ES_URL) if ES_ENABLED else None
    if not es_client:
        logger.error("Elasticsearch client not available")
        return

    logger.info("\nVerifying seeded documents...")

    try:
        result = es_client.count(index="agent_kb")
        count = result.get("count", 0)
        logger.info(f"✓ Total documents in agent_kb: {count}")

        # Test search
        search_result = es_client.search(
            index="agent_kb",
            body={
                "query": {"match": {"content": "phishing"}},
                "size": 3,
            },
        )
        hits = search_result.get("hits", {}).get("total", {}).get("value", 0)
        logger.info(f"✓ Search test ('phishing'): {hits} results")

    except Exception as e:
        logger.error(f"Verification failed: {e}")


def main():
    """Main seeding function."""
    logger.info("=" * 60)
    logger.info("Agent Knowledge Base Seeding")
    logger.info("=" * 60)

    success = seed_knowledge_base()
    if success:
        verify_seeding()
        logger.info("\n✓ Knowledge base seeding complete!")
        return 0
    else:
        logger.error("\n✗ Knowledge base seeding failed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
