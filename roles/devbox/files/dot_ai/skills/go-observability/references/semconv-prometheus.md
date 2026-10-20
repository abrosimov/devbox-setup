# Semantic Conventions and Prometheus Translation

Names come from the OpenTelemetry semantic conventions (`go.opentelemetry.io/otel/semconv/v1.xx.0`
holds the attribute keys; metric names are constants in the same package). Pin the version the
project already imports; for a new project take the newest stable version in `go.mod`'s otel line.

## Metric Names

| Area | Metric | Instrument | Unit | Required attributes | Stability |
|------|--------|------------|------|---------------------|-----------|
| HTTP server | `http.server.request.duration` | histogram | `s` | `http.request.method`, `url.scheme`, `http.route` (when routed), `http.response.status_code`, `error.type` (on error), `network.protocol.name` | stable |
| HTTP server | `http.server.active_requests` | updowncounter | `{request}` | `http.request.method`, `url.scheme` | development |
| HTTP server | `http.server.request.body.size`, `http.server.response.body.size` | histogram | `By` | as duration | development |
| HTTP client | `http.client.request.duration` | histogram | `s` | `http.request.method`, `server.address`, `server.port`, `http.response.status_code`, `error.type` | stable |
| RPC/gRPC | `rpc.server.call.duration`, `rpc.client.call.duration` | histogram | `s` | `rpc.system`, `rpc.service`, `rpc.method`, `rpc.response.status_code` | development |
| DB | `db.client.operation.duration` | histogram | `s` | `db.system.name`, `db.operation.name`, `db.collection.name`, `error.type` | stable |
| DB pool | `db.client.connection.count` (`db.client.connection.state` = `idle`/`used`), `db.client.connection.wait_time`, `db.client.connection.timeouts`, `db.client.connection.pending_requests` | updowncounter / histogram / counter / updowncounter | `{connection}`, `s`, `{timeout}` | `db.client.connection.pool.name` | development |
| Messaging | `messaging.client.operation.duration`, `messaging.client.sent.messages`, `messaging.client.consumed.messages`, `messaging.process.duration` | histogram / counter / counter / histogram | `s`, `{message}` | `messaging.system`, `messaging.operation.name`, `messaging.destination.name`, `error.type` | development |
| Go runtime | `go.memory.used`, `go.memory.limit`, `go.memory.allocated`, `go.memory.allocations`, `go.memory.gc.goal`, `go.goroutine.count`, `go.processor.limit`, `go.schedule.duration`, `go.config.gogc` | gauge / counter / histogram | `By`, `{goroutine}`, `s` | — (`go.memory.type` for `used`) | development, via `go.opentelemetry.io/contrib/instrumentation/runtime` |
| Process | `process.cpu.time`, `process.memory.usage`, `process.open_file_descriptor.count`, `process.uptime` | counter / updowncounter | `s`, `By`, `{count}` | `process.cpu.state` | development |

Semconv histogram bucket boundaries for HTTP, RPC and DB durations (seconds):
`0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10`. Set them with an
explicit-bucket `View` on the OTel SDK or `prometheus.HistogramOpts.Buckets`; for `client_golang`
prefer `NativeHistogramBucketFactor: 1.1` with the classic buckets kept for compatibility.

Domain metrics: `<app>.<component>.<measure>` in OTel form (`orders.reconcile.errors`,
`orders.queue.oldest_age`), the same attribute keys as semconv where one exists (`error.type`,
`messaging.destination.name`), and a `{thing}` unit for counts.

## Attribute Rules

| Attribute | Value | Never |
|-----------|-------|-------|
| `http.route` | router template `/orders/{id}` | raw path |
| `error.type` | typed error name, gRPC status, HTTP class `5xx`; `_OTHER` for unclassified | `err.Error()` |
| `server.address` | hostname from config | resolved IP per request |
| `db.operation.name` | `SELECT`, `INSERT`, stored procedure name | SQL text |
| `messaging.destination.name` | topic or queue name | partition + offset |
| user, tenant, order ids | log attribute or span attribute | metric attribute |

Cardinality budget per metric = product of the attribute cardinalities × instances. Write it in the
catalogue; anything over a few hundred series per instance needs a reason.

## OTLP to Prometheus Translation

The collector's Prometheus exporters and `go.opentelemetry.io/otel/exporters/prometheus` apply the
same rules:

| OTel | Prometheus |
|------|------------|
| `.` in names | `_` |
| unit `s`, `By`, `ms` | suffix `_seconds`, `_bytes`, `_milliseconds` |
| unit `1` on a gauge | suffix `_ratio` |
| counter (monotonic sum) | suffix `_total` (after the unit suffix: `_seconds_total`) |
| `{request}` style annotations | dropped |
| resource attributes | `target_info{job, instance, service_name, ...}` gauge = 1 |
| instrumentation scope | `otel_scope_name`, `otel_scope_version` labels on every series |
| attribute keys with `.` | `_` (`http_route`, `error_type`) |

So `http.server.request.duration` (histogram, `s`) scrapes as
`http_server_request_duration_seconds_bucket`, `_sum`, `_count`, and `messaging.client.sent.messages`
(counter) as `messaging_client_sent_messages_total`.

Switching suffixes off (only when the project already has unsuffixed names and dashboards):
`prometheus.WithoutUnits()`, `prometheus.WithoutCounterSuffixes()`, `prometheus.WithoutScopeInfo()`,
`prometheus.WithoutTargetInfo()` on the Go exporter; `add_metric_suffixes: false` on the collector's
`prometheus` exporter. Dashboards and rules must use whichever form the pipeline emits; the catalogue
records the Prometheus name next to the OTel name.

## Bootstrap Snippets

Both compile as `examples/bootstrap/main.go`.

OpenTelemetry SDK, OTLP to the collector plus a Prometheus scrape endpoint:

```go
exp, err := otlpmetricgrpc.New(ctx)                 // OTEL_EXPORTER_OTLP_ENDPOINT from env
promExp, err := prometheus.New()                     // registers on prometheus.DefaultRegisterer
provider := sdkmetric.NewMeterProvider(
    sdkmetric.WithReader(sdkmetric.NewPeriodicReader(exp)),
    sdkmetric.WithReader(promExp),
    sdkmetric.WithResource(res),                     // service.name, service.version, deployment.environment.name
    sdkmetric.WithView(sdkmetric.NewView(
        sdkmetric.Instrument{Name: "http.server.request.duration"},
        sdkmetric.Stream{Aggregation: sdkmetric.AggregationExplicitBucketHistogram{Boundaries: semconvBuckets}},
    )),
)
otel.SetMeterProvider(provider)
_ = runtime.Start(runtime.WithMinimumReadMemStatsInterval(time.Second))
mux.Handle("/metrics", promhttp.Handler())
handler := otelhttp.NewHandler(mux, "server", otelhttp.WithMetricAttributesFn(routeAttr))
```

`client_golang` only:

```go
reqDuration := promauto.With(reg).NewHistogramVec(prometheus.HistogramOpts{
    Name:    "http_server_request_duration_seconds",
    Help:    "HTTP server request duration.",
    Buckets: semconvBuckets,
    NativeHistogramBucketFactor: 1.1,
}, []string{"http_request_method", "http_route", "http_response_status_code"})
```

## RED in PromQL with semconv names

```promql
# rate per route
sum by (http_route) (rate(http_server_request_duration_seconds_count{service_name="$service"}[5m]))
# error ratio
sum(rate(http_server_request_duration_seconds_count{service_name="$service", http_response_status_code=~"5.."}[5m]))
  / sum(rate(http_server_request_duration_seconds_count{service_name="$service"}[5m]))
# p99
histogram_quantile(0.99, sum by (le, http_route) (rate(http_server_request_duration_seconds_bucket{service_name="$service"}[5m])))
# join version onto anything
sum by (service_version) (up * on (job, instance) group_left (service_version) target_info)
```

## Sources

- OpenTelemetry semantic conventions (HTTP, RPC, database, messaging, runtime, process metrics;
  attribute requirement levels) — https://opentelemetry.io/docs/specs/semconv/
- Prometheus and OpenMetrics compatibility (the OTLP → Prometheus translation rules) —
  https://opentelemetry.io/docs/specs/otel/compatibility/prometheus_and_openmetrics/
- Prometheus metric and label naming — https://prometheus.io/docs/practices/naming/
- Prometheus histograms, native histograms — https://prometheus.io/docs/concepts/metric_types/ ,
  https://prometheus.io/docs/specs/native_histograms/
- OpenTelemetry Go SDK and contrib (`otelhttp`, `runtime`, Prometheus exporter) —
  https://pkg.go.dev/go.opentelemetry.io/otel , https://pkg.go.dev/go.opentelemetry.io/contrib
- `client_golang` — https://pkg.go.dev/github.com/prometheus/client_golang/prometheus
