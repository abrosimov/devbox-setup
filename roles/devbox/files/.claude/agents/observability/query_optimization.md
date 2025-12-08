# Query Optimization

Reference patterns for optimizing PromQL and LogQL queries.

## PromQL Optimization

### Cardinality Management

**Cardinality = unique combinations of label values**

High cardinality is the #1 cause of Prometheus performance issues.

| Cardinality Level | Series Count | Impact |
|-------------------|--------------|--------|
| Low | < 10,000 | No issues |
| Medium | 10,000 - 100,000 | Monitor closely |
| High | 100,000 - 1,000,000 | Performance degradation |
| Extreme | > 1,000,000 | System instability |

### Identifying High-Cardinality Metrics

```promql
# Count series per metric
count by (__name__) ({__name__=~".+"})

# Find metrics with most series
topk(10, count by (__name__) ({__name__=~".+"}))

# Check cardinality of specific labels
count(http_requests_total) by (path)
count(http_requests_total) by (user_id)  # DANGER: likely high cardinality
```

### Label Selection Best Practices

```promql
# GOOD: Use equality matchers when possible
http_requests_total{service="api", status="200"}

# BAD: Regex on high-cardinality labels
http_requests_total{path=~".*"}

# GOOD: Limit regex scope
http_requests_total{path=~"/api/v1/.*"}

# BAD: Negative regex (scans everything)
http_requests_total{status!~"2.."}

# GOOD: Explicit list for small sets
http_requests_total{status=~"4..|5.."}
```

### Aggregation Strategies

```promql
# ALWAYS aggregate early to reduce cardinality

# BAD: Aggregate late (processes all series first)
sum(rate(http_requests_total[5m]))

# GOOD: Specify labels to keep
sum by (service) (rate(http_requests_total[5m]))

# GOOD: Specify labels to drop (when keeping most)
sum without (instance, pod) (rate(http_requests_total[5m]))

# Rule of thumb:
# - Use `by` when keeping 1-3 labels
# - Use `without` when dropping 1-3 labels
```

### Time Range Optimization

```promql
# Query cost scales linearly with time range

# Short ranges (< 1h): Fine for detailed analysis
rate(http_requests_total[5m])

# Medium ranges (1h - 24h): Use larger step
rate(http_requests_total[5m])[6h:1m]  # 1-minute resolution

# Long ranges (> 24h): Use recording rules or larger step
rate(http_requests_total[5m])[7d:5m]  # 5-minute resolution
```

### Recording Rules for Expensive Queries

```yaml
# Pre-compute expensive aggregations
groups:
  - name: expensive_queries
    interval: 30s
    rules:
      # Instead of: sum by (service) (rate(http_requests_total[5m]))
      - record: service:http_requests:rate5m
        expr: sum by (service) (rate(http_requests_total[5m]))

      # Instead of: histogram_quantile(0.99, sum by (le) (rate(...)))
      - record: service:http_request_duration:p99
        expr: |
          histogram_quantile(0.99,
            sum by (service, le) (rate(http_request_duration_seconds_bucket[5m]))
          )
```

**When to use recording rules:**
- Query is used in dashboards with > 100 users
- Query appears in alerting rules
- Query takes > 1 second to execute
- Query is executed frequently (< 1 minute intervals)

### Subquery Optimization

```promql
# Subqueries are expensive - use sparingly

# BAD: Nested subquery with small step
max_over_time(rate(http_requests_total[5m])[1h:10s])
# Evaluates rate() 360 times (1h / 10s)

# BETTER: Larger step size
max_over_time(rate(http_requests_total[5m])[1h:1m])
# Evaluates rate() 60 times

# BEST: Use recording rule + simple query
max_over_time(service:http_requests:rate5m[1h])
```

### Common Query Patterns

#### Rate and Increase

```promql
# Rate: per-second average over range
rate(http_requests_total[5m])

# Increase: total increase over range
increase(http_requests_total[5m])

# irate: instant rate (last two points only) - use for volatile metrics
irate(http_requests_total[5m])

# Relationship: increase ≈ rate * range_seconds
# increase(x[5m]) ≈ rate(x[5m]) * 300
```

#### Histogram Percentiles

```promql
# Single percentile
histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))

# Multiple percentiles (efficient - shares rate calculation)
histogram_quantile(0.50, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))
histogram_quantile(0.90, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))
histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))

# With grouping
histogram_quantile(0.99, sum by (service, le) (rate(http_request_duration_seconds_bucket[5m])))
```

#### Error Rates

```promql
# Error ratio (handles zero denominator)
sum(rate(http_requests_total{status=~"5.."}[5m]))
/
(sum(rate(http_requests_total[5m])) > 0)

# With default value for zero traffic
sum(rate(http_requests_total{status=~"5.."}[5m]))
/
sum(rate(http_requests_total[5m]))
or vector(0)

# Per-service error rate
sum by (service) (rate(http_requests_total{status=~"5.."}[5m]))
/
sum by (service) (rate(http_requests_total[5m]))
```

#### Availability

```promql
# Availability over time range
avg_over_time(up{job="api"}[24h])

# Availability percentage
100 * avg_over_time(up{job="api"}[24h])

# SLO calculation (99.9% = 0.999)
(
  sum(rate(http_requests_total{status!~"5.."}[30d]))
  /
  sum(rate(http_requests_total[30d]))
) >= 0.999
```

### Anti-Patterns to Avoid

#### DON'T: Use Unbounded Queries

```promql
# BAD: No time bounds, returns all data
http_requests_total

# GOOD: Use rate/increase with range
rate(http_requests_total[5m])
```

#### DON'T: Over-aggregate Then Filter

```promql
# BAD: Sum everything, then filter (wasteful)
sum(http_requests_total) by (service)  # Don't do this
# Then try to filter in dashboard

# GOOD: Filter first, then aggregate
sum by (service) (http_requests_total{namespace="production"})
```

#### DON'T: Use Regex When Equality Works

```promql
# BAD: Regex for exact match
http_requests_total{service=~"api"}

# GOOD: Equality matcher
http_requests_total{service="api"}
```

#### DON'T: Ignore Series Churn

```promql
# BAD: High-churn labels in aggregations
sum by (pod) (rate(http_requests_total[5m]))
# Pod names change frequently, creating new series

# GOOD: Stable labels for aggregation
sum by (deployment) (rate(http_requests_total[5m]))
```

## LogQL Optimization

### Query Structure Order

**Critical: Order matters for performance**

```logql
# Optimal order (fastest to slowest):
{label_selector}                    # 1. Label selector (index lookup)
  |= "line_filter"                  # 2. Line filter (string search)
  | parser                          # 3. Parser (structured extraction)
  | label_filter                    # 4. Label filter (post-parse filter)
  | line_format                     # 5. Line formatting
```

### Label Selector Optimization

```logql
# GOOD: Specific label selectors
{namespace="production", app="api"}

# BAD: Broad selector
{namespace="production"}  # Returns all apps

# BAD: Regex on high-cardinality labels
{pod=~"api-.*"}

# GOOD: Use app label instead
{app="api"}
```

### Line Filter Performance

```logql
# Line filters are faster than parsers

# GOOD: Filter before parsing
{app="api"} |= "error" | json

# BAD: Parse everything, filter later
{app="api"} | json | level="error"

# Multiple line filters (AND logic)
{app="api"} |= "error" |= "database"

# Negative filter (exclude)
{app="api"} |= "error" != "timeout"

# Regex line filter (slower than |=)
{app="api"} |~ "error.*connection"
```

### Parser Selection

**Performance ranking (fastest to slowest):**

| Parser | Use Case | Performance |
|--------|----------|-------------|
| `pattern` | Known, fixed formats | Fastest |
| `logfmt` | key=value format | Fast |
| `json` | JSON logs | Moderate |
| `regexp` | Custom patterns | Slowest |

#### Pattern Parser (Fastest)

```logql
# Best for structured logs with fixed format
# Log: 2024-01-15 10:30:00 INFO [api] Request processed in 150ms
{app="api"}
  | pattern `<timestamp> <level> [<component>] <message>`
  | level="ERROR"
```

#### Logfmt Parser

```logql
# For logfmt: level=info msg="request processed" duration=150ms
{app="api"}
  |= "error"  # Line filter first!
  | logfmt
  | level="error"
```

#### JSON Parser

```logql
# For JSON logs
{app="api"}
  |= "error"  # Line filter first!
  | json
  | level="error"

# Extract specific fields only (faster)
{app="api"}
  |= "error"
  | json level, message, duration
```

#### Regexp Parser (Slowest - Avoid if Possible)

```logql
# Only when other parsers don't work
{app="api"}
  |= "error"
  | regexp `(?P<level>\w+): (?P<message>.*)`
```

### Aggregation Queries

```logql
# Count errors over time
count_over_time({app="api"} |= "error" [5m])

# Rate of errors
rate({app="api"} |= "error" [5m])

# Sum bytes (log volume)
sum(bytes_over_time({app="api"}[1h]))

# Group by extracted label
sum by (level) (
  count_over_time({app="api"} | json | __error__="" [5m])
)

# Top talkers (highest log volume)
topk(10, sum by (pod) (bytes_over_time({namespace="production"}[1h])))
```

### Time Range Considerations

```logql
# Short ranges (< 1h): Good for debugging
{app="api"} |= "error" | json

# Medium ranges (1h - 24h): Use aggregations
sum(count_over_time({app="api"} |= "error" [1h]))

# Long ranges (> 24h): Be very specific
sum(count_over_time(
  {app="api", namespace="production"}
  |= "error"
  | json
  | status_code >= 500
  [24h]
))
```

### Common LogQL Patterns

#### Error Analysis

```logql
# Find all errors
{app="api"} |= "error" | json | level="error"

# Error count by type
sum by (error_type) (
  count_over_time({app="api"} | json | level="error" [1h])
)

# Error rate
rate({app="api"} |= "error" [5m])
```

#### Request Tracing

```logql
# Find specific request
{app="api"} |= "request_id=abc123"

# Trace across services (use trace_id)
{namespace="production"} |= "trace_id=xyz789"
```

#### Performance Analysis

```logql
# Slow requests (parse duration from logs)
{app="api"}
  | json
  | duration > 1000
  | line_format "{{.method}} {{.path}} took {{.duration}}ms"

# Request latency distribution
quantile_over_time(0.99,
  {app="api"} | json | unwrap duration [5m]
) by (endpoint)
```

### Anti-Patterns to Avoid

#### DON'T: Parse Before Filtering

```logql
# BAD: Parser runs on all logs
{app="api"} | json | level="error"

# GOOD: Filter first, parse filtered logs only
{app="api"} |= "error" | json | level="error"
```

#### DON'T: Use Broad Label Selectors

```logql
# BAD: Too broad
{namespace=~".*"}

# GOOD: Specific namespace
{namespace="production", app="api"}
```

#### DON'T: Ignore __error__ Label

```logql
# BAD: Includes parse failures silently
{app="api"} | json | level="error"

# GOOD: Exclude parse errors
{app="api"} | json | __error__="" | level="error"

# Or investigate parse errors
{app="api"} | json | __error__!=""
```

#### DON'T: Use Regex When Simple Filter Works

```logql
# BAD: Regex for simple string
{app="api"} |~ "error"

# GOOD: Equality filter
{app="api"} |= "error"
```

## Performance Testing

### PromQL Query Analysis

```bash
# Use Prometheus HTTP API to get query stats
curl -s "http://prometheus:9090/api/v1/query?query=rate(http_requests_total[5m])" | jq '.data.stats'

# Check query execution time
curl -s "http://prometheus:9090/api/v1/query?query=rate(http_requests_total[5m])" \
  -w "\nTime: %{time_total}s\n"
```

### Grafana Query Inspector

In Grafana:
1. Open panel edit mode
2. Click "Query Inspector"
3. Check:
   - Query execution time
   - Data points returned
   - Bytes transferred

### Identifying Slow Queries

```promql
# Prometheus self-monitoring: slow queries
prometheus_engine_query_duration_seconds{quantile="0.99"}

# Queries exceeding threshold
prometheus_engine_query_duration_seconds{quantile="0.99"} > 10
```

## Summary: Optimization Checklist

### PromQL

- [ ] Use equality matchers over regex where possible
- [ ] Aggregate early with `by` or `without`
- [ ] Avoid high-cardinality labels in aggregations
- [ ] Use recording rules for expensive queries
- [ ] Choose appropriate time ranges and step sizes
- [ ] Avoid subqueries when simpler alternatives exist

### LogQL

- [ ] Start with specific label selectors
- [ ] Apply line filters before parsers
- [ ] Choose the fastest parser for your log format
- [ ] Exclude parse errors with `__error__=""`
- [ ] Use aggregations for time-based analysis
- [ ] Limit time ranges to what's needed

### General

- [ ] Test queries in isolation before adding to dashboards
- [ ] Monitor query performance over time
- [ ] Review and optimize slow queries regularly
- [ ] Document complex queries with comments
- [ ] Use recording rules for dashboard queries with many viewers
