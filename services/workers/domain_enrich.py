#!/usr/bin/env python3
"""
Domain Enrichment Worker for Email Risk Detection v3.1

Fetches WHOIS data and DNS MX records for email sender domains,
populating the domain_enrich index to enable domain age detection.

Usage:
  python services/workers/domain_enrich.py --once
  python services/workers/domain_enrich.py --daemon --interval 3600

Environment Variables:
  ES_URL - Elasticsearch endpoint (default: http://localhost:9200)
  ES_INDEX - Email index to scan (default: gmail_emails)
  ES_ENRICH_INDEX - Enrichment index (default: domain_enrich)
  WHOIS_API_KEY - Optional API key for WHOIS service
"""

import argparse
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Environment configuration
ES_URL = os.environ.get("ES_URL", "http://localhost:9200")
ES_INDEX = os.environ.get("ES_INDEX", "gmail_emails")
ES_ENRICH_INDEX = os.environ.get("ES_ENRICH_INDEX", "domain_enrich")
WHOIS_API_KEY = os.environ.get("WHOIS_API_KEY", "")

# Constants
BATCH_SIZE = 100
CACHE_TTL_DAYS = 7  # Re-enrich domains older than 7 days


def ensure_enrichment_index():
    """Create enrichment index if it doesn't exist."""
    mapping = {
        "mappings": {
            "properties": {
                "domain": {"type": "keyword"},
                "created_at": {"type": "date"},
                "age_days": {"type": "integer"},
                "mx_host": {"type": "keyword"},
                "mx_exists": {"type": "boolean"},
                "registrar": {"type": "keyword"},
                "enriched_at": {"type": "date"},
                "risk_hint": {"type": "keyword"},
                "whois_error": {"type": "text"},
            }
        }
    }

    response = requests.put(f"{ES_URL}/{ES_ENRICH_INDEX}", json=mapping)
    if response.status_code == 200:
        logger.info(f"Created enrichment index: {ES_ENRICH_INDEX}")
    elif response.status_code == 400 and "already exists" in response.text.lower():
        logger.info(f"Enrichment index already exists: {ES_ENRICH_INDEX}")
    else:
        logger.error(
            f"Failed to create enrichment index: {response.status_code} {response.text}"
        )
        raise Exception("Could not ensure enrichment index")


def get_unenriched_domains() -> List[str]:
    """
    Query emails index for unique sender domains that haven't been
    enriched recently (or at all).
    """
    # Get unique domains from emails
    query = {
        "size": 0,
        "aggs": {"unique_domains": {"terms": {"field": "from_domain", "size": 1000}}},
    }

    response = requests.post(f"{ES_URL}/{ES_INDEX}/_search", json=query)
    response.raise_for_status()
    data = response.json()

    all_domains = [
        bucket["key"]
        for bucket in data.get("aggregations", {})
        .get("unique_domains", {})
        .get("buckets", [])
    ]

    if not all_domains:
        logger.info("No domains found in email index")
        return []

    # Filter out domains that were enriched recently
    cutoff = (datetime.utcnow() - timedelta(days=CACHE_TTL_DAYS)).isoformat()
    must_not_query = {
        "size": 10000,
        "query": {
            "bool": {
                "must": [{"range": {"enriched_at": {"gte": cutoff}}}],
                "must_not": [],
            }
        },
        "_source": ["domain"],
    }

    response = requests.post(f"{ES_URL}/{ES_ENRICH_INDEX}/_search", json=must_not_query)
    response.raise_for_status()
    enriched_data = response.json()

    recently_enriched = {
        hit["_source"]["domain"]
        for hit in enriched_data.get("hits", {}).get("hits", [])
    }

    unenriched = [d for d in all_domains if d not in recently_enriched]
    logger.info(
        f"Found {len(unenriched)} domains to enrich (out of {len(all_domains)} total)"
    )
    return unenriched


def get_mx_records(domain: str) -> Dict[str, any]:
    """
    Query DNS MX records for domain.
    Returns: {mx_exists: bool, mx_host: str or None}
    """
    try:
        import dns.resolver

        mx_records = dns.resolver.resolve(domain, "MX")
        if mx_records:
            primary_mx = str(mx_records[0].exchange).rstrip(".")
            return {"mx_exists": True, "mx_host": primary_mx}
        return {"mx_exists": False, "mx_host": None}
    except ImportError:
        logger.warning("dnspython not installed, skipping MX lookup")
        return {"mx_exists": None, "mx_host": None}
    except Exception as e:
        logger.debug(f"MX lookup failed for {domain}: {e}")
        return {"mx_exists": False, "mx_host": None}


def get_whois_data(domain: str) -> Dict[str, any]:
    """
    Fetch WHOIS data for domain.
    Returns: {created_at: ISO date, age_days: int, registrar: str}

    Uses python-whois library for local queries, or falls back to
    WHOIS API if WHOIS_API_KEY is set.
    """
    # Try local whois first (free, no rate limits)
    try:
        import whois

        w = whois.whois(domain)
        created_at = w.creation_date

        # Handle multiple creation dates (some TLDs return list)
        if isinstance(created_at, list):
            created_at = created_at[0]

        if created_at:
            age_days = (datetime.utcnow() - created_at).days
            return {
                "created_at": created_at.isoformat()
                if hasattr(created_at, "isoformat")
                else str(created_at),
                "age_days": age_days,
                "registrar": w.registrar or "Unknown",
                "whois_error": None,
            }
        else:
            return {
                "created_at": None,
                "age_days": None,
                "registrar": "Unknown",
                "whois_error": "No creation date in WHOIS",
            }
    except ImportError:
        logger.warning(
            "python-whois not installed, install with: pip install python-whois"
        )
        # Fall back to API if available
        if WHOIS_API_KEY:
            return get_whois_api(domain)
        return {
            "created_at": None,
            "age_days": None,
            "registrar": None,
            "whois_error": "WHOIS library not installed",
        }
    except Exception as e:
        logger.debug(f"WHOIS lookup failed for {domain}: {e}")
        # Fall back to API if available
        if WHOIS_API_KEY:
            return get_whois_api(domain)
        return {
            "created_at": None,
            "age_days": None,
            "registrar": None,
            "whois_error": str(e),
        }


def get_whois_api(domain: str) -> Dict[str, any]:
    """
    Fetch WHOIS data from external API (requires WHOIS_API_KEY).
    Example: WHOIS XML API, WhoisXMLAPI.com, etc.
    """
    # Placeholder for external API integration
    # Replace with actual API endpoint and logic
    logger.warning(f"WHOIS API not implemented for {domain}")
    return {
        "created_at": None,
        "age_days": None,
        "registrar": None,
        "whois_error": "API not configured",
    }


def enrich_domain(domain: str) -> Dict[str, any]:
    """
    Enrich a single domain with WHOIS and MX data.
    Returns enrichment document ready for indexing.
    """
    logger.info(f"Enriching domain: {domain}")

    # Get MX records
    mx_data = get_mx_records(domain)

    # Get WHOIS data
    whois_data = get_whois_data(domain)

    # Determine risk hint based on age
    risk_hint = "unknown"
    if whois_data.get("age_days") is not None:
        age = whois_data["age_days"]
        if age < 30:
            risk_hint = "very_young"  # High risk
        elif age < 90:
            risk_hint = "young"  # Medium risk
        elif age < 365:
            risk_hint = "recent"  # Low risk
        else:
            risk_hint = "established"  # Trusted

    enrichment = {
        "domain": domain,
        "enriched_at": datetime.utcnow().isoformat(),
        **mx_data,
        **whois_data,
        "risk_hint": risk_hint,
    }

    return enrichment


def bulk_index_enrichments(enrichments: List[Dict[str, any]]):
    """Bulk index enrichment documents to ES."""
    if not enrichments:
        return

    ndjson_lines = []
    for doc in enrichments:
        # Use domain as document ID for easy lookups
        ndjson_lines.append(
            json.dumps({"index": {"_index": ES_ENRICH_INDEX, "_id": doc["domain"]}})
        )
        ndjson_lines.append(json.dumps(doc))

    ndjson = "\n".join(ndjson_lines) + "\n"

    response = requests.post(
        f"{ES_URL}/_bulk",
        data=ndjson,
        headers={"Content-Type": "application/x-ndjson"},
    )
    response.raise_for_status()

    result = response.json()
    if result.get("errors"):
        logger.error(f"Bulk indexing errors: {json.dumps(result, indent=2)}")
    else:
        logger.info(f"Successfully indexed {len(enrichments)} domain enrichments")


def run_enrichment_cycle():
    """Run one enrichment cycle: fetch unenriched domains and enrich them."""
    logger.info("Starting enrichment cycle")

    # Ensure index exists
    ensure_enrichment_index()

    # Get domains to enrich
    domains = get_unenriched_domains()

    if not domains:
        logger.info("No domains to enrich")
        return

    # Process in batches
    enrichments = []
    for i, domain in enumerate(domains):
        try:
            enrichment = enrich_domain(domain)
            enrichments.append(enrichment)

            # Bulk index every BATCH_SIZE domains
            if len(enrichments) >= BATCH_SIZE:
                bulk_index_enrichments(enrichments)
                enrichments = []

            # Rate limit: 1 request per second to avoid WHOIS throttling
            if i < len(domains) - 1:
                time.sleep(1)

        except Exception as e:
            logger.error(f"Failed to enrich domain {domain}: {e}")

    # Index remaining enrichments
    if enrichments:
        bulk_index_enrichments(enrichments)

    logger.info("Enrichment cycle complete")


def run_daemon(interval: int):
    """Run enrichment in daemon mode (continuous loop)."""
    logger.info(f"Starting daemon mode (interval: {interval}s)")

    while True:
        try:
            run_enrichment_cycle()
        except Exception as e:
            logger.error(f"Enrichment cycle failed: {e}")

        logger.info(f"Sleeping for {interval} seconds...")
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(
        description="Domain Enrichment Worker for Email Risk Detection"
    )
    parser.add_argument(
        "--once", action="store_true", help="Run once and exit (default mode)"
    )
    parser.add_argument(
        "--daemon", action="store_true", help="Run continuously in daemon mode"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Interval between enrichment cycles in daemon mode (default: 3600s/1h)",
    )

    args = parser.parse_args()

    if args.daemon:
        run_daemon(args.interval)
    else:
        run_enrichment_cycle()


if __name__ == "__main__":
    main()
