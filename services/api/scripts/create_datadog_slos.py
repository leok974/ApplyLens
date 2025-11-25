#!/usr/bin/env python3
"""
Datadog SLO Creation Script for ApplyLens Observability Copilot

Creates Service Level Objectives (SLOs) for the hackathon demo:
1. LLM Classification Latency SLO (99% < 2000ms)
2. Ingest Freshness SLO (99% < 5min) - Optional

Prerequisites:
    - DD_API_KEY: Datadog API key
    - DD_APP_KEY: Datadog Application key
    - DD_SITE: Datadog site (e.g., us5.datadoghq.com)
"""

import os
import sys
import json
import requests


def validate_environment():
    """Validate required environment variables are set."""
    required_vars = ["DD_API_KEY", "DD_APP_KEY", "DD_SITE"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print(f"❌ Error: Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    print("✅ Environment variables validated")
    print(f"   DD_SITE: {os.getenv('DD_SITE')}")


def create_llm_latency_slo():
    """Create LLM Classification Latency SLO (99% < 2000ms)."""

    dd_site = os.getenv("DD_SITE")
    dd_api_key = os.getenv("DD_API_KEY")
    dd_app_key = os.getenv("DD_APP_KEY")

    url = f"https://api.{dd_site}/api/v1/slo"
    headers = {
        "DD-API-KEY": dd_api_key,
        "DD-APPLICATION-KEY": dd_app_key,
        "Content-Type": "application/json",
    }

    # SLO Payload
    payload = {
        "name": "ApplyLens – LLM Classify Latency SLO",
        "description": (
            "Ensures 99% of LLM classification calls complete within 2000ms. "
            "Monitors Gemini API performance and triggers alerts when latency degrades. "
            "Created for Google Cloud AI Partner Catalyst hackathon."
        ),
        "type": "metric",
        "tags": [
            "env:hackathon",
            "component:llm",
            "task:classify",
            "hackathon:google-cloud-ai",
        ],
        "thresholds": [
            {"timeframe": "7d", "target": 99.0, "warning": 99.5},
            {"timeframe": "30d", "target": 99.0, "warning": 99.5},
        ],
        "query": {
            "numerator": "sum:applylens.llm.latency_ms{env:hackathon,task_type:classify}.as_count() - sum:applylens.llm.latency_ms{env:hackathon,task_type:classify}.rollup(count).filter(>2000)",
            "denominator": "sum:applylens.llm.latency_ms{env:hackathon,task_type:classify}.as_count()",
        },
        "target_threshold": 99.0,
        "warning_threshold": 99.5,
        "timeframe": "7d",
    }

    print("\n📊 Creating SLO: LLM Classification Latency")
    print("   Target: 99% of requests < 2000ms")
    print("   Time windows: 7d, 30d")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        slo_id = result["data"][0]["id"]
        slo_url = f"https://{dd_site}/slo?slo_id={slo_id}"

        print("   ✅ Created successfully")
        print(f"   ID: {slo_id}")
        print(f"   URL: {slo_url}")

        return {"id": slo_id, "url": slo_url, "name": payload["name"]}

    except requests.exceptions.HTTPError as e:
        print(f"   ❌ HTTP Error: {e}")
        print(f"   Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def create_monitor_based_llm_slo():
    """
    Alternative: Create a simpler monitor-based SLO.
    This is easier to set up as it doesn't require complex metric queries.
    """

    dd_site = os.getenv("DD_SITE")
    dd_api_key = os.getenv("DD_API_KEY")
    dd_app_key = os.getenv("DD_APP_KEY")

    # First, create a monitor for latency threshold
    monitor_url = f"https://api.{dd_site}/api/v1/monitor"
    headers = {
        "DD-API-KEY": dd_api_key,
        "DD-APPLICATION-KEY": dd_app_key,
        "Content-Type": "application/json",
    }

    monitor_payload = {
        "name": "ApplyLens – LLM Latency Monitor (for SLO)",
        "type": "metric alert",
        "query": "avg(last_5m):p95:applylens.llm.latency_ms{env:hackathon,task_type:classify} > 2000",
        "message": "LLM latency exceeded SLO threshold",
        "tags": ["env:hackathon", "component:llm", "slo:latency"],
        "options": {
            "thresholds": {"critical": 2000, "warning": 1500},
            "notify_no_data": False,
            "notify_audit": False,
            "include_tags": True,
        },
    }

    print("\n📊 Creating Monitor-Based SLO")
    print("   Step 1: Creating latency monitor...")

    try:
        # Create monitor
        monitor_response = requests.post(
            monitor_url, headers=headers, json=monitor_payload, timeout=30
        )
        monitor_response.raise_for_status()
        monitor_result = monitor_response.json()
        monitor_id = monitor_result["id"]

        print(f"   ✅ Monitor created: {monitor_id}")

        # Create SLO based on monitor
        slo_url = f"https://api.{dd_site}/api/v1/slo"
        slo_payload = {
            "name": "ApplyLens – LLM Classify Latency SLO (Monitor-Based)",
            "description": (
                "Monitor-based SLO: 99% uptime target for LLM latency monitor. "
                "Alerts when p95 latency exceeds 2000ms. "
                "Created for Google Cloud AI Partner Catalyst hackathon."
            ),
            "type": "monitor",
            "tags": ["env:hackathon", "component:llm", "task:classify"],
            "thresholds": [
                {"timeframe": "7d", "target": 99.0, "warning": 99.5},
                {"timeframe": "30d", "target": 99.0},
            ],
            "monitor_ids": [monitor_id],
            "target_threshold": 99.0,
            "warning_threshold": 99.5,
            "timeframe": "7d",
        }

        print("   Step 2: Creating SLO...")

        slo_response = requests.post(
            slo_url, headers=headers, json=slo_payload, timeout=30
        )
        slo_response.raise_for_status()

        slo_result = slo_response.json()
        slo_id = slo_result["data"][0]["id"]
        slo_view_url = f"https://{dd_site}/slo?slo_id={slo_id}"

        print("   ✅ SLO created successfully")
        print(f"   SLO ID: {slo_id}")
        print(f"   Monitor ID: {monitor_id}")
        print(f"   URL: {slo_view_url}")

        return {
            "id": slo_id,
            "url": slo_view_url,
            "name": slo_payload["name"],
            "monitor_id": monitor_id,
        }

    except requests.exceptions.HTTPError as e:
        print(f"   ❌ HTTP Error: {e}")
        print(f"   Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def create_ingest_freshness_slo():
    """Create Ingest Freshness SLO (99% < 5min) - Optional."""

    dd_site = os.getenv("DD_SITE")
    dd_api_key = os.getenv("DD_API_KEY")
    dd_app_key = os.getenv("DD_APP_KEY")

    monitor_url = f"https://api.{dd_site}/api/v1/monitor"
    headers = {
        "DD-API-KEY": dd_api_key,
        "DD-APPLICATION-KEY": dd_app_key,
        "Content-Type": "application/json",
    }

    # Create monitor for ingest lag
    monitor_payload = {
        "name": "ApplyLens – Ingest Lag Monitor (for SLO)",
        "type": "metric alert",
        "query": "avg(last_5m):avg:applylens.ingest_lag_seconds{env:hackathon} > 300",
        "message": "Email ingest lag exceeded 5 minutes",
        "tags": ["env:hackathon", "component:ingest", "slo:freshness"],
        "options": {
            "thresholds": {"critical": 300, "warning": 180},
            "notify_no_data": False,
            "notify_audit": False,
            "include_tags": True,
        },
    }

    print("\n📊 Creating Ingest Freshness SLO (Optional)")
    print("   Step 1: Creating ingest lag monitor...")

    try:
        # Create monitor
        monitor_response = requests.post(
            monitor_url, headers=headers, json=monitor_payload, timeout=30
        )
        monitor_response.raise_for_status()
        monitor_result = monitor_response.json()
        monitor_id = monitor_result["id"]

        print(f"   ✅ Monitor created: {monitor_id}")

        # Create SLO
        slo_url = f"https://api.{dd_site}/api/v1/slo"
        slo_payload = {
            "name": "ApplyLens – Ingest Freshness SLO",
            "description": (
                "Ensures 99% of emails are ingested within 5 minutes of receipt. "
                "Monitors Gmail sync pipeline performance."
            ),
            "type": "monitor",
            "tags": ["env:hackathon", "component:ingest"],
            "thresholds": [{"timeframe": "7d", "target": 99.0, "warning": 99.5}],
            "monitor_ids": [monitor_id],
            "target_threshold": 99.0,
            "warning_threshold": 99.5,
            "timeframe": "7d",
        }

        print("   Step 2: Creating SLO...")

        slo_response = requests.post(
            slo_url, headers=headers, json=slo_payload, timeout=30
        )
        slo_response.raise_for_status()

        slo_result = slo_response.json()
        slo_id = slo_result["data"][0]["id"]
        slo_view_url = f"https://{dd_site}/slo?slo_id={slo_id}"

        print("   ✅ SLO created successfully")
        print(f"   SLO ID: {slo_id}")
        print(f"   URL: {slo_view_url}")

        return {
            "id": slo_id,
            "url": slo_view_url,
            "name": slo_payload["name"],
            "monitor_id": monitor_id,
        }

    except requests.exceptions.HTTPError as e:
        print(f"   ❌ HTTP Error: {e}")
        print(f"   Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def main():
    """Create all SLOs."""

    print("=" * 70)
    print("Datadog SLO Creator")
    print("ApplyLens Observability Copilot – Hackathon")
    print("=" * 70)

    validate_environment()

    slos_created = []

    # Create LLM Latency SLO (monitor-based, simpler approach)
    print("\n" + "=" * 70)
    print("Creating SLO #1: LLM Classification Latency")
    print("=" * 70)

    llm_slo = create_monitor_based_llm_slo()
    if llm_slo:
        slos_created.append(llm_slo)

    # Create Ingest Freshness SLO (optional)
    print("\n" + "=" * 70)
    print("Creating SLO #2: Ingest Freshness (Optional)")
    print("=" * 70)
    print("⚠️  Note: This SLO requires applylens.ingest_lag_seconds metric")
    print("   Skip this if you haven't implemented ingest metrics yet")

    response = input("\nCreate Ingest Freshness SLO? [y/N]: ").strip().lower()

    if response == "y":
        ingest_slo = create_ingest_freshness_slo()
        if ingest_slo:
            slos_created.append(ingest_slo)
    else:
        print("   ⏭️  Skipped Ingest Freshness SLO")

    # Summary
    print("\n" + "=" * 70)
    print("✅ SLO Creation Complete!")
    print("=" * 70)

    if slos_created:
        print(f"\n📊 Created {len(slos_created)} SLO(s):")
        for i, slo in enumerate(slos_created, 1):
            print(f"\n   {i}. {slo['name']}")
            print(f"      ID: {slo['id']}")
            print(f"      URL: {slo['url']}")
            if "monitor_id" in slo:
                print(f"      Monitor ID: {slo['monitor_id']}")

        # Save SLO info
        output = {
            "slos": slos_created,
            "created_at": "2025-11-25",
            "dashboard_id": "vap-jgg-r7t",
        }

        output_file = "/tmp/datadog_slos_info.json"
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)

        print(f"\n💾 SLO info saved to: {output_file}")

        print("\n📈 Next Steps:")
        print("   1. View SLOs in Datadog: https://us5.datadoghq.com/slo")
        print("   2. Add SLO widgets to dashboard (vap-jgg-r7t)")
        print(
            "   3. Configure incident monitors (see hackathon/DATADOG_SETUP.md Section 3)"
        )
        print("   4. Run traffic generator to populate SLO data")
    else:
        print("\n⚠️  No SLOs were created")

    print("=" * 70)


if __name__ == "__main__":
    # Check if running in interactive mode
    if sys.stdin.isatty():
        main()
    else:
        # Non-interactive mode: create only LLM SLO
        print("=" * 70)
        print("Datadog SLO Creator (Non-Interactive)")
        print("ApplyLens Observability Copilot – Hackathon")
        print("=" * 70)

        validate_environment()

        print("\n" + "=" * 70)
        print("Creating SLO: LLM Classification Latency")
        print("=" * 70)

        llm_slo = create_monitor_based_llm_slo()

        if llm_slo:
            print("\n" + "=" * 70)
            print("✅ SLO Created Successfully!")
            print("=" * 70)
            print(f"\n📊 {llm_slo['name']}")
            print(f"   ID: {llm_slo['id']}")
            print(f"   URL: {llm_slo['url']}")
            print(f"   Monitor ID: {llm_slo['monitor_id']}")

            output = {"slos": [llm_slo], "created_at": "2025-11-25"}

            with open("/tmp/datadog_slos_info.json", "w") as f:
                json.dump(output, f, indent=2)

            print("\n💾 SLO info saved to: /tmp/datadog_slos_info.json")
            print("=" * 70)
