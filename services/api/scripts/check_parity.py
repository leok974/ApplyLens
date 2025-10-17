#!/usr/bin/env python3
"""
DB-ES Parity Check Script

Compares specified fields between PostgreSQL database and Elasticsearch index
to detect data drift and inconsistencies.

Usage:
    # Check all automation fields on 1000 random emails
    python scripts/check_parity.py --fields risk_score,expires_at,category --sample 1000

    # Output to JSON file
    python scripts/check_parity.py --fields risk_score --sample 500 --output parity.json

    # Allow up to 5 mismatches before failing
    python scripts/check_parity.py --fields risk_score --sample 1000 --allow 5

Environment Variables:
    DATABASE_URL        - PostgreSQL connection string
    ELASTICSEARCH_URL   - Elasticsearch URL
    ES_INDEX            - Elasticsearch index name (default: gmail_emails_v2)
    SAMPLE              - Number of emails to sample (default: 1000)
    FIELDS              - Comma-separated fields to check
    OUTPUT              - Output file path (JSON format)
    ALLOW               - Maximum allowed mismatches before exit code 1
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Any
from datetime import datetime, date, timezone
import csv

# Add app to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db import get_db
from app.models import Email
from app.elasticsearch_client import get_es_client
from app.utils.schema_guard import require_min_migration
from sqlalchemy import select, func
import time

# Try to import metrics (optional)
try:
    from app.metrics import (
        parity_checks_total,
        parity_mismatches_total,
        parity_mismatch_ratio,
        parity_last_check_timestamp,
    )

    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False


# Tolerance for float comparisons
FLOAT_TOLERANCE = 0.001

# Field types for comparison logic
NUMERIC_FIELDS = {"risk_score", "source_confidence"}
DATE_FIELDS = {"expires_at", "received_at", "parsed_at"}
TEXT_FIELDS = {"category", "sender", "subject"}
JSON_FIELDS = {"features_json", "profile_tags"}


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Check parity between PostgreSQL and Elasticsearch"
    )
    parser.add_argument(
        "--fields",
        type=str,
        default=os.getenv("FIELDS", "risk_score,expires_at,category"),
        help="Comma-separated list of fields to check",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=int(os.getenv("SAMPLE", "1000")),
        help="Number of emails to sample",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=os.getenv("OUTPUT"),
        help="Output file path (JSON format)",
    )
    parser.add_argument("--csv", type=str, help="Output CSV file path for mismatches")
    parser.add_argument(
        "--allow",
        type=int,
        default=int(os.getenv("ALLOW", "0")),
        help="Maximum allowed mismatches before failing",
    )
    parser.add_argument(
        "--stratify", action="store_true", help="Stratify sample by category/date"
    )

    return parser.parse_args()


def compare_values(field: str, db_value: Any, es_value: Any) -> bool:
    """
    Compare two values based on field type.

    Returns True if values match within tolerance.
    """
    # Handle None values
    if db_value is None and es_value is None:
        return True
    if db_value is None or es_value is None:
        return False

    # Numeric fields (float comparison with tolerance)
    if field in NUMERIC_FIELDS:
        try:
            db_float = float(db_value)
            es_float = float(es_value)
            return abs(db_float - es_float) < FLOAT_TOLERANCE
        except (ValueError, TypeError):
            return False

    # Date fields (day-level equality)
    if field in DATE_FIELDS:
        try:
            # Parse dates and compare at day level
            if isinstance(db_value, (datetime, date)):
                db_date = (
                    db_value.date() if isinstance(db_value, datetime) else db_value
                )
            else:
                db_date = datetime.fromisoformat(
                    str(db_value).replace("Z", "+00:00")
                ).date()

            if isinstance(es_value, (datetime, date)):
                es_date = (
                    es_value.date() if isinstance(es_value, datetime) else es_value
                )
            else:
                es_date = datetime.fromisoformat(
                    str(es_value).replace("Z", "+00:00")
                ).date()

            return db_date == es_date
        except (ValueError, TypeError, AttributeError):
            return False

    # JSON fields (compare as dicts)
    if field in JSON_FIELDS:
        try:
            db_json = json.loads(db_value) if isinstance(db_value, str) else db_value
            es_json = json.loads(es_value) if isinstance(es_value, str) else es_value
            return db_json == es_json
        except (json.JSONDecodeError, TypeError):
            return False

    # Text fields (exact string match)
    return str(db_value).strip() == str(es_value).strip()


def fetch_db_sample(
    db, email_ids: List[int], fields: List[str]
) -> Dict[int, Dict[str, Any]]:
    """Fetch sample emails from database."""
    print(f"Fetching {len(email_ids)} emails from database...")

    # Build query to fetch specific fields
    query = select(Email).where(Email.id.in_(email_ids))

    results = {}
    for email in db.execute(query).scalars():
        email_data = {}
        for field in fields:
            value = getattr(email, field, None)
            # Convert datetime to ISO string for comparison
            if isinstance(value, datetime):
                value = value.isoformat()
            email_data[field] = value
        results[email.id] = email_data

    print(f"✓ Fetched {len(results)} emails from DB")
    return results


def fetch_es_sample(
    es_client, email_ids: List[int], fields: List[str], index: str
) -> Dict[int, Dict[str, Any]]:
    """Fetch sample emails from Elasticsearch."""
    print(f"Fetching {len(email_ids)} emails from Elasticsearch...")

    # Convert IDs to strings for ES
    str_ids = [str(id) for id in email_ids]

    try:
        response = es_client.mget(index=index, ids=str_ids, _source=fields)

        results = {}
        for doc in response["docs"]:
            if doc.get("found"):
                email_id = int(doc["_id"])
                source = doc["_source"]
                email_data = {field: source.get(field) for field in fields}
                results[email_id] = email_data

        print(f"✓ Fetched {len(results)} emails from ES")
        return results

    except Exception as e:
        print(f"✗ Error fetching from ES: {e}")
        sys.exit(1)


def sample_email_ids(db, sample_size: int, stratify: bool = False) -> List[int]:
    """Sample email IDs from database."""
    print(f"Sampling {sample_size} email IDs...")

    # Get total count
    total_count = db.execute(select(func.count(Email.id))).scalar()
    print(f"Total emails in DB: {total_count}")

    if sample_size >= total_count:
        # Use all emails
        print("Sample size >= total, using all emails")
        result = db.execute(select(Email.id)).scalars().all()
        return list(result)

    if stratify:
        # Stratified sampling (TODO: implement category/date-based stratification)
        print("Note: Stratified sampling not yet implemented, using random")

    # Random sampling via SQL
    result = (
        db.execute(select(Email.id).order_by(func.random()).limit(sample_size))
        .scalars()
        .all()
    )

    print(f"✓ Sampled {len(result)} email IDs")
    return list(result)


def generate_report(
    db_data: Dict[int, Dict[str, Any]],
    es_data: Dict[int, Dict[str, Any]],
    fields: List[str],
) -> Dict[str, Any]:
    """Generate parity report comparing DB and ES data."""
    print("\nComparing data...")

    # Track mismatches
    mismatches = []
    mismatches_by_field = {field: 0 for field in fields}

    # Compare each email
    all_ids = set(db_data.keys()) | set(es_data.keys())

    for email_id in all_ids:
        db_email = db_data.get(email_id, {})
        es_email = es_data.get(email_id, {})

        # Check if email exists in both
        if not db_email:
            mismatches.append(
                {"id": email_id, "issue": "missing_in_db", "db": None, "es": es_email}
            )
            continue

        if not es_email:
            mismatches.append(
                {"id": email_id, "issue": "missing_in_es", "db": db_email, "es": None}
            )
            continue

        # Compare fields
        email_mismatches = {}
        for field in fields:
            db_value = db_email.get(field)
            es_value = es_email.get(field)

            if not compare_values(field, db_value, es_value):
                email_mismatches[field] = {"db": db_value, "es": es_value}
                mismatches_by_field[field] += 1

        if email_mismatches:
            mismatches.append(
                {"id": email_id, "issue": "field_mismatch", "fields": email_mismatches}
            )

    # Build report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {"sample_size": len(all_ids), "fields": fields},
        "summary": {
            "total_checked": len(all_ids),
            "total_mismatches": len(mismatches),
            "mismatch_percentage": round(len(mismatches) / len(all_ids) * 100, 2)
            if all_ids
            else 0,
            "by_field": mismatches_by_field,
        },
        "mismatches": mismatches[:100],  # Limit to first 100 for report
    }

    print(f"\n{'='*60}")
    print("PARITY CHECK RESULTS")
    print(f"{'='*60}")
    print(f"Total checked: {report['summary']['total_checked']}")
    print(f"Mismatches: {report['summary']['total_mismatches']}")
    print(f"Mismatch rate: {report['summary']['mismatch_percentage']}%")
    print("\nMismatches by field:")
    for field, count in mismatches_by_field.items():
        print(f"  {field}: {count}")
    print(f"{'='*60}\n")

    return report


def save_report(report: Dict[str, Any], output_path: str):
    """Save report to JSON file."""
    print(f"Saving report to {output_path}...")
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    print("✓ Report saved")


def save_csv(report: Dict[str, Any], csv_path: str, fields: List[str]):
    """Save mismatches to CSV file."""
    print(f"Saving mismatches to {csv_path}...")

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)

        # Header
        header = ["id", "issue"]
        for field in fields:
            header.extend([f"{field}_db", f"{field}_es"])
        writer.writerow(header)

        # Rows
        for mismatch in report["mismatches"]:
            row = [mismatch["id"], mismatch["issue"]]

            if mismatch["issue"] == "field_mismatch":
                field_data = mismatch["fields"]
                for field in fields:
                    if field in field_data:
                        row.extend([field_data[field]["db"], field_data[field]["es"]])
                    else:
                        row.extend(["", ""])
            else:
                # Missing in DB or ES
                for field in fields:
                    row.extend(["", ""])

            writer.writerow(row)

    print("✓ CSV saved")


def main():
    """Main entry point."""
    args = parse_args()

    # Parse fields
    fields = [f.strip() for f in args.fields.split(",")]
    print(f"Checking parity for fields: {', '.join(fields)}")
    print(f"Sample size: {args.sample}")
    print(f"Allowed mismatches: {args.allow}\n")

    # Check schema version
    print("Checking database schema...")
    require_min_migration("0012_add_emails_features_json", "automation fields")
    print("✓ Schema version check passed\n")

    # Get clients
    db = next(get_db())
    es_client = get_es_client()
    es_index = os.getenv("ES_INDEX", "gmail_emails_v2")

    try:
        # Sample email IDs
        email_ids = sample_email_ids(db, args.sample, args.stratify)

        # Fetch data from both sources
        db_data = fetch_db_sample(db, email_ids, fields)
        es_data = fetch_es_sample(es_client, email_ids, fields, es_index)

        # Generate report
        report = generate_report(db_data, es_data, fields)

        # Update metrics
        if METRICS_AVAILABLE:
            try:
                parity_checks_total.inc()
                total_mismatches = report["summary"]["total_mismatches"]
                total_checked = report["summary"]["total_checked"]
                parity_mismatches_total.inc(total_mismatches)

                if total_checked > 0:
                    ratio = total_mismatches / total_checked
                    parity_mismatch_ratio.set(ratio)

                parity_last_check_timestamp.set(time.time())
            except Exception as e:
                print(f"Warning: Could not update metrics: {e}")

        # Save output files
        if args.output:
            save_report(report, args.output)

        if args.csv:
            save_csv(report, args.csv, fields)

        # Determine exit code
        total_mismatches = report["summary"]["total_mismatches"]

        if total_mismatches > args.allow:
            print(f"\n✗ FAILED: {total_mismatches} mismatches (allowed: {args.allow})")
            sys.exit(1)
        elif total_mismatches > 0:
            print(
                f"\n⚠ WARNING: {total_mismatches} mismatches (within tolerance: {args.allow})"
            )
            sys.exit(0)
        else:
            print("\n✓ SUCCESS: No mismatches detected!")
            sys.exit(0)

    finally:
        db.close()


if __name__ == "__main__":
    main()
