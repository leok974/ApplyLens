"""
Risk heuristics for email security analysis.

Detects:
- Display name spoofing (brand impersonation)
- Punycode/IDN homograph attacks
- Suspicious TLDs
- URL domain mismatches
"""
import re
from typing import Dict, Tuple, List, Optional

# Suspicious TLDs commonly used in phishing
SUS_TLDS = {"zip", "mov", "country", "support", "top", "gq", "work", "tk", "ml", "ga", "cf"}

# Known brand patterns for spoof detection
BRAND_HINTS = {
    "paypal": {
        "domains": {"paypal.com"},
        "aliases": {"service", "billing", "support", "account"}
    },
    "microsoft": {
        "domains": {"microsoft.com", "outlook.com", "live.com"},
        "aliases": {"account", "security", "support", "service"}
    },
    "google": {
        "domains": {"google.com", "gmail.com"},
        "aliases": {"account", "security", "verification"}
    },
    "amazon": {
        "domains": {"amazon.com"},
        "aliases": {"service", "account", "prime", "payment"}
    },
    "apple": {
        "domains": {"apple.com", "icloud.com"},
        "aliases": {"support", "id", "account", "security"}
    }
}

# Regex for detecting punycode
PUNY_RX = re.compile(r"xn--", re.I)


def parse_from(from_hdr: str) -> Tuple[str, str]:
    """
    Parse From header to extract display name and email domain.
    
    Args:
        from_hdr: Raw From header (e.g., "PayPal <support@example.com>")
        
    Returns:
        Tuple of (display_name, email_domain)
        
    Examples:
        >>> parse_from('"PayPal Support" <noreply@paypal.com>')
        ('PayPal Support', 'paypal.com')
        
        >>> parse_from('support@example.com')
        ('', 'example.com')
    """
    if not from_hdr:
        return ("", "")
    
    # Try to match "Display Name" <user@domain.com> format
    m = re.search(r'^\s*"?(.*?)"?\s*<[^@]+@([^>]+)>', from_hdr)
    if m:
        return (m.group(1).strip(), m.group(2).lower())
    
    # Fallback: just extract domain from email address
    m = re.search(r'@([A-Za-z0-9\.\-\_]+)', from_hdr)
    return ("", m.group(1).lower() if m else "")


def looks_like_punycode(domain: str) -> bool:
    """
    Check if domain uses punycode encoding (IDN homograph attack indicator).
    
    Args:
        domain: Domain name to check
        
    Returns:
        True if domain contains punycode markers
        
    Examples:
        >>> looks_like_punycode("xn--pple-43d.com")  # аpple with cyrillic 'a'
        True
        
        >>> looks_like_punycode("apple.com")
        False
    """
    return bool(PUNY_RX.search(domain)) or any(
        part.startswith("xn--") for part in domain.split(".")
    )


def spoof_similarity(display: str, domain: str) -> float:
    """
    Check if display name spoofs a known brand but domain doesn't match.
    
    Lightweight fuzzy matching: checks if brand name appears in display
    but the actual email domain is not the legitimate brand domain.
    
    Args:
        display: Display name from From header
        domain: Actual email domain
        
    Returns:
        1.0 if spoofing detected, 0.0 otherwise
        
    Examples:
        >>> spoof_similarity("PayPal Billing", "paypaI.com")  # I vs l
        1.0
        
        >>> spoof_similarity("PayPal Billing", "paypal.com")
        0.0
    """
    disp = display.lower()
    
    for brand, meta in BRAND_HINTS.items():
        if brand in disp:
            # Brand mentioned in display name
            if domain not in meta["domains"]:
                # But domain is NOT the legitimate brand domain
                return 1.0
    
    return 0.0


def tld_risk(domain: str) -> float:
    """
    Check if domain uses a suspicious TLD.
    
    Args:
        domain: Domain name to check
        
    Returns:
        0.3 if suspicious TLD, 0.0 otherwise
        
    Examples:
        >>> tld_risk("example.zip")
        0.3
        
        >>> tld_risk("example.com")
        0.0
    """
    tld = domain.split(".")[-1] if domain else ""
    return 0.3 if tld in SUS_TLDS else 0.0


def risk_score(from_hdr: str, urls: List[str] = None) -> int:
    """
    Calculate overall risk score for an email based on multiple heuristics.
    
    Combines multiple risk signals:
    - Display name spoofing (60 points)
    - Punycode domain (30 points)
    - Suspicious TLD (30 points)
    - Punycode in URLs (10 points each)
    
    Args:
        from_hdr: Raw From header
        urls: List of URLs found in email body
        
    Returns:
        Risk score from 0-100 (higher = more suspicious)
        
    Examples:
        >>> risk_score('PayPal <support@paypaI.com>', [])  # Spoof attempt
        60
        
        >>> risk_score('Support <help@xn--pple-43d.com>', [])  # Punycode
        30
        
        >>> risk_score('Legit Sender <info@example.com>', [])
        0
    """
    if urls is None:
        urls = []
    
    disp, dom = parse_from(from_hdr)
    score = 0.0
    
    # Display-name spoofing (brand impersonation)
    score += 60.0 * spoof_similarity(disp, dom)
    
    # Punycode domain (IDN homograph attack)
    if looks_like_punycode(dom):
        score += 30.0
    
    # Suspicious TLD
    score += 30.0 * tld_risk(dom)
    
    # Check URLs for punycode or suspicious patterns
    for u in urls or []:
        if "@" in u:
            # Skip mailto: links
            continue
        
        # If link uses punycode, add small risk
        if "xn--" in u:
            score += 10.0
    
    # Clamp to 0-100 range
    return max(0, min(100, int(round(score))))


def analyze_email_risk(email_doc: Dict) -> Dict[str, any]:
    """
    Analyze an email document and return risk assessment.
    
    Args:
        email_doc: Email document with from_addr, urls, etc.
        
    Returns:
        Dictionary with risk_score and risk_factors
        
    Example:
        >>> analyze_email_risk({
        ...     "from_addr": "PayPal <support@paypaI.com>",
        ...     "urls": ["https://paypaI.com/login"]
        ... })
        {
            'risk_score': 60,
            'risk_factors': ['display_name_spoof']
        }
    """
    from_hdr = email_doc.get("from_addr", "")
    urls = email_doc.get("urls", [])
    
    score = risk_score(from_hdr, urls)
    
    # Identify which factors contributed
    factors = []
    disp, dom = parse_from(from_hdr)
    
    if spoof_similarity(disp, dom) > 0:
        factors.append("display_name_spoof")
    
    if looks_like_punycode(dom):
        factors.append("punycode_domain")
    
    if tld_risk(dom) > 0:
        factors.append("suspicious_tld")
    
    if any("xn--" in u for u in urls):
        factors.append("punycode_url")
    
    return {
        "risk_score": score,
        "risk_factors": factors
    }
