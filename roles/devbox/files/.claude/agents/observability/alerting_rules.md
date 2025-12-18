# Prometheus Alerting Rules

Reference patterns for creating Prometheus alerting rules using PrometheusRule CRD.

## PrometheusRule CRD Structure

### Basic Structure

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: <service>-alerts
  namespace: monitoring
  labels:
    # Required for Prometheus Operator to discover this rule
    release: prometheus
    app: prometheus
    # Custom labels for organisation
    team: platform
    service: <service>
spec:
  groups:
    - name: <service>.rules
      # Optional: evaluation interval (default: global evaluation_interval)
      interval: 30s
      rules:
        - alert: AlertName
          expr: <promql_expression>
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Short description"
            description: "Detailed description with {{ $value }}"
```

### Complete Example

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: api-service-alerts
  namespace: monitoring
  labels:
    release: prometheus
    team: backend
    service: api
spec:
  groups:
    # Alerting rules
    - name: api.alerts
      rules:
        - alert: APIHighErrorRate
          expr: |
            (
              sum(rate(http_requests_total{service="api", status=~"5.."}[5m]))
              /
              sum(rate(http_requests_total{service="api"}[5m]))
            ) > 0.01
          for: 5m
          labels:
            severity: warning
            team: backend
            service: api
          annotations:
            summary: "API error rate is high"
            description: "Error rate is {{ $value | humanizePercentage }} (threshold: 1%)"
            runbook_url: "https://runbooks.example.com/api-high-error-rate"
            dashboard_url: "https://grafana.example.com/d/api-overview"

    # Recording rules (pre-computed metrics)
    - name: api.recording
      interval: 30s
      rules:
        - record: api:http_requests:rate5m
          expr: sum(rate(http_requests_total{service="api"}[5m]))

        - record: api:http_errors:rate5m
          expr: sum(rate(http_requests_total{service="api", status=~"5.."}[5m]))
```

## Severity Levels

### Standard Severity Scheme

| Severity | Response Time | Notification | Examples |
|----------|---------------|--------------|----------|
| `critical` | Immediate (page) | PagerDuty/OpsGenie | Service down, data loss risk |
| `warning` | Hours | Slack channel | Degraded performance, approaching limits |
| `info` | Next business day | Email/ticket | Anomalies, trends |

### Severity Labels

```yaml
labels:
  severity: critical  # Pages on-call
  # OR
  severity: warning   # Slack notification
  # OR
  severity: info      # Low priority notification
```

### Alertmanager Routing Example

```yaml
# alertmanager.yaml
route:
  receiver: default
  routes:
    - match:
        severity: critical
      receiver: pagerduty
      continue: true

    - match:
        severity: warning
      receiver: slack-warnings

    - match:
        severity: info
      receiver: slack-info
```

## Time Windows

### The `for` Clause

Prevents alerting on transient spikes:

```yaml
# Alert only if condition is true for 5 minutes
- alert: HighErrorRate
  expr: error_rate > 0.01
  for: 5m  # Must be true continuously for 5 minutes
```

**Guidelines:**

| Metric Type | Recommended `for` | Rationale |
|-------------|-------------------|-----------|
| Error rates | 5m | Filter transient errors |
| Latency | 5m | Filter outliers |
| Resource usage | 10-15m | Resources fluctuate |
| Saturation | 5m | Quick response needed |
| Batch job failure | 0m (immediate) | Already delayed |

### The `keep_firing_for` Clause

Prevents flapping when metrics are intermittent:

```yaml
- alert: HighErrorRate
  expr: error_rate > 0.01
  for: 5m
  keep_firing_for: 10m  # Keep alert firing for 10m after condition clears
```

**Use cases:**
- Metrics that disappear briefly (pod restarts)
- Preventing alert flood during recovery
- Giving time to verify fix

## Alert Design Principles

### 1. Alert on Symptoms, Not Causes

```yaml
# BAD: Alerting on cause (internal metric)
- alert: HighCPU
  expr: node_cpu_utilization > 0.9
  annotations:
    summary: "High CPU usage"

# GOOD: Alerting on symptom (user impact)
- alert: HighLatency
  expr: |
    histogram_quantile(0.99,
      sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
    ) > 0.5
  annotations:
    summary: "User-facing latency is high (p99 > 500ms)"
```

### 2. Include Useful Annotations

```yaml
annotations:
  # Short summary for notification title
  summary: "{{ $labels.service }} error rate is {{ $value | humanizePercentage }}"

  # Detailed description for investigation
  description: |
    Service {{ $labels.service }} in namespace {{ $labels.namespace }}
    has error rate {{ $value | humanizePercentage }} which exceeds
    the threshold of 1%.

    Affected pods: {{ $labels.pod }}
    Time: {{ $externalLabels.cluster }}

  # Link to runbook (HIGHLY RECOMMENDED)
  runbook_url: "https://runbooks.example.com/high-error-rate"

  # Link to relevant dashboard
  dashboard_url: "https://grafana.example.com/d/svc-overview?var-service={{ $labels.service }}"
```

### 3. Use Meaningful Alert Names

```yaml
# BAD: Generic names
- alert: Alert1
- alert: ServiceProblem
- alert: Error

# GOOD: Descriptive names
- alert: APIHighErrorRate
- alert: DatabaseConnectionPoolExhausted
- alert: KubernetesNodeNotReady
- alert: PodCrashLooping
```

### 4. Include Context Labels

```yaml
labels:
  severity: warning
  # Team ownership
  team: backend
  # Service identification
  service: api
  # Environment (if not in metric)
  environment: production
  # Alert category
  category: availability
```

## Common Alert Templates

### RED Method Alerts

#### Request Rate Drop

```yaml
- alert: RequestRateDrop
  expr: |
    (
      sum(rate(http_requests_total{service="$SERVICE"}[5m]))
      /
      sum(rate(http_requests_total{service="$SERVICE"}[5m] offset 1h))
    ) < 0.5
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Request rate dropped by more than 50%"
    description: "Current rate is {{ $value | humanizePercentage }} of the rate 1 hour ago"
```

#### High Error Rate

```yaml
- alert: HighErrorRate
  expr: |
    (
      sum(rate(http_requests_total{status=~"5..", service="$SERVICE"}[5m]))
      /
      sum(rate(http_requests_total{service="$SERVICE"}[5m]))
    ) > 0.01
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Error rate exceeds 1%"
    description: "Error rate is {{ $value | humanizePercentage }}"
```

#### High Latency

```yaml
- alert: HighLatencyP99
  expr: |
    histogram_quantile(0.99,
      sum(rate(http_request_duration_seconds_bucket{service="$SERVICE"}[5m])) by (le)
    ) > 0.5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "P99 latency exceeds 500ms"
    description: "P99 latency is {{ $value | humanizeDuration }}"

- alert: HighLatencyP50
  expr: |
    histogram_quantile(0.50,
      sum(rate(http_request_duration_seconds_bucket{service="$SERVICE"}[5m])) by (le)
    ) > 0.2
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Median latency exceeds 200ms"
```

### USE Method Alerts

#### High CPU Utilization

```yaml
- alert: HighCPUUtilization
  expr: |
    (
      sum(rate(container_cpu_usage_seconds_total{namespace="$NAMESPACE"}[5m])) by (pod)
      /
      sum(kube_pod_container_resource_limits{resource="cpu", namespace="$NAMESPACE"}) by (pod)
    ) > 0.9
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Pod {{ $labels.pod }} CPU usage above 90%"
    description: "CPU utilization is {{ $value | humanizePercentage }}"
```

#### Memory Pressure

```yaml
- alert: HighMemoryUtilization
  expr: |
    (
      sum(container_memory_usage_bytes{namespace="$NAMESPACE"}) by (pod)
      /
      sum(kube_pod_container_resource_limits{resource="memory", namespace="$NAMESPACE"}) by (pod)
    ) > 0.9
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Pod {{ $labels.pod }} memory usage above 90%"
    description: "Memory utilization is {{ $value | humanizePercentage }}"
```

#### Disk Space

```yaml
- alert: DiskSpaceLow
  expr: |
    (
      node_filesystem_avail_bytes{mountpoint="/"}
      /
      node_filesystem_size_bytes{mountpoint="/"}
    ) < 0.1
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Disk space below 10% on {{ $labels.instance }}"
    description: "Available space: {{ $value | humanizePercentage }}"
```

### Kubernetes Alerts

#### Pod Not Ready

```yaml
- alert: KubePodNotReady
  expr: |
    sum by (namespace, pod) (
      max by (namespace, pod) (kube_pod_status_phase{phase=~"Pending|Unknown"}) *
      on(namespace, pod) group_left(owner_kind)
      max by (namespace, pod, owner_kind) (kube_pod_owner{owner_kind!="Job"})
    ) > 0
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} not ready"
    description: "Pod has been in non-ready state for more than 15 minutes"
```

#### Pod Crash Looping

```yaml
- alert: KubePodCrashLooping
  expr: |
    max_over_time(kube_pod_container_status_waiting_reason{reason="CrashLoopBackOff"}[5m]) >= 1
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} crash looping"
    description: "Container {{ $labels.container }} in pod {{ $labels.pod }} is crash looping"
```

#### Deployment Replicas Mismatch

```yaml
- alert: KubeDeploymentReplicasMismatch
  expr: |
    (
      kube_deployment_spec_replicas
      !=
      kube_deployment_status_replicas_available
    ) and (
      changes(kube_deployment_status_replicas_updated[10m]) == 0
    )
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Deployment {{ $labels.namespace }}/{{ $labels.deployment }} replica mismatch"
    description: "Desired: {{ $value }}, Available: {{ printf \"kube_deployment_status_replicas_available{namespace='%s', deployment='%s'}\" $labels.namespace $labels.deployment | query | first | value }}"
```

### Database Alerts

#### Connection Pool Exhausted

```yaml
- alert: DatabaseConnectionPoolExhausted
  expr: |
    (
      sum(pg_stat_activity_count{state="active"}) by (datname)
      /
      sum(pg_settings_max_connections) by (datname)
    ) > 0.9
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Database {{ $labels.datname }} connection pool nearly exhausted"
    description: "{{ $value | humanizePercentage }} of connections in use"
```

#### Slow Queries

```yaml
- alert: DatabaseSlowQueries
  expr: |
    rate(pg_stat_activity_max_tx_duration{state="active"}[5m]) > 60
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Long-running queries detected on {{ $labels.datname }}"
```

### SLO-Based Alerts

#### Error Budget Burn Rate

```yaml
# Fast burn - 2% of monthly budget in 1 hour
- alert: ErrorBudgetFastBurn
  expr: |
    (
      1 - (
        sum(rate(http_requests_total{status!~"5.."}[1h]))
        /
        sum(rate(http_requests_total[1h]))
      )
    ) > (14.4 * 0.001)  # 14.4x burn rate for 99.9% SLO
  for: 2m
  labels:
    severity: critical
    category: slo
  annotations:
    summary: "Error budget burning fast"
    description: "At current rate, monthly error budget will be exhausted in {{ $value | humanizeDuration }}"

# Slow burn - 5% of monthly budget in 6 hours
- alert: ErrorBudgetSlowBurn
  expr: |
    (
      1 - (
        sum(rate(http_requests_total{status!~"5.."}[6h]))
        /
        sum(rate(http_requests_total[6h]))
      )
    ) > (6 * 0.001)  # 6x burn rate for 99.9% SLO
  for: 30m
  labels:
    severity: warning
    category: slo
  annotations:
    summary: "Error budget burning slowly but steadily"
```

## Recording Rules

### When to Use Recording Rules

| Use Case | Example |
|----------|---------|
| Expensive queries used in alerts | Error rate calculation |
| Dashboard queries | Pre-aggregate high-cardinality metrics |
| SLO calculations | Pre-compute availability |
| Cross-service aggregations | Total requests across all services |

### Recording Rule Naming Convention

```
level:metric:operations

level    = Aggregation level (e.g., job, instance, service)
metric   = Metric name (without _total, _count, etc.)
operations = Operations applied (e.g., rate5m, sum)
```

**Examples:**
```yaml
# Service-level request rate
service:http_requests:rate5m

# Job-level error ratio
job:http_errors:ratio_rate5m

# Instance-level CPU
instance:node_cpu:utilization
```

### Recording Rules Template

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: service-recording-rules
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
    - name: service.recording
      interval: 30s
      rules:
        # Request rate
        - record: service:http_requests:rate5m
          expr: sum(rate(http_requests_total[5m])) by (service)

        # Error rate
        - record: service:http_errors:rate5m
          expr: sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)

        # Error ratio
        - record: service:http_errors:ratio_rate5m
          expr: |
            service:http_errors:rate5m
            /
            service:http_requests:rate5m

        # Latency percentiles
        - record: service:http_request_duration_seconds:p99
          expr: |
            histogram_quantile(0.99,
              sum(rate(http_request_duration_seconds_bucket[5m])) by (service, le)
            )

        - record: service:http_request_duration_seconds:p50
          expr: |
            histogram_quantile(0.50,
              sum(rate(http_request_duration_seconds_bucket[5m])) by (service, le)
            )
```

## Alertmanager Integration

### Inhibition Rules

Suppress lower-severity alerts when higher-severity fires:

```yaml
# alertmanager.yaml
inhibit_rules:
  # If critical fires, suppress warning for same service
  - source_match:
      severity: critical
    target_match:
      severity: warning
    equal: [service, namespace]

  # If cluster is down, suppress all node alerts
  - source_match:
      alertname: ClusterDown
    target_match_re:
      alertname: Node.*
    equal: [cluster]
```

### Grouping

```yaml
route:
  group_by: [alertname, service, namespace]
  group_wait: 30s      # Wait before sending first notification
  group_interval: 5m   # Wait before sending updates
  repeat_interval: 4h  # Resend if still firing
```

## Validation

### Using promtool

```bash
# Validate rule file syntax
promtool check rules rules.yaml

# Test rules against sample data
promtool test rules test.yaml

# Example test file
cat > test.yaml <<EOF
rule_files:
  - rules.yaml

evaluation_interval: 1m

tests:
  - interval: 1m
    input_series:
      - series: 'http_requests_total{service="api", status="500"}'
        values: '1+1x10'  # 1, 2, 3, ... 11
      - series: 'http_requests_total{service="api", status="200"}'
        values: '100+100x10'  # 100, 200, ... 1100
    alert_rule_test:
      - eval_time: 10m
        alertname: HighErrorRate
        exp_alerts:
          - exp_labels:
              severity: warning
              service: api
EOF

promtool test rules test.yaml
```

### Dry-Run with kubectl

```bash
# Validate CRD syntax
kubectl apply --dry-run=client -f rules.yaml

# Check if Prometheus Operator will pick it up
kubectl get prometheusrule -n monitoring
kubectl describe prometheusrule <name> -n monitoring
```

## Anti-Patterns to Avoid

### DON'T: Alert on Causes

```yaml
# BAD
- alert: HighCPU
  expr: cpu_usage > 90%
  # So what? User doesn't care about CPU

# GOOD
- alert: HighLatency
  expr: p99_latency > 500ms
  # User experiences slow response
```

### DON'T: Use Short `for` Duration

```yaml
# BAD - will flap
- alert: HighErrorRate
  expr: error_rate > 0.01
  for: 30s  # Too short

# GOOD
- alert: HighErrorRate
  expr: error_rate > 0.01
  for: 5m  # Filters transient spikes
```

### DON'T: Skip Annotations

```yaml
# BAD
- alert: SomethingWrong
  expr: some_metric > 100
  # No context for on-call engineer

# GOOD
- alert: APIHighErrorRate
  expr: api_error_rate > 0.01
  annotations:
    summary: "..."
    description: "..."
    runbook_url: "..."
```

### DON'T: Create Alert Storms

```yaml
# BAD - one alert per pod
- alert: PodHighMemory
  expr: container_memory_usage > 1Gi
  # 100 pods = 100 alerts

# GOOD - aggregate first
- alert: DeploymentHighMemory
  expr: |
    sum(container_memory_usage) by (deployment) > 10Gi
  # One alert per deployment
```

## Validation Checklist

Before deploying alerting rules:

- [ ] Alert names are descriptive and follow naming convention
- [ ] `for` duration is appropriate for metric type
- [ ] Severity is correctly assigned
- [ ] All alerts have `summary` and `description` annotations
- [ ] Runbook URL is provided for critical/warning alerts
- [ ] Labels include team ownership
- [ ] PromQL expressions are tested
- [ ] Recording rules exist for expensive queries used in alerts
- [ ] Thresholds are based on actual SLOs, not arbitrary values
- [ ] Alert won't cause storm (proper aggregation)
