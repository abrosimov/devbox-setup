# Alert Rules

Runnable files: `examples/rules/checkout/` (`alerts.yaml`, `recording.yaml`,
`tests/alerts_test.yaml`), checked with `promtool check rules` and `promtool test rules`.

Rule files are Prometheus rule YAML; wrap them in a `PrometheusRule` CRD only when the project runs
the Prometheus Operator. Every rule has labels `severity` (`page`/`ticket`), `layer`
(`product`/`technology`/`code`), `maturity` (`none`/`baseline`/`observed`/`agreed`) and annotations
`summary`, `description`, `runbook_url`. Every rule has a promtool unit test with one firing and one
non-firing case.

## Product Layer: Multi-Window Burn Rate

Recording rules first, so the alert expressions stay short and cheap:

```yaml
groups:
  - name: checkout.sli
    interval: 30s
    rules:
      - record: sli:checkout_errors:ratio_rate5m
        expr: |
          sum(rate(http_server_request_duration_seconds_count{service_name="checkout", http_route="/checkout", http_response_status_code=~"5.."}[5m]))
          / sum(rate(http_server_request_duration_seconds_count{service_name="checkout", http_route="/checkout"}[5m]))
      - record: sli:checkout_errors:ratio_rate30m
        expr: ...[30m]...
      - record: sli:checkout_errors:ratio_rate1h
        expr: ...[1h]...
      - record: sli:checkout_errors:ratio_rate6h
        expr: ...[6h]...
      - record: sli:checkout_errors:ratio_rate3d
        expr: ...[3d]...
```

With SLO = 99.9 % availability, error budget `1 - 0.999 = 0.001`:

```yaml
  - name: checkout.slo
    rules:
      - alert: CheckoutErrorBudgetBurnFast
        expr: |
          sli:checkout_errors:ratio_rate1h > (14.4 * 0.001)
          and
          sli:checkout_errors:ratio_rate5m > (14.4 * 0.001)
        for: 2m
        labels: { severity: page, layer: product, maturity: agreed }
        annotations:
          summary: "Checkout burning error budget at 14.4x (2% of 30-day budget in 1h)"
          description: "1h error ratio {{ $value | humanizePercentage }} against SLO 99.9%"
          runbook_url: https://<runbooks>/CheckoutErrorBudgetBurnFast
      - alert: CheckoutErrorBudgetBurnMedium
        expr: |
          sli:checkout_errors:ratio_rate6h > (6 * 0.001)
          and
          sli:checkout_errors:ratio_rate30m > (6 * 0.001)
        for: 15m
        labels: { severity: page, layer: product, maturity: agreed }
      - alert: CheckoutErrorBudgetBurnSlow
        expr: |
          sli:checkout_errors:ratio_rate3d > (1 * 0.001)
          and
          sli:checkout_errors:ratio_rate6h > (1 * 0.001)
        for: 1h
        labels: { severity: ticket, layer: product, maturity: agreed }
```

Latency SLOs use the same shape with the SLI defined as the ratio of requests slower than the
threshold: `1 - (sum(rate(..._bucket{le="0.5"}[5m])) / sum(rate(..._count[5m])))`.

Window and burn-rate table:

| Severity | Budget consumed | Long | Short | Burn rate | `for` |
|----------|-----------------|------|-------|-----------|-------|
| page | 2 % in 1h | 1h | 5m | 14.4 | 2m |
| page | 5 % in 6h | 6h | 30m | 6 | 15m |
| ticket | 10 % in 3d | 3d | 6h | 1 | 1h |

Stage `baseline` uses the same rules with `severity: ticket` and a placeholder SLO one nine below
the observed success ratio; stage `none` has no product rules at all.

## Technology Layer Templates

```yaml
  - name: checkout.technology
    rules:
      - alert: DBPoolExhausted
        expr: |
          sum by (db_client_connection_pool_name) (db_client_connection_count{db_client_connection_state="used"})
          / sum by (db_client_connection_pool_name) (db_client_connection_max) > 0.9
        for: 5m
        labels: { severity: ticket, layer: technology, maturity: none }
      - alert: ConsumerLagAgeHigh
        expr: orders_queue_oldest_age_seconds > 300
        for: 5m
        labels: { severity: ticket, layer: technology, maturity: none }
      - alert: ConsumerStalled
        expr: rate(messaging_client_consumed_messages_total[10m]) == 0 and orders_queue_depth > 0
        for: 10m
        labels: { severity: page, layer: technology, maturity: none }
      - alert: GoroutineGrowth
        expr: deriv(go_goroutine_count[30m]) > 1 and go_goroutine_count > 5000
        for: 30m
        labels: { severity: ticket, layer: technology, maturity: none }
      - alert: GCPauseHigh
        expr: histogram_quantile(0.99, sum by (le) (rate(go_schedule_duration_seconds_bucket[5m]))) > 0.1
        for: 10m
        labels: { severity: ticket, layer: technology, maturity: none }
      - alert: PodRestartLoop
        expr: increase(kube_pod_container_status_restarts_total{container="checkout"}[1h]) > 3
        labels: { severity: page, layer: technology, maturity: none }
      - alert: DiskRunwayShort
        expr: predict_linear(node_filesystem_avail_bytes{mountpoint="/data"}[6h], 4 * 3600) < 0
        for: 30m
        labels: { severity: page, layer: technology, maturity: none }
      - alert: CertificateExpiringSoon
        expr: (probe_ssl_earliest_cert_expiry - time()) < 14 * 86400
        labels: { severity: ticket, layer: technology, maturity: none }
      - alert: DependencyErrorRateHigh
        expr: |
          sum by (server_address) (rate(http_client_request_duration_seconds_count{error_type!=""}[5m]))
          / sum by (server_address) (rate(http_client_request_duration_seconds_count[5m])) > 0.05
        for: 10m
        labels: { severity: ticket, layer: technology, maturity: none }
```

Other candidates by component type: replication lag, WAL size, file descriptors against the limit,
TLS handshake failures, DNS resolution failures, OOM kills, rate limiter rejections, cache hit ratio
collapse, thread or worker pool saturation, clock skew.

## Code Layer Templates

```yaml
  - name: checkout.code
    rules:
      - alert: PanicsRecovered
        expr: increase(checkout_panics_total[10m]) > 0
        labels: { severity: ticket, layer: code, maturity: none }
      - alert: SwallowedErrorsSpike
        expr: sum by (error_type) (rate(checkout_reconcile_errors_total[5m])) > 0.1
        for: 10m
        labels: { severity: ticket, layer: code, maturity: none }
      - alert: RetriesExhausted
        expr: increase(checkout_payment_retries_exhausted_total[15m]) > 5
        labels: { severity: ticket, layer: code, maturity: none }
      - alert: CircuitBreakerOpen
        expr: checkout_breaker_state{state="open"} == 1
        for: 5m
        labels: { severity: ticket, layer: code, maturity: none }
      - alert: DeadLetterWrites
        expr: increase(checkout_dead_letter_total[30m]) > 0
        labels: { severity: ticket, layer: code, maturity: none }
      - alert: InvariantViolated
        expr: increase(checkout_invariant_violations_total[5m]) > 0
        labels: { severity: page, layer: code, maturity: none }
        annotations:
          summary: "Runtime invariant {{ $labels.invariant }} violated"
```

Zero is the expected value of every detector; a detector that fires weekly is either a bug to fix or
a threshold to revisit, never a rule to silence.

## promtool Unit Tests

`observability/rules/checkout/tests/alerts_test.yaml`:

```yaml
rule_files:
  - ../alerts.yaml
  - ../recording.yaml

evaluation_interval: 1m

tests:
  - interval: 1m
    input_series:
      - series: 'sli:checkout_errors:ratio_rate1h'
        values: '0.02x90'                 # 2% for 90 minutes
      - series: 'sli:checkout_errors:ratio_rate5m'
        values: '0.02x90'
    alert_rule_test:
      - eval_time: 5m
        alertname: CheckoutErrorBudgetBurnFast
        exp_alerts:
          - exp_labels:
              severity: page
              layer: product
              maturity: agreed
            exp_annotations:
              summary: "Checkout burning error budget at 14.4x (2% of 30-day budget in 1h)"
              description: "1h error ratio 2% against SLO 99.9%"
              runbook_url: https://<runbooks>/CheckoutErrorBudgetBurnFast
  - interval: 1m
    input_series:
      - series: 'sli:checkout_errors:ratio_rate1h'
        values: '0.0005x90'               # under budget: must not fire
      - series: 'sli:checkout_errors:ratio_rate5m'
        values: '0.0005x90'
    alert_rule_test:
      - eval_time: 30m
        alertname: CheckoutErrorBudgetBurnFast
        exp_alerts: []
  - interval: 1m
    input_series:
      - series: 'checkout_panics_total{instance="a"}'
        values: '0 0 0 1 1 1'             # one panic at minute 3
    alert_rule_test:
      - eval_time: 5m
        alertname: PanicsRecovered
        exp_alerts:
          - exp_labels: { severity: ticket, layer: code, maturity: none, instance: a }
    promql_expr_test:
      - expr: increase(checkout_panics_total[10m])
        eval_time: 5m
        exp_samples:
          - labels: '{instance="a"}'
            value: 1
```

Series values syntax: `a b c` literal samples, `0+10x5` arithmetic progression, `1x60` repeat,
`_` missing sample, `stale` staleness marker. Recording rules in the tested files are evaluated,
so burn-rate tests can feed raw counters instead of the recorded ratios when preferred.

Run: `promtool test rules observability/rules/*/tests/*.yaml`.

## Runbook Template

`observability/runbooks/<Alertname>.md`:

```markdown
# <Alertname>

**Layer**: product | technology | code · **Severity**: page | ticket · **Owner**: <team>

## What fired
One sentence on the condition, with the expression.

## What the user sees
Impact if nothing is done, and how fast it gets worse.

## First five minutes
1. Dashboard panel: <link>, row <name>.
2. Query to localise: `...`
3. Known causes, most likely first, each with the signal that confirms it.

## Mitigation
Exact commands or buttons, including rollback.

## Afterwards
What to record, which detector or threshold to revisit.
```

## Sources

- Google SRE Workbook, ch. 5 *Alerting on SLOs* (the multiwindow, multi-burn-rate table) —
  https://sre.google/workbook/alerting-on-slos/
- Google SRE Book, ch. 6 *Monitoring Distributed Systems* (symptoms versus causes) —
  https://sre.google/sre-book/monitoring-distributed-systems/
- Rob Ewaschuk, *My Philosophy on Alerting* (the pages-versus-tickets rule) —
  https://docs.google.com/document/d/199PqyG3UsyXlwieHaqbGiWVa8eMWi8zzAn0YfcApr8Q
- Prometheus alerting rules and unit testing —
  https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/ ,
  https://prometheus.io/docs/prometheus/latest/configuration/unit_testing_rules/
- Prometheus Operator `PrometheusRule` — https://prometheus-operator.dev/docs/developer/alerting/
- Brian Brazil, *Prometheus: Up & Running* (2nd ed., O'Reilly 2023), recording rules and alerting chapters
