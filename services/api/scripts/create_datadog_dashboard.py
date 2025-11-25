#!/usr/bin/env python3
"""
Datadog Dashboard Creation Script for ApplyLens Observability Copilot

Programmatically creates/updates the "ApplyLens Observability Copilot – Hackathon"
dashboard using the Datadog Dashboards API.

Prerequisites:
    - DD_API_KEY: Datadog API key
    - DD_APP_KEY: Datadog Application key
    - DD_SITE: Datadog site (e.g., us5.datadoghq.com)

Usage:
    export DD_API_KEY=your_api_key
    export DD_APP_KEY=your_app_key
    export DD_SITE=us5.datadoghq.com
    python scripts/create_datadog_dashboard.py

Or run inside container:
    docker cp services/api/scripts/create_datadog_dashboard.py applylens-api-prod:/tmp/
    docker exec \
      -e DD_API_KEY=$DD_API_KEY \
      -e DD_APP_KEY=$DD_APP_KEY \
      -e DD_SITE=us5.datadoghq.com \
      applylens-api-prod \
      python /tmp/create_datadog_dashboard.py
"""

import os
import sys
import requests


DASHBOARD_TITLE = "ApplyLens Observability Copilot – Hackathon"


def validate_environment():
    """Validate required environment variables are set."""
    required_vars = ["DD_API_KEY", "DD_APP_KEY", "DD_SITE"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print(f"❌ Error: Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    print("✅ Environment variables validated")
    print(f"   DD_SITE: {os.getenv('DD_SITE')}")


def find_existing_dashboard(title: str):
    """Find dashboard by title, return ID if exists."""
    dd_site = os.getenv("DD_SITE")
    dd_api_key = os.getenv("DD_API_KEY")
    dd_app_key = os.getenv("DD_APP_KEY")

    url = f"https://api.{dd_site}/api/v1/dashboard"
    headers = {
        "DD-API-KEY": dd_api_key,
        "DD-APPLICATION-KEY": dd_app_key,
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        dashboards = response.json().get("dashboards", [])

        for dash in dashboards:
            if dash.get("title") == title:
                return dash.get("id")

        return None
    except Exception as e:
        print(f"⚠️  Warning: Could not search for existing dashboard: {e}")
        return None


def build_dashboard_payload():
    """Build the dashboard configuration payload."""
    return {
        "title": DASHBOARD_TITLE,
        "description": (
            "Real-time observability for ApplyLens AI classification system. "
            "Monitors LLM performance, cost, security risk detection, and API health. "
            "Created for Google Cloud AI Partner Catalyst hackathon."
        ),
        "widgets": [
            # Section 1: LLM Performance
            {
                "definition": {
                    "type": "note",
                    "content": "# 📊 LLM Performance & Cost",
                    "background_color": "gray",
                    "font_size": "16",
                    "text_align": "left",
                    "show_tick": False,
                },
                "layout": {"x": 0, "y": 0, "width": 12, "height": 1},
            },
            {
                "definition": {
                    "title": "LLM Classification Latency (p50/p95/p99)",
                    "show_legend": True,
                    "legend_layout": "auto",
                    "legend_columns": ["avg", "max", "value"],
                    "type": "timeseries",
                    "requests": [
                        {
                            "q": "avg:applylens.llm.latency_ms{env:hackathon,task_type:classify}.rollup(avg, 60)",
                            "display_type": "line",
                            "style": {
                                "palette": "dog_classic",
                                "line_type": "solid",
                                "line_width": "normal",
                            },
                            "metadata": [
                                {
                                    "expression": "avg:applylens.llm.latency_ms{env:hackathon,task_type:classify}.rollup(avg, 60)",
                                    "alias_name": "p50",
                                }
                            ],
                        },
                        {
                            "q": "p95:applylens.llm.latency_ms{env:hackathon,task_type:classify}.rollup(max, 60)",
                            "display_type": "line",
                            "style": {
                                "palette": "warm",
                                "line_type": "solid",
                                "line_width": "normal",
                            },
                            "metadata": [
                                {
                                    "expression": "p95:applylens.llm.latency_ms{env:hackathon,task_type:classify}.rollup(max, 60)",
                                    "alias_name": "p95",
                                }
                            ],
                        },
                        {
                            "q": "p99:applylens.llm.latency_ms{env:hackathon,task_type:classify}.rollup(max, 60)",
                            "display_type": "line",
                            "style": {
                                "palette": "orange",
                                "line_type": "solid",
                                "line_width": "thick",
                            },
                            "metadata": [
                                {
                                    "expression": "p99:applylens.llm.latency_ms{env:hackathon,task_type:classify}.rollup(max, 60)",
                                    "alias_name": "p99",
                                }
                            ],
                        },
                    ],
                },
                "layout": {"x": 0, "y": 1, "width": 6, "height": 3},
            },
            {
                "definition": {
                    "title": "LLM Error Rate (%)",
                    "show_legend": False,
                    "type": "timeseries",
                    "requests": [
                        {
                            "q": "(sum:applylens.llm.error_total{env:hackathon}.as_rate() / sum:applylens.llm.requests{env:hackathon}.as_rate()) * 100",
                            "display_type": "line",
                            "style": {
                                "palette": "warm",
                                "line_type": "solid",
                                "line_width": "normal",
                            },
                        }
                    ],
                },
                "layout": {"x": 6, "y": 1, "width": 6, "height": 3},
            },
            {
                "definition": {
                    "title": "Tokens / 5min",
                    "type": "query_value",
                    "requests": [
                        {
                            "q": "sum:applylens.llm.tokens_used{env:hackathon}.rollup(sum, 300)",
                            "aggregator": "last",
                        }
                    ],
                    "autoscale": True,
                    "precision": 0,
                },
                "layout": {"x": 0, "y": 4, "width": 3, "height": 2},
            },
            {
                "definition": {
                    "title": "Estimated Cost / Hour (USD)",
                    "type": "query_value",
                    "requests": [
                        {
                            "q": "sum:applylens.llm.cost_estimate_usd{env:hackathon}.rollup(sum, 3600)",
                            "aggregator": "last",
                        }
                    ],
                    "autoscale": True,
                    "precision": 4,
                },
                "layout": {"x": 3, "y": 4, "width": 3, "height": 2},
            },
            {
                "definition": {
                    "title": "LLM Operations by Task Type",
                    "type": "toplist",
                    "requests": [
                        {
                            "q": "top(avg:applylens.llm.latency_ms{env:hackathon} by {task_type}.rollup(avg, 60), 10, 'mean', 'desc')"
                        }
                    ],
                },
                "layout": {"x": 6, "y": 4, "width": 6, "height": 2},
            },
            # Section 2: Email Ingest & SLO
            {
                "definition": {
                    "type": "note",
                    "content": "# 📧 Email Ingest & SLO",
                    "background_color": "gray",
                    "font_size": "16",
                    "text_align": "left",
                    "show_tick": False,
                },
                "layout": {"x": 0, "y": 6, "width": 12, "height": 1},
            },
            {
                "definition": {
                    "title": "Email Ingest Lag (seconds)",
                    "show_legend": False,
                    "type": "timeseries",
                    "requests": [
                        {
                            "q": "avg:applylens.ingest_lag_seconds{env:hackathon}",
                            "display_type": "line",
                            "style": {
                                "palette": "dog_classic",
                                "line_type": "solid",
                                "line_width": "normal",
                            },
                        }
                    ],
                    "markers": [
                        {
                            "value": "y = 300",
                            "display_type": "error dashed",
                            "label": "SLO Threshold (5min)",
                        }
                    ],
                },
                "layout": {"x": 0, "y": 7, "width": 6, "height": 3},
            },
            {
                "definition": {
                    "title": "% Within Ingest SLO (< 5min)",
                    "type": "query_value",
                    "requests": [
                        {
                            "q": "(count:applylens.ingest_event_total{env:hackathon,lag_slo_status:ok} / count:applylens.ingest_event_total{env:hackathon}) * 100",
                            "aggregator": "last",
                        }
                    ],
                    "autoscale": True,
                    "precision": 2,
                },
                "layout": {"x": 6, "y": 7, "width": 6, "height": 3},
            },
            # Section 3: Security Risk Detection
            {
                "definition": {
                    "type": "note",
                    "content": "# 🔒 Security Risk Detection",
                    "background_color": "gray",
                    "font_size": "16",
                    "text_align": "left",
                    "show_tick": False,
                },
                "layout": {"x": 0, "y": 10, "width": 12, "height": 1},
            },
            {
                "definition": {
                    "title": "High-Risk Detection Rate (%)",
                    "show_legend": False,
                    "type": "timeseries",
                    "requests": [
                        {
                            "q": "avg:applylens.security_high_risk_rate{env:hackathon}",
                            "display_type": "line",
                            "style": {
                                "palette": "warm",
                                "line_type": "solid",
                                "line_width": "normal",
                            },
                        }
                    ],
                },
                "layout": {"x": 0, "y": 11, "width": 6, "height": 3},
            },
            {
                "definition": {
                    "title": "Quarantine Actions (Last 24h)",
                    "type": "query_value",
                    "requests": [
                        {
                            "q": "sum:applylens.quarantine_actions_total{env:hackathon,action:quarantine}.rollup(sum, 86400)",
                            "aggregator": "last",
                        }
                    ],
                    "autoscale": True,
                    "precision": 0,
                },
                "layout": {"x": 6, "y": 11, "width": 3, "height": 3},
            },
            # Section 4: API Health
            {
                "definition": {
                    "type": "note",
                    "content": "# 🚀 API Health & Performance",
                    "background_color": "gray",
                    "font_size": "16",
                    "text_align": "left",
                    "show_tick": False,
                },
                "layout": {"x": 0, "y": 14, "width": 12, "height": 1},
            },
            {
                "definition": {
                    "title": "API Request Duration (p95)",
                    "show_legend": True,
                    "type": "timeseries",
                    "requests": [
                        {
                            "q": "p95:trace.http.request.duration.by.service{service:applylens-api-hackathon}",
                            "display_type": "line",
                            "style": {
                                "palette": "dog_classic",
                                "line_type": "solid",
                                "line_width": "normal",
                            },
                        }
                    ],
                },
                "layout": {"x": 0, "y": 15, "width": 4, "height": 3},
            },
            {
                "definition": {
                    "title": "API Error Count",
                    "show_legend": False,
                    "type": "timeseries",
                    "requests": [
                        {
                            "q": "sum:trace.http.request.errors{service:applylens-api-hackathon}.as_count()",
                            "display_type": "bars",
                            "style": {"palette": "warm"},
                        }
                    ],
                },
                "layout": {"x": 4, "y": 15, "width": 4, "height": 3},
            },
            {
                "definition": {
                    "title": "API Uptime % (24h)",
                    "type": "query_value",
                    "requests": [
                        {
                            "q": "(sum:trace.http.request{service:applylens-api-hackathon,http.status_code:2*}.as_count() / sum:trace.http.request{service:applylens-api-hackathon}.as_count()) * 100",
                            "aggregator": "last",
                        }
                    ],
                    "autoscale": True,
                    "precision": 2,
                },
                "layout": {"x": 8, "y": 15, "width": 4, "height": 3},
            },
        ],
        "template_variables": [],
        "layout_type": "ordered",
        "is_read_only": False,
        "notify_list": [],
        "reflow_type": "fixed",
    }


def create_or_update_dashboard():
    """Create new dashboard or update existing one."""
    dd_site = os.getenv("DD_SITE")
    dd_api_key = os.getenv("DD_API_KEY")
    dd_app_key = os.getenv("DD_APP_KEY")

    headers = {
        "DD-API-KEY": dd_api_key,
        "DD-APPLICATION-KEY": dd_app_key,
        "Content-Type": "application/json",
    }

    payload = build_dashboard_payload()

    # Check if dashboard already exists
    existing_id = find_existing_dashboard(DASHBOARD_TITLE)

    if existing_id:
        # Update existing dashboard
        url = f"https://api.{dd_site}/api/v1/dashboard/{existing_id}"
        print(f"📝 Updating existing dashboard (ID: {existing_id})...")

        try:
            response = requests.put(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            print("✅ Dashboard updated successfully!")
            print(f"   Dashboard ID: {existing_id}")
            print(f"   Dashboard URL: https://app.{dd_site}/dashboard/{existing_id}")
            print(f"   Title: {DASHBOARD_TITLE}")
            print(f"   Widgets: {len(payload['widgets'])}")
            return 0

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to update dashboard: {e}")
            if hasattr(e.response, "text"):
                print(f"   Response: {e.response.text}")
            return 1

    else:
        # Create new dashboard
        url = f"https://api.{dd_site}/api/v1/dashboard"
        print(f"📊 Creating new dashboard: {DASHBOARD_TITLE}...")

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            dashboard_id = result.get("id")
            print("✅ Dashboard created successfully!")
            print(f"   Dashboard ID: {dashboard_id}")
            print(f"   Dashboard URL: https://app.{dd_site}/dashboard/{dashboard_id}")
            print(f"   Title: {DASHBOARD_TITLE}")
            print(f"   Widgets: {len(payload['widgets'])}")
            return 0

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to create dashboard: {e}")
            if hasattr(e.response, "text"):
                print(f"   Response: {e.response.text}")
            return 1


def main():
    """Main execution."""
    print("=" * 80)
    print("Datadog Dashboard Creation – ApplyLens Observability Copilot")
    print("=" * 80)
    print()

    validate_environment()
    print()

    exit_code = create_or_update_dashboard()

    print()
    print("=" * 80)
    if exit_code == 0:
        print("✅ Dashboard operation completed successfully")
    else:
        print("❌ Dashboard operation failed")
    print("=" * 80)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
