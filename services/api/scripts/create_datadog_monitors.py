#!/usr/bin/env python3
"""
Datadog Monitor Creation Script for ApplyLens Observability Copilot

Creates monitors for the hackathon demo:
1. LLM Latency Spike (p95 > 3000ms) → Create incident
2. LLM Error Burst (error rate > 5%) → Create incident
3. Token/Cost Anomaly (usage > 3x baseline) → Create incident

Phase 3C - Additional monitors (replaces Prometheus alerts):
4. Backfill Failing → Replaces Prometheus alert "BackfillFailing"
5. Backfill Rate Limited Spike → Replaces Prometheus alert "BackfillRateLimitedSpike"
6. Gmail Disconnected → Replaces Prometheus alert "GmailDisconnected"

Reference: docs/OBSERVABILITY_STACK_PLAN.md (Gap Analysis section)
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


def create_backfill_failing_monitor():
    """Monitor 4: Backfill Failing - Replaces Prometheus alert 'BackfillFailing'."""

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
🚨 **Backfill Job Failures Detected**

**Impact**: {{value}} backfill errors in last 10 minutes
**Threshold**: > 0 errors

🔍 **Investigation Steps**:
1. Check logs for backfill error details: Filter by `service:applylens-api error backfill`
2. Verify Gmail API status: https://www.google.com/appsstatus/dashboard/
3. Check OAuth token expiration: Review user authentication status
4. Inspect rate limiting: Check for 429 responses

🛠️ **Common Causes & Fixes**:
- **Gmail API errors**: Check credentials and OAuth scopes
- **Rate limiting**: Reduce backfill batch size or increase delay between requests
- **Token expiration**: Re-authenticate user accounts
- **Network issues**: Verify connectivity to Gmail API endpoints
- **Invalid email IDs**: Check for corrupted data in backfill queue

📊 **Runbook**:
- Backfill documentation: See `services/api/README.md` for backfill procedures
- Manual backfill trigger: `POST /api/backfill` with appropriate parameters

{{/is_alert}}

{{#is_recovery}}
✅ **Backfill Errors Resolved**
No backfill errors detected in last 10 minutes.
{{/is_recovery}}"""

    payload = {
        "name": "ApplyLens – Backfill failing",
        "type": "metric alert",
        "query": "sum(last_10m):sum:applylens.backfill.errors{*}.as_count() > 0",
        "message": message,
        "tags": [
            "component:backfill",
            "priority:warning",
            "replaces:prometheus-BackfillFailing",
        ],
        "options": {
            "thresholds": {"critical": 0},
            "notify_no_data": False,
            "notify_audit": False,
            "include_tags": True,
            "require_full_window": True,
        },
        "priority": 2,
    }

    print("\n📊 Creating Monitor: Backfill Failing")
    print("   Threshold: > 0 errors in 10min")
    print("   Replaces: Prometheus alert 'BackfillFailing'")

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


def create_backfill_rate_limited_monitor():
    """Monitor 5: Backfill Rate Limited Spike - Replaces Prometheus alert 'BackfillRateLimitedSpike'."""

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
⚠️ **Backfill Rate Limiting Spike**

**Impact**: {{value}} rate-limited requests in last 15 minutes
**Threshold**: > 10 rate limits in 15 minutes

🔍 **Investigation**:
1. Check Gmail API quota usage: https://console.cloud.google.com/apis/api/gmail.googleapis.com/quotas
2. Review backfill job frequency and batch sizes
3. Verify if multiple users triggering backfills simultaneously
4. Check for retry loops causing quota exhaustion

🛠️ **Mitigation Options**:
- **Reduce backfill rate**: Increase delay between API calls
- **Implement exponential backoff**: Add retry delays for 429 responses
- **Batch optimization**: Reduce number of emails per batch
- **Quota increase**: Request higher Gmail API quota from Google Cloud Console
- **Temporary pause**: Stop backfill jobs until quota resets (typically hourly/daily)

💡 **Gmail API Quotas**:
- Standard quota: 250 quota units per user per second
- Batch requests: 1,000 quota units per request
- Quota resets: Per-user quotas reset every 100 seconds

📊 **Monitoring**:
- Check rate limit trend: `applylens.backfill.rate_limited` metric
- Compare with successful requests: `applylens.backfill.success`

{{/is_alert}}

{{#is_recovery}}
✅ **Rate Limiting Normalized**
Backfill rate limits back to normal levels.
{{/is_recovery}}"""

    payload = {
        "name": "ApplyLens – Backfill rate limited spike",
        "type": "metric alert",
        "query": "sum(last_15m):sum:applylens.backfill.rate_limited{*}.as_count() > 10",
        "message": message,
        "tags": [
            "component:backfill",
            "priority:info",
            "replaces:prometheus-BackfillRateLimitedSpike",
        ],
        "options": {
            "thresholds": {"critical": 10, "warning": 5},
            "notify_no_data": False,
            "notify_audit": False,
            "include_tags": True,
            "require_full_window": False,
        },
        "priority": 3,
    }

    print("\n📊 Creating Monitor: Backfill Rate Limited Spike")
    print("   Threshold: > 10 rate limits in 15min (warning: 5)")
    print("   Replaces: Prometheus alert 'BackfillRateLimitedSpike'")

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


def create_gmail_disconnected_monitor():
    """Monitor 6: Gmail Disconnected - Replaces Prometheus alert 'GmailDisconnected'."""

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
🔴 **Gmail Connection Lost**

**Impact**: ApplyLens is not ingesting new emails
**Duration**: Gmail connection down for > 15 minutes

🔍 **Investigation Steps**:
1. Check user authentication status: Review OAuth token validity
2. Verify Gmail API status: https://www.google.com/appsstatus/dashboard/
3. Check application logs for auth errors: Filter by `gmail auth error`
4. Inspect `/api/gmail/status` endpoint response

🛠️ **Recovery Steps**:
- **OAuth token expired**: Trigger re-authentication flow for affected users
- **Credentials revoked**: User needs to re-authorize ApplyLens
- **API outage**: Wait for Gmail service recovery (monitor status page)
- **Network issues**: Check connectivity and firewall rules
- **Scope changes**: Verify OAuth scopes haven't changed

📊 **Verification**:
- Check `applylens.gmail.connected` gauge metric (should be 1 when connected)
- Verify email ingest is resuming: Monitor `applylens.ingest_lag_seconds`
- Test connection: Call `/api/gmail/status` endpoint

⚡ **Manual Reconnect**:
```bash
# Trigger OAuth re-auth for user
POST /api/auth/gmail/reconnect
```

{{/is_alert}}

{{#is_recovery}}
✅ **Gmail Connection Restored**
Gmail connection is back online. Email ingestion should resume automatically.
{{/is_recovery}}"""

    payload = {
        "name": "ApplyLens – Gmail disconnected",
        "type": "metric alert",
        "query": "max(last_15m):max:applylens.gmail.connected{*} < 1",
        "message": message,
        "tags": [
            "component:gmail",
            "priority:warning",
            "replaces:prometheus-GmailDisconnected",
        ],
        "options": {
            "thresholds": {"critical": 1},
            "notify_no_data": True,
            "no_data_timeframe": 20,
            "notify_audit": False,
            "include_tags": True,
            "require_full_window": True,
        },
        "priority": 2,
    }

    print("\n📊 Creating Monitor: Gmail Disconnected")
    print("   Threshold: connected gauge < 1 for 15min")
    print("   Replaces: Prometheus alert 'GmailDisconnected'")

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

    # Monitor 4: Backfill Failing (Phase 3C)
    print("\n" + "=" * 70)
    print("Creating Monitor #4: Backfill Failing (Phase 3C)")
    print("=" * 70)

    backfill_monitor = create_backfill_failing_monitor()
    if backfill_monitor:
        monitors_created.append(backfill_monitor)

    # Monitor 5: Backfill Rate Limited (Phase 3C)
    print("\n" + "=" * 70)
    print("Creating Monitor #5: Backfill Rate Limited Spike (Phase 3C)")
    print("=" * 70)

    rate_limit_monitor = create_backfill_rate_limited_monitor()
    if rate_limit_monitor:
        monitors_created.append(rate_limit_monitor)

    # Monitor 6: Gmail Disconnected (Phase 3C)
    print("\n" + "=" * 70)
    print("Creating Monitor #6: Gmail Disconnected (Phase 3C)")
    print("=" * 70)

    gmail_monitor = create_gmail_disconnected_monitor()
    if gmail_monitor:
        monitors_created.append(gmail_monitor)

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

        output_file = "datadog_monitors_info.json"
        try:
            with open(output_file, "w") as f:
                json.dump(output, f, indent=2)
            print(f"\n💾 Monitor info saved to: {output_file}")
        except Exception as e:
            print(f"\n⚠️  Could not save monitor info: {e}")

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
