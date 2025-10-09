"""
Email Parsing Heuristics Test Suite
Tests company, role, and source extraction from various email formats
"""

import sys
sys.path.append('/app')

from app.email_parsing import extract_company, extract_role, extract_source


# Test cases for company extraction
print("=" * 60)
print("COMPANY EXTRACTION TESTS")
print("=" * 60)

test_cases_company = [
    {
        "name": "Standard careers email",
        "sender": "Careers <careers@openai.com>",
        "body": "",
        "subject": "",
        "expected": "openai"
    },
    {
        "name": "Recruiting email with company mention",
        "sender": "recruiting@anthropic.com",
        "body": "Thank you for applying to the position at Anthropic",
        "subject": "",
        "expected": "Anthropic"
    },
    {
        "name": "Named sender",
        "sender": "Google Recruiting Team <jobs@example.com>",
        "body": "",
        "subject": "",
        "expected": "Google Recruiting Team"
    },
    {
        "name": "Domain only",
        "sender": "hr@stripe.com",
        "body": "",
        "subject": "",
        "expected": "stripe"
    }
]

for tc in test_cases_company:
    result = extract_company(tc["sender"], tc["body"], tc["subject"])
    status = "✅ PASS" if tc["expected"].lower() in result.lower() else "❌ FAIL"
    print(f"\n{status} {tc['name']}")
    print(f"   Input: {tc['sender'][:50]}")
    print(f"   Expected: {tc['expected']}")
    print(f"   Got: {result}")

# Test cases for role extraction
print("\n" + "=" * 60)
print("ROLE EXTRACTION TESTS")
print("=" * 60)

test_cases_role = [
    {
        "name": "Subject with 'for X role'",
        "subject": "Your Application for Research Engineer role",
        "body": "",
        "expected": "Research Engineer"
    },
    {
        "name": "Subject with 'Position:'",
        "subject": "Position: Senior AI Safety Researcher",
        "body": "",
        "expected": "Senior AI Safety Researcher"
    },
    {
        "name": "Subject with 'Job:'",
        "subject": "Job: Full Stack Developer",
        "body": "",
        "expected": "Full Stack Developer"
    },
    {
        "name": "Subject with 'Application for'",
        "subject": "Application for ML Engineer",
        "body": "",
        "expected": "ML Engineer"
    },
    {
        "name": "Body with role pattern",
        "subject": "",
        "body": "We are excited about your application for Data Scientist role at our company",
        "expected": "Data Scientist"
    }
]

for tc in test_cases_role:
    result = extract_role(tc["subject"], tc["body"])
    status = "✅ PASS" if tc["expected"].lower() in result.lower() else "❌ FAIL"
    print(f"\n{status} {tc['name']}")
    print(f"   Input: {tc['subject'] or tc['body'][:50]}")
    print(f"   Expected: {tc['expected']}")
    print(f"   Got: {result}")

# Test cases for source detection
print("\n" + "=" * 60)
print("SOURCE DETECTION TESTS")
print("=" * 60)

test_cases_source = [
    {
        "name": "Lever email",
        "sender": "jobs@lever.co",
        "subject": "Application via Lever",
        "body": "",
        "expected": "Lever"
    },
    {
        "name": "Greenhouse email",
        "sender": "recruiting@greenhouse.io",
        "subject": "Your Greenhouse application",
        "body": "",
        "expected": "Greenhouse"
    },
    {
        "name": "LinkedIn email",
        "sender": "jobs-listings@linkedin.com",
        "subject": "Job opportunity",
        "body": "This job was posted on LinkedIn",
        "expected": "LinkedIn"
    },
    {
        "name": "Workday email",
        "sender": "noreply@workday.com",
        "subject": "Application received",
        "body": "Your Workday application has been received",
        "expected": "Workday"
    },
    {
        "name": "Indeed email",
        "sender": "jobs@indeed.com",
        "subject": "Indeed job alert",
        "body": "",
        "expected": "Indeed"
    },
    {
        "name": "Generic email (fallback)",
        "sender": "hr@randomcompany.com",
        "subject": "Application received",
        "body": "Thank you for your application",
        "expected": "Email"
    }
]

for tc in test_cases_source:
    result = extract_source({}, tc["sender"], tc["subject"], tc["body"])
    status = "✅ PASS" if result == tc["expected"] else "❌ FAIL"
    print(f"\n{status} {tc['name']}")
    print(f"   Sender: {tc['sender']}")
    print(f"   Expected: {tc['expected']}")
    print(f"   Got: {result}")

print("\n" + "=" * 60)
print("INTEGRATED TEST - Complete Email Parsing")
print("=" * 60)

sample_email = {
    "sender": "Careers Team <careers@stripe.com>",
    "subject": "Your Application for Senior Backend Engineer role at Stripe",
    "body": "Thank you for applying to the Senior Backend Engineer position at Stripe via Greenhouse. We will review your application shortly.",
}

company = extract_company(sample_email["sender"], sample_email["body"], sample_email["subject"])
role = extract_role(sample_email["subject"], sample_email["body"])
source = extract_source({}, sample_email["sender"], sample_email["subject"], sample_email["body"])

print(f"\nSample Email:")
print(f"  From: {sample_email['sender']}")
print(f"  Subject: {sample_email['subject']}")
print(f"  Body: {sample_email['body'][:80]}...")
print(f"\nExtracted Data:")
print(f"  ✅ Company: {company}")
print(f"  ✅ Role: {role}")
print(f"  ✅ Source: {source}")

print("\n" + "=" * 60)
print("TEST SUITE COMPLETE")
print("=" * 60)
