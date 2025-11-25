#!/usr/bin/env python3
"""
Datadog Dashboard Creation Script for ApplyLens Observability Copilot (Simplified)

Uses direct HTTP requests to Datadog API to avoid complex type dependencies.
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
    print(f"   DD_API_KEY: {os.getenv('DD_API_KEY')[:8]}...")
    print(f"   DD_APP_KEY: {os.getenv('DD_APP_KEY')[:8]}...")


def create_dashboard_payload():
    """Create the dashboard JSON payload."""
    return {
        "title": "ApplyLens Observability Copilot – Hackathon",
        "description": (
            "Comprehensive observability dashboard for ApplyLens hackathon demo.\n\n"
            "Monitors:\n"
            "- 🤖 LLM Health: Gemini classification/extraction performance\n"
            "- 📥 Ingest Freshness: Email processing lag\n"
            "- 🛡️ Security: Risk detection and quarantine actions\n"
            "- 🏗️ Infrastructure: API performance and uptime"
        ),
        "layout_type": "ordered",
        "notify_list": [],
        "template_variables": [
            {
                "name": "env",
                "prefix": "env",
                "available_values": [],
                "default": "hackathon",
            }
        ],
        "widgets": [
            # Section: LLM Health
            {
                "definition": {
                    "type": "note",
                    "content": "# 🤖 LLM Health",
                    "background_color": "gray",
                    "font_size": "18",
                    "text_align": "center",
                    "show_tick": False,
                }
            },
            # Widget 1: LLM Latency (p50/p95/p99)
            {
                "definition": {
                    "type": "timeseries",
                    "title": "LLM Classification Latency (p50/p95/p99)",
                    "show_legend": True,
                    "legend_layout": "auto",
                    "legend_columns": ["avg", "max", "value"],
                    "requests": [
                        {
                            "q": "avg:applylens.llm.latency_ms{env:hackathon,task_type:classify}.rollup(avg, 60)",
                            "display_type": "line",
                            "style": {
                                "palette": "dog_classic",
                                "line_type": "solid",
                                "line_width": "normal",
                            },
                        },
                        {
                            "q": "p95:applylens.llm.latency_ms{env:hackathon,task_type:classify}.rollup(max, 60)",
                            "display_type": "line",
                            "style": {
                                "palette": "warm",
                                "line_type": "dashed",
                                "line_width": "normal",
                            },
                        },
                        {
                            "q": "p99:applylens.llm.latency_ms{env:hackathon,task_type:classify}.rollup(max, 60)",
                            "display_type": "line",
                            "style": {
                                "palette": "red",
                                "line_type": "dotted",
                                "line_width": "normal",
                            },
                        },
                    ],
                    "yaxis": {"min": "auto", "max": "auto"},
                    "markers": [
                        {
                            "value": "y = 2000",
                            "display_type": "error dashed",
                            "label": "SLO Target (2000ms)",
                        }
                    ],
                }
            },
            # Widget 2: LLM Error Rate
            {
                "definition": {
                    "type": "timeseries",
                    "title": "LLM Error Rate (%)",
                    "show_legend": False,
                    "requests": [
                        {
                            "q": "(sum:applylens.llm.error_total{env:hackathon}.as_rate() / sum:applylens.llm.test.requests{env:hackathon}.as_rate()) * 100",
                            "display_type": "line",
                            "style": {
                                "palette": "red",
                                "line_type": "solid",
                                "line_width": "thick",
                            },
                        }
                    ],
                    "yaxis": {"min": "0", "max": "100"},
                    "markers": [
                        {
                            "value": "y = 5",
                            "display_type": "error dashed",
                            "label": "Alert Threshold (5%)",
                        }
                    ],
                }
            },
            # Widget 3: Token Usage
            {
                "definition": {
                    "type": "query_value",
                    "title": "Tokens / 5min",
                    "requests": [
                        {
                            "q": "sum:applylens.llm.test.tokens_used{env:hackathon}.rollup(sum, 300)",
                            "aggregator": "last",
                        }
                    ],
                    "autoscale": True,
                    "precision": 0,
                    "text_align": "center",
                }
            },
            # Widget 4: Cost Estimate
            {
                "definition": {
                    "type": "query_value",
                    "title": "Estimated Cost / Hour (USD)",
                    "requests": [
                        {
                            "q": "sum:applylens.llm.cost_estimate_usd{env:hackathon}.rollup(sum, 3600)",
                            "aggregator": "last",
                        }
                    ],
                    "autoscale": False,
                    "precision": 4,
                    "text_align": "center",
                    "custom_unit": "$",
                }
            },
            # Widget 5: Task Type Breakdown
            {
                "definition": {
                    "type": "toplist",
                    "title": "LLM Operations by Task Type",
                    "requests": [
                        {
                            "q": "top(avg:applylens.llm.latency_ms{env:hackathon} by {task_type}.rollup(avg, 60), 10, 'mean', 'desc')"
                        }
                    ],
                }
            },
            # Section: Ingest Freshness
            {
                "definition": {
                    "type": "note",
                    "content": "# 📥 Ingest Freshness (Optional)",
                    "background_color": "gray",
                    "font_size": "18",
                    "text_align": "center",
                    "show_tick": False,
                }
            },
            # Widget 6: Ingest Lag
            {
                "definition": {
                    "type": "timeseries",
                    "title": "Email Ingest Lag (seconds)",
                    "show_legend": False,
                    "requests": [
                        {
                            "q": "avg:applylens.ingest_lag_seconds{env:hackathon}",
                            "display_type": "line",
                            "style": {
                                "palette": "cool",
                                "line_type": "solid",
                                "line_width": "normal",
                            },
                        }
                    ],
                    "yaxis": {"min": "auto", "max": "auto"},
                    "markers": [
                        {
                            "value": "y = 60",
                            "display_type": "ok dashed",
                            "label": "Good (< 60s)",
                        },
                        {
                            "value": "y = 300",
                            "display_type": "error dashed",
                            "label": "SLO Target (300s)",
                        },
                    ],
                }
            },
            # Widget 7: SLO Compliance
            {
                "definition": {
                    "type": "query_value",
                    "title": "% Within Ingest SLO (< 5min)",
                    "requests": [
                        {
                            "q": "(count:applylens.ingest_event_total{env:hackathon,lag_slo_status:ok} / count:applylens.ingest_event_total{env:hackathon}) * 100",
                            "aggregator": "last",
                        }
                    ],
                    "autoscale": False,
                    "precision": 2,
                    "text_align": "center",
                    "custom_unit": "%",
                }
            },
            # Section: Security Signals
            {
                "definition": {
                    "type": "note",
                    "content": "# 🛡️ Security Signals (Optional)",
                    "background_color": "gray",
                    "font_size": "18",
                    "text_align": "center",
                    "show_tick": False,
                }
            },
            # Widget 8: Security Risk
            {
                "definition": {
                    "type": "timeseries",
                    "title": "High-Risk Detection Rate (%)",
                    "show_legend": True,
                    "requests": [
                        {
                            "q": "avg:applylens.security_high_risk_rate{env:hackathon}",
                            "display_type": "line",
                            "style": {
                                "palette": "orange",
                                "line_type": "solid",
                                "line_width": "normal",
                            },
                        },
                        {
                            "q": "avg:applylens.security_high_risk_rate{env:hackathon}.rollup(avg, 604800)",
                            "display_type": "line",
                            "style": {
                                "palette": "grey",
                                "line_type": "dashed",
                                "line_width": "thin",
                            },
                        },
                    ],
                    "yaxis": {"min": "0", "max": "auto"},
                }
            },
            # Section: Infrastructure
            {
                "definition": {
                    "type": "note",
                    "content": "# 🏗️ Infrastructure",
                    "background_color": "gray",
                    "font_size": "18",
                    "text_align": "center",
                    "show_tick": False,
                }
            },
            # Widget 10: API Duration
            {
                "definition": {
                    "type": "timeseries",
                    "title": "API Request Duration (p95)",
                    "show_legend": True,
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
                    "yaxis": {"min": "auto", "max": "auto"},
                }
            },
            # Widget 11: API Errors
            {
                "definition": {
                    "type": "timeseries",
                    "title": "API Error Count",
                    "show_legend": False,
                    "requests": [
                        {
                            "q": "sum:trace.http.request.errors{service:applylens-api-hackathon}.as_count()",
                            "display_type": "bars",
                            "style": {"palette": "red"},
                        }
                    ],
                    "yaxis": {"min": "0", "max": "auto"},
                }
            },
            # Widget 12: API Uptime
            {
                "definition": {
                    "type": "query_value",
                    "title": "API Uptime % (24h)",
                    "requests": [
                        {
                            "q": "(sum:trace.http.request{service:applylens-api-hackathon,http.status_code:2*}.as_count() / sum:trace.http.request{service:applylens-api-hackathon}.as_count()) * 100",
                            "aggregator": "last",
                        }
                    ],
                    "autoscale": False,
                    "precision": 2,
                    "text_align": "center",
                    "custom_unit": "%",
                }
            },
        ],
    }


def create_dashboard():
    """Create the dashboard via Datadog HTTP API."""

    validate_environment()

    dd_site = os.getenv("DD_SITE")
    dd_api_key = os.getenv("DD_API_KEY")
    dd_app_key = os.getenv("DD_APP_KEY")

    url = f"https://api.{dd_site}/api/v1/dashboard"
    headers = {
        "DD-API-KEY": dd_api_key,
        "DD-APPLICATION-KEY": dd_app_key,
        "Content-Type": "application/json",
    }

    payload = create_dashboard_payload()

    print(f"\n🔨 Building dashboard with {len(payload['widgets'])} widgets...")
    print(f"📡 Calling Datadog API: {url}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        dashboard_id = result.get("id")
        dashboard_url = f"https://{dd_site}/dashboard/{dashboard_id}"

        print("\n" + "=" * 70)
        print("✅ Dashboard Created Successfully!")
        print("=" * 70)
        print("\n📊 Dashboard Details:")
        print(f"   Title: {result.get('title')}")
        print(f"   ID: {dashboard_id}")
        print(f"   URL: {dashboard_url}")
        print("\n🔗 View Dashboard:")
        print(f"   {dashboard_url}")
        print("\n💡 Next Steps:")
        print("   1. Open the dashboard and verify all widgets are rendering")
        print(
            "   2. Some widgets may show 'No data' - run traffic generator to populate"
        )
        print("   3. Create SLOs (see hackathon/DATADOG_SETUP.md Section 2)")
        print("   4. Configure monitors (see hackathon/DATADOG_SETUP.md Section 3)")
        print("=" * 70)

        # Save dashboard info
        output = {
            "dashboard_id": dashboard_id,
            "dashboard_url": dashboard_url,
            "title": result.get("title"),
            "created": True,
        }

        with open("/tmp/datadog_dashboard_info.json", "w") as f:
            json.dump(output, f, indent=2)

        print("\n💾 Dashboard info saved to: /tmp/datadog_dashboard_info.json")

        return dashboard_url

    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        print(f"Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 70)
    print("Datadog Dashboard Creator (Simplified)")
    print("ApplyLens Observability Copilot – Hackathon")
    print("=" * 70)
    dashboard_url = create_dashboard()
    print(f"\n✨ Dashboard ready: {dashboard_url}")
