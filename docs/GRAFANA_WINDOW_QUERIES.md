# Grafana Queries for Window Days Analysis

This document provides PromQL queries for monitoring assistant tool usage with window_days tracking.

## Assistant Tool Queries by Window Bucket

### Query Rate by Window Bucket and Hit Status

Track how often users are finding results in different time windows:

```promql
sum(rate(assistant_tool_queries_total{tool="summarize"}[5m])) by (window_bucket, has_hits)
```

**Use case**: Identify if users are mostly searching recent emails (7d, 30d) or need historical data (60d, 90+)

### Total Queries by Tool and Window

```promql
sum(assistant_tool_queries_total) by (tool, window_bucket)
```

**Use case**: Compare tool usage across different time windows

### Hit Rate by Window Bucket

Percentage of queries that return results:

```promql
sum(rate(assistant_tool_queries_total{has_hits="1"}[5m])) by (window_bucket) 
/ 
sum(rate(assistant_tool_queries_total[5m])) by (window_bucket) * 100
```

**Use case**: Understand if longer time windows improve hit rates

### Most Common Window Selection

```promql
topk(1, sum(increase(assistant_tool_queries_total[1h])) by (window_bucket))
```

**Use case**: Identify the most popular time window setting

## Dashboard Panel Suggestions

### Panel 1: Query Distribution by Window
- **Visualization**: Pie chart or bar chart
- **Query**: 
  ```promql
  sum(increase(assistant_tool_queries_total[24h])) by (window_bucket)
  ```
- **Legend**: `{{ window_bucket }} days`

### Panel 2: Hit Rate Trend
- **Visualization**: Time series (line graph)
- **Query**: 
  ```promql
  sum(rate(assistant_tool_queries_total{has_hits="1"}[5m])) 
  / 
  sum(rate(assistant_tool_queries_total[5m])) * 100
  ```
- **Y-axis**: Percentage (0-100)
- **Unit**: Percent

### Panel 3: Tool Usage Heatmap
- **Visualization**: Heatmap
- **Query**: 
  ```promql
  sum(rate(assistant_tool_queries_total[5m])) by (tool, window_bucket)
  ```
- **X-axis**: window_bucket
- **Y-axis**: tool

### Panel 4: Zero-Result Queries
Track queries that return no results:

```promql
sum(increase(assistant_tool_queries_total{has_hits="0"}[1h])) by (window_bucket, tool)
```

**Use case**: Identify time windows where users frequently get no results

## Alert Rules

### Alert: High Zero-Result Rate

```promql
(
  sum(rate(assistant_tool_queries_total{has_hits="0"}[5m])) 
  / 
  sum(rate(assistant_tool_queries_total[5m]))
) > 0.5
```

**Condition**: Alert if more than 50% of queries return no results
**Action**: Investigate data freshness, sync issues, or user education needs

### Alert: Window Bucket Imbalance

```promql
stddev(sum(rate(assistant_tool_queries_total[5m])) by (window_bucket)) > 10
```

**Condition**: Alert if usage across window buckets is highly unbalanced
**Action**: May indicate UX issues or user confusion about window selection

## Grafana Dashboard JSON Template

```json
{
  "panels": [
    {
      "title": "Queries by Time Window",
      "targets": [
        {
          "expr": "sum(rate(assistant_tool_queries_total[5m])) by (window_bucket)",
          "legendFormat": "{{ window_bucket }} days"
        }
      ],
      "type": "timeseries"
    },
    {
      "title": "Hit Rate by Window",
      "targets": [
        {
          "expr": "sum(rate(assistant_tool_queries_total{has_hits=\"1\"}[5m])) by (window_bucket) / sum(rate(assistant_tool_queries_total[5m])) by (window_bucket) * 100",
          "legendFormat": "{{ window_bucket }}d hit rate"
        }
      ],
      "type": "graph",
      "yaxis": {
        "format": "percent",
        "max": 100,
        "min": 0
      }
    }
  ]
}
```

## Business Insights

### Understanding User Behavior

1. **Window Preference Analysis**:
   - If 90+ bucket dominates → Users need historical data
   - If 7d bucket dominates → Users focus on recent emails
   - Balanced distribution → Good UX, users adapt window to task

2. **Hit Rate Correlation**:
   - Compare hit rates across windows
   - Lower hit rate in 7d might indicate insufficient data sync
   - Higher hit rate in 60d+ might indicate users keeping old emails

3. **Tool-Window Patterns**:
   - Which tools are used with which windows?
   - Example: "clean" tool might correlate with 30d+ windows
   - "find" tool might correlate with shorter 7d windows

## Performance Metrics

### ES Query Performance by Window

```promql
histogram_quantile(0.95, 
  sum(rate(elasticsearch_query_duration_seconds_bucket[5m])) by (le, window_bucket)
)
```

**Use case**: Identify if longer time windows cause slower queries

### Cache Hit Rate by Window

```promql
sum(rate(redis_cache_hits_total[5m])) by (window_bucket) 
/ 
sum(rate(redis_cache_requests_total[5m])) by (window_bucket)
```

**Use case**: Understand if certain windows are more cacheable
