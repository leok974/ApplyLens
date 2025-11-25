# Traffic Generator for ApplyLens Hackathon Demo

## Overview

The traffic generator creates controlled load on the ApplyLens API to demonstrate Datadog monitoring, dashboards, SLOs, and incident management.

## Modes

### 1. Normal Traffic (`normal_traffic`)
Sends realistic email classification requests at a steady rate.

**Use case**: Baseline metrics, healthy system demonstration

```bash
python scripts/traffic_generator.py --mode normal_traffic --rate 10 --duration 300
```

**What it does**:
- Sends 10 requests/second for 5 minutes
- Random selection from sample job emails
- Expected: Low latency (<500ms), no errors

### 2. Latency Injection (`latency_injection`)
Introduces artificial delays to trigger latency monitors.

**Use case**: Demonstrate latency spike detection and incident creation

```bash
python scripts/traffic_generator.py --mode latency_injection --rate 20 --duration 120
```

**What it does**:
- 30% of requests have 2-5 second delays
- Triggers p95 latency > 3000ms monitor
- Creates Datadog incident automatically

**Expected monitor**: `LLM latency spike`

### 3. Error Injection (`error_injection`)
Sends malformed requests to trigger error rate monitors.

**Use case**: Demonstrate error burst detection

```bash
python scripts/traffic_generator.py --mode error_injection --rate 15 --duration 90
```

**What it does**:
- 50% of requests are intentionally malformed (400 errors)
- Triggers error_rate > 5% monitor
- Creates incident with error codes

**Expected monitor**: `LLM error burst`

### 4. Token Bloat (`token_bloat`)
Sends massive prompts to trigger cost anomaly detection.

**Use case**: Demonstrate cost monitoring and runaway prompt detection

```bash
python scripts/traffic_generator.py --mode token_bloat --rate 25 --duration 60
```

**What it does**:
- Sends emails with 10,000+ character prompts
- Triggers token usage > 3x baseline
- Creates incident for cost investigation

**Expected monitor**: `Cost anomaly`

## CLI Reference

```bash
python scripts/traffic_generator.py [OPTIONS]
```

**Options**:
- `--mode`: Traffic mode (default: `normal_traffic`)
  - Choices: `normal_traffic`, `latency_injection`, `error_injection`, `token_bloat`
- `--rate`: Requests per second (default: 10)
- `--duration`: Duration in seconds (default: 300)
- `--url`: API base URL (default: `http://localhost:8000`)
- `--verbose`: Enable debug logging

**Examples**:

```bash
# Quick 30-second smoke test
python scripts/traffic_generator.py --mode normal_traffic --rate 5 --duration 30

# Aggressive latency test
python scripts/traffic_generator.py --mode latency_injection --rate 50 --duration 60

# Error storm
python scripts/traffic_generator.py --mode error_injection --rate 100 --duration 30

# Cost spike simulation
python scripts/traffic_generator.py --mode token_bloat --rate 30 --duration 120
```

## Demo Video Workflow

### Step 1: Show Healthy Baseline (0:00-0:30)
```bash
# Terminal 1: Start traffic generator
python scripts/traffic_generator.py --mode normal_traffic --rate 10 --duration 600

# Browser: Show Datadog dashboard
# - LLM Health panel showing green
# - Latency p95 ~200-500ms
# - Error rate 0%
# - Token usage steady
```

### Step 2: Trigger Latency Monitor (0:30-1:30)
```bash
# Terminal 1: Stop normal traffic (Ctrl+C)
# Terminal 1: Start latency injection
python scripts/traffic_generator.py --mode latency_injection --rate 20 --duration 180

# Browser: Watch Datadog
# - Latency dashboard spikes red
# - Monitor transitions to ALERT state
# - Incident auto-created with dashboard link
# - Show trace with slow spans
```

### Step 3: Show Incident Details (1:30-2:00)
```bash
# Browser: Navigate to incident
# - View incident timeline
# - Show attached dashboard
# - Display trace samples
# - Demonstrate runbook steps
```

### Step 4: Trigger Cost Anomaly (2:00-2:30)
```bash
# Terminal 1: Stop latency injection
# Terminal 1: Start token bloat
python scripts/traffic_generator.py --mode token_bloat --rate 30 --duration 120

# Browser: Show Datadog
# - Token usage chart spikes 10x
# - Cost anomaly monitor fires
# - New incident created
# - Show prompt analysis
```

### Step 5: Recovery & Wrap-up (2:30-3:00)
```bash
# Terminal 1: Stop all traffic
# Browser: Show dashboard returning to green
# - All monitors resolve
# - Incidents marked as resolved
# - Summary metrics for demo period
```

## Monitoring Traffic in Datadog

### Key Metrics to Watch

1. **LLM Latency**: `llm_latency_ms`
   - Should be <500ms in normal mode
   - Spikes to >3000ms in latency_injection mode

2. **Error Rate**: `llm_error_rate`
   - Should be ~0% in normal mode
   - Jumps to ~50% in error_injection mode

3. **Token Usage**: `llm_tokens_used`
   - Steady ~100-200 tokens/request in normal mode
   - Spikes to 5000+ in token_bloat mode

4. **Request Volume**: `http_requests_total{endpoint="/hackathon/classify"}`
   - Should match configured rate

### Filtering Traffic

All generated traffic includes header:
```
X-Traffic-Type: HACKATHON_TRAFFIC*
```

Use this to filter in Datadog:
```
http.headers.x-traffic-type:HACKATHON_TRAFFIC*
```

## Troubleshooting

### "Connection refused"
- Ensure API is running: `docker-compose -f docker-compose.hackathon.yml up -d`
- Check API health: `curl http://localhost:8000/health/live`

### "503 Service Unavailable"
- Check Gemini is configured: `curl http://localhost:8000/debug/llm`
- Verify `GOOGLE_CLOUD_PROJECT` and `USE_GEMINI_FOR_CLASSIFY` are set

### No metrics in Datadog
- Verify Datadog agent is running: `docker ps | grep datadog`
- Check API key: `docker logs applylens-datadog-agent`
- Confirm DD_SERVICE/DD_ENV tags are set

### Rate too high
- Reduce `--rate` parameter
- Check API container CPU: `docker stats applylens-api-hackathon`

## Advanced Usage

### Custom Email Samples
Edit `scripts/traffic_generator.py` and modify `SAMPLE_EMAILS` list.

### Parallel Traffic
Run multiple generators simultaneously:
```bash
# Terminal 1: Background normal traffic
python scripts/traffic_generator.py --mode normal_traffic --rate 5 --duration 600 &

# Terminal 2: Periodic latency spikes
while true; do
  python scripts/traffic_generator.py --mode latency_injection --rate 20 --duration 30
  sleep 120
done
```

### Custom Failure Modes
Extend the `TrafficGenerator` class with new methods:
```python
async def _custom_failure_request(self):
    # Your custom failure logic
    pass
```

## Integration Tests

Verify traffic generator works:
```bash
# Quick smoke test (30 seconds)
python scripts/traffic_generator.py --mode normal_traffic --rate 5 --duration 30 --verbose

# Check summary shows >90% success rate
```
