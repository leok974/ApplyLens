"""
Unit tests for email classification logic

Tests the rule-based email categorization system:
- Promotions detection (has_unsubscribe + deal keywords)
- Bills detection (invoice/payment keywords)
- Security detection (phishing/risk indicators)
- Applications detection (ATS domains)
- Risk scoring
"""
from app.logic.classify import (
    weak_category,
    calculate_risk_score,
    extract_profile_tags,
    classify_email,
)


class TestPromotionsDetection:
    """Test promotional email detection"""
    
    def test_promo_detection_with_unsubscribe_and_deal_words(self):
        """Emails with unsubscribe links and promotional keywords = promotions"""
        email = {
            "has_unsubscribe": True,
            "subject": "Limited time deal – 20% off",
            "body_text": "Click to save on your favorite items"
        }
        assert weak_category(email) == "promotions"
    
    def test_promo_with_various_deal_keywords(self):
        """Test different promotional keywords"""
        keywords = [
            "50% off sale",
            "Free shipping coupon",
            "Flash sale expires tonight",
            "Buy now discount",
            "Clearance offer",
        ]
        for keyword in keywords:
            email = {"has_unsubscribe": True, "subject": keyword, "body_text": ""}
            assert weak_category(email) == "promotions", f"Failed for keyword: {keyword}"
    
    def test_no_promo_without_unsubscribe_link(self):
        """Emails without unsubscribe link should not be categorized as promo"""
        email = {
            "has_unsubscribe": False,
            "subject": "20% off sale",  # Has promo keywords but no unsubscribe
            "body_text": ""
        }
        # Should fall back to personal (not promotions)
        assert weak_category(email) != "promotions"


class TestBillsDetection:
    """Test bill/invoice email detection"""
    
    def test_bill_detection_keywords(self):
        """Emails with invoice/payment keywords = bills"""
        email = {
            "subject": "Your monthly statement",
            "body_text": "Amount due by 10/15: $127.00"
        }
        assert weak_category(email) == "bills"
    
    def test_various_bill_keywords(self):
        """Test different billing keywords"""
        keywords = [
            "Invoice #12345",
            "Receipt for your purchase",
            "Payment due",
            "Balance overdue",
            "Subscription renewal",
            "Transaction charged",
        ]
        for keyword in keywords:
            email = {"subject": keyword, "body_text": ""}
            assert weak_category(email) == "bills", f"Failed for keyword: {keyword}"
    
    def test_bill_with_amount(self):
        """Bill with monetary amount"""
        email = {
            "subject": "Your bill is ready",
            "body_text": "Total due: $250.00",
            "money_amounts": [250.0]
        }
        assert weak_category(email) == "bills"


class TestSecurityDetection:
    """Test security alert detection"""
    
    def test_security_keywords_trigger_security_category(self):
        """Emails with security keywords = security"""
        email = {
            "subject": "Unusual activity detected on your account",
            "body_text": "Please verify your account immediately"
        }
        assert weak_category(email) == "security"
    
    def test_high_risk_score_triggers_security(self):
        """High risk score alone should trigger security category"""
        email = {
            "subject": "Normal subject",
            "body_text": "Normal body",
            "risk_score": 85
        }
        assert weak_category(email) == "security"
    
    def test_various_security_keywords(self):
        """Test different security alert keywords"""
        keywords = [
            "Password reset request",
            "Security alert: suspicious login",
            "Account locked",
            "Unauthorized access detected",
            "Confirm your identity",
        ]
        for keyword in keywords:
            email = {"subject": keyword, "body_text": ""}
            assert weak_category(email) == "security", f"Failed for keyword: {keyword}"


class TestApplicationsDetection:
    """Test job application email detection"""
    
    def test_ats_domain_triggers_applications(self):
        """Emails from ATS domains = applications"""
        email = {
            "sender_domain": "greenhouse.io",
            "subject": "Thank you for your application",
            "body_text": ""
        }
        assert weak_category(email) == "applications"
    
    def test_various_ats_domains(self):
        """Test different ATS provider domains"""
        ats_domains = [
            "greenhouse.io",
            "lever.co",
            "workday.com",
            "jobvite.com",
            "icims.com",
        ]
        for domain in ats_domains:
            email = {"sender_domain": domain, "subject": "Application update", "body_text": ""}
            assert weak_category(email) == "applications", f"Failed for domain: {domain}"
    
    def test_application_keywords(self):
        """Emails with application keywords = applications"""
        email = {
            "subject": "Interview scheduled for Software Engineer position",
            "body_text": "We received your application and would like to schedule an interview"
        }
        assert weak_category(email) == "applications"
    
    def test_avoid_promo_false_positive(self):
        """Don't classify promotional emails about jobs as applications"""
        email = {
            "has_unsubscribe": True,
            "subject": "Find your dream job opportunity - 50% off resume service",
            "body_text": "Limited time offer on career coaching"
        }
        # Should be promotions, not applications
        assert weak_category(email) == "promotions"


class TestRiskScoring:
    """Test risk score calculation"""
    
    def test_urgent_language_increases_risk(self):
        """Urgent language should increase risk score"""
        email = {
            "subject": "URGENT: Act now or your account will be suspended",
            "body_text": ""
        }
        score = calculate_risk_score(email)
        assert score > 0
    
    def test_suspicious_links_increase_risk(self):
        """Shortened URLs should increase risk score"""
        email = {
            "subject": "Click here",
            "body_text": "Visit bit.ly/abc123",
            "urls": ["bit.ly/abc123"]
        }
        score = calculate_risk_score(email)
        assert score > 0
    
    def test_phishing_indicators_high_risk(self):
        """Phishing indicators should result in high risk score"""
        email = {
            "subject": "Verify your PayPal credentials immediately",
            "body_text": "Update payment info or account will be suspended",
            "sender": "paypal@suspicious-domain.com"
        }
        score = calculate_risk_score(email)
        assert score >= 30  # Should have significant risk
    
    def test_excessive_links_increase_risk(self):
        """Too many links = spam indicator"""
        email = {
            "subject": "Check out these deals",
            "body_text": "",
            "urls": ["http://example.com/" + str(i) for i in range(15)]  # 15 links
        }
        score = calculate_risk_score(email)
        assert score > 0
    
    def test_clean_email_low_risk(self):
        """Normal email should have low/zero risk score"""
        email = {
            "subject": "Meeting tomorrow at 2pm",
            "body_text": "Looking forward to our discussion",
            "sender": "colleague@company.com",
            "urls": []
        }
        score = calculate_risk_score(email)
        assert score < 20  # Should be low risk


class TestProfileTags:
    """Test personalization tag extraction"""
    
    def test_interest_matching(self):
        """User interests should be extracted as tags"""
        email = {
            "subject": "New tech gadgets on sale",
            "body_text": "Check out the latest smartphones"
        }
        tags = extract_profile_tags(email, user_interests=["tech", "gadgets"])
        assert "interest:tech" in tags
        assert "interest:gadgets" in tags
    
    def test_urgency_tag(self):
        """Urgent emails should get urgency tag"""
        email = {
            "subject": "Expires today - last chance!",
            "body_text": ""
        }
        tags = extract_profile_tags(email)
        assert "urgent" in tags
    
    def test_high_value_tag(self):
        """Emails with high monetary value get value tags"""
        email = {
            "subject": "Invoice",
            "body_text": "",
            "money_amounts": [500.0]
        }
        tags = extract_profile_tags(email)
        assert "high-value" in tags
    
    def test_very_high_value_tag(self):
        """Very high value emails"""
        email = {
            "subject": "Payment",
            "body_text": "",
            "money_amounts": [2500.0]
        }
        tags = extract_profile_tags(email)
        assert "very-high-value" in tags


class TestFullClassification:
    """Test the complete classification pipeline"""
    
    def test_classify_promotional_email(self):
        """Full classification of a promotional email"""
        email = {
            "has_unsubscribe": True,
            "subject": "Amazon Flash Sale - 40% off",
            "body_text": "Limited time offer expires tonight",
            "sender": "deals@amazon.com",
            "sender_domain": "amazon.com",
        }
        result = classify_email(email)
        
        assert result["category"] == "promotions"
        assert result["confidence"] > 0.7
        assert isinstance(result["risk_score"], float)
    
    def test_classify_bill_email(self):
        """Full classification of a bill"""
        email = {
            "subject": "Your Verizon bill is ready",
            "body_text": "Amount due: $127.50 by Oct 15",
            "sender": "billing@verizon.com",
            "money_amounts": [127.50],
        }
        result = classify_email(email)
        
        assert result["category"] == "bills"
        assert result["risk_score"] < 20  # Bills shouldn't be risky
    
    def test_classify_security_alert(self):
        """Full classification of a security alert"""
        email = {
            "subject": "Suspicious login detected",
            "body_text": "We noticed unusual activity on your account",
            "sender": "security@company.com",
        }
        result = classify_email(email)
        
        assert result["category"] == "security"
    
    def test_classify_application_email(self):
        """Full classification of a job application response"""
        email = {
            "sender_domain": "greenhouse.io",
            "subject": "Application received for Senior Engineer",
            "body_text": "Thank you for applying. We will review your application.",
        }
        result = classify_email(email)
        
        assert result["category"] == "applications"
        assert result["confidence"] >= 0.9  # ATS domain = high confidence


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_email(self):
        """Should handle empty/minimal emails"""
        email = {}
        category = weak_category(email)
        assert category == "personal"  # Default category
    
    def test_missing_fields(self):
        """Should handle missing fields gracefully"""
        email = {"subject": "Test"}  # No body_text, sender, etc.
        result = classify_email(email)
        assert "category" in result
        assert "risk_score" in result
    
    def test_none_values(self):
        """Should handle None values"""
        email = {
            "subject": None,
            "body_text": None,
            "sender": None,
        }
        category = weak_category(email)
        assert isinstance(category, str)
    
    def test_unicode_content(self):
        """Should handle Unicode characters"""
        email = {
            "subject": "Große Rabatte! 🎉",
            "body_text": "Sparen Sie 30% auf alles",
            "has_unsubscribe": True,
        }
        category = weak_category(email)
        assert category == "promotions"
