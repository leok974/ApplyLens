#!/usr/bin/env python3
"""
Datadog Monitor Creation Script for ApplyLens Observability Copilot

Creates monitors for the hackathon demo:
1. LLM Latency Spike (p95 > 3000ms) → Create incident
2. LLM Error Burst (error rate > 5%) → Create incident
3. Token/Cost Anomaly (usage > 3x baseline) → Create incident
"""

import os
import sys
import json
import requests


def validate_environment():
    """Validate required environment variables."""
    required_vars = ["DD_API_KEY", "DD_APP_KEY", "DD_SITE"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print(f"❌ Error: Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    print("✅ Environment variables validated")


def create_llm_latency_spike_monitor():
    """Monitor 1: LLM Latency Spike."""

    dd_site = os.getenv("DD_SITE")
    dd_api_key = os.getenv("DD_API_KEY")
    dd_app_key = os.getenv("DD_APP_KEY")

    url = f"https://api.{dd_site}/api/v1/monitor"
    headers = {
        "DD-API-KEY": dd_api_key,
        "DD-APPLICATION-KEY": dd_app_key,
        "Content-Type": "application/json",
    }

    message = """{{#is_alert}}
⚠️ **LLM Latency Spike Detected**

**Impact**: Users experiencing slow email classification/extraction
**Metric**: {{value}} ms (p95 latency over last 5m)
**Threshold**: 3000ms

🔍 **First Response Steps**:
1. Open LLM Health Dashboard: https://us5.datadoghq.com/dashboard/vap-jgg-r7t
2. Check if spike correlates with traffic increase
3. Inspect recent traces with tag `task_type:classify` or `task_type:extract`
4. Review Gemini API status

🛠️ **Mitigation Options**:
- If Gemini unstable: Reduce traffic rate or enable heuristic-only mode
- If traffic spike: Scale up workers or throttle requests
- Check for prompt changes that increased token count
{{/is_alert}}

{{#is_recovery}}
✅ **LLM Latency Recovered**
Latency returned to normal (p95 < 3000ms).
{{/is_recovery}}"""

    payload = {
        "name": "ApplyLens – LLM latency spike (hackathon)",
        "type": "metric alert",
        "query": "max(last_5m):p95:applylens.llm.latency_ms{env:hackathon} > 3000",
        "message": message,
        "tags": [
            "env:hackathon",
            "component:llm",
            "priority:high",
            "incident:auto-create",
        ],
        "options": {
            "thresholds": {"critical": 3000, "warning": 2500},
            "notify_no_data": False,
            "notify_audit": False,
            "include_tags": True,
            "require_full_window": False,
            "escalation_message": "LLM latency still elevated after 15 minutes",
        },
        "priority": 2,
    }

    print("\n📊 Creating Monitor: LLM Latency Spike")
    print("   Threshold: p95 > 3000ms (warning: 2500ms)")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        monitor_id = result["id"]
        monitor_url = f"https://{dd_site}/monitors/{monitor_id}"

        print("   ✅ Created successfully")
        print(f"   ID: {monitor_id}")
        print(f"   URL: {monitor_url}")

        return {"id": monitor_id, "url": monitor_url, "name": payload["name"]}

    except requests.exceptions.HTTPError as e:
        print(f"   ❌ HTTP Error: {e}")
        print(f"   Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def create_llm_error_burst_monitor():
    """Monitor 2: LLM Error Burst."""

    dd_site = os.getenv("DD_SITE")
    dd_api_key = os.getenv("DD_API_KEY")
    dd_app_key = os.getenv("DD_APP_KEY")

    url = f"https://api.{dd_site}/api/v1/monitor"
    headers = {
        "DD-API-KEY": dd_api_key,
        "DD-APPLICATION-KEY": dd_app_key,
        "Content-Type": "application/json",
    }

    message = """{{#is_alert}}
🚨 **LLM Error Burst Detected**

**Impact**: {{value}} errors in last 5 minutes
**Threshold**: > 10 errors in 5 minutes

🔍 **Investigation Steps**:
1. Check LLM Health Dashboard: https://us5.datadoghq.com/dashboard/vap-jgg-r7t → Error Rate panel
2. Filter logs by `env:hackathon AND error`
3. Check error distribution (timeout vs auth vs validation)
4. Review Gemini API status page

🛠️ **Common Causes & Fixes**:
- **Provider outage**: Enable heuristic-only mode (set USE_GEMINI_FOR_CLASSIFY=0)
- **Auth misconfiguration**: Verify GOOGLE_CLOUD_PROJECT and credentials
- **Invalid inputs**: Check recent email parsing changes
- **Rate limiting**: Reduce traffic generator rate

📊 **Quick Links**:
- Dashboard: https://us5.datadoghq.com/dashboard/vap-jgg-r7t
- Logs: Filter by `env:hackathon error`
{{/is_alert}}

{{#is_recovery}}
✅ **LLM Error Rate Recovered**
Error rate back to normal levels.
{{/is_recovery}}"""

    payload = {
        "name": "ApplyLens – LLM error burst (hackathon)",
        "type": "metric alert",
        "query": "sum(last_5m):sum:applylens.llm.error_total{env:hackathon}.as_count() > 10",
        "message": message,
        "tags": [
            "env:hackathon",
            "component:llm",
            "priority:critical",
            "incident:auto-create",
        ],
        "options": {
            "thresholds": {"critical": 10, "warning": 5},
            "notify_no_data": False,
            "notify_audit": False,
            "include_tags": True,
            "require_full_window": False,
        },
        "priority": 1,
    }

    print("\n📊 Creating Monitor: LLM Error Burst")
    print("   Threshold: > 10 errors in 5min (warning: 5)")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        monitor_id = result["id"]
        monitor_url = f"https://{dd_site}/monitors/{monitor_id}"

        print("   ✅ Created successfully")
        print(f"   ID: {monitor_id}")
        print(f"   URL: {monitor_url}")

        return {"id": monitor_id, "url": monitor_url, "name": payload["name"]}

    except requests.exceptions.HTTPError as e:
        print(f"   ❌ HTTP Error: {e}")
        print(f"   Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def create_token_anomaly_monitor():
    """Monitor 3: Token/Cost Anomaly."""

    dd_site = os.getenv("DD_SITE")
    dd_api_key = os.getenv("DD_API_KEY")
    dd_app_key = os.getenv("DD_APP_KEY")

    url = f"https://api.{dd_site}/api/v1/monitor"
    headers = {
        "DD-API-KEY": dd_api_key,
        "DD-APPLICATION-KEY": dd_app_key,
        "Content-Type": "application/json",
    }

    message = """{{#is_alert}}
⚠️ **LLM Token Usage Anomaly**

**Current Usage**: {{value}} tokens in last 10 minutes
**Baseline**: Check 1-hour average for comparison

🔍 **Possible Causes**:
- Traffic generator running in `token_bloat` mode
- Prompt drift (prompts getting longer)
- Retry loop or duplicate processing
- Legitimate traffic spike

📊 **Investigation**:
1. Check traffic generator: Verify it's in `normal_traffic` mode
2. Review recent traces for repeated operations
3. Check if `task_type:extract` spike (higher token usage)
4. Inspect prompt templates for unexpected expansion

💰 **Cost Impact**:
Monitor cost estimate metric: `applylens.llm.cost_estimate_usd`

🛠️ **Mitigation**:
- Adjust traffic generator rate if testing
- Review and optimize prompts if production
- Enable rate limiting if necessary
{{/is_alert}}

{{#is_recovery}}
✅ **Token Usage Normalized**
Usage returned to baseline levels.
{{/is_recovery}}"""

    payload = {
        "name": "ApplyLens – LLM token usage anomaly (hackathon)",
        "type": "metric alert",
        "query": "sum(last_10m):sum:applylens.llm.test.tokens_used{env:hackathon} > 50000",
        "message": message,
        "tags": [
            "env:hackathon",
            "component:llm",
            "priority:low",
            "incident:auto-create",
        ],
        "options": {
            "thresholds": {"critical": 50000, "warning": 30000},
            "notify_no_data": False,
            "notify_audit": False,
            "include_tags": True,
            "require_full_window": False,
        },
        "priority": 3,
    }

    print("\n📊 Creating Monitor: Token/Cost Anomaly")
    print("   Threshold: > 50k tokens in 10min (warning: 30k)")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        monitor_id = result["id"]
        monitor_url = f"https://{dd_site}/monitors/{monitor_id}"

        print("   ✅ Created successfully")
        print(f"   ID: {monitor_id}")
        print(f"   URL: {monitor_url}")

        return {"id": monitor_id, "url": monitor_url, "name": payload["name"]}

    except requests.exceptions.HTTPError as e:
        print(f"   ❌ HTTP Error: {e}")
        print(f"   Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def main():
    """Create all monitors."""

    print("=" * 70)
    print("Datadog Monitor Creator")
    print("ApplyLens Observability Copilot – Hackathon")
    print("=" * 70)

    validate_environment()

    monitors_created = []

    # Monitor 1: Latency Spike
    print("\n" + "=" * 70)
    print("Creating Monitor #1: LLM Latency Spike")
    print("=" * 70)

    latency_monitor = create_llm_latency_spike_monitor()
    if latency_monitor:
        monitors_created.append(latency_monitor)

    # Monitor 2: Error Burst
    print("\n" + "=" * 70)
    print("Creating Monitor #2: LLM Error Burst")
    print("=" * 70)

    error_monitor = create_llm_error_burst_monitor()
    if error_monitor:
        monitors_created.append(error_monitor)

    # Monitor 3: Token Anomaly
    print("\n" + "=" * 70)
    print("Creating Monitor #3: Token/Cost Anomaly")
    print("=" * 70)

    token_monitor = create_token_anomaly_monitor()
    if token_monitor:
        monitors_created.append(token_monitor)

    # Summary
    print("\n" + "=" * 70)
    print("✅ Monitor Creation Complete!")
    print("=" * 70)

    if monitors_created:
        print(f"\n📊 Created {len(monitors_created)} monitor(s):")
        for i, monitor in enumerate(monitors_created, 1):
            print(f"\n   {i}. {monitor['name']}")
            print(f"      ID: {monitor['id']}")
            print(f"      URL: {monitor['url']}")

        # Save monitor info
        output = {
            "monitors": monitors_created,
            "created_at": "2025-11-25",
            "dashboard_id": "vap-jgg-r7t",
            "slo_id": "d22bff39b3365745bbe3cb7853eaa659",
        }

        output_file = "/tmp/datadog_monitors_info.json"
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)

        print(f"\n💾 Monitor info saved to: {output_file}")

        print("\n📈 Next Steps:")
        print("   1. View monitors: https://us5.datadoghq.com/monitors/manage")
        print("   2. Test monitors by running traffic generator:")
        print(
            "      python scripts/traffic_generator.py --mode latency_injection --rate 2.0 --duration 300"
        )
        print("   3. Verify incidents are auto-created when monitors alert")
        print(
            "   4. Check dashboard has all data: https://us5.datadoghq.com/dashboard/vap-jgg-r7t"
        )
    else:
        print("\n⚠️  No monitors were created")

    print("=" * 70)


if __name__ == "__main__":
    main()
