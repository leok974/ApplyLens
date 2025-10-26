# services/api/app/routers/applications.py
"""
Applications API - Internal/legacy endpoint for job applications

NOTE: This is now considered an internal/legacy API.
For the stable public contract that the UI should use, see /api/tracker instead.

The /tracker endpoint returns a simpler schema (company, role, stage, source, last_activity_at)
optimized for the UI, while this endpoint provides full pagination and filtering capabilities
for internal use cases or future advanced features.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..deps.user import get_current_user_email
from ..es import ES_ENABLED, INDEX, es

router = APIRouter(prefix="/applications", tags=["applications"])
logger = logging.getLogger(__name__)

# ---------- Pydantic Models ----------


class Application(BaseModel):
    id: str
    company: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    applied_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    source: Optional[str] = None


class ApplicationListResponse(BaseModel):
    items: List[Application]
    next_cursor: Optional[str] = None  # opaque token for next page
    sort: str
    order: str
    total: Optional[int] = None  # ES returns fast; BQ optional


# ---------- Constants ----------

ALLOWED_SORT = {"updated_at", "applied_at", "company", "status"}
DEFAULT_SORT = "updated_at"
DEFAULT_ORDER = "desc"

# ---------- Cursor Helpers ----------


def _encode_cursor(payload: Dict[str, Any]) -> str:
    """Encode cursor data to opaque base64 token"""
    return base64.urlsafe_b64encode(json.dumps(payload, default=str).encode()).decode()


def _decode_cursor(token: str) -> Dict[str, Any]:
    """Decode cursor token; raises HTTPException 400 if invalid"""
    try:
        return json.loads(base64.urlsafe_b64decode(token.encode()).decode())
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid cursor")


def _has_bigquery() -> bool:
    return bool(os.getenv("BQ_PROJECT")) and (
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("BQ_SA_JSON")
    )


def _has_es() -> bool:
    return bool(os.getenv("ELASTICSEARCH_URL") or os.getenv("ES_HOST"))


# ---------- BigQuery Implementation ----------


def _list_applications_bq(
    limit: int,
    status: Optional[str],
    sort: str,
    order: str,
    cursor: Optional[str],
) -> ApplicationListResponse:
    """Fetch applications from BigQuery with offset-based cursor pagination"""
    try:
        import tempfile

        from google.cloud import bigquery

        project = os.getenv("BQ_PROJECT")
        dataset = os.getenv("BQ_DATASET", "applylens")
        table = os.getenv("BQ_TABLE", "public_applications")

        # Inline SA support
        if os.getenv("BQ_SA_JSON") and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            tf = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
            tf.write(os.getenv("BQ_SA_JSON").encode("utf-8"))
            tf.flush()
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tf.name

        client = bigquery.Client(project=project)

        # OFFSET cursor
        offset = 0
        if cursor:
            data = _decode_cursor(cursor)
            offset = int(data.get("offset", 0))

        where = "WHERE TRUE"
        params = []
        if status:
            where += " AND status = @status"
            params.append(bigquery.ScalarQueryParameter("status", "STRING", status))

        # Map sort field
        sort_col = {
            "updated_at": "updated_at",
            "applied_at": "applied_at",
            "company": "company",
            "status": "status",
        }.get(sort, "updated_at")
        order_sql = "DESC" if order.lower() == "desc" else "ASC"

        # Total count (optional; skip if you want cheaper queries)
        count_sql = f"SELECT COUNT(1) AS c FROM `{project}.{dataset}.{table}` {where}"
        count_job = client.query(
            count_sql, bigquery.QueryJobConfig(query_parameters=params)
        )
        total = list(count_job.result())[0].c

        # Main query with pagination
        sql = f"""
        SELECT
          CAST(id AS STRING)         AS id,
          company, role, status,
          SAFE.TIMESTAMP(applied_at) AS applied_at,
          SAFE.TIMESTAMP(updated_at) AS updated_at,
          source
        FROM `{project}.{dataset}.{table}`
        {where}
        ORDER BY {sort_col} {order_sql} NULLS LAST, id ASC
        LIMIT @limit OFFSET @offset
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
                bigquery.ScalarQueryParameter("offset", "INT64", offset),
                *params,
            ]
        )
        rows = list(client.query(sql, job_config=job_config).result())

        items = [
            Application(
                id=str(getattr(r, "id", "")),
                company=getattr(r, "company", None),
                role=getattr(r, "role", None),
                status=getattr(r, "status", None),
                applied_at=getattr(r, "applied_at", None),
                updated_at=getattr(r, "updated_at", None),
                source=getattr(r, "source", None),
            )
            for r in rows
        ]

        # Calculate next cursor
        next_cursor = None
        if len(items) == limit and (offset + limit) < total:
            next_cursor = _encode_cursor({"offset": offset + limit})

        return ApplicationListResponse(
            items=items, next_cursor=next_cursor, sort=sort, order=order, total=total
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"BigQuery error: {e}")


# ---------- Elasticsearch Implementation ----------


def _list_applications_es(
    limit: int,
    status: Optional[str],
    sort: str,
    order: str,
    cursor: Optional[str],
) -> ApplicationListResponse:
    """Fetch applications from Elasticsearch with search_after cursor pagination"""
    try:
        from elasticsearch import Elasticsearch

        url = (
            os.getenv("ELASTICSEARCH_URL")
            or f"http://{os.getenv('ES_HOST','localhost')}:{os.getenv('ES_PORT','9200')}"
        )
        user = os.getenv("ES_USER")
        pwd = os.getenv("ES_PASS")
        index = os.getenv("ES_APPS_INDEX", "applications_v1")

        es = Elasticsearch(
            url, basic_auth=(user, pwd) if user and pwd else None, verify_certs=False
        )

        # Map sort to fields (keyword for text)
        sort_field = {
            "updated_at": "updated_at",
            "applied_at": "applied_at",
            "company": "company.keyword",
            "status": "status.keyword",
        }.get(sort, "updated_at")
        sort_dir = "desc" if order.lower() == "desc" else "asc"

        must = []
        if status:
            must.append({"term": {"status.keyword": status}})
        query = {"bool": {"must": must}} if must else {"match_all": {}}

        search_after = None
        if cursor:
            data = _decode_cursor(cursor)
            search_after = data.get("sa")

        body: Dict[str, Any] = {
            "size": limit,
            "query": query,
            "sort": [
                {
                    sort_field: {"order": sort_dir, "unmapped_type": "keyword"}
                },  # primary
                {"id.keyword": {"order": "asc"}},  # tiebreaker
            ],
            "_source": [
                "id",
                "company",
                "role",
                "status",
                "applied_at",
                "updated_at",
                "source",
            ],
        }
        if search_after:
            body["search_after"] = search_after

        res = es.search(index=index, **body)
        hits = res.get("hits", {}).get("hits", [])

        items: List[Application] = []
        for h in hits:
            s = h.get("_source", {})
            items.append(
                Application(
                    id=str(s.get("id") or h.get("_id")),
                    company=s.get("company"),
                    role=s.get("role"),
                    status=s.get("status"),
                    applied_at=s.get("applied_at"),
                    updated_at=s.get("updated_at"),
                    source=s.get("source"),
                )
            )

        next_cursor = None
        if len(hits) == limit:
            # Last hit's sort vector becomes next cursor
            next_cursor = _encode_cursor({"sa": hits[-1].get("sort")})

        # Total: can use track_total_hits=True (default) in modern ES
        total = res.get("hits", {}).get("total", {}).get("value")

        return ApplicationListResponse(
            items=items, next_cursor=next_cursor, sort=sort, order=order, total=total
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Elasticsearch error: {e}")


# ---------- Router Endpoint ----------


@router.get("", response_model=ApplicationListResponse)
def list_applications(
    limit: int = Query(25, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by status"),
    sort: str = Query(
        DEFAULT_SORT, description=f"One of: {', '.join(sorted(ALLOWED_SORT))}"
    ),
    order: str = Query(DEFAULT_ORDER, description="asc|desc"),
    cursor: Optional[str] = Query(None, description="Opaque cursor from previous page"),
):
    """
    List applications with cursor-based pagination and sorting.

    - **limit**: Max items per page (1-200, default 25)
    - **status**: Filter by status (applied, interview, offer, rejected, etc.)
    - **sort**: Sort field (updated_at, applied_at, company, status)
    - **order**: Sort order (asc or desc)
    - **cursor**: Opaque token from previous page's next_cursor

    Returns items with next_cursor for subsequent pages.
    """
    # Sanitize sort and order
    sort = sort if sort in ALLOWED_SORT else DEFAULT_SORT
    order = order.lower() if order.lower() in {"asc", "desc"} else DEFAULT_ORDER

    if _has_bigquery():
        return _list_applications_bq(limit, status, sort, order, cursor)
    if _has_es():
        return _list_applications_es(limit, status, sort, order, cursor)

    # Demo fallback (stable-ish order)
    demo = [
        Application(
            id="app_demo_2",
            company="Acme Corp",
            role="Full-Stack Developer",
            status="interview",
            applied_at=datetime(2025, 9, 12),
            updated_at=datetime(2025, 10, 1),
            source="Lever",
        ),
        Application(
            id="app_demo_1",
            company="OpenAI",
            role="ML Engineer",
            status="applied",
            applied_at=datetime(2025, 9, 5),
            updated_at=datetime(2025, 9, 20),
            source="Greenhouse",
        ),
        Application(
            id="app_demo_3",
            company="TechCorp",
            role="Senior Backend Engineer",
            status="offer",
            applied_at=datetime(2025, 9, 20),
            updated_at=datetime(2025, 10, 5),
            source="LinkedIn",
        ),
        Application(
            id="app_demo_4",
            company="StartupXYZ",
            role="DevOps Engineer",
            status="rejected",
            applied_at=datetime(2025, 8, 15),
            updated_at=datetime(2025, 9, 1),
            source="Indeed",
        ),
    ]

    # Apply status filter
    filtered = demo
    if status:
        filtered = [r for r in demo if r.status == status]

    # Simple sort for demo (just by updated_at desc for now)
    if sort == "updated_at":
        filtered = sorted(
            filtered,
            key=lambda x: x.updated_at or datetime.min,
            reverse=(order == "desc"),
        )
    elif sort == "applied_at":
        filtered = sorted(
            filtered,
            key=lambda x: x.applied_at or datetime.min,
            reverse=(order == "desc"),
        )
    elif sort == "company":
        filtered = sorted(
            filtered, key=lambda x: x.company or "", reverse=(order == "desc")
        )
    elif sort == "status":
        filtered = sorted(
            filtered, key=lambda x: x.status or "", reverse=(order == "desc")
        )

    # Apply limit
    items = filtered[:limit]

    return ApplicationListResponse(
        items=items,
        next_cursor=None,  # No pagination for demo
        sort=sort,
        order=order,
        total=len(filtered),
    )


# ---------- Tracker Models ----------


class TrackerRow(BaseModel):
    """Application row for the Tracker page"""

    company: str
    role: str
    source: str
    status: str
    last_update: str  # ISO datetime


# ---------- Tracker Endpoint ----------


@router.get("/tracker", response_model=List[TrackerRow])
def get_tracker_applications(user_email: str = Depends(get_current_user_email)):
    """
    Get application rows for the Tracker page derived from Gmail emails.

    This is a read-only endpoint that groups job-related emails by company
    and returns them as application rows for the Tracker UI.

    Safe for production - no mutations, graceful fallback to empty list.
    """
    try:
        # If Elasticsearch is disabled or not available, return empty list
        if not ES_ENABLED or es is None:
            logger.info("Tracker: ES disabled, returning empty list")
            return []

        # Query ES for job-related emails for this user
        # Look for emails with label_heuristics: offer, interview, rejection, application_receipt
        body = {
            "size": 100,  # Get up to 100 recent job emails
            "query": {
                "bool": {
                    "must": [
                        {"term": {"owner_email.keyword": user_email}},
                    ],
                    "should": [
                        {"term": {"label_heuristics": "offer"}},
                        {"term": {"label_heuristics": "interview"}},
                        {"term": {"label_heuristics": "rejection"}},
                        {"term": {"label_heuristics": "application_receipt"}},
                    ],
                    "minimum_should_match": 1,
                }
            },
            "sort": [{"received_at": {"order": "desc"}}],
            "_source": [
                "company",
                "role",
                "source",
                "label_heuristics",
                "received_at",
                "sender",
            ],
        }

        result = es.search(index=INDEX, body=body)
        hits = result.get("hits", {}).get("hits", [])

        # Group emails by company and build application rows
        # Use a dict to deduplicate by company
        apps_by_company = {}

        for hit in hits:
            src = hit.get("_source", {})
            company = src.get("company") or _extract_company_from_sender(
                src.get("sender", "")
            )
            role = src.get("role", "Unknown Role")
            source = src.get("source", "Gmail")
            labels = src.get("label_heuristics", [])
            received_at = src.get("received_at")

            # Skip if no company identified
            if not company:
                continue

            # Determine status from label_heuristics
            status = "Applied"
            if "offer" in labels:
                status = "Offer"
            elif "interview" in labels:
                status = "Interview Scheduled"
            elif "rejection" in labels:
                status = "Rejected"
            elif "application_receipt" in labels:
                status = "Applied"

            # Only keep the most recent email per company
            if company not in apps_by_company:
                apps_by_company[company] = TrackerRow(
                    company=company,
                    role=role,
                    source=source,
                    status=status,
                    last_update=received_at or datetime.utcnow().isoformat(),
                )
            else:
                # Update if this email is more recent or has a "higher" status
                existing = apps_by_company[company]
                status_priority = {
                    "Offer": 4,
                    "Interview Scheduled": 3,
                    "Rejected": 2,
                    "Applied": 1,
                }
                if status_priority.get(status, 0) > status_priority.get(
                    existing.status, 0
                ):
                    apps_by_company[company].status = status
                    apps_by_company[company].last_update = (
                        received_at or existing.last_update
                    )

        # Convert to list and sort by last_update descending
        rows = list(apps_by_company.values())
        rows.sort(key=lambda x: x.last_update, reverse=True)

        logger.info(f"Tracker: Found {len(rows)} applications for user {user_email}")
        return rows

    except Exception as e:
        # Fail gracefully - log error and return empty list
        logger.exception(f"Tracker endpoint failed for user {user_email}: {e}")
        return []


def _extract_company_from_sender(sender: str) -> str:
    """
    Extract company name from sender email address.
    E.g., "jobs@lever.co" -> "Lever"
    """
    if not sender:
        return ""

    # Extract domain from email
    if "@" in sender:
        domain = sender.split("@")[-1]
        # Remove TLD and convert to title case
        company = domain.split(".")[0]
        return company.title()

    return sender.title()
