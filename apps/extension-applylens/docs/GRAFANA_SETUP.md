# Grafana Dashboard Setup

## Overview

This directory contains a pre-configured Grafana dashboard for monitoring ApplyLens Companion/Autofill metrics.

## Dashboard Metrics

The dashboard visualizes the following Prometheus metrics:

- `applylens_autofill_agg_runs_total` - Aggregator runs by status
- `applylens_autofill_profiles_updated_total` - Total profiles updated
- `applylens_autofill_runs_total` - Autofill runs by status
- `applylens_autofill_time_ms_bucket` - Autofill time distribution (histogram)
- `applylens_autofill_profiles_rejected_total` - Profiles rejected by quality guards (optional)

## Dashboard Panels

1. **Aggregator Runs by Status** - Time series showing aggregator execution rates
2. **Profiles Updated (Last 24h)** - Single stat showing profile update count
3. **Autofill Runs by Status** - Time series showing autofill execution rates
4. **Autofill Success Ratio (Last 1h)** - Success percentage with color thresholds
5. **Autofill Time to Fill (p50/p90)** - Performance percentiles
6. **Profiles Rejected by Quality Guards** - Rate of quality guard rejections

## Installation Steps

1. **Find your Prometheus datasource UID:**
   - In Grafana, go to Configuration → Data Sources
   - Click on your Prometheus datasource
   - Copy the UID from the URL (e.g., `P1809F7CD0C75ACF3`)

2. **Update the dashboard JSON:**
   ```bash
   # Replace YOUR_PROM_DS_UID with your actual UID
   sed -i 's/YOUR_PROM_DS_UID/P1809F7CD0C75ACF3/g' grafana-companion-autofill.json
   ```

   Or manually edit `grafana-companion-autofill.json` and replace all instances of `YOUR_PROM_DS_UID`.

3. **Import the dashboard:**
   - In Grafana, go to Dashboards → Import
   - Click "Upload JSON file"
   - Select `grafana-companion-autofill.json`
   - Click "Load" then "Import"

## Configuration

### Refresh Interval
Default: 30 seconds. Adjust in dashboard settings if needed.

### Time Range
Default: Last 6 hours. Use the time picker to adjust.

### Thresholds
Success ratio color coding:
- Red: < 80%
- Yellow: 80-95%
- Green: ≥ 95%

Adjust thresholds in panel settings if your requirements differ.

## Quality Guard Metrics

The "Profiles Rejected by Quality Guards" panel requires the optional metric `applylens_autofill_profiles_rejected_total`. This tracks when profiles are rejected due to:
- `success_rate < 0.6`
- `avg_edit_chars > 500`

If this metric is not implemented, the panel will show "No data" but won't affect other panels.

## Troubleshooting

**No data showing:**
- Verify Prometheus datasource is accessible
- Check that metrics are being scraped (query Prometheus directly)
- Ensure time range includes data

**Some panels empty:**
- Verify all expected metrics are being emitted
- Check PromQL queries in panel settings
- Review Prometheus scrape config

**Performance issues:**
- Increase scrape interval if too frequent
- Reduce dashboard refresh rate
- Optimize PromQL queries (increase rate intervals)
