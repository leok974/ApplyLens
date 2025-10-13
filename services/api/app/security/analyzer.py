# services/api/app/security/analyzer.py
from __future__ import annotations

import json
import re
import idna
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from pydantic import BaseModel


# ---------- Public result types ----------

class RiskFlag(BaseModel):
    signal: str          # e.g., "DMARC_FAIL"
    evidence: str        # human-readable explanation (kept concise)
    weight: int          # contribution to final score (can be negative)


class RiskAnalysis(BaseModel):
    risk_score: int
    flags: List[RiskFlag]
    quarantined: bool = False


# ---------- Weights & config ----------

@dataclass(frozen=True)
class RiskWeights:
    DMARC_FAIL: int = 25
    SPF_FAIL: int = 15
    DKIM_FAIL: int = 15
    DISPLAY_NAME_SPOOF: int = 15
    NEW_DOMAIN: int = 10
    PUNYCODE_OR_HOMOGLYPH: int = 10
    SUSPICIOUS_TLD: int = 10
    URL_HOST_MISMATCH: int = 10
    MALICIOUS_KEYWORD: int = 10
    EXECUTABLE_OR_HTML_ATTACHMENT: int = 20
    BLOCKLISTED_HASH_OR_HOST: int = 30
    TRUSTED_DOMAIN: int = -15  # subtracts risk
    # Aggregate / policy
    QUARANTINE_THRESHOLD: int = 70  # score ≥ threshold → quarantined


DEFAULT_SUSPICIOUS_TLDS: Set[str] = {
    "xyz", "ru", "top", "click", "link", "kim", "country", "gq", "work", "zip"
}

# Common executable/HTML-ish mimes that should be quarantined for review panel
QUARANTINE_MIME_PREFIXES: Tuple[str, ...] = (
    "application/x-msdownload", "application/x-msdos-program", "application/x-executable",
    "application/x-dosexec", "application/vnd.microsoft.portable-executable",
    "application/octet-stream",  # conservative: many malware droppers use this
    "text/html", "application/xhtml+xml",
)

# Conservative keyword patterns (lowercased body/subject)
MALICIOUS_KEYWORD_PATTERNS: Tuple[re.Pattern, ...] = tuple(
    re.compile(p) for p in [
        r"invoice\.exe", r"payment\s*verification\s*link",
        r"urgent\s*action\s*required", r"password\s*reset\s*attachment",
    ]
)

# Simple URL regex; good enough for first-pass scanning.
URL_REGEX = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)


# ---------- Blocklist provider ----------

class BlocklistProvider:
    """Simple JSON-backed blocklist provider. You can swap this for Redis/ES later."""
    def __init__(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Normalize to lowercase for host/hash
        self.block_hosts: Set[str] = {h.lower() for h in data.get("hosts", [])}
        self.block_hashes: Set[str] = {h.lower() for h in data.get("hashes", [])}
        self.trusted_domains: Set[str] = {d.lower() for d in data.get("trusted_domains", [])}

    def is_blocked_host(self, host: str) -> bool:
        return host.lower() in self.block_hosts

    def is_blocked_hash(self, file_hash: str) -> bool:
        return file_hash.lower() in self.block_hashes

    def is_trusted_domain(self, domain: str) -> bool:
        return domain.lower() in self.trusted_domains


# ---------- Analyzer ----------

@dataclass
class EmailRiskAnalyzer:
    weights: RiskWeights = field(default_factory=RiskWeights)
    suspicious_tlds: Set[str] = field(default_factory=lambda: set(DEFAULT_SUSPICIOUS_TLDS))
    blocklists: Optional[BlocklistProvider] = None

    # --- Public API ---

    def analyze(self, *, headers: Dict[str, str], from_name: str, from_email: str,
                subject: str, body_text: str, body_html: Optional[str],
                urls_visible_text_pairs: Optional[List[Tuple[str, str]]] = None,
                attachments: Optional[List[Dict[str, Any]]] = None,
                domain_first_seen_days_ago: Optional[int] = None) -> RiskAnalysis:
        """
        Minimal inputs expected from your pipeline:
        - headers: original email headers dict (must include 'Authentication-Results' if available)
        - from_name: display name portion (e.g., "PayPal Support")
        - from_email: RFC email address (e.g., "no-reply@security-paypal.com")
        - subject/body_text/body_html: raw content (lowercased internally when needed)
        - urls_visible_text_pairs: optional list of (visible_text, href_url) extracted upstream;
          if not provided and body_html exists, we'll regex-parse URLs only.
        - attachments: list of dicts: {"filename": str, "mime_type": str, "sha256": str|None}
        - domain_first_seen_days_ago: int indicating "newness" (None = unknown)
        """
        flags: List[RiskFlag] = []
        w = self.weights

        # 1) Authentication-Results (DMARC/SPF/DKIM)
        auth_header = headers.get("Authentication-Results", "") or headers.get("Authentication-results", "")
        if _auth_contains(auth_header, "dmarc", "fail", default_none=True):
            flags.append(RiskFlag(signal="DMARC_FAIL", evidence=f"auth={auth_header[:120]}", weight=w.DMARC_FAIL))
        if _auth_contains(auth_header, "spf", "fail", default_none=True):
            flags.append(RiskFlag(signal="SPF_FAIL", evidence=f"auth={auth_header[:120]}", weight=w.SPF_FAIL))
        if _auth_contains(auth_header, "dkim", "fail", default_none=True):
            flags.append(RiskFlag(signal="DKIM_FAIL", evidence=f"auth={auth_header[:120]}", weight=w.DKIM_FAIL))

        # 2) Display name spoof (Name ≠ domain)
        from_domain = _domain_of(from_email)
        if from_domain:
            if self.blocklists and self.blocklists.is_trusted_domain(from_domain):
                flags.append(RiskFlag(signal="TRUSTED_DOMAIN", evidence=f"domain={from_domain}", weight=w.TRUSTED_DOMAIN))

            if from_name and _looks_like_brand_mismatch(from_name, from_domain):
                flags.append(RiskFlag(signal="DISPLAY_NAME_SPOOF",
                                      evidence=f'name="{from_name}" domain="{from_domain}"',
                                      weight=w.DISPLAY_NAME_SPOOF))

            # 3) Punycode/homoglyphs
            if _is_punycode_or_homoglyph(from_domain):
                flags.append(RiskFlag(signal="PUNYCODE_OR_HOMOGLYPH",
                                      evidence=f"domain={from_domain}",
                                      weight=w.PUNYCODE_OR_HOMOGLYPH))

            # 4) Suspicious TLD
            tld = from_domain.rsplit(".", 1)[-1].lower() if "." in from_domain else ""
            if tld and tld in self.suspicious_tlds:
                flags.append(RiskFlag(signal="SUSPICIOUS_TLD", evidence=f"tld=.{tld}", weight=w.SUSPICIOUS_TLD))

        # 5) Newly-seen domains
        if domain_first_seen_days_ago is not None and domain_first_seen_days_ago <= 3:
            flags.append(RiskFlag(signal="NEW_DOMAIN",
                                  evidence=f"first_seen_days_ago={domain_first_seen_days_ago}",
                                  weight=w.NEW_DOMAIN))

        # 6) URLs: host ≠ visible text (if given) and blocklists
        url_pairs = urls_visible_text_pairs or []
        extracted_urls = set()
        if not url_pairs and body_html:
            # Fallback: extract raw URLs; we won't have visible text comparisons
            extracted_urls.update(URL_REGEX.findall(body_html))
        if body_text:
            extracted_urls.update(URL_REGEX.findall(body_text))

        for visible, href in url_pairs:
            host = _host_of(href)
            if not host:
                continue
            if visible and host and visible.strip().lower() not in {host.lower(), href.lower()}:
                flags.append(RiskFlag(signal="URL_HOST_MISMATCH",
                                      evidence=f'visible="{visible}" href="{href}"',
                                      weight=w.URL_HOST_MISMATCH))
            if self.blocklists and host and self.blocklists.is_blocked_host(host):
                flags.append(RiskFlag(signal="BLOCKLISTED_HASH_OR_HOST",
                                      evidence=f"host={host}",
                                      weight=w.BLOCKLISTED_HASH_OR_HOST))

        for url in extracted_urls:
            host = _host_of(url)
            if self.blocklists and host and self.blocklists.is_blocked_host(host):
                flags.append(RiskFlag(signal="BLOCKLISTED_HASH_OR_HOST",
                                      evidence=f"host={host}",
                                      weight=w.BLOCKLISTED_HASH_OR_HOST))

        # 7) Malicious keywords
        lower_blob = f"{subject or ''}\n{body_text or ''}".lower()
        for rx in MALICIOUS_KEYWORD_PATTERNS:
            if rx.search(lower_blob):
                flags.append(RiskFlag(signal="MALICIOUS_KEYWORD",
                                      evidence=f"pattern={rx.pattern}",
                                      weight=w.MALICIOUS_KEYWORD))

        # 8) Attachments: executables/HTML or blocklisted hashes
        for att in (attachments or []):
            mt = (att.get("mime_type") or "").lower()
            fn = att.get("filename") or "unknown"
            if any(mt.startswith(pfx) for pfx in QUARANTINE_MIME_PREFIXES):
                flags.append(RiskFlag(signal="EXECUTABLE_OR_HTML_ATTACHMENT",
                                      evidence=f"{fn} ({mt})",
                                      weight=w.EXECUTABLE_OR_HTML_ATTACHMENT))
            sha = (att.get("sha256") or "").lower()
            if sha and self.blocklists and self.blocklists.is_blocked_hash(sha):
                flags.append(RiskFlag(signal="BLOCKLISTED_HASH_OR_HOST",
                                      evidence=f"sha256={sha[:12]}…",
                                      weight=w.BLOCKLISTED_HASH_OR_HOST))

        # Final score (clamped)
        score = max(0, min(100, sum(f.weight for f in flags)))
        quarantined = score >= w.QUARANTINE_THRESHOLD

        return RiskAnalysis(risk_score=score, flags=flags, quarantined=quarantined)


# ---------- Helpers ----------

def _auth_contains(header: str, mechanism: str, needle: str, default_none: bool = False) -> bool:
    if not header:
        return False if not default_none else True  # treat missing as weak signal only when requested
    h = header.lower()
    return (mechanism.lower() in h) and (needle.lower() in h)

def _domain_of(email: str) -> str:
    if not email or "@" not in email:
        return ""
    return email.split("@", 1)[1].strip().lower()

_BRAND_TOKEN_RX = re.compile(r"[a-z0-9]+", re.IGNORECASE)

def _looks_like_brand_mismatch(display_name: str, domain: str) -> bool:
    """
    Heuristic: if display name contains a brand token not present in domain, flag it.
    Example: display_name="PayPal Support", domain="account-security.com" → True
    """
    name_tokens = set(_BRAND_TOKEN_RX.findall(display_name.lower()))
    dom_tokens = set(_BRAND_TOKEN_RX.findall(domain.lower()))
    if not name_tokens:
        return False
    # ignore very short tokens (e.g., 'llc', 'inc', 'co')
    name_tokens = {t for t in name_tokens if len(t) >= 3 and t not in {"inc", "llc", "co", "the"}}
    # mismatch if any brand-like token appears in name but not in domain
    return any((t not in dom_tokens) for t in name_tokens)

def _is_punycode_or_homoglyph(domain: str) -> bool:
    # IDNA punycode domains typically start with xn--
    if "xn--" in domain:
        return True
    # Try encode/decode; errors may indicate weird/unmappable characters
    try:
        _ = idna.encode(domain).decode("ascii")
        return False
    except Exception:
        return True

def _host_of(url: str) -> Optional[str]:
    try:
        # Avoid importing urllib just for speed; quick parse
        m = re.match(r"^https?://([^/:]+)", url.strip(), flags=re.IGNORECASE)
        return m.group(1).lower() if m else None
    except Exception:
        return None
