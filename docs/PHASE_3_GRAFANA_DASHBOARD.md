# Phase 3 — Grafana Dashboard (JSON Import)

> Import this JSON into Grafana (Dashboards → Import) to get the 3 required demo panels wired to your API. It uses a **JSON API** data source named `ApplyLens API`.

## Prerequisites

1. **Install Grafana Plugin:**
   ```bash
   grafana-cli plugins install marcusolsson-json-datasource
   ```
   Or install via Grafana UI: Configuration → Plugins → JSON API

2. **Add Data Source:**
   - Go to: Configuration → Data Sources → Add data source
   - Search for: "JSON API"
   - Configure:
     - **Name:** `ApplyLens API`
     - **URL:** `https://applylens.app` (or `http://localhost:8003` for local dev)
     - **Allowed cookies:** (if needed for auth)
     - **Custom HTTP Headers:** (if needed for auth)
   - Save & Test

## Panels Included

1. **Warehouse Divergence (24h)** - Real-time health stat with color thresholds
2. **Activity by Day** - Time series bar chart of email volume
3. **Top Senders (30d)** - Table of most frequent senders
4. **Categories (30d)** - Horizontal bar chart of email categories

## Dashboard JSON

```json
{
  "id": null,
  "uid": "applylens-overview",
  "title": "ApplyLens Overview",
  "tags": ["applylens", "demo"],
  "timezone": "browser",
  "schemaVersion": 38,
  "version": 1,
  "refresh": "30s",
  "time": { "from": "now-30d", "to": "now" },
  "templating": {
    "list": [
      {
        "name": "api_base",
        "type": "textbox",
        "label": "API Base",
        "query": "https://applylens.app",
        "current": { 
          "text": "https://applylens.app", 
          "value": "https://applylens.app" 
        },
        "options": []
      }
    ]
  },
  "panels": [
    {
      "type": "stat",
      "title": "Warehouse Divergence (24h)",
      "gridPos": { "x": 0, "y": 0, "w": 8, "h": 4 },
      "datasource": { 
        "type": "marcusolsson-json-datasource", 
        "uid": "ApplyLens_API" 
      },
      "targets": [
        {
          "refId": "A",
          "url": "${api_base}/api/metrics/divergence-24h",
          "method": "GET",
          "format": "json",
          "cacheDurationSeconds": 15,
          "headers": [],
          "jsonPath": "$.divergence_pct"
        }
      ],
      "options": {
        "reduceOptions": { 
          "calcs": ["lastNotNull"], 
          "fields": "", 
          "values": false 
        },
        "colorMode": "value",
        "textMode": "auto",
        "graphMode": "none",
        "justifyMode": "auto"
      },
      "fieldConfig": {
        "defaults": {
          "unit": "percent",
          "decimals": 2,
          "thresholds": { 
            "mode": "absolute", 
            "steps": [
              { "color": "green", "value": null },
              { "color": "yellow", "value": 2 },
              { "color": "red", "value": 5 }
            ]
          }
        },
        "overrides": []
      }
    },
    {
      "type": "timeseries",
      "title": "Activity by Day",
      "gridPos": { "x": 0, "y": 4, "w": 24, "h": 8 },
      "datasource": { 
        "type": "marcusolsson-json-datasource", 
        "uid": "ApplyLens_API" 
      },
      "targets": [
        {
          "refId": "A",
          "url": "${api_base}/api/metrics/activity-daily",
          "method": "GET",
          "format": "json",
          "cacheDurationSeconds": 30,
          "headers": []
        }
      ],
      "fieldConfig": {
        "defaults": {
          "custom": { 
            "drawStyle": "bars",
            "barAlignment": 0,
            "fillOpacity": 80,
            "gradientMode": "none",
            "lineInterpolation": "linear",
            "lineWidth": 1,
            "pointSize": 5,
            "showPoints": "never",
            "spanNulls": false
          },
          "unit": "none",
          "color": { "mode": "palette-classic" }
        },
        "overrides": []
      },
      "options": {
        "legend": { 
          "displayMode": "hidden",
          "placement": "bottom",
          "showLegend": false
        },
        "tooltip": { 
          "mode": "single",
          "sort": "none"
        }
      },
      "transformations": [
        {
          "id": "organize",
          "options": {
            "excludeByName": {},
            "indexByName": {},
            "renameByName": {
              "date": "Date",
              "message_count": "Messages"
            }
          }
        },
        {
          "id": "convertFieldType",
          "options": {
            "conversions": [
              {
                "destinationType": "time",
                "targetField": "date"
              }
            ],
            "fields": {}
          }
        }
      ]
    },
    {
      "type": "table",
      "title": "Top Senders (30d)",
      "gridPos": { "x": 0, "y": 12, "w": 12, "h": 8 },
      "datasource": { 
        "type": "marcusolsson-json-datasource", 
        "uid": "ApplyLens_API" 
      },
      "targets": [
        {
          "refId": "A",
          "url": "${api_base}/api/metrics/top-senders-30d?limit=10",
          "method": "GET",
          "format": "json",
          "cacheDurationSeconds": 30,
          "headers": []
        }
      ],
      "options": {
        "showHeader": true,
        "cellHeight": "sm",
        "footer": {
          "show": false,
          "reducer": ["sum"],
          "fields": ""
        }
      },
      "fieldConfig": {
        "defaults": {
          "custom": {
            "align": "auto",
            "displayMode": "auto"
          }
        },
        "overrides": [
          {
            "matcher": { "id": "byName", "options": "messages" },
            "properties": [
              {
                "id": "custom.displayMode",
                "value": "color-background"
              },
              {
                "id": "custom.align",
                "value": "right"
              }
            ]
          }
        ]
      },
      "transformations": [
        {
          "id": "organize",
          "options": {
            "excludeByName": {},
            "indexByName": {
              "sender": 0,
              "messages": 1
            },
            "renameByName": {
              "sender": "Sender",
              "messages": "Messages"
            }
          }
        }
      ]
    },
    {
      "type": "barchart",
      "title": "Categories (30d)",
      "gridPos": { "x": 12, "y": 12, "w": 12, "h": 8 },
      "datasource": { 
        "type": "marcusolsson-json-datasource", 
        "uid": "ApplyLens_API" 
      },
      "targets": [
        {
          "refId": "A",
          "url": "${api_base}/api/metrics/categories-30d",
          "method": "GET",
          "format": "json",
          "cacheDurationSeconds": 30,
          "headers": []
        }
      ],
      "options": {
        "legend": { 
          "displayMode": "hidden",
          "placement": "bottom",
          "showLegend": false
        },
        "tooltip": { 
          "mode": "single",
          "sort": "none"
        },
        "orientation": "horizontal",
        "xTickLabelRotation": 0,
        "xTickLabelSpacing": 100,
        "barWidth": 0.97,
        "barRadius": 0,
        "groupWidth": 0.7,
        "showValue": "never"
      },
      "fieldConfig": {
        "defaults": {
          "unit": "none",
          "color": { "mode": "palette-classic" },
          "custom": {
            "axisPlacement": "auto",
            "axisLabel": "",
            "scaleDistribution": { "type": "linear" }
          }
        },
        "overrides": []
      },
      "transformations": [
        {
          "id": "organize",
          "options": {
            "excludeByName": {},
            "indexByName": {
              "category": 0,
              "messages": 1
            },
            "renameByName": {
              "category": "Category",
              "messages": "Messages"
            }
          }
        }
      ]
    }
  ]
}
```

## Import Instructions

1. **Open Grafana** and navigate to: Dashboards → Import
2. **Paste the JSON** above into the "Import via panel json" text area
3. **Configure:**
   - Select data source: `ApplyLens API`
   - Change UID if needed
4. **Import**
5. **Test:** Dashboard should load with 4 panels showing data from your API

## Local Development

For local development, update the `api_base` variable:

1. Click the gear icon (⚙️) in top right
2. Go to: Variables → api_base
3. Change value to: `http://localhost:8003`
4. Save dashboard

## Troubleshooting

**No data showing:**
- Check data source is correctly configured
- Verify API is running and accessible
- Check browser console for CORS errors
- Test endpoints directly: `curl http://localhost:8003/api/metrics/divergence-24h`

**Plugin not found:**
- Install plugin: `grafana-cli plugins install marcusolsson-json-datasource`
- Restart Grafana after installation
- Or use Grafana UI: Configuration → Plugins → search "JSON API"

**Permission errors:**
- Check Grafana user has permission to install plugins
- May need to run Grafana CLI with sudo/admin privileges
- Check Grafana logs for detailed error messages

## Screenshots for Demo

Capture these views for your hackathon demo:

1. **Full dashboard** - All 4 panels visible
2. **Divergence stat** - Close-up showing green/yellow/red status
3. **Activity chart** - Time series with visible trend
4. **Top senders table** - Showing realistic email senders
5. **Categories chart** - Horizontal bar chart with categories

## Alternative: Infinity Data Source

If you can't install the JSON API plugin, use the built-in **Infinity** data source instead:

1. Add Infinity data source (built-in, no install needed)
2. For each panel, change data source to "Infinity"
3. Update query type to "JSON"
4. Use same URLs as above

The dashboard will work identically with Infinity.
