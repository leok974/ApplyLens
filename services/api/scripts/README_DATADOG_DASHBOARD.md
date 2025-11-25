# Datadog Dashboard Creation Script

This script programmatically creates the **"ApplyLens Observability Copilot – Hackathon"** dashboard using the Datadog API.

## Prerequisites

1. **Datadog API Key** (`DD_API_KEY`)
2. **Datadog Application Key** (`DD_APP_KEY`)
3. **Datadog Site** (`DD_SITE`)

### Getting Your Keys

1. **API Key**:
   - Go to: https://app.datadoghq.com/organization-settings/api-keys
   - Copy your existing API key (or create a new one)

2. **Application Key**:
   - Go to: https://app.datadoghq.com/organization-settings/application-keys
   - Click "New Key"
   - Name: "ApplyLens Hackathon Dashboard Creator"
   - Copy the key (save it securely - you won't see it again!)

3. **Site**:
   - Your site URL (e.g., `us5.datadoghq.com`, `datadoghq.com`, `datadoghq.eu`)

## Installation

Install the Datadog API client:

```bash
pip install datadog-api-client
```

## Usage

### Option 1: Environment Variables

```bash
export DD_API_KEY=your_api_key_here
export DD_APP_KEY=your_app_key_here
export DD_SITE=us5.datadoghq.com

python scripts/create_datadog_dashboard.py
```

### Option 2: Inline (one-liner)

```bash
DD_API_KEY=xxx DD_APP_KEY=yyy DD_SITE=us5.datadoghq.com python scripts/create_datadog_dashboard.py
```

### Option 3: From Docker Container

```bash
docker exec -e DD_API_KEY=xxx -e DD_APP_KEY=yyy -e DD_SITE=us5.datadoghq.com \
  applylens-api-prod python scripts/create_datadog_dashboard.py
```

## What Gets Created

The script creates a dashboard with **4 sections** and **12+ widgets**:

### 🤖 LLM Health
- **Widget 1**: LLM Classification Latency (p50/p95/p99)
- **Widget 2**: LLM Error Rate (%)
- **Widget 3**: Token Usage (per 5min)
- **Widget 4**: Cost Estimate (USD/hour)
- **Widget 5**: Task Type Breakdown (classify vs extract)

### 📥 Ingest Freshness (Optional)
- **Widget 6**: Email Ingest Lag (seconds)
- **Widget 7**: % Within Ingest SLO (<5min)

### 🛡️ Security Signals (Optional)
- **Widget 8**: High-Risk Detection Rate
- **Widget 9**: Quarantine Actions (last 24h)

### 🏗️ Infrastructure
- **Widget 10**: API Request Duration (p95)
- **Widget 11**: API Error Count
- **Widget 12**: API Uptime %

## Output

On success, the script will:

1. **Print the dashboard URL**:
   ```
   ✅ Dashboard Created Successfully!
   📊 Dashboard URL: https://us5.datadoghq.com/dashboard/abc-123-def
   ```

2. **Save dashboard info** to `datadog_dashboard_info.json`:
   ```json
   {
     "dashboard_id": "abc-123-def",
     "dashboard_url": "https://us5.datadoghq.com/dashboard/abc-123-def",
     "title": "ApplyLens Observability Copilot – Hackathon",
     "created_at": "2025-11-25T13:30:00Z"
   }
   ```

## Next Steps

After creating the dashboard:

1. **View the dashboard** in Datadog UI
2. **Create SLOs** (see `hackathon/DATADOG_SETUP.md` Section 2)
3. **Add SLO widgets** to the top of the dashboard
4. **Configure monitors** (see `hackathon/DATADOG_SETUP.md` Section 3)
5. **Run traffic generator** to populate metrics:
   ```bash
   python scripts/traffic_generator.py --mode normal_traffic --rate 1.0 --duration 900
   ```

## Troubleshooting

### Error: "Missing required environment variables"
- Make sure you've exported `DD_API_KEY`, `DD_APP_KEY`, and `DD_SITE`

### Error: "Authentication failed"
- Verify your API key is correct
- Check your Application key has `dashboards_write` permission
- Confirm `DD_SITE` matches your account region

### Error: "Module not found: datadog_api_client"
- Install the client: `pip install datadog-api-client`

### Widgets showing "No data"
- Run the traffic generator to populate metrics
- Or use the test metrics script: `python scripts/test-datadog-metrics.py`
- Wait 30-60 seconds for metrics to appear in Datadog

## Customization

To modify the dashboard:

1. **Edit widget queries**: Update the metric queries in each `create_*_widget()` function
2. **Change layout**: Modify `WidgetLayout(x=, y=, width=, height=)` parameters
3. **Add new widgets**: Create new widget functions and add to the `widgets` list
4. **Adjust thresholds**: Update marker values (e.g., SLO targets)

## Reference

- **Datadog Dashboards API**: https://docs.datadoghq.com/api/latest/dashboards/
- **Widget Types**: https://docs.datadoghq.com/dashboards/widgets/
- **Dashboard Spec**: See `hackathon/DATADOG_SETUP.md` for detailed widget specifications
