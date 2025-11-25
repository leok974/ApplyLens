import base64
import datetime as dt
import logging
import os
import re
from typing import Dict, List, Optional

import bleach
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from elasticsearch import Elasticsearch, helpers
from google.auth.transport.requests import Request as GRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from .ingest.due_dates import (
    extract_due_dates,
    extract_earliest_due_date,
    extract_money_amounts,
)
from .ingest.gmail_metrics import compute_thread_reply_metrics
from .models import Application, AppStatus, Email, OAuthToken
from .security.analyzer import BlocklistProvider, EmailRiskAnalyzer
from .core.crypto import Crypto

ELASTICSEARCH_URL = os.getenv("ES_URL")
ES_INDEX = os.getenv("ELASTICSEARCH_INDEX", "gmail_emails")

# Initialize crypto for token decryption
crypto = Crypto()

# Initialize security analyzer (singleton)
_BLOCKLIST_PROVIDER = None
_SECURITY_ANALYZER = None


def get_security_analyzer() -> EmailRiskAnalyzer:
    """Get or create security analyzer instance (singleton pattern)."""
    global _BLOCKLIST_PROVIDER, _SECURITY_ANALYZER
    if _SECURITY_ANALYZER is None:
        blocklist_path = os.path.join(
            os.path.dirname(__file__), "security", "blocklists.json"
        )
        _BLOCKLIST_PROVIDER = BlocklistProvider(blocklist_path)
        _SECURITY_ANALYZER = EmailRiskAnalyzer(blocklists=_BLOCKLIST_PROVIDER)
    return _SECURITY_ANALYZER


LABEL_MAP_BOOSTS = {
    "interview": 3.0,
    "offer": 4.0,
    "rejection": 0.5,
}

ATS_SYNONYMS = ["lever", "workday", "smartrecruiters", "greenhouse"]

logger = logging.getLogger(__name__)


def _get_creds(db: Session, user_email: str) -> Credentials:
    tok: OAuthToken = (
        db.query(OAuthToken).filter_by(provider="google", user_email=user_email).first()
    )
    if not tok:
        raise ValueError("No OAuth token for user")

    # Log redacted client ID for debugging (helpful for spotting mismatches)
    # Show last 40 chars to see the full unique part (e.g., "...p72bhr.apps.googleusercontent.com")
    client_id_suffix = tok.client_id[-40:] if tok.client_id else "unknown"
    logger.info(
        f"Creating credentials for {user_email} with client_id suffix: ...{client_id_suffix}"
    )

    # Decrypt tokens (they are stored encrypted with AES-GCM)
    access_token_str = (
        crypto.dec(tok.access_token).decode() if tok.access_token else None
    )
    refresh_token_str = (
        crypto.dec(tok.refresh_token).decode() if tok.refresh_token else None
    )

    creds = Credentials(
        token=access_token_str,
        refresh_token=refresh_token_str,
        token_uri=tok.token_uri,
        client_id=tok.client_id,
        client_secret=tok.client_secret,
        scopes=tok.scopes.split(),
    )
    if not creds.valid and creds.refresh_token:
        try:
            logger.info(
                f"Refreshing token for {user_email} using client_id suffix: ...{client_id_suffix}"
            )
            creds.refresh(GRequest())
            # persist refreshed tokens (encrypt before storing)
            tok.access_token = crypto.enc(creds.token.encode())
            tok.expiry = creds.expiry
            db.commit()
            logger.info(f"Token refresh successful for {user_email}")
        except Exception as refresh_error:
            # If refresh fails (invalid_grant, etc.), delete the invalid token
            # and raise an error prompting user to re-authenticate
            from google.auth import exceptions as google_exceptions

            if isinstance(refresh_error, google_exceptions.RefreshError):
                logger.error(
                    f"Token refresh failed for {user_email}: {str(refresh_error)}"
                )
                # Delete invalid token from database
                db.delete(tok)
                db.commit()
                logger.info(f"Deleted invalid token for {user_email}")
                raise ValueError(
                    "OAuth token invalid or expired. Please re-authenticate at /api/auth/google/login"
                ) from refresh_error
            else:
                # Re-raise other exceptions
                raise
    return creds


def _strip_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    # light sanitize
    return bleach.clean(text, tags=[], strip=True)


def _parts_to_text(payload: dict) -> str:
    # Prefer text/plain
    def find_text_plain(p):
        if p.get("mimeType") == "text/plain" and p.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(p["body"]["data"]).decode(errors="replace")
        for sp in p.get("parts", []) or []:
            v = find_text_plain(sp)
            if v:  # noqa: E701
                return v
        return None

    def find_text_html(p):
        if p.get("mimeType") == "text/html" and p.get("body", {}).get("data"):
            html = base64.urlsafe_b64decode(p["body"]["data"]).decode(errors="replace")
            return _strip_html(html)
        for sp in p.get("parts", []) or []:
            v = find_text_html(sp)
            if v:  # noqa: E701
                return v
        return None

    text = find_text_plain(payload)
    if text:
        return text
    html_text = find_text_html(payload)
    if html_text:
        return html_text
    # Fallback: body.data at top
    body = payload.get("body", {}).get("data")
    if body:
        raw = base64.urlsafe_b64decode(body).decode(errors="replace")
        try:
            return _strip_html(raw)
        except Exception:
            return raw
    return ""


def _header(headers: List[Dict], name: str) -> Optional[str]:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value")
    return None


INTERVIEW_REGEX = re.compile(r"(?i)\binterview|phone screen|onsite\b")
REJECT_REGEX = re.compile(
    r"(?i)\b(not selected|unfortunately|regret to inform|rejection)\b"
)
OFFER_REGEX = re.compile(r"(?i)\boffer\b")
RECEIPT_REGEX = re.compile(r"(?i)\bapplication (received|submitted|confirmation)\b")
NEWSLETTER_HINT = re.compile(r"(?i)\bunsubscribe\b")

# NEW: Company and role extraction patterns
COMPANY_REGEX = re.compile(
    r"(?i)(?:from|at|with|@)\s+([A-Z][A-Za-z0-9\s&.,'-]{2,40}?)(?:\s+(?:team|recruiting|talent|hr|careers)|\s*<|\s*\(|$)"
)
ROLE_REGEX = re.compile(
    r"(?i)(?:for|position:|role:|as)\s+([A-Za-z0-9\s/+-]{3,60}?)(?:\s+at|\s+position|\s*-|\s*\||$)"
)


def extract_company(sender: str, body: str) -> Optional[str]:
    """Extract company name from sender or body text"""
    # Try sender domain first
    if sender and "@" in sender:
        domain = sender.split("@")[1].split(">")[0].strip()
        # Extract main domain (e.g., acme.com from careers.acme.com)
        parts = domain.split(".")
        if len(parts) >= 2:
            company = parts[-2].capitalize()
            if company.lower() not in ["gmail", "yahoo", "outlook", "hotmail", "mail"]:
                return company

    # Try body text pattern matching
    match = COMPANY_REGEX.search(body[:500] if body else "")
    if match:
        return match.group(1).strip()

    return None


def extract_role(subject: str) -> Optional[str]:
    """Extract job role from subject line"""
    if not subject:
        return None
    match = ROLE_REGEX.search(subject)
    if match:
        return match.group(1).strip()
    return None


def extract_source(
    headers: List[Dict], sender: str, subject: str, body: str
) -> Optional[str]:
    """Extract ATS/source from headers or content"""
    hnames = {h["name"].lower(): h["value"] for h in headers}
    for k in ["list-unsubscribe", "x-mailer", "x-sendgrid-sender"]:
        if k in hnames:
            return k
    for k in ATS_SYNONYMS:
        if (
            k in (sender or "").lower()
            or k in (subject or "").lower()
            or k in (body or "").lower()
        ):
            return k
    return None


def estimate_source_confidence(src: Optional[str]) -> float:
    """Estimate confidence of source detection"""
    if not src:
        return 0.0
    if src in ("lever", "workday", "smartrecruiters", "greenhouse"):
        return 0.9
    if src in ("list-unsubscribe", "x-mailer", "x-sendgrid-sender"):
        return 0.6
    return 0.4


def upsert_application_for_email(
    db: Session, email_obj: Email
) -> Optional[Application]:
    """
    Find or create an Application using (thread_id) or (company+role) as key.
    Links the email to the application.
    """
    if not (email_obj.company or email_obj.role or email_obj.thread_id):
        return None

    app = None
    # Try to find by thread_id first
    if email_obj.thread_id:
        app = db.query(Application).filter_by(thread_id=email_obj.thread_id).first()

    # Try to find by company+role
    if not app and email_obj.company:
        app = (
            db.query(Application)
            .filter(Application.company == email_obj.company)
            .filter(Application.role == email_obj.role)
            .order_by(Application.id.desc())
            .first()
        )

    # Create new application if not found
    if not app:
        app = Application(
            company=email_obj.company or "unknown",
            role=email_obj.role,
            source=email_obj.source,
            source_confidence=email_obj.source_confidence,
            thread_id=email_obj.thread_id,
            status=(
                AppStatus.interview
                if "interview" in (email_obj.label_heuristics or [])
                else AppStatus.applied
            ),
            last_email_id=email_obj.id,
        )
        db.add(app)
        db.flush()  # get app.id

    # Update thread_id if missing
    if not app.thread_id and email_obj.thread_id:
        app.thread_id = email_obj.thread_id

    # Update source if we have better confidence
    if email_obj.source and (
        not app.source or app.source_confidence < email_obj.source_confidence
    ):
        app.source = email_obj.source
        app.source_confidence = email_obj.source_confidence

    app.last_email_id = email_obj.id
    db.flush()

    # Link email -> application
    email_obj.application_id = app.id
    return app


def derive_labels(sender: str, subject: str, body: str) -> List[str]:
    """Heuristically derive email labels based on content"""
    labels = []
    subj = subject or ""
    text = " ".join([subj, body or ""])
    s = (sender or "").lower()

    if INTERVIEW_REGEX.search(text):
        labels.append("interview")
    if OFFER_REGEX.search(text):
        labels.append("offer")
    if REJECT_REGEX.search(text):
        labels.append("rejection")
    if RECEIPT_REGEX.search(text):
        labels.append("application_receipt")
    if (
        NEWSLETTER_HINT.search(text)
        or any(k in s for k in ["news", "newsletter", "noreply"])
        or "list-unsubscribe" in text.lower()
    ):
        labels.append("newsletter_ads")
    return list(set(labels))


def es_client():
    return Elasticsearch(ELASTICSEARCH_URL)


def ensure_es_index():
    """Ensure the Elasticsearch index exists with proper mappings"""
    es = es_client()
    if es.indices.exists(index=ES_INDEX):
        return
    es.indices.create(
        index=ES_INDEX,
        settings={
            "analysis": {
                "filter": {
                    "ats_synonyms": {
                        "type": "synonym",
                        "synonyms": [", ".join(ATS_SYNONYMS)],
                    }
                },
                "analyzer": {
                    "ats_analyzer": {
                        "tokenizer": "standard",
                        "filter": ["lowercase", "ats_synonyms"],
                    }
                },
            }
        },
        mappings={
            "properties": {
                "gmail_id": {"type": "keyword"},
                "thread_id": {"type": "keyword"},
                "subject": {"type": "text", "analyzer": "ats_analyzer"},
                "body_text": {"type": "text", "analyzer": "ats_analyzer"},
                "sender": {"type": "keyword"},
                "recipient": {"type": "keyword"},
                "received_at": {"type": "date"},
                "labels": {"type": "keyword"},
                "label_heuristics": {"type": "keyword"},
                "subject_suggest": {"type": "completion"},
                # NEW: quick hooks for filtering
                "company": {"type": "keyword"},
                "role": {"type": "text", "analyzer": "ats_analyzer"},
                "source": {"type": "keyword"},
                "source_confidence": {"type": "float"},
            }
        },
    )


def index_bulk_emails(docs: List[dict]):
    """Bulk index emails into Elasticsearch"""
    if not docs:  # noqa: E701
        return
    es = es_client()
    ensure_es_index()
    actions = []
    for d in docs:
        actions.append(
            {"_index": ES_INDEX, "_id": d["gmail_id"], "_op_type": "index", **d}
        )
    helpers.bulk(es, actions)


def gmail_backfill(db: Session, user_email: str, days: int = 60) -> int:
    """Backfill Gmail messages into database and Elasticsearch"""
    creds = _get_creds(db, user_email)
    svc = build("gmail", "v1", credentials=creds, cache_discovery=False)
    (dt.datetime.utcnow() - relativedelta(days=days)).strftime("%Y/%m/%d")
    q = f"newer_than:{days}d"
    # Or use after: yyyy/mm/dd -> f"after:{after_date}"

    # First, get all threads (not individual messages)
    threads = []
    page_token = None
    while True:
        resp = (
            svc.users()
            .threads()
            .list(userId="me", q=q, pageToken=page_token, maxResults=500)
            .execute()
        )
        threads.extend(resp.get("threads", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    es_docs = []
    inserted = 0

    # Process each thread
    for thread_meta in threads:
        thread_id = thread_meta["id"]

        # Get full thread with all messages
        thread = (
            svc.users()
            .threads()
            .get(userId="me", id=thread_id, format="full")
            .execute()
        )
        messages = thread.get("messages", [])

        # Compute reply metrics once per thread
        metrics = compute_thread_reply_metrics(messages, user_email.lower())

        # Process each message in the thread
        for meta in messages:
            payload = meta.get("payload", {})
            headers = payload.get("headers", [])
            subject = _header(headers, "Subject") or ""
            sender = _header(headers, "From") or ""
            recipient = _header(headers, "To") or ""
            internal_date = int(meta.get("internalDate", "0")) // 1000
            received_at = dt.datetime.utcfromtimestamp(internal_date)

            body_text = _parts_to_text(payload)
            label_heur = derive_labels(sender, subject, body_text)

            # NEW: Extract quick hooks
            company = extract_company(sender, body_text)
            role = extract_role(subject)
            source = extract_source(headers, sender, subject, body_text)
            source_conf = estimate_source_confidence(source)

            # NEW: Extract due dates and money amounts for bills
            combined_text = f"{subject} {body_text}"
            due_dates = extract_due_dates(combined_text, received_at)
            money_amounts = extract_money_amounts(combined_text)
            earliest_due = extract_earliest_due_date(combined_text, received_at)

            # Upsert in DB
            existing = db.query(Email).filter_by(gmail_id=meta["id"]).first()
            if not existing:
                existing = Email(gmail_id=meta["id"])
                db.add(existing)

            existing.thread_id = thread_id
            existing.subject = subject
            existing.body_text = body_text
            existing.sender = sender
            existing.recipient = recipient
            existing.received_at = received_at
            existing.labels = meta.get("labelIds", [])
            existing.label_heuristics = label_heur
            existing.raw = meta

            # NEW: Save quick hooks
            existing.company = company
            existing.role = role
            existing.source = source
            existing.source_confidence = source_conf

            # NEW: Save reply metrics (denormalized per message)
            if metrics["first_user_reply_at"]:
                existing.first_user_reply_at = dt.datetime.fromisoformat(
                    metrics["first_user_reply_at"]
                )
            if metrics["last_user_reply_at"]:
                existing.last_user_reply_at = dt.datetime.fromisoformat(
                    metrics["last_user_reply_at"]
                )
            existing.user_reply_count = metrics["user_reply_count"]

            # Security analysis: Run analyzer on each email
            try:
                analyzer = get_security_analyzer()
                headers_dict = {h["name"]: h["value"] for h in headers}

                # Parse from_name and from_email
                from_match = re.match(r'^"?([^"<]+)"?\s*<?([^>]+)>?$', sender)
                from_name = from_match.group(1).strip() if from_match else ""
                from_email = from_match.group(2).strip() if from_match else sender

                # Run security analysis
                risk_result = analyzer.analyze(
                    headers=headers_dict,
                    from_name=from_name,
                    from_email=from_email,
                    subject=subject,
                    body_text=body_text,
                    body_html=None,  # Could extract HTML from parts if needed
                    urls_visible_text_pairs=None,  # Auto-extract from body
                    attachments=[],  # Could parse from payload parts if needed
                    domain_first_seen_days_ago=None,  # Could compute from whois or tracking
                )

                # Store security analysis results
                existing.risk_score = float(risk_result.risk_score)
                existing.flags = [f.dict() for f in risk_result.flags]
                existing.quarantined = risk_result.quarantined

            except Exception as e:
                # Log error but don't fail the entire backfill
                print(f"Warning: Security analysis failed for {meta['id']}: {e}")
                existing.risk_score = 0.0
                existing.flags = []
                existing.quarantined = False

            db.flush()  # get email.id for linking
            upsert_application_for_email(db, existing)  # NEW: Link to application

            inserted += 1

            # Prepare ES doc
            es_docs.append(
                {
                    "gmail_id": existing.gmail_id,
                    "thread_id": existing.thread_id,
                    "subject": subject,
                    "body_text": body_text,
                    "sender": sender,
                    "recipient": recipient,
                    "received_at": received_at.isoformat(),
                    "labels": existing.labels or [],
                    "label_heuristics": label_heur,
                    "subject_suggest": {"input": [subject] if subject else []},
                    # NEW: Index quick hooks for filtering
                    "company": company,
                    "role": role,
                    "source": source,
                    "source_confidence": source_conf,
                    # NEW: Index reply metrics
                    "first_user_reply_at": metrics["first_user_reply_at"],
                    "last_user_reply_at": metrics["last_user_reply_at"],
                    "user_reply_count": metrics["user_reply_count"],
                    "replied": metrics["replied"],
                    # NEW: Index due dates and money amounts for bills
                    "dates": due_dates,
                    "money_amounts": money_amounts,
                    "expires_at": earliest_due,
                    # Security analysis fields (if analyzed)
                    "risk_score": (
                        int(existing.risk_score) if existing.risk_score else 0
                    ),
                    "quarantined": (
                        existing.quarantined
                        if hasattr(existing, "quarantined")
                        else False
                    ),
                    "flags": existing.flags if existing.flags else [],
                }
            )

    db.commit()
    index_bulk_emails(es_docs)
    return inserted


def gmail_backfill_with_progress(
    db: Session,
    user_email: str,
    days: int = 60,
    progress_callback: Optional[callable] = None,
) -> int:
    """
    Backfill Gmail messages with progress tracking.

    Args:
        db: Database session
        user_email: Gmail user email
        days: Number of days to backfill
        progress_callback: Optional callback function(processed: int, total: int)

    Returns:
        Number of emails inserted
    """
    creds = _get_creds(db, user_email)
    svc = build("gmail", "v1", credentials=creds, cache_discovery=False)
    q = f"newer_than:{days}d"

    # First, get all threads (not individual messages)
    threads = []
    page_token = None
    while True:
        try:
            resp = (
                svc.users()
                .threads()
                .list(userId="me", q=q, pageToken=page_token, maxResults=500)
                .execute()
            )
        except HttpError as e:
            if e.resp.status == 429:
                # Track rate limiting in Datadog (Phase 3C)
                from .observability.datadog import track_backfill_rate_limited

                track_backfill_rate_limited(user_id=user_email, quota_user="me")
                logger.warning(
                    f"Gmail API rate limited (429) during backfill for {user_email}"
                )
            raise  # Re-raise to let caller handle retry logic

        threads.extend(resp.get("threads", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    # Count total messages across all threads (estimate)
    total_messages = 0
    for thread_meta in threads:
        # Most threads have 1-5 messages, use snippet length as rough proxy
        # For now, just use thread count as approximation (will refine during processing)
        total_messages += 1

    # Report initial total
    if progress_callback:
        progress_callback(0, total_messages)

    es_docs = []
    inserted = 0
    processed_threads = 0

    # Process each thread
    for thread_meta in threads:
        thread_id = thread_meta["id"]

        # Get full thread with all messages
        try:
            thread = (
                svc.users()
                .threads()
                .get(userId="me", id=thread_id, format="full")
                .execute()
            )
        except HttpError as e:
            if e.resp.status == 429:
                # Track rate limiting in Datadog (Phase 3C)
                from .observability.datadog import track_backfill_rate_limited

                track_backfill_rate_limited(user_id=user_email, quota_user="me")
                logger.warning(
                    f"Gmail API rate limited (429) fetching thread {thread_id}"
                )
            raise  # Re-raise to let caller handle retry logic

        messages = thread.get("messages", [])

        # Update total now that we know actual message count
        if processed_threads == 0:
            # Estimate total based on first thread
            avg_msgs_per_thread = len(messages)
            total_messages = len(threads) * max(1, avg_msgs_per_thread)
            if progress_callback:
                progress_callback(0, total_messages)

        # Compute reply metrics once per thread
        metrics = compute_thread_reply_metrics(messages, user_email.lower())

        # Process each message in the thread
        for meta in messages:
            payload = meta.get("payload", {})
            headers = payload.get("headers", [])
            subject = _header(headers, "Subject") or ""
            sender = _header(headers, "From") or ""
            recipient = _header(headers, "To") or ""
            internal_date = int(meta.get("internalDate", "0")) // 1000
            received_at = dt.datetime.utcfromtimestamp(internal_date)

            # Parse body
            body_text = _parts_to_text(payload)
            label_heur = derive_labels(sender, subject, body_text)

            # Extract quick hooks
            company = extract_company(sender, body_text)
            role = extract_role(subject)
            source = extract_source(headers, sender, subject, body_text)
            source_conf = estimate_source_confidence(source)

            # Extract due dates and money amounts
            combined_text = f"{subject} {body_text}"
            due_dates = extract_due_dates(combined_text, received_at)
            money_amounts = extract_money_amounts(combined_text)
            earliest_due = extract_earliest_due_date(combined_text, received_at)

            # Upsert in DB
            existing = db.query(Email).filter_by(gmail_id=meta["id"]).first()
            if not existing:
                existing = Email(gmail_id=meta["id"])
                db.add(existing)

            existing.thread_id = thread_id
            existing.subject = subject
            existing.sender = sender
            existing.recipient = recipient
            existing.received_at = received_at
            existing.body_text = body_text
            existing.labels = (
                [_header(headers, "X-Gmail-Labels")]
                if _header(headers, "X-Gmail-Labels")
                else []
            )
            existing.label_heuristics = label_heur
            existing.company = company
            existing.role = role
            existing.source = source
            existing.source_confidence = source_conf
            existing.dates = due_dates
            existing.money_amounts = money_amounts
            existing.expires_at = earliest_due

            # Security analysis (safe fallback)
            try:
                from .security import analyze_email_security, SecurityAnalysisInput

                risk_result = analyze_email_security(
                    SecurityAnalysisInput(
                        from_address=sender,
                        subject=subject,
                        body=body_text,
                        urls_visible_text_pairs=None,
                        attachments=[],
                        domain_first_seen_days_ago=None,
                    )
                )
                existing.risk_score = float(risk_result.risk_score)
                existing.flags = [f.dict() for f in risk_result.flags]
                existing.quarantined = risk_result.quarantined
            except Exception as e:
                print(f"Warning: Security analysis failed for {meta['id']}: {e}")
                existing.risk_score = 0.0
                existing.flags = []
                existing.quarantined = False

            db.flush()
            upsert_application_for_email(db, existing)

            inserted += 1

            # Prepare ES doc
            es_docs.append(
                {
                    "gmail_id": existing.gmail_id,
                    "thread_id": existing.thread_id,
                    "subject": subject,
                    "body_text": body_text,
                    "sender": sender,
                    "recipient": recipient,
                    "received_at": received_at.isoformat(),
                    "labels": existing.labels or [],
                    "label_heuristics": label_heur,
                    "subject_suggest": {"input": [subject] if subject else []},
                    "company": company,
                    "role": role,
                    "source": source,
                    "source_confidence": source_conf,
                    "first_user_reply_at": metrics["first_user_reply_at"],
                    "last_user_reply_at": metrics["last_user_reply_at"],
                    "user_reply_count": metrics["user_reply_count"],
                    "replied": metrics["replied"],
                    "dates": due_dates,
                    "money_amounts": money_amounts,
                    "expires_at": earliest_due,
                    "risk_score": int(existing.risk_score)
                    if existing.risk_score
                    else 0,
                    "quarantined": existing.quarantined
                    if hasattr(existing, "quarantined")
                    else False,
                    "flags": existing.flags if existing.flags else [],
                }
            )

            # Report progress every 10 emails
            if inserted % 10 == 0 and progress_callback:
                progress_callback(inserted, total_messages)

        processed_threads += 1

        # Report progress after each thread
        if progress_callback:
            progress_callback(inserted, total_messages)

    db.commit()
    index_bulk_emails(es_docs)

    # Final progress update
    if progress_callback:
        progress_callback(inserted, inserted)

    return inserted
