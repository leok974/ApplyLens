# Chaos Engineering Guide

**Version:** 1.0  
**Last Updated:** October 17, 2025  
**Audience:** SRE Team, Engineering Team

---

## Table of Contents

1. [Introduction](#introduction)
2. [Chaos Engineering Principles](#chaos-engineering-principles)
3. [Getting Started](#getting-started)
4. [Chaos Types](#chaos-types)
5. [Running Chaos Tests](#running-chaos-tests)
6. [Scheduled Chaos](#scheduled-chaos)
7. [Interpreting Results](#interpreting-results)
8. [Best Practices](#best-practices)

---

## Introduction

Chaos engineering is the practice of intentionally injecting failures into a system to validate its resilience and ability to recover. At ApplyLens, we use chaos engineering to:

1. **Validate resilience:** Ensure systems handle failures gracefully
2. **Maintain SLO compliance:** Verify SLOs are met even under failure conditions
3. **Improve confidence:** Build confidence in production deployments
4. **Identify weaknesses:** Find and fix resilience gaps before they cause outages

### Why Chaos Engineering?

- **Proactive:** Find issues before they impact users
- **Realistic:** Test real failure scenarios
- **Continuous:** Regular testing maintains resilience
- **Educational:** Teaches teams about system behavior

---

## Chaos Engineering Principles

### 1. Build a Hypothesis

Before injecting chaos, define what you expect to happen:

**Example:**
- **Hypothesis:** "If the Gmail API returns 503 errors, the system will retry with exponential backoff and maintain >95% success rate"
- **Expected Behavior:** Automatic retry with backoff
- **Success Criteria:** Success rate >95% after retries

### 2. Inject Real-World Failures

Focus on failures that actually occur in production:

- **API outages** (503, 500 errors)
- **Network latency** (slow responses)
- **Rate limiting** (429 errors)
- **Database errors** (connection failures)
- **Timeouts** (request timeouts)

### 3. Minimize Blast Radius

Start small and gradually increase scope:

1. **Development:** Test on dev environment
2. **Staging:** Full chaos testing
3. **Canary:** Limited production chaos (10% traffic)
4. **Production:** Controlled chaos during low-traffic hours

### 4. Automate Experiments

Run chaos tests automatically:

- **CI/CD Pipeline:** On every deployment
- **Scheduled:** Weekly chaos runs
- **Continuous:** Low-level chaos in staging

### 5. Measure Impact

Track metrics during chaos:

- **Error rate:** Should stay within error budget
- **Latency (P95):** Should stay within SLO targets
- **Recovery time:** How quickly system recovers
- **User impact:** Minimal to none

---

## Getting Started

### Installation

Chaos testing framework is included in the ApplyLens API:

```bash
cd services/api
pip install -r requirements-dev.txt
```

### Enable Chaos Mode

**IMPORTANT:** Chaos injection is disabled by default for safety.

```python
from app.chaos.injector import chaos_injector

# Enable chaos (only in tests!)
chaos_injector.enable_experiment_mode()

# Your tests here...

# Disable after tests
chaos_injector.disable_experiment_mode()
```

### Basic Example

```python
from app.chaos.injector import chaos_injector, ChaosType

# Enable chaos for testing
chaos_injector.enable_experiment_mode()

try:
    # Inject API outage with 30% probability
    with chaos_injector.inject(ChaosType.API_OUTAGE, probability=0.3):
        result = external_api_call()
except ChaosException:
    # Handle failure (retry, fallback, etc.)
    result = fallback_handler()
finally:
    chaos_injector.disable_experiment_mode()
```

---

## Chaos Types

### 1. API Outage

**What it does:** Simulates external API failures (503, 500 errors)

**Use cases:**
- Gmail API unavailable
- OpenAI API down
- Third-party service outage

**Configuration:**
```python
chaos_injector.inject(
    ChaosType.API_OUTAGE,
    probability=0.3,        # 30% chance of failure
    status_code=503,        # HTTP status code
    error_message="Service temporarily unavailable"
)
```

**Expected resilience:**
- Automatic retry with exponential backoff
- Circuit breaker after 5 consecutive failures
- Fallback to cache or degraded mode

---

### 2. High Latency

**What it does:** Injects artificial delays into requests

**Use cases:**
- Slow database queries
- Network congestion
- Elasticsearch performance degradation

**Configuration:**
```python
chaos_injector.inject(
    ChaosType.HIGH_LATENCY,
    delay_ms=1000,          # 1-second delay
    probability=0.1         # 10% of requests
)
```

**Expected resilience:**
- Timeout handling (requests abort after threshold)
- Graceful degradation (use cache if too slow)
- Request queuing or rate limiting

---

### 3. Rate Limiting

**What it does:** Simulates API rate limit errors (429)

**Use cases:**
- Gmail API quota exceeded
- OpenAI API rate limits
- Third-party service throttling

**Configuration:**
```python
chaos_injector.inject(
    ChaosType.RATE_LIMIT,
    probability=0.2,        # 20% chance
    status_code=429
)
```

**Expected resilience:**
- Exponential backoff (wait before retry)
- Request queue (buffer requests)
- Graceful degradation

---

### 4. Database Errors

**What it does:** Simulates database connection failures

**Use cases:**
- Database connection pool exhausted
- Database temporarily unavailable
- Network partition

**Configuration:**
```python
chaos_injector.inject(
    ChaosType.DATABASE_ERROR,
    probability=0.1,
    error_message="Connection pool exhausted"
)
```

**Expected resilience:**
- Automatic retry with backoff
- Connection pool management
- Read replica failover

---

### 5. Timeout

**What it does:** Simulates request timeouts

**Use cases:**
- Long-running queries
- Hung connections
- Network issues

**Configuration:**
```python
chaos_injector.inject(
    ChaosType.TIMEOUT,
    probability=0.05
)
```

**Expected resilience:**
- Timeout detection and abort
- Retry with shorter timeout
- Fallback to cached data

---

## Running Chaos Tests

### Local Testing

Run chaos tests locally during development:

```bash
cd services/api

# Run all chaos tests
pytest tests/chaos/ -v

# Run specific test class
pytest tests/chaos/test_chaos_recovery.py::TestAPIOutageChaos -v

# Run with coverage
pytest tests/chaos/ -v --cov=app/chaos --cov-report=html
```

### CI/CD Integration

Chaos tests run automatically on every deployment to staging:

```yaml
# .github/workflows/chaos-testing.yml
name: Chaos Testing
on:
  push:
    branches: [main]
jobs:
  chaos-tests:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/chaos/ -v
```

### Manual Trigger

Trigger chaos tests manually via GitHub Actions:

1. Go to **Actions** → **Chaos Testing**
2. Click **Run workflow**
3. Select:
   - **Environment:** staging or canary
   - **Chaos Type:** all, api_outage, high_latency, etc.
   - **Duration:** 5-30 minutes
4. Click **Run workflow**

### Scheduled Chaos

Automated chaos runs weekly:

- **Schedule:** Sundays at 2 AM UTC
- **Environment:** Staging
- **Duration:** 10 minutes
- **Chaos Types:** All

---

## Scheduled Chaos

### Weekly Chaos Runs

ApplyLens runs automated chaos tests weekly to continuously validate resilience:

**Schedule:**
- **Day:** Sunday
- **Time:** 2:00 AM UTC (low traffic)
- **Environment:** Staging
- **Duration:** 10 minutes

**What's tested:**
- API outages (Gmail, OpenAI)
- High latency (Elasticsearch, Database)
- Rate limiting
- Database errors
- Timeout handling

### Monitoring During Chaos

During chaos experiments, we monitor:

1. **Error Rate:** Should stay <2%
2. **P95 Latency:** Should stay within SLO (<1.5s)
3. **Recovery Time:** Should be <5 seconds
4. **SLO Compliance:** Error budget consumption

**Dashboards:**
- https://grafana.applylens.io/d/chaos-monitoring

### Alerts

Chaos tests trigger alerts if:

- **Error rate >5%:** Resilience insufficient
- **P95 latency >3x SLO:** Performance degradation too severe
- **Recovery time >30s:** Automatic recovery not working

**Notification Channels:**
- Slack #chaos-engineering
- GitHub Issues (auto-created)

---

## Interpreting Results

### Success Criteria

A chaos test passes if:

1. **Error rate stays within budget:** <2% errors
2. **SLO compliance maintained:** P95 latency <1.5s
3. **Automatic recovery works:** System recovers without manual intervention
4. **No cascading failures:** Failures don't propagate across services

### Chaos Metrics

After each chaos experiment, review metrics:

```python
metrics = chaos_injector.get_metrics()
print(chaos_injector.generate_report())
```

**Sample Report:**
```
Chaos Engineering Report
==================================================

Chaos Type: api_outage
  Duration: 0:10:00
  Injections: 25/100
  Success Rate: 25.0%
  Average Impact: 523.45ms
  Recovery Rate: 96.0%
  Recovery Attempts: 24/25

Chaos Type: high_latency
  Duration: 0:10:00
  Injections: 10/100
  Success Rate: 10.0%
  Average Impact: 1024.12ms
  Recovery Rate: 100.0%
  Recovery Attempts: 10/10
```

### Interpreting Metrics

| Metric | Good | Needs Improvement | Action Required |
|--------|------|-------------------|-----------------|
| Success Rate | Match probability | N/A | Fix injection logic |
| Recovery Rate | >95% | 80-95% | <80% - Fix resilience |
| Average Impact | <SLO target | 1-2x SLO | >2x SLO - Optimize |
| Error Rate | <2% | 2-5% | >5% - Add resilience |

---

## Best Practices

### 1. Start Small

- **Dev First:** Test in development environment
- **Low Probability:** Start with 10% failure rate
- **Short Duration:** 5-minute experiments initially
- **Single Chaos:** One failure type at a time

### 2. Increase Gradually

```python
# Week 1: Low probability
chaos_injector.inject(ChaosType.API_OUTAGE, probability=0.1)

# Week 2: Medium probability
chaos_injector.inject(ChaosType.API_OUTAGE, probability=0.3)

# Week 3: High probability
chaos_injector.inject(ChaosType.API_OUTAGE, probability=0.5)

# Week 4: Combined chaos
with chaos_injector.inject(ChaosType.API_OUTAGE, probability=0.2):
    with chaos_injector.inject(ChaosType.HIGH_LATENCY, delay_ms=500, probability=0.1):
        # Test combined failures
        pass
```

### 3. Always Disable After Tests

**CRITICAL:** Never leave chaos enabled in production!

```python
try:
    chaos_injector.enable_experiment_mode()
    # Run tests
finally:
    chaos_injector.disable_experiment_mode()
```

### 4. Use Hypothesis-Driven Testing

**Bad:**
```python
# Just inject failures and see what happens
chaos_injector.inject(ChaosType.API_OUTAGE)
```

**Good:**
```python
# Hypothesis: System should retry and recover
# Expected: Success rate >95% after retries
# Measured: Actual success rate vs expected
chaos_injector.inject(ChaosType.API_OUTAGE, probability=0.3)
assert success_rate >= 0.95, "Retry logic not working"
```

### 5. Monitor SLO Compliance

Always check SLO metrics during chaos:

```python
# Before chaos
baseline_error_rate = get_error_rate()
baseline_p95_latency = get_p95_latency()

# During chaos
with chaos_injector.inject(ChaosType.API_OUTAGE, probability=0.2):
    run_load_test()

# After chaos
final_error_rate = get_error_rate()
final_p95_latency = get_p95_latency()

# Validate SLO compliance
assert final_error_rate < 0.02, "Error rate exceeds SLO"
assert final_p95_latency < 1.5, "Latency exceeds SLO"
```

### 6. Document Learnings

After each chaos experiment:

1. **What broke?** Document failure modes discovered
2. **Why?** Root cause analysis
3. **How to fix?** Implement resilience patterns
4. **Validation:** Re-run chaos to confirm fix

**Template:**
```markdown
## Chaos Experiment: API Outage - 2025-10-17

### Hypothesis
Gmail API outages should be handled gracefully with <5% error rate.

### Result
❌ Error rate reached 15% during chaos injection.

### Root Cause
No retry logic for Gmail API calls.

### Fix
Implemented exponential backoff with 3 retries.

### Validation
Re-ran chaos test: Error rate now 2% ✅
```

---

## Troubleshooting

### Chaos Not Injecting

**Problem:** Chaos injection not happening

**Solutions:**
```python
# 1. Verify chaos is enabled
assert chaos_injector.is_enabled(), "Chaos not enabled"

# 2. Check probability
chaos_injector.inject(ChaosType.API_OUTAGE, probability=1.0)  # 100%

# 3. Enable experiment mode
chaos_injector.enable_experiment_mode()
```

### Tests Failing

**Problem:** Chaos tests consistently failing

**Solutions:**
1. **Increase error budget:** Adjust SLO targets if too strict
2. **Implement resilience:** Add retry logic, circuit breakers
3. **Reduce blast radius:** Lower chaos probability
4. **Add fallbacks:** Implement degraded mode

### SLO Violations

**Problem:** SLOs violated during chaos

**Expected:** Some SLO degradation is normal during chaos

**Action Required if:**
- Error rate >5%: Add resilience (retry, circuit breaker)
- P95 latency >2x SLO: Optimize performance or add timeout
- Recovery time >30s: Improve automatic recovery

---

## Related Documentation

- [Production Handbook](../PRODUCTION_HANDBOOK.md)
- [SLA Overview](../SLA_OVERVIEW.md)
- [Incident Playbooks](../playbooks/)
- [On-Call Handbook](../ONCALL_HANDBOOK.md)

---

## Resources

### Internal
- **Chaos Dashboard:** https://grafana.applylens.io/d/chaos-monitoring
- **Chaos Test Results:** GitHub Actions artifacts
- **Slack Channel:** #chaos-engineering

### External
- [Principles of Chaos Engineering](https://principlesofchaos.org/)
- [Chaos Engineering Book](https://www.oreilly.com/library/view/chaos-engineering/9781491988459/)
- [Netflix Chaos Monkey](https://netflix.github.io/chaosmonkey/)

---

**Document Ownership:** SRE Team  
**Review Frequency:** Quarterly  
**Last Review:** October 17, 2025  
**Next Review:** January 17, 2026
