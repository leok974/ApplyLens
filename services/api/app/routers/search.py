from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import re
from ..es import es, ES_ENABLED, INDEX

# ---- Tunables for "demo pop"
LABEL_WEIGHTS = {
    "offer": 4.0,
    "interview": 3.0,
    "rejection": 0.5,
}
RECENCY = {
    "origin": "now",
    "scale": "7d",   # ~half-life feel
    "offset": "0d",
    "decay": 0.5,
}
SEARCH_FIELDS = ["subject^3", "body_text", "sender^1.5", "to"]
INDEX_ALIAS = INDEX  # Use configured index/alias

router = APIRouter(prefix="/search", tags=["search"])


class SearchHit(BaseModel):
    """Single search result."""
    id: Optional[int] = None
    gmail_id: Optional[str] = None
    thread_id: Optional[str] = None
    subject: Optional[str] = None
    sender: Optional[str] = None
    recipient: Optional[str] = None
    labels: List[str] = []
    label_heuristics: List[str] = []
    received_at: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    source: Optional[str] = None
    score: float
    snippet: Optional[str] = None
    highlight: dict = {}
    # Highlight fields for easy access
    subject_highlight: Optional[str] = None
    body_highlight: Optional[str] = None
    # Reply metrics
    first_user_reply_at: Optional[str] = None
    user_reply_count: int = 0
    replied: bool = False
    time_to_response_hours: Optional[float] = None
    # ML-powered fields (Phase 35)
    category: Optional[str] = None
    expires_at: Optional[str] = None
    event_start_at: Optional[str] = None
    event_end_at: Optional[str] = None
    interests: List[str] = []
    confidence: Optional[float] = None


class SearchResponse(BaseModel):
    """Search response with results and metadata."""
    total: int
    hits: List[SearchHit]
    info: Optional[str] = None


@router.get("/", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, description="Search query"),
    size: int = Query(25, ge=1, le=100, description="Number of results"),
    scale: str = Query("7d", description="Recency scale: 3d|7d|14d"),
    labels: Optional[List[str]] = Query(None, description="Filter by labels (repeatable)"),
    date_from: Optional[str] = Query(None, description="ISO date/time (e.g. 2025-10-01 or 2025-10-01T00:00:00Z)"),
    date_to: Optional[str] = Query(None, description="ISO date/time"),
    replied: Optional[bool] = Query(None, description="Filter replied threads: true|false"),
    sort: str = Query("relevance", description="relevance|received_desc|received_asc|ttr_asc|ttr_desc"),
    label_filter: Optional[str] = Query(None, description="Filter by label_heuristics: interview, offer, rejection, application_receipt, newsletter_ads"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    source: Optional[str] = Query(None, description="Filter by source (e.g., lever, workday)"),
    categories: Optional[List[str]] = Query(None, description="Filter by ML category (ats, bills, banks, events, promotions)"),
    hide_expired: bool = Query(True, description="Hide expired emails (expires_at < now) and past events (event_start_at < now)"),
    risk_min: Optional[int] = Query(None, ge=0, le=100, description="Minimum risk score (0-100)"),
    risk_max: Optional[int] = Query(None, ge=0, le=100, description="Maximum risk score (0-100)"),
    quarantined: Optional[bool] = Query(None, description="Filter by quarantine status: true|false")
):
    """
    Smart search with:
    - ATS synonym expansion (Lever, Workday, SmartRecruiters, Greenhouse)
    - Label boost scoring (offer^4, interview^3, rejection^0.5)
    - 7-day recency decay (Gaussian)
    - Field boosting (subject^3, sender^1.5)
    - Phrase + prefix matching
    """
    if not ES_ENABLED or es is None:
        return SearchResponse(total=0, hits=[], info="Elasticsearch disabled")
    
    # Validate / normalize scale (defensive)
    allowed = {"3d", "7d", "14d"}
    scale = scale if scale in allowed else "7d"
    recency = {**RECENCY, "scale": scale}
    
    # Build base query with phrase + prefix matching
    base_query = {
        "simple_query_string": {
            "query": f'"{q}" | {q}*',
            "fields": SEARCH_FIELDS,
            "default_operator": "and"
        }
    }
    
    # Build filter list
    filters = []
    
    # Add label filters
    if labels:
        filters.append({"terms": {"labels": labels}})
    if label_filter:
        filters.append({"term": {"label_heuristics": label_filter}})
    
    # Add date range filter
    range_q = {}
    if date_from:
        range_q["gte"] = date_from
    if date_to:
        range_q["lte"] = date_to
    if range_q:
        filters.append({"range": {"received_at": range_q}})
    
    # Add replied filter
    if replied is not None:
        filters.append({"term": {"replied": replied}})
    
    # Add company/source filters
    if company:
        filters.append({"term": {"company": company}})
    if source:
        filters.append({"term": {"source": source}})
    
    # Add ML category filter (Phase 35)
    if categories:
        filters.append({"terms": {"category": categories}})
    
    # Add risk score filter (Security)
    if risk_min is not None or risk_max is not None:
        risk_range = {}
        if risk_min is not None:
            risk_range["gte"] = risk_min
        if risk_max is not None:
            risk_range["lte"] = risk_max
        filters.append({"range": {"risk_score": risk_range}})
    
    # Add quarantine filter (Security)
    if quarantined is not None:
        filters.append({"term": {"quarantined": quarantined}})
    
    # Add hide expired filter (Phase 35)
    if hide_expired:
        # Exclude emails where expires_at is in the past
        filters.append({
            "bool": {
                "should": [
                    {"bool": {"must_not": {"exists": {"field": "expires_at"}}}},
                    {"range": {"expires_at": {"gte": "now"}}}
                ],
                "minimum_should_match": 1
            }
        })
        # Exclude emails where event_start_at is in the past
        filters.append({
            "bool": {
                "should": [
                    {"bool": {"must_not": {"exists": {"field": "event_start_at"}}}},
                    {"range": {"event_start_at": {"gte": "now"}}}
                ],
                "minimum_should_match": 1
            }
        })
    
    # --- Build sort ---
    es_sort = None
    if sort in ("received_desc", "received_asc"):
        es_sort = [{"received_at": {"order": "desc" if sort == "received_desc" else "asc"}}]
    elif sort in ("ttr_asc", "ttr_desc"):
        # Script computes hours between received_at and first_user_reply_at.
        # If missing reply, return a very large number for asc (push to bottom),
        # and a very small number for desc (bring to top) to make intent explicit.
        order = "asc" if sort == "ttr_asc" else "desc"
        script_source = """
          def r = doc.containsKey('received_at') && !doc['received_at'].empty ? doc['received_at'].value.toInstant().toEpochMilli() : null;
          def f = doc.containsKey('first_user_reply_at') && !doc['first_user_reply_at'].empty ? doc['first_user_reply_at'].value.toInstant().toEpochMilli() : null;
          if (r == null) return params.missing;
          if (f == null) return params.no_reply;
          if (f < r) return params.missing;
          return (f - r) / 3600000.0;
        """
        es_sort = [{
            "_script": {
                "type": "number",
                "order": order,
                "script": {
                    "source": script_source,
                    "params": {
                        "missing": 9.22e18,
                        "no_reply": (0 - 9.22e18) if sort == "ttr_desc" else 9.22e18
                    }
                }
            }
        }]
    else:
        sort = "relevance"
    
    # Wrap in bool query if filters present
    if filters:
        query = {
            "bool": {
                "must": [base_query],
                "filter": filters
            }
        }
    else:
        query = base_query
    
    # Build function_score query with label boosts + recency decay
    body = {
        "size": size,
        "query": {
            "function_score": {
                "query": query,
                "functions": [
                    # Label boosts (demo-ready scoring)
                    {"filter": {"terms": {"labels": ["offer"]}}, "weight": LABEL_WEIGHTS["offer"]},
                    {"filter": {"terms": {"labels": ["interview"]}}, "weight": LABEL_WEIGHTS["interview"]},
                    {"filter": {"terms": {"labels": ["rejection"]}}, "weight": LABEL_WEIGHTS["rejection"]},
                    # Also check label_heuristics
                    {"filter": {"term": {"label_heuristics": "offer"}}, "weight": LABEL_WEIGHTS["offer"]},
                    {"filter": {"term": {"label_heuristics": "interview"}}, "weight": LABEL_WEIGHTS["interview"]},
                    {"filter": {"term": {"label_heuristics": "rejection"}}, "weight": LABEL_WEIGHTS["rejection"]},
                    # 7-day recency decay (Gaussian half-life)
                    {"gauss": {"received_at": recency}}
                ],
                "score_mode": "multiply",
                "boost_mode": "multiply"
            }
        },
        **({"sort": es_sort} if es_sort else {}),
        "highlight": {
            "pre_tags": ["<mark>"],
            "post_tags": ["</mark>"],
            "fields": {
                "subject": {},
                "body_text": {"fragment_size": 150, "number_of_fragments": 3}
            }
        }
    }
    
    res = es.search(index=INDEX_ALIAS, body=body)
    
    hits = []
    for h in res["hits"]["hits"]:
        source = h["_source"]
        highlight = h.get("highlight", {})
        
        # Extract snippet from highlight or body_text
        snippet = None
        if "body_text" in highlight:
            snippet = " ... ".join(highlight["body_text"])[:300]
        elif source.get("body_text"):
            snippet = source["body_text"][:300] + "..."
        
        # Compute time_to_response_hours server-side
        time_to_response_hours = None
        if source.get("first_user_reply_at") and source.get("received_at"):
            try:
                first_reply_str = source["first_user_reply_at"].replace("Z", "+00:00")
                received_str = source["received_at"]
                # Add timezone if missing
                if "+" not in received_str and not received_str.endswith("Z"):
                    received_str += "+00:00"
                else:
                    received_str = received_str.replace("Z", "+00:00")
                    
                first_reply = datetime.fromisoformat(first_reply_str)
                received = datetime.fromisoformat(received_str)
                time_to_response_hours = (first_reply - received).total_seconds() / 3600.0
            except Exception:
                pass
        
        hits.append(SearchHit(
            id=source.get("id"),
            gmail_id=source.get("gmail_id"),
            thread_id=source.get("thread_id"),
            subject=source.get("subject"),
            sender=source.get("sender") or source.get("from_addr"),
            recipient=source.get("recipient"),
            labels=source.get("labels", []),
            label_heuristics=source.get("label_heuristics", []),
            received_at=source.get("received_at"),
            company=source.get("company"),
            role=source.get("role"),
            source=source.get("source"),
            score=h.get("_score") or 0.0,  # ES returns null for custom sorts
            snippet=snippet,
            highlight=highlight,
            # Highlight fields for easy access
            subject_highlight=highlight.get("subject", [None])[0] if "subject" in highlight else None,
            body_highlight=" ... ".join(highlight.get("body_text", [])) if "body_text" in highlight else None,
            # Reply metrics
            first_user_reply_at=source.get("first_user_reply_at"),
            user_reply_count=source.get("user_reply_count", 0),
            replied=source.get("replied", False),
            time_to_response_hours=time_to_response_hours,
            # ML fields (Phase 37)
            category=source.get("category"),
            expires_at=source.get("expires_at"),
            event_start_at=source.get("event_start_at"),
            event_end_at=source.get("event_end_at"),
            interests=source.get("interests", []),
            confidence=source.get("confidence"),
        ))
    
    return SearchResponse(
        total=res["hits"]["total"]["value"],
        hits=hits
    )


# ----- Explain endpoint -----

def _heuristic_reason(doc: dict) -> str:
    """Fallback reasoning if ES `reason` field not present."""
    subj = doc.get("subject", "")
    labels = doc.get("labels") or []
    label_heuristics = doc.get("label_heuristics") or []
    
    # Check Gmail categories first
    if "CATEGORY_PROMOTIONS" in labels:
        return "Gmail: Promotions category"
    if "CATEGORY_SOCIAL" in labels:
        return "Gmail: Social category"
    if "CATEGORY_UPDATES" in labels:
        return "Gmail: Updates category"
    if "CATEGORY_FORUMS" in labels:
        return "Gmail: Forums category"
    
    # Check label heuristics
    if "offer" in label_heuristics:
        return "Detected as job offer"
    if "interview" in label_heuristics:
        return "Detected as interview"
    if "rejection" in label_heuristics:
        return "Detected as rejection"
    if "newsletter_ads" in label_heuristics:
        return "Detected as newsletter/ad"
    if "application_receipt" in label_heuristics:
        return "Detected as application receipt"
    
    # Check unsubscribe header
    if doc.get("list_unsubscribe") or doc.get("has_unsubscribe"):
        return "Unsubscribe header present"
    
    # Check promo/newsletter flags
    if doc.get("is_promo"):
        return "Promo keywords detected"
    if doc.get("is_newsletter"):
        return "Newsletter pattern detected"
    
    # Keyword analysis
    if re.search(r"(deal|sale|promo|coupon|% off|discount)", subj, re.I):
        return "Promo keywords in subject"
    
    return "Uncategorized"


class ExplainResponse(BaseModel):
    """Explanation of why an email was categorized."""
    id: str
    reason: str
    evidence: dict


@router.get("/explain/{doc_id}", response_model=ExplainResponse)
def explain(doc_id: str):
    """
    Explain why an email was categorized/scored the way it was.
    
    Returns reasoning based on:
    - Gmail labels (CATEGORY_*)
    - Label heuristics (offer, interview, rejection, etc.)
    - List-Unsubscribe header presence
    - Promo/newsletter flags and keywords
    """
    if not ES_ENABLED or es is None:
        raise HTTPException(status_code=503, detail="Elasticsearch disabled")
    
    try:
        # Get document from ES
        result = es.get(index=INDEX, id=doc_id)
        doc = result["_source"]
    except Exception as e:
        if "404" in str(e) or "not_found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document: {str(e)}")
    
    # Use stored reason or generate heuristic
    reason = doc.get("reason") or _heuristic_reason(doc)
    
    # Collect evidence
    evidence = {
        "labels": doc.get("labels", []),
        "label_heuristics": doc.get("label_heuristics", []),
        "list_unsubscribe": bool(doc.get("list_unsubscribe") or doc.get("has_unsubscribe")),
        "is_promo": doc.get("is_promo", False),
        "is_newsletter": doc.get("is_newsletter", False),
        "keywords_hit": bool(re.search(
            r"(deal|sale|promo|coupon|% off|discount)",
            doc.get("subject", ""),
            re.I
        )),
        "sender": doc.get("sender") or doc.get("from_addr"),
        "sender_domain": doc.get("sender_domain"),
    }
    
    return ExplainResponse(
        id=doc_id,
        reason=reason,
        evidence=evidence
    )


# ----- Quick actions (dry-run) -----

class ActionRequest(BaseModel):
    """Request body for quick actions."""
    doc_id: str
    note: Optional[str] = None


class ActionResponse(BaseModel):
    """Response for quick actions."""
    status: str
    action: str
    doc_id: str
    message: Optional[str] = None


async def _record_audit(action: str, doc_id: str, note: Optional[str] = None):
    """Record action to audit log index (dry-run, no Gmail mutation)."""
    if not ES_ENABLED or es is None:
        return
    
    try:
        audit_index = "applylens_audit"
        payload = {
            "action": action,
            "doc_id": doc_id,
            "note": note,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        es.index(index=audit_index, body=payload)
    except Exception as e:
        # Log but don't fail the request
        print(f"Warning: Failed to record audit log: {e}")


@router.post("/actions/archive", response_model=ActionResponse)
async def archive(req: ActionRequest):
    """
    Archive email (dry-run mode).
    
    Records intent to applylens_audit index without mutating Gmail.
    In production, this would remove the INBOX label via Gmail API.
    """
    await _record_audit("archive", req.doc_id, req.note)
    return ActionResponse(
        status="accepted",
        action="archive",
        doc_id=req.doc_id,
        message="Dry-run: Archive action recorded to audit log"
    )


@router.post("/actions/mark_safe", response_model=ActionResponse)
async def mark_safe(req: ActionRequest):
    """
    Mark email as safe (dry-run mode).
    
    Records intent to applylens_audit index without mutating Gmail.
    In production, this would add a custom 'safe' label via Gmail API.
    """
    await _record_audit("mark_safe", req.doc_id, req.note)
    return ActionResponse(
        status="accepted",
        action="mark_safe",
        doc_id=req.doc_id,
        message="Dry-run: Mark safe action recorded to audit log"
    )


@router.post("/actions/mark_suspicious", response_model=ActionResponse)
async def mark_suspicious(req: ActionRequest):
    """
    Mark email as suspicious (dry-run mode).
    
    Records intent to applylens_audit index without mutating Gmail.
    In production, this would add a custom 'suspicious' label via Gmail API.
    """
    await _record_audit("mark_suspicious", req.doc_id, req.note)
    return ActionResponse(
        status="accepted",
        action="mark_suspicious",
        doc_id=req.doc_id,
        message="Dry-run: Mark suspicious action recorded to audit log"
    )


@router.post("/actions/unsubscribe_dryrun", response_model=ActionResponse)
async def unsubscribe_dryrun(req: ActionRequest):
    """
    Unsubscribe from email list (dry-run mode).
    
    Records intent to applylens_audit index without performing actual unsubscribe.
    In production, this would parse list_unsubscribe header and make HTTP request.
    """
    await _record_audit("unsubscribe_dryrun", req.doc_id, req.note)
    return ActionResponse(
        status="accepted",
        action="unsubscribe_dryrun",
        doc_id=req.doc_id,
        message="Dry-run: Unsubscribe action recorded to audit log"
    )
