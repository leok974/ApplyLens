# Intelligence Report Guide

This guide explains how to generate, deliver, and interpret weekly intelligence reports for agent evaluation.

## Table of Contents

- [Overview](#overview)
- [Generating Reports](#generating-reports)
- [Slack Integration](#slack-integration)
- [Email Delivery](#email-delivery)
- [Reading Reports](#reading-reports)
- [Trend Analysis](#trend-analysis)
- [Acting on Recommendations](#acting-on-recommendations)

## Overview

Intelligence reports provide weekly summaries of agent performance, highlighting trends, anomalies, and actionable recommendations.

### What's Included

Each report contains:
- **Executive Summary**: High-level overview (pass/fail, key metrics)
- **Agent Performance**: Per-agent quality, latency, success rate
- **Trend Analysis**: Week-over-week changes and forecasts
- **Top Issues**: Most common failures, violations, and errors
- **Recommendations**: Prioritized action items
- **Red Team Results**: Security testing outcomes

### Report Schedule

- **Generated**: Every Monday at 9 AM
- **Lookback**: Previous 7 days (Monday-Sunday)
- **Delivery**: Slack + Email
- **Retention**: 90 days in database

## Generating Reports

### Automatic Generation

Reports are generated automatically via cron/scheduler:

```bash
# Add to crontab
0 9 * * 1 cd /app/services/api && python -m app.eval.generate_report

# Or use systemd timer (Linux)
# /etc/systemd/system/intelligence-report.timer
[Unit]
Description=Weekly Intelligence Report

[Timer]
OnCalendar=Mon *-*-* 09:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

### Manual Generation

Generate reports on-demand:

```bash
# Generate for current week
python -m app.eval.generate_report

# Generate for specific date range
python -m app.eval.generate_report --start-date 2025-10-10 --end-date 2025-10-17

# Generate for specific agents
python -m app.eval.generate_report --agents inbox_triage,insights_writer

# Export to file
python -m app.eval.generate_report --output report.html

# Skip delivery (just generate, don't send)
python -m app.eval.generate_report --no-delivery
```

### Using Python API

```python
from app.eval.intelligence_report import IntelligenceReportGenerator
from app.db import SessionLocal
from datetime import datetime, timedelta

db = SessionLocal()
generator = IntelligenceReportGenerator(db)

# Generate report for last week
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

report = generator.generate_report(
    start_date=start_date,
    end_date=end_date,
    agent_ids=None  # All agents
)

# Access report data
print(f"Report Period: {report.period_start} to {report.period_end}")
print(f"Overall Status: {report.overall_status}")  # "pass" or "fail"
print(f"Agents Evaluated: {len(report.agent_summaries)}")

for summary in report.agent_summaries:
    print(f"\n{summary.agent_id}:")
    print(f"  Quality: {summary.quality_score:.1f}")
    print(f"  Trend: {summary.quality_trend}")  # "improving", "stable", "declining"
    print(f"  Gate Status: {summary.gate_status}")  # "pass" or "fail"
```

### Report Output Formats

#### HTML (Default)

Rich, formatted reports with charts and styling:

```python
html_report = generator.generate_html_report(report)
# Returns HTML string ready for email/web display
```

#### JSON

Machine-readable format for APIs:

```python
json_report = generator.generate_json_report(report)
# Returns dict that can be serialized to JSON
```

#### Markdown

Plain text format for Slack:

```python
md_report = generator.generate_markdown_report(report)
# Returns Markdown string for Slack messages
```

## Slack Integration

Send reports to Slack channels.

### Setup

1. **Create Slack App**:
   - Go to https://api.slack.com/apps
   - Create new app
   - Add `chat:write` permission
   - Install to workspace
   - Copy Bot Token

2. **Configure Environment**:

```bash
# .env
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_CHANNEL_INTELLIGENCE=#agent-intelligence
SLACK_CHANNEL_ALERTS=#agent-alerts  # For critical issues
```

3. **Test Connection**:

```python
from app.eval.intelligence_report import SlackDelivery
from app.config import settings

slack = SlackDelivery(
    token=settings.SLACK_BOT_TOKEN,
    channel=settings.SLACK_CHANNEL_INTELLIGENCE
)

# Test message
slack.send_test_message()
```

### Sending Reports

```python
from app.eval.intelligence_report import IntelligenceReportGenerator, SlackDelivery

generator = IntelligenceReportGenerator(db)
slack = SlackDelivery(token=..., channel=...)

# Generate and send
report = generator.generate_report(...)
slack.send_report(report)
```

### Slack Message Format

Reports are sent as:
1. **Main message**: Executive summary with overall status
2. **Thread replies**: Detailed per-agent breakdowns
3. **Attachments**: Charts (if enabled)

Example Slack message:

```
📊 **Weekly Intelligence Report**
Period: Oct 10 - Oct 17, 2025

**Overall Status**: ⚠️  NEEDS ATTENTION (2/4 agents passing)

**Summary**:
✅ inbox_triage: Quality 92.3 (+2.1) 
❌ insights_writer: Quality 81.5 (-3.2) - BELOW BUDGET
✅ knowledge_update: Quality 87.8 (+0.5)
❌ warehouse: Quality 78.2 (-5.1) - DECLINING TREND

**Top Issues**:
1. insights_writer: High latency (p95 = 3200ms)
2. warehouse: Invariant violations (PII leaks)
3. All agents: Red team detection rate = 82%

**Actions Required**:
🔴 CRITICAL: Fix PII leaks in warehouse agent
🟡 WARNING: Optimize insights_writer latency
🟡 WARNING: Improve red team defenses

Full report: http://dashboard/reports/2025-w42
```

### Customizing Slack Messages

```python
class CustomSlackDelivery(SlackDelivery):
    """Custom Slack formatting."""
    
    def format_message(self, report):
        """Override to customize message format."""
        
        # Use emojis for visual appeal
        status_emoji = "✅" if report.overall_status == "pass" else "❌"
        
        # Highlight critical issues
        critical_issues = [
            issue for issue in report.top_issues 
            if issue.severity == "critical"
        ]
        
        message = f"{status_emoji} **Weekly Report**\n"
        message += f"Period: {report.period_start} - {report.period_end}\n\n"
        
        if critical_issues:
            message += "🚨 **CRITICAL ISSUES**:\n"
            for issue in critical_issues:
                message += f"  • {issue.description}\n"
            message += "\n"
        
        # Add agent summaries
        for summary in report.agent_summaries:
            status = "✅" if summary.gate_status == "pass" else "❌"
            trend = self._trend_emoji(summary.quality_trend)
            message += f"{status} {summary.agent_id}: {summary.quality_score:.1f} {trend}\n"
        
        return message
    
    def _trend_emoji(self, trend):
        return {"improving": "📈", "stable": "➡️", "declining": "📉"}.get(trend, "❓")
```

## Email Delivery

Send reports via email.

### Setup

```bash
# .env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@company.com
EMAIL_TO=team@company.com,manager@company.com
```

### Sending Email Reports

```python
from app.eval.intelligence_report import EmailDelivery

email = EmailDelivery(
    smtp_host=settings.SMTP_HOST,
    smtp_port=settings.SMTP_PORT,
    username=settings.SMTP_USER,
    password=settings.SMTP_PASSWORD,
    from_email=settings.EMAIL_FROM
)

# Generate HTML report
html_report = generator.generate_html_report(report)

# Send
email.send_report(
    to=settings.EMAIL_TO.split(','),
    subject=f"Agent Intelligence Report - Week {report.week_number}",
    html_body=html_report
)
```

### Email Template Customization

```python
# templates/intelligence_report.html

<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; }
        .pass { color: green; }
        .fail { color: red; }
        .warning { color: orange; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
    </style>
</head>
<body>
    <h1>Agent Intelligence Report</h1>
    <p><strong>Period:</strong> {{ report.period_start }} to {{ report.period_end }}</p>
    
    <h2>Overall Status: <span class="{{ report.overall_status }}">{{ report.overall_status.upper() }}</span></h2>
    
    <h3>Agent Performance</h3>
    <table>
        <tr>
            <th>Agent</th>
            <th>Quality</th>
            <th>Trend</th>
            <th>Status</th>
        </tr>
        {% for summary in report.agent_summaries %}
        <tr>
            <td>{{ summary.agent_id }}</td>
            <td>{{ summary.quality_score }}</td>
            <td>{{ summary.quality_trend }}</td>
            <td class="{{ summary.gate_status }}">{{ summary.gate_status }}</td>
        </tr>
        {% endfor %}
    </table>
    
    <!-- Add more sections: charts, issues, recommendations -->
</body>
</html>
```

## Reading Reports

### Executive Summary

The top section provides at-a-glance status:

```
Overall Status: PASS ✅  (3/4 agents passing gates)
Period: Oct 10-17, 2025
Total Executions: 12,450
Avg Quality: 87.3 (+1.2 from last week)
```

**Interpretation:**
- **PASS**: All critical agents meeting budgets
- **NEEDS ATTENTION**: Some agents below budget or declining
- **FAIL**: Multiple critical agents failing

### Agent Performance Table

Detailed per-agent metrics:

| Agent | Quality | Δ | Latency (p95) | Success Rate | Gate Status |
|-------|---------|---|---------------|--------------|-------------|
| inbox_triage | 92.3 | +2.1 | 1,250ms | 98.5% | ✅ PASS |
| insights_writer | 81.5 | -3.2 | 3,200ms | 95.1% | ❌ FAIL |
| knowledge_update | 87.8 | +0.5 | 1,800ms | 97.2% | ✅ PASS |
| warehouse | 78.2 | -5.1 | 2,100ms | 92.3% | ❌ FAIL |

**Key Columns:**
- **Quality**: Overall quality score (0-100)
- **Δ**: Change from last week (+/- indicates direction)
- **Latency (p95)**: 95th percentile latency
- **Success Rate**: % of executions without errors
- **Gate Status**: Pass/fail based on budgets

### Trend Indicators

Understand quality trajectories:

- **📈 Improving**: Quality increased ≥ 2 points
- **➡️ Stable**: Quality changed < 2 points
- **📉 Declining**: Quality decreased ≥ 2 points

### Top Issues

Most impactful problems ranked by severity:

```
1. 🔴 CRITICAL: PII leak detected in warehouse agent (15 violations)
   Impact: Data privacy violation, compliance risk
   Action: Deploy PII sanitization filter immediately

2. 🟡 WARNING: insights_writer latency exceeds budget (3200ms vs 2000ms)
   Impact: Slow user experience, timeout risk
   Action: Profile and optimize database queries

3. 🟡 WARNING: Red team detection rate = 82% (target: 95%)
   Impact: Security vulnerability
   Action: Add prompt injection invariants
```

### Recommendations

Prioritized action items:

```
IMMEDIATE (This Week):
1. Fix PII leak in warehouse agent
2. Add integration test for PII detection
3. Deploy to production

SHORT-TERM (Next 2 Weeks):
1. Optimize insights_writer database queries
2. Add caching layer for common queries
3. Increase latency budget to 2500ms temporarily

LONG-TERM (Next Month):
1. Improve red team defenses across all agents
2. Retrain ML models with recent data
3. Conduct manual security audit
```

## Trend Analysis

### Week-over-Week Comparison

Track how metrics change:

```python
# In report
for summary in report.agent_summaries:
    print(f"{summary.agent_id}:")
    print(f"  Quality: {summary.quality_score:.1f} ({summary.quality_delta:+.1f})")
    print(f"  Latency: {summary.latency_p95}ms ({summary.latency_delta:+d}ms)")
    print(f"  Success Rate: {summary.success_rate:.1%} ({summary.success_rate_delta:+.1%})")
```

### Forecasting

Project future performance:

```python
from app.eval.intelligence_report import TrendAnalyzer

analyzer = TrendAnalyzer(db)

# Get 30-day forecast
forecast = analyzer.forecast_quality(
    agent_id="inbox_triage",
    days_ahead=30
)

print(f"Current Quality: {forecast.current:.1f}")
print(f"Projected (30d): {forecast.projected:.1f}")
print(f"Confidence: {forecast.confidence:.1%}")

if forecast.projected < 85:
    print("⚠️  Quality projected to fall below budget!")
```

### Anomaly Detection

Identify unusual patterns:

```python
anomalies = analyzer.detect_anomalies(
    agent_id="inbox_triage",
    lookback_days=30
)

for anomaly in anomalies:
    print(f"Anomaly on {anomaly.date}:")
    print(f"  Metric: {anomaly.metric}")
    print(f"  Expected: {anomaly.expected:.1f}")
    print(f"  Actual: {anomaly.actual:.1f}")
    print(f"  Deviation: {anomaly.std_devs:.1f} std devs")
```

### Correlation Analysis

Find relationships between metrics:

```python
# Does latency correlate with quality?
correlation = analyzer.analyze_correlation(
    agent_id="inbox_triage",
    metric_x="latency_p95",
    metric_y="quality_score",
    lookback_days=90
)

print(f"Correlation: {correlation.coefficient:.2f}")
print(f"Interpretation: {correlation.strength}")  # "strong", "moderate", "weak", "none"

if correlation.coefficient < -0.5:
    print("⚠️  High latency associated with lower quality!")
```

## Acting on Recommendations

### Priority Framework

Recommendations are prioritized using:

1. **Severity**: Critical > Warning > Info
2. **Impact**: User-facing > Internal > Nice-to-have
3. **Effort**: Quick wins > Medium effort > Large projects

### Example Workflow

When you receive a report:

#### 1. Review Critical Issues (Within 1 hour)

```bash
# Filter for critical issues
cat report.json | jq '.top_issues[] | select(.severity == "critical")'

# Create tickets
for issue in critical_issues:
    create_ticket(
        title=f"[CRITICAL] {issue.description}",
        priority="P0",
        assignee="on-call-engineer"
    )
```

#### 2. Triage Warnings (Same day)

```bash
# Review warnings
cat report.json | jq '.top_issues[] | select(.severity == "warning")'

# Assign to team members
for issue in warnings:
    if issue.category == "performance":
        assign_to("performance-team")
    elif issue.category == "quality":
        assign_to("ml-team")
```

#### 3. Plan Long-term Improvements (Weekly planning)

```bash
# Extract recommendations
cat report.json | jq '.recommendations[] | select(.timeframe == "long-term")'

# Add to backlog
for rec in long_term_recommendations:
    add_to_backlog(
        title=rec.title,
        description=rec.description,
        effort=rec.estimated_effort
    )
```

### Tracking Progress

Monitor how recommendations are addressed:

```python
# In next week's report
from app.eval.intelligence_report import RecommendationTracker

tracker = RecommendationTracker(db)

# Mark recommendation as completed
tracker.mark_completed(
    recommendation_id="rec_123",
    completed_date=datetime.now(),
    notes="Deployed PII filter v2.1"
)

# Check progress
progress = tracker.get_progress(weeks=4)
print(f"Recommendations Completed: {progress.completed}/{progress.total}")
print(f"Completion Rate: {progress.completion_rate:.1%}")
```

### Validating Fixes

After implementing recommendations, verify impact:

```python
# Compare before/after metrics
before = db.query(AgentMetricsDaily).filter(
    AgentMetricsDaily.date == date_before_fix
).first()

after = db.query(AgentMetricsDaily).filter(
    AgentMetricsDaily.date == date_after_fix
).first()

improvement = {
    "quality": after.quality_score - before.quality_score,
    "latency": before.latency_p95 - after.latency_p95,  # Lower is better
    "violations": before.invariant_violations - after.invariant_violations
}

print(f"Quality improved by {improvement['quality']:.1f} points")
print(f"Latency reduced by {improvement['latency']}ms")
print(f"Violations reduced by {improvement['violations']}")
```

## Best Practices

### 1. Read Reports Consistently

Establish a team ritual:
- **Monday 10 AM**: Review report in team standup
- **Assign action items**: Each critical issue gets an owner
- **Set deadlines**: Critical = 24h, Warning = 1 week
- **Follow up**: Check progress in next week's report

### 2. Customize for Your Team

Adjust report content based on audience:

```python
# Executive report (high-level)
exec_report = generator.generate_report(
    detail_level="executive",  # Summary only
    include_charts=True,
    include_technical_details=False
)

# Engineering report (detailed)
eng_report = generator.generate_report(
    detail_level="detailed",
    include_charts=True,
    include_technical_details=True,
    include_code_examples=True
)
```

### 3. Set Up Alerts for Critical Issues

Don't wait for weekly report if something breaks:

```python
# In report generation
if report.has_critical_issues():
    send_immediate_alert(
        channel="#agent-alerts",
        message=f"🚨 CRITICAL: {report.critical_issue_summary()}",
        mention=["@oncall", "@team-lead"]
    )
```

### 4. Archive and Compare Historical Reports

Track long-term trends:

```bash
# Archive reports
mkdir -p reports/archive
mv report_$(date +%Y-w%V).html reports/archive/

# Compare with historical data
python -m app.eval.intelligence_report --compare-weeks 1,4,12
```

### 5. Use Reports in Retrospectives

Review quarterly:
- Which agents improved the most?
- Which recommendations had biggest impact?
- What patterns emerged?
- What should we focus on next quarter?

## Next Steps

- See [EVAL_GUIDE.md](./EVAL_GUIDE.md) for evaluation fundamentals
- See [BUDGETS_AND_GATES.md](./BUDGETS_AND_GATES.md) for setting budgets
- See [DASHBOARD_ALERTS.md](./DASHBOARD_ALERTS.md) for real-time monitoring
- See [REDTEAM.md](./REDTEAM.md) for security testing
