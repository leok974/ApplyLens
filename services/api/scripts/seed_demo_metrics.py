#!/usr/bin/env python3
"""
Seed demo metrics data for testing and demo mode.

This script seeds the cache with demo divergence data controlled by environment variables.
Useful for testing HealthBadge states and Grafana dashboards without a real warehouse.

Environment Variables:
    DEMO_DIVERGENCE_STATE: One of "ok", "degraded", "paused" (default: "ok")
    DEMO_DIVERGENCE_PCT: Custom divergence percentage (default: auto from state)
    REDIS_URL: Redis connection string (default: redis://localhost:6379/0)

Usage:
    # Seed healthy state
    python seed_demo_metrics.py

    # Seed degraded state
    DEMO_DIVERGENCE_STATE=degraded python seed_demo_metrics.py

    # Seed paused state
    DEMO_DIVERGENCE_STATE=paused python seed_demo_metrics.py

    # Custom divergence percentage
    DEMO_DIVERGENCE_PCT=3.5 python seed_demo_metrics.py
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.cache import cache_set


def get_demo_state() -> str:
    """Get desired demo state from environment."""
    state = os.getenv("DEMO_DIVERGENCE_STATE", "ok").lower()
    if state not in ["ok", "degraded", "paused"]:
        print(f"Warning: Invalid state '{state}', using 'ok'")
        state = "ok"
    return state


def get_divergence_pct(state: str) -> float | None:
    """Get divergence percentage based on state or environment override."""
    custom_pct = os.getenv("DEMO_DIVERGENCE_PCT")
    
    if custom_pct:
        try:
            return float(custom_pct)
        except ValueError:
            print(f"Warning: Invalid DEMO_DIVERGENCE_PCT '{custom_pct}', using default")
    
    # Default percentages for each state
    defaults = {
        "ok": 0.5,      # < 2%
        "degraded": 3.5,  # 2-5%
        "paused": None    # > 5% or error (null)
    }
    
    return defaults.get(state, 0.0)


def seed_divergence_metrics():
    """Seed divergence metrics in cache."""
    state = get_demo_state()
    divergence_pct = get_divergence_pct(state)
    
    # Build payload
    if state == "ok":
        payload = {
            "es_count": 10050,
            "bq_count": 10000,
            "divergence_pct": divergence_pct if divergence_pct is not None else 0.5,
            "status": "ok",
            "message": f"Divergence: {divergence_pct or 0.5:.2f}% (OK)"
        }
    elif state == "degraded":
        payload = {
            "es_count": 10350,
            "bq_count": 10000,
            "divergence_pct": divergence_pct if divergence_pct is not None else 3.5,
            "status": "degraded",
            "message": f"Divergence: {divergence_pct or 3.5:.2f}% (DEGRADED)"
        }
    else:  # paused
        payload = {
            "es_count": 0,
            "bq_count": 0,
            "divergence_pct": divergence_pct,  # Will be None
            "status": "paused",
            "message": "System paused due to high divergence or error"
        }
    
    # Write to cache
    cache_key = "metrics:divergence_24h"
    cache_set(cache_key, payload, 300)  # 5 minute TTL for demo
    
    print(f"✓ Seeded divergence metrics:")
    print(f"  State: {state}")
    print(f"  Divergence: {divergence_pct}%")
    print(f"  Payload: {json.dumps(payload, indent=2)}")
    
    return payload


def seed_activity_daily():
    """Seed daily activity metrics."""
    from datetime import datetime, timedelta
    
    today = datetime.now().date()
    data = []
    
    for i in range(30):
        day = today - timedelta(days=i)
        # Add some variance to make it look realistic
        base_count = 50
        variance = (i % 10) * 10
        daily_count = base_count + variance
        
        data.append({
            "date": day.isoformat(),
            "message_count": daily_count
        })
    
    cache_key = "metrics:activity_daily"
    cache_set(cache_key, data, 300)
    
    print(f"✓ Seeded activity-daily metrics ({len(data)} days)")
    return data


def seed_top_senders():
    """Seed top senders metrics."""
    data = [
        {"sender": "noreply@github.com", "messages": 234},
        {"sender": "notifications@slack.com", "messages": 156},
        {"sender": "team@stripe.com", "messages": 89},
        {"sender": "updates@linkedin.com", "messages": 67},
        {"sender": "noreply@google.com", "messages": 45},
        {"sender": "jobs@lever.co", "messages": 34},
        {"sender": "no-reply@glassdoor.com", "messages": 28},
        {"sender": "alerts@datadog.com", "messages": 23},
        {"sender": "support@notion.so", "messages": 19},
        {"sender": "team@figma.com", "messages": 15},
    ]
    
    cache_key = "metrics:top_senders:10"
    cache_set(cache_key, data, 300)
    
    print(f"✓ Seeded top-senders-30d metrics ({len(data)} senders)")
    return data


def seed_categories():
    """Seed category metrics."""
    data = [
        {"category": "primary", "messages": 445},
        {"category": "promotions", "messages": 289},
        {"category": "social", "messages": 156},
        {"category": "updates", "messages": 123},
        {"category": "forums", "messages": 67},
    ]
    
    cache_key = "metrics:categories_30d"
    cache_set(cache_key, data, 300)
    
    print(f"✓ Seeded categories-30d metrics ({len(data)} categories)")
    return data


def main():
    """Seed all demo metrics."""
    print("=" * 60)
    print("Seeding Demo Metrics")
    print("=" * 60)
    
    try:
        seed_divergence_metrics()
        seed_activity_daily()
        seed_top_senders()
        seed_categories()
        
        print("=" * 60)
        print("✓ All demo metrics seeded successfully!")
        print("=" * 60)
        print()
        print("Test endpoints:")
        print("  curl http://localhost:8003/api/metrics/divergence-24h")
        print("  curl http://localhost:8003/api/metrics/activity-daily")
        print("  curl http://localhost:8003/api/metrics/top-senders-30d")
        print("  curl http://localhost:8003/api/metrics/categories-30d")
        print()
        
    except Exception as e:
        print(f"✗ Error seeding metrics: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
