---
name: go-observability
description: >
  Observability for Go services: debuggability audits, semconv metrics, logs and spans,
  three-layer alerting with promtool tests, SLO derivation, Grafana dashboards as Go code. Use
  when asking how a service would be debugged, adding instrumentation, or when Prometheus,
  Grafana, OTel, SLO, alerts or PromQL is mentioned.
problem: "Dashboards and alerts get built from whatever metrics exist, cover the product's model rather than its failure modes, and leave the 3am debugging question unanswered."
related: [go-engineer, lint-discipline, observability_engineer]
---

# Go Observability

The question every signal answers: when this breaks at 3am, how do we see it, localise it and
know what to do? Product dashboards describe the product's model; outages happen in reality,
which the technology and code layers below cover.

## Methods

| Method | Applies to | Gives |
|--------|-----------|-------|
| RED (rate, errors, duration) | request-driven services, consumers | product and dependency rows |
| USE (utilisation, saturation, errors) | every resource: CPU, memory, pools, queues, disks | technology rows |
| Four golden signals | the overview row of a dashboard | "is it us" |
| SLO, error budget, burn rate | user journeys | product alerts, the maturity ladder |
| Symptom-based alerting | all layers | pages for what users feel, tickets for causes |
| Failure-mode table | the audit | the rows nobody asked for |

## Signal catalogue

`observability_design.md` has one row per signal, and nothing is instrumented, charted or
alerted on without a row:

| ID | Failure revealed | Decision supported | Measure | Instrument | Name | Attributes | Budget | Layer |
|----|------------------|--------------------|---------|------------|------|------------|--------|-------|

Budget = distinct attribute combinations per instance; a histogram costs each × (buckets + 2)
series on scrape. Attribute values are bounded: route template not path, error class not
message, enum not id. Layers: product (journeys, SLOs), technology (saturation, dependencies),
code (detectors for paths that should be rare).

## Audit

One row per component and failure: Component | Failure | Detect today | Localise today | Gap
(`blind`, `late`, `noisy`, `unlocalised`, `covered`) | Proposed signal | Layer | Cost (`trivial`,
`small`, `design`). Rank by "would have hidden an incident", then cost. Heuristics with the
pattern that finds them:

1. Swallowed errors: `ast-grep -p '_ = $F($$$)'` (then `errcheck -blank`), `if $$$; err != nil { $$$ }`
   bodies without a log or metric call, `recover()` without a counter, silent `context.Canceled` branches.
2. Invisible background work: `go $F($$$)` without a lifetime metric, tickers without a
   last-success timestamp, retry loops without an exhausted counter, consumers without lag.
3. Unmeasured waits: pools, semaphores, buffered channels with no wait histogram; timeouts
   configured and never counted.
4. Broken correlation: `context.Background()` on request paths, goroutines and publishers that
   drop the span context, log lines without `trace_id`.
5. Unbounded labels: `WithLabelValues(`/`attribute.String(` fed ids, `URL.Path`, `err.Error()`.
6. Health that lies: one handler for liveness and readiness; no `build_info`.
7. Logs that cannot be queried: ids in the message text, `ERROR` for expected conditions.

## Instrumentation

- SDK: follow the project (`MeterProvider` → OTel; `prometheus.NewRegistry`/`promauto` →
  client_golang); nothing → OTel SDK exporting over OTLP, plus the Prometheus reader only when
  Prometheus scrapes the service. Never two metric SDKs in one process. A service with no
  bootstrap gets one as its own catalogue row and work-stream item, never instruments sprinkled in.
- Names: semconv where it covers the area, `<app>.<component>.<measure>` otherwise; units on the
  instrument (`s`, `By`, `{request}`), never in the name.
- Instruments: counter for events (rate it), histogram for durations and sizes (seconds), up-down
  counter for in-flight, observable gauge for depth, age, lag, last success; `build_info{version,
  commit} = 1`.
- Errors: `error.type` is the class (`errors.As` target, gRPC code, status string as emitted by
  otelhttp); `recover()` counts `app.panics{error.type}` and logs once with the stack.
- Logs (`log/slog`): one line per failure at the boundary that handles it, attributes not text
  for ids, `trace_id`/`span_id` from the context, `ERROR` means a person acts.
- Spans: `otelhttp`/`otelgrpc` at the edges, a span per outbound call and DB operation, context
  carried through goroutines and in message headers.
- Code-layer detectors: panics recovered, swallowed-error branches, retries exhausted, breaker
  open, dead-letter writes, impossible `default` branches, `app.invariant.violations{invariant}`
  with the domain model's `INV-n` ids. Zero is their expected value.

Semconv names as of v1.43 (Prometheus form after translation):

| Area | Name | Instrument, unit | Attributes | Status |
|------|------|------------------|------------|--------|
| HTTP server | `http.server.request.duration` → `http_server_request_duration_seconds` | histogram, s | `http.request.method`, `url.scheme`, `http.route`, `http.response.status_code`, `error.type` | stable |
| HTTP client | `http.client.request.duration` | histogram, s | `http.request.method`, `server.address`, `server.port`, `http.response.status_code`, `error.type` | stable |
| DB | `db.client.operation.duration` | histogram, s | `db.system.name`, `db.operation.name`, `db.collection.name`, `error.type` | stable |
| DB pool | `db.client.connection.count{db.client.connection.state}`, `.max`, `.wait_time`, `.timeouts`, `.pending_requests` | up-down / histogram / counter | `db.client.connection.pool.name` | development |
| RPC | `rpc.server.call.duration`, `rpc.client.call.duration` | histogram, s | `rpc.system.name`, `rpc.method`, `rpc.response.status_code`, `error.type` | development |
| Messaging | `messaging.client.operation.duration`, `messaging.client.sent.messages`, `messaging.client.consumed.messages`, `messaging.process.duration` | histogram / counter | `messaging.system`, `messaging.operation.name`, `messaging.destination.name`, `error.type` | development |
| Go runtime (`contrib/instrumentation/runtime`) | `go.memory.used`, `go.memory.limit`, `go.goroutine.count`, `go.schedule.duration` (scheduler latency, not GC pause), `go.config.gogc` | up-down / histogram | `go.memory.type` | development |

Translation (collector and the Go exporter alike): `.` → `_`; unit suffix `_seconds`, `_bytes`;
counters `_total` after the unit; gauges with unit `1` get `_ratio`; resource attributes become
`target_info{job, instance, service_name, ...}`; scope becomes `otel_scope_name`/`_version`
labels. Pin `prometheus.WithTranslationStrategy(otlptranslator.UnderscoreEscapingWithSuffixes)`
explicitly (today's default, announced to change); `WithoutUnits`/`WithoutCounterSuffixes` are
deprecated. HTTP and RPC bucket boundaries come with the semconv instruments
(`httpconv.NewServerRequestDuration`); `otelhttp` sets `http.route` from `r.Pattern` itself.

## Alerts

| Layer | Source | Examples | Severity |
|-------|--------|----------|----------|
| product | journeys → SLI → SLO → burn rate | checkout availability, search latency | page on fast burn, ticket on slow |
| technology | saturation, dependency health | pool exhausted, consumer stalled, restarts, disk runway, cert expiry, dependency error rate | ticket; page when the runway is under an hour |
| code | detectors above | panics, retries exhausted, breaker open, DLQ, invariant violations | ticket; page on invariant violation |

Every component has all three layers or a one-line reason. Every rule carries labels `severity`
(`page`/`ticket`) and `layer`, annotations `summary`, `description`, `runbook_url`, a runbook
stub, and a promtool unit test with a firing and a non-firing case. Product rules also carry
`maturity` (§SLO ladder). A rule that fires weekly is a bug or a threshold to revisit, never a
silence. PromQL joins (`and`, `/`) need identical label sets: aggregate both sides or use
`on (label)`.

Burn-rate alerts over a 30-day window, `burn = budget_fraction × 720 h / long_window_h`:

| Severity | Budget consumed | Long | Short | Burn | `for` |
|----------|-----------------|------|-------|------|-------|
| page | 2 % in 1 h | 1h | 5m | 14.4 | 2m |
| page | 5 % in 6 h | 6h | 30m | 6 | 15m |
| ticket | 10 % in 3 d | 3d | 6h | 1 | 1h |

Expression: `sli:errors:ratio_rate1h > 14.4 × (1 − SLO) and sli:errors:ratio_rate5m > 14.4 ×
(1 − SLO)` over recording rules; latency SLIs are the ratio of requests slower than the
threshold. promtool series syntax: `a b c`, `0+10x5`, `1x60`, `_`, `stale`.

## SLO ladder

| Stage | Exists | Alerts | Exit |
|-------|--------|--------|------|
| `none` | no SLI data | technology and code only | baseline instrumented |
| `baseline` | SLIs emitted, black-box probes on key journeys | plus a placeholder burn-rate at `ticket` | 4 weeks of data |
| `observed` | percentiles over the window | burn-rate at the proposed SLO, `ticket` | owners accept |
| `agreed` | SLO signed off | all layers, pages on | — |

Propose from a baseline: the next standard availability target below observed (99.99 → 99.95 →
99.9 → 99.5 → 99), latency 20 % above observed p99; both are defaults the owner decides.

## Dashboards

One Go program on the Grafana Foundation SDK (`github.com/grafana/grafana-foundation-sdk/go`,
packages `dashboard`, `timeseries`, `stat`, `prometheus`, `cog`), one file per service, a `-o`
flag that renders `<uid>.json`, rendered JSON committed. Rows: overview (SLO status, burn, `build_info`), traffic (RED per route
or consumer), dependencies, saturation, detectors, runtime. Every panel has a unit, a legend from
the attribute that matters, a bounded series count, a catalogue id in its description; alerting
panels link the runbook. Jsonnet is not used.

## Gates

```bash
go build ./... && go vet ./...
promtool check rules observability/rules/*/*.yaml
promtool test rules observability/rules/*/tests/*.yaml
go run ./observability/dashboards -o observability/dashboards/out && jq empty observability/dashboards/out/*.json
```

`promtool` comes with the `prometheus` formula; `gcx` runs read-only PromQL against a datasource
to confirm a query returns series. Artefacts are repository files: `observability_audit.md`,
`observability_design.md`, instrumentation diff, `observability/{dashboards,rules/<service>/
{alerts,recording}.yaml,rules/<service>/tests/,runbooks/}`. Nothing deploys from here.

## Sources

- Google SRE Book ch. 6, SRE Workbook ch. 2 and 5 — https://sre.google/books/ ; Ewaschuk, *My
  Philosophy on Alerting*
- Wilkie, *The RED Method*; Gregg, *The USE Method* — https://www.brendangregg.com/usemethod.html
- OpenTelemetry semantic conventions and Prometheus compatibility — https://opentelemetry.io/docs/specs/
- Prometheus practices, unit-testing rules — https://prometheus.io/docs/practices/
- Grafana Foundation SDK — https://github.com/grafana/grafana-foundation-sdk
- Majors, Fong-Jones, Miranda, *Observability Engineering* (O'Reilly, 2022)
