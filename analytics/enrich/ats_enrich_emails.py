"""
ATS Enrichment Job for Phase 6

Enriches emails with ATS (Applicant Tracking System) data from warehouse.

Assumptions:
- Fivetran syncs Greenhouse, Lever, Workday data to warehouse
- Warehouse has materialized view: vw_applications_enriched
- View contains: application_id, system, company, email, stage, last_stage_change, interview_date

Process:
1. Fetch vw_applications_enriched (CSV/Parquet export or direct connector)
2. Compute ghosting_risk score based on stage staleness
3. Match emails by recipient email address
4. Bulk update Elasticsearch emails index with ats.* fields

Schedule: Run after each Fivetran sync (e.g., daily at 2am)
"""

import os
import sys
from datetime import datetime
import pandas as pd
from elasticsearch import Elasticsearch, helpers

# ES connection
ES_URL = os.getenv("ES_URL", "http://localhost:9200")
ES = Elasticsearch(ES_URL)

# Warehouse view path (CSV or Parquet export)
ATS_VIEW_PATH = os.getenv(
    "ATS_VIEW_PATH", "/data/warehouse/vw_applications_enriched.parquet"
)


def fetch_warehouse_view() -> pd.DataFrame:
    """
    Fetch applications data from warehouse.

    In production, replace this with:
    - Direct BigQuery/Snowflake/Redshift connector
    - Or scheduled export to S3/GCS bucket

    Expected columns:
    - application_id: str
    - system: str (greenhouse|lever|workday)
    - company: str
    - email: str (candidate email)
    - stage: str (Applied, Screening, Onsite, Offer, etc.)
    - last_stage_change: datetime
    - interview_date: datetime (nullable)
    """
    if not os.path.exists(ATS_VIEW_PATH):
        print(f"Warning: ATS view not found at {ATS_VIEW_PATH}")
        print("Using empty DataFrame (no enrichment)")
        return pd.DataFrame(
            columns=[
                "application_id",
                "system",
                "company",
                "email",
                "stage",
                "last_stage_change",
                "interview_date",
            ]
        )

    # Read from file
    if ATS_VIEW_PATH.endswith(".parquet"):
        return pd.read_parquet(ATS_VIEW_PATH)
    elif ATS_VIEW_PATH.endswith(".csv"):
        return pd.read_csv(ATS_VIEW_PATH)
    else:
        raise ValueError(f"Unsupported file format: {ATS_VIEW_PATH}")


def compute_ghosting_risk(row: pd.Series, now: pd.Timestamp) -> float:
    """
    Compute ghosting risk score based on application staleness.

    Rules:
    - No last_stage_change: 0.2 (unknown)
    - No interview scheduled and last change >14 days ago: 0.5 + 0.03 * days
    - Interview scheduled or recent activity: 0.1 (low risk)

    Returns:
        Float between 0.0 (no risk) and 1.0 (high risk)
    """
    lsc = row.get("last_stage_change")

    if pd.isna(lsc):
        return 0.2  # Unknown, low default risk

    # Parse datetime
    if isinstance(lsc, str):
        lsc = pd.to_datetime(lsc)

    days_since_change = (now - lsc).days

    # If no interview scheduled and stale, risk increases with time
    if pd.isna(row.get("interview_date")) and days_since_change >= 14:
        risk = 0.5 + (0.03 * days_since_change)
        return min(1.0, risk)  # Cap at 1.0

    # Recent activity or interview scheduled = low risk
    return 0.1


def enrich_emails(df: pd.DataFrame) -> int:
    """
    Bulk update emails in Elasticsearch with ATS data.

    Args:
        df: DataFrame with ATS data

    Returns:
        Number of emails enriched
    """
    if df.empty:
        print("No ATS data to enrich")
        return 0

    now = pd.Timestamp.utcnow()

    # Compute ghosting risk for all rows
    df["ghosting_risk"] = df.apply(lambda r: compute_ghosting_risk(r, now), axis=1)

    # Get unique candidate emails
    candidate_emails = df["email"].dropna().unique().tolist()

    if not candidate_emails:
        print("No candidate emails found in ATS data")
        return 0

    print(f"Searching for emails from {len(candidate_emails)} candidates...")

    # Fetch emails from these candidates (recipient or sender)
    # Use scroll API for large result sets
    query = {
        "bool": {
            "should": [
                {"terms": {"recipient": candidate_emails}},
                {"terms": {"sender": candidate_emails}},
            ],
            "minimum_should_match": 1,
        }
    }

    # Initial search with scroll
    page = ES.search(index="emails", body={"query": query, "size": 1000}, scroll="5m")

    scroll_id = page["_scroll_id"]
    total_hits = page["hits"]["total"]["value"]

    print(f"Found {total_hits} emails to enrich")

    # Build bulk update actions
    actions = []
    processed = 0

    while True:
        hits = page["hits"]["hits"]

        if not hits:
            break

        for hit in hits:
            email_doc = hit["_source"]
            email_id = hit["_id"]

            # Match with ATS data by email address
            candidate_email = email_doc.get("recipient") or email_doc.get("sender")

            if not candidate_email:
                continue

            # Find most recent application for this candidate
            cand_apps = df[df["email"] == candidate_email]

            if cand_apps.empty:
                continue

            # Use most recent application (by last_stage_change)
            latest = cand_apps.sort_values("last_stage_change", ascending=False).iloc[0]

            # Build ATS object
            ats_data = {
                "system": latest.get("system"),
                "application_id": latest.get("application_id"),
                "stage": latest.get("stage"),
                "last_stage_change": (
                    latest["last_stage_change"].isoformat()
                    if pd.notna(latest.get("last_stage_change"))
                    else None
                ),
                "interview_date": (
                    latest["interview_date"].isoformat()
                    if pd.notna(latest.get("interview_date"))
                    else None
                ),
                "company": latest.get("company"),
                "ghosting_risk": float(latest["ghosting_risk"]),
            }

            # Add update action
            actions.append(
                {
                    "_op_type": "update",
                    "_index": "emails",
                    "_id": email_id,
                    "doc": {"ats": ats_data},
                    "doc_as_upsert": True,
                }
            )

            processed += 1

        # Get next page
        page = ES.scroll(scroll_id=scroll_id, scroll="5m")

    # Clear scroll
    ES.clear_scroll(scroll_id=scroll_id)

    # Execute bulk update
    if actions:
        print(f"Enriching {len(actions)} emails with ATS data...")
        success, errors = helpers.bulk(ES, actions, raise_on_error=False)
        print(f"Successfully enriched {success} emails")

        if errors:
            print(f"Errors: {len(errors)}")
            for err in errors[:5]:  # Show first 5 errors
                print(f"  - {err}")

        return success
    else:
        print("No emails to enrich")
        return 0


def main():
    """Main enrichment job."""
    print("=" * 60)
    print("ATS Enrichment Job - Phase 6")
    print(f"Started: {datetime.utcnow().isoformat()}")
    print("=" * 60)

    # Fetch warehouse data
    print("\n1. Fetching warehouse view...")
    df = fetch_warehouse_view()
    print(f"   Loaded {len(df)} applications")

    if not df.empty:
        print(f"   Systems: {df['system'].value_counts().to_dict()}")
        print(f"   Stages: {df['stage'].value_counts().to_dict()}")

    # Enrich emails
    print("\n2. Enriching emails...")
    enriched_count = enrich_emails(df)

    # Summary
    print("\n" + "=" * 60)
    print(f"Completed: {datetime.utcnow().isoformat()}")
    print(f"Enriched {enriched_count} emails with ATS data")
    print("=" * 60)

    return enriched_count


if __name__ == "__main__":
    try:
        count = main()
        sys.exit(0 if count >= 0 else 1)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
