# Grafana PromQL Queries for ApplyLens Observability

## Assistant Tool Efficacy Metrics

### Hits vs. No-Hits Distribution
Shows the breakdown of tool queries that found results vs. those that didn't.

```promql
sum by (has_hits) (rate(assistant_tool_queries_total[5m]))
```

**Visualization:** Pie chart or Time series
- `has_hits="1"` - Queries that returned results
- `has_hits="0"` - Queries that found nothing

---

### Tool Usage by Type
Shows which tools are most frequently used.

```promql
sum by (tool) (rate(assistant_tool_queries_total[5m]))
```

**Visualization:** Bar chart or Time series
- Tools: summarize, find, clean, unsubscribe, flag, follow-up, calendar, task

---

### Tool Success Rate
Percentage of queries that find results per tool.

```promql
sum by (tool) (rate(assistant_tool_queries_total{has_hits="1"}[5m]))
/
sum by (tool) (rate(assistant_tool_queries_total[5m]))
* 100
```

**Visualization:** Gauge or Time series
- Shows effectiveness of each tool
- Target: >80% success rate

---

### Empty Result Queries (Alert Candidate)
Rate of queries returning no results.

```promql
sum(rate(assistant_tool_queries_total{has_hits="0"}[5m]))
```

**Alert Condition:** `> 0.5` (more than 0.5 empty queries per second)
- May indicate data sync issues
- May indicate user query quality issues

---

## API Performance Metrics

### Chat Endpoint Error Rate
5xx error budget burndown for chat endpoint.

```promql
sum(rate(http_requests_total{handler="/api/chat",status=~"5.."}[5m]))
/
sum(rate(http_requests_total{handler="/api/chat"}[5m]))
```

**Visualization:** Gauge
- Target: < 0.01 (1% error rate)
- Alert if > 0.05 (5% error rate)

---

### Chat Endpoint Latency (p95)
95th percentile response time for chat.

```promql
histogram_quantile(0.95, 
  sum(rate(http_request_duration_seconds_bucket{handler="/api/chat"}[5m])) by (le)
)
```

**Visualization:** Time series
- Target: < 2s for p95
- Alert if > 5s

---

### Chat Endpoint Request Rate
Requests per second to chat endpoint.

```promql
sum(rate(http_requests_total{handler="/api/chat"}[5m]))
```

**Visualization:** Time series
- Shows usage patterns
- Useful for capacity planning

---

## Elasticsearch Performance

### ES Search Latency (p95)
95th percentile search duration (if ES metrics exported).

```promql
histogram_quantile(0.95, 
  sum(rate(es_search_duration_seconds_bucket[5m])) by (le)
)
```

**Visualization:** Time series
- Target: < 0.5s for p95
- Alert if > 2s

---

### ES Search Rate
Searches per second to Elasticsearch.

```promql
sum(rate(es_search_total[5m]))
```

**Visualization:** Time series
- Correlate with chat request rate
- Should be roughly 1:1 with chat requests

---

### ES Error Rate
Percentage of ES searches that fail.

```promql
sum(rate(es_search_errors_total[5m]))
/
sum(rate(es_search_total[5m]))
```

**Alert Condition:** `> 0.05` (5% error rate)

---

## Redis Cache Performance

### Cache Hit Rate
Percentage of cache hits vs. total cache operations.

```promql
sum(rate(redis_cache_hits_total[5m]))
/
(sum(rate(redis_cache_hits_total[5m])) + sum(rate(redis_cache_misses_total[5m])))
* 100
```

**Visualization:** Gauge
- Target: > 80% hit rate
- Shows cache effectiveness

---

### Cache Operation Latency
95th percentile cache operation duration.

```promql
histogram_quantile(0.95,
  sum(rate(redis_operation_duration_seconds_bucket[5m])) by (le, operation)
)
```

**Visualization:** Time series by operation (get, set, delete)
- Target: < 10ms for p95

---

## Email Statistics Endpoints

### Stats Endpoint Cache Performance
Hit rate specifically for `/api/emails/stats`.

```promql
sum(rate(http_requests_total{handler="/api/emails/stats",cache_status="hit"}[5m]))
/
sum(rate(http_requests_total{handler="/api/emails/stats"}[5m]))
* 100
```

**Target:** > 90% (with 60s TTL)

---

### Stats Endpoint Response Time
Cached vs. uncached response times.

```promql
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket{handler="/api/emails/stats"}[5m])) 
  by (le, cache_status)
)
```

**Expected:**
- Cached: < 0.5s
- Uncached: < 3s (database aggregations)

---

## Database Performance

### Database Query Duration
95th percentile database query time.

```promql
histogram_quantile(0.95,
  sum(rate(db_query_duration_seconds_bucket[5m])) by (le, query_type)
)
```

**Visualization:** Time series by query_type
- Target: < 1s for p95

---

### Database Connection Pool Usage
Number of active vs. idle connections.

```promql
# Active connections
db_connections_active

# Idle connections
db_connections_idle

# Total capacity
db_connections_max
```

**Alert Condition:** `db_connections_active / db_connections_max > 0.8` (80% utilization)

---

## System Resources

### API Container CPU Usage
```promql
rate(container_cpu_usage_seconds_total{container="applylens-api-prod"}[5m]) * 100
```

**Alert:** > 80% sustained

---

### API Container Memory Usage
```promql
container_memory_usage_bytes{container="applylens-api-prod"} 
/ 
container_spec_memory_limit_bytes{container="applylens-api-prod"}
* 100
```

**Alert:** > 85%

---

### Redis Memory Usage
```promql
redis_memory_used_bytes / redis_memory_max_bytes * 100
```

**Alert:** > 90%

---

## Composite Dashboards

### Assistant Health Overview
- Tool success rate gauge (target: >80%)
- Empty result rate (alert if high)
- Chat endpoint error rate (target: <1%)
- Chat endpoint p95 latency (target: <2s)

### Performance Overview
- Request rate (chat, stats, count)
- Response times (p50, p95, p99)
- Error rates by endpoint
- Cache hit rates

### Infrastructure Overview
- CPU/Memory usage per container
- Database connection pool
- Redis memory usage
- ES cluster health

---

## Alert Rules (Recommended)

### Critical Alerts
```yaml
# High error rate
- alert: HighChatErrorRate
  expr: sum(rate(http_requests_total{handler="/api/chat",status=~"5.."}[5m])) / sum(rate(http_requests_total{handler="/api/chat"}[5m])) > 0.05
  for: 5m
  severity: critical

# Database connection pool exhausted
- alert: DatabasePoolExhausted
  expr: db_connections_active / db_connections_max > 0.9
  for: 2m
  severity: critical

# High memory usage
- alert: HighMemoryUsage
  expr: container_memory_usage_bytes{container="applylens-api-prod"} / container_spec_memory_limit_bytes{container="applylens-api-prod"} > 0.9
  for: 5m
  severity: critical
```

### Warning Alerts
```yaml
# Slow chat responses
- alert: SlowChatResponses
  expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{handler="/api/chat"}[5m])) by (le)) > 5
  for: 10m
  severity: warning

# Low cache hit rate
- alert: LowCacheHitRate
  expr: sum(rate(redis_cache_hits_total[5m])) / (sum(rate(redis_cache_hits_total[5m])) + sum(rate(redis_cache_misses_total[5m]))) < 0.7
  for: 15m
  severity: warning

# High empty result rate
- alert: HighEmptyResultRate
  expr: sum(rate(assistant_tool_queries_total{has_hits="0"}[5m])) > 0.5
  for: 10m
  severity: warning
```

---

## Custom Metrics to Export (Future)

If these metrics aren't already exported, consider adding them:

```python
# In services/api/app/metrics.py

from prometheus_client import Histogram, Counter

# ES search duration
es_search_duration = Histogram(
    "es_search_duration_seconds",
    "Elasticsearch search duration",
    ["index", "query_type"],
)

# Redis cache operations
redis_cache_hits = Counter("redis_cache_hits_total", "Redis cache hits")
redis_cache_misses = Counter("redis_cache_misses_total", "Redis cache misses")

# Database query duration
db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["query_type"],
)
```

---

Last Updated: October 15, 2025
