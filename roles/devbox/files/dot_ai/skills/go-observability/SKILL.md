---
name: go-observability
description: >
  Observability for Go services: debuggability audits, semconv-named metrics, logs and spans,
  three-layer alerting (SLO burn rate, technology, code detectors) with promtool tests, SLO
  derivation, Grafana dashboards as Go code. Use when asking how a service would be debugged,
  adding instrumentation, or when Prometheus, Grafana, OTel, SLO or PromQL is mentioned.
problem: "Dashboards and alerts get built from whatever metrics happen to exist, cover the product's model rather than its failure modes, and leave the 3am debugging question unanswered."
related: [go-engineer, lint-discipline, observability_engineer]
---

# Go Observability

The question every signal answers: **when this breaks at 3am, how do we see it, localise it and
know what to do?** A metric, log line or span without an answer to that question is cost without
value. Product dashboards describe the product's model; outages happen in reality. Reality is
covered by the technology and code layers below, which is where most of the signals live.

## Table of Contents

- [Signal Catalogue](#signal-catalogue)
- [Debuggability Audit](#debuggability-audit)
- [Instrumentation in Go](#instrumentation-in-go)
- [Three Alert Layers](#three-alert-layers)
- [SLO Maturity Ladder](#slo-maturity-ladder)
- [Dashboards as Go Code](#dashboards-as-go-code)
- [Validation Gates](#validation-gates)
- [Artefact Layout](#artefact-layout)
- [Pitfalls](#pitfalls)

References: `references/debuggability-checklist.md` (audit heuristics and grep patterns),
`references/semconv-prometheus.md` (metric names, attributes, Prometheus translation),
`references/alert-rules.md` (rule templates, burn-rate maths, promtool tests, runbook template),
`references/foundation-sdk.md` (dashboard and Grafana-managed alert code).

---

## Signal Catalogue

The first artefact of any observability work is `observability_design.md`, a catalogue. Nothing is
instrumented, charted or alerted on without a row:

| ID | Failure it reveals | Decision it supports | Signal | Type | Name | Attributes | Budget | Layer |
|----|--------------------|----------------------|--------|------|------|------------|--------|-------|
| S-1 | Checkout latency regression | page vs ticket, rollback | request duration | histogram | `http.server.request.duration` | `http.request.method`, `http.route`, `http.response.status_code` | 40 series | product |
| S-2 | DB pool exhausted | scale pool / find leak | pool wait time | histogram | `db.client.connection.wait_time` | `db.client.connection.pool.name` | 4 series | technology |
| S-3 | Swallowed error in `reconcile()` | know a silent path fired | counter | counter | `app.reconcile.errors` | `error.type` | 10 series | code |

Columns are mandatory. "Budget" is the maximum series count for that metric on one instance, computed
from attribute cardinalities; an attribute with unbounded values (user id, path with parameters,
free-text error message) never appears. Three layers: **product** (user journeys and SLOs),
**technology** (saturation and dependency health), **code** (detectors for paths that should be rare).

## Debuggability Audit

Read the system as the person on call. For each component, fill a failure-mode table:

| Component | What can fail | How we would know today | How we would localise it | Gap | Proposed signal |
|-----------|---------------|-------------------------|--------------------------|-----|-----------------|
| `orders.Worker` | consumer stalls | nothing; lag not exported | — | blind | consumer lag gauge, age of oldest message |
| `payments.Client` | upstream 5xx burst | error log per call (unbounded) | no per-dependency metric | noisy, no metric | `rpc.client.call.duration` with `error.type` |

Heuristics that find gaps fastest, with grep and ast-grep patterns in
`references/debuggability-checklist.md`:

1. **Swallowed errors**: `_ = f()`, `if err != nil { return }` without log or metric, `recover()`
   without a counter, `errors.Is(..., context.Canceled)` branches that return silently.
2. **Invisible background work**: goroutines started in constructors with no lifetime metric, tickers
   with no "last successful run" timestamp, retry loops without an exhausted counter.
3. **Unmeasured waits**: pools, semaphores, channel sends with no wait histogram; timeouts configured
   but never counted when hit.
4. **Broken correlation**: `context.Background()` inside request paths, goroutines and queue
   consumers that drop the span context, log lines without `trace_id`.
5. **Unbounded labels**: ids, raw URLs, error strings used as attribute values.
6. **Health that lies**: liveness and readiness merged, readiness that does not check dependencies,
   no `build_info`.
7. **Logs that cannot be queried**: `fmt.Sprintf` messages carrying the entity id in the text, levels
   used for emphasis rather than action.

Every gap becomes a catalogue row with the proposed signal; the audit report ranks gaps by "would
have hidden an incident" first, cost second.

## Instrumentation in Go

**Which SDK**: follow the project. A `MeterProvider`/`TracerProvider` in `main` means the OpenTelemetry
SDK; `prometheus.NewRegistry` or `promauto` means `client_golang`; nothing means the OpenTelemetry SDK
with an OTLP exporter to the collector and, when Prometheus scrapes directly, the Prometheus exporter.
Never mix two metric SDKs in one process. Names follow semconv either way; `client_golang` users write
the translated Prometheus name directly (`http_server_request_duration_seconds`).

**Naming**: semconv names for anything semconv covers (HTTP, RPC, DB, messaging, runtime, process);
`<app>.<component>.<thing>` for domain metrics. Units in the instrument, not in the name, for OTel
(`s`, `By`, `{request}`); Prometheus names carry the unit suffix after translation
(`_seconds`, `_bytes`, `_total`). Table and translation rules in `references/semconv-prometheus.md`.

**Instruments**:

| Measure | Instrument | Rule |
|---------|------------|------|
| Events that happen | Counter (`_total`) | monotonic; rate it, never read it raw |
| Duration, size | Histogram | seconds; semconv buckets for HTTP; native/exponential histograms when the backend supports them |
| In-flight, pool in use | UpDownCounter | add on start, subtract on end, in `defer` |
| Depth, age, lag, last success time | Gauge (observable) | callback reads the real value; "age of oldest" beats "count" |
| Version, config | Gauge `build_info{version,commit}` = 1 | one series, joins everywhere |

**Errors**: one `error.type` attribute holding the error class (`errors.As` to a typed error,
`status.Code` for gRPC, the HTTP status class otherwise), never the message. A `recover()` increments
`app.panics` with `error.type` and re-raises or returns, and logs once with the stack.

**Logs** (`log/slog` unless the project has a logger): one line per failure at the boundary that
handles it, carrying the wrapped error chain; no line at each layer the error passes through.
Attributes, not text, for ids (`slog.String("order_id", id)`); `trace_id` and `span_id` from
`trace.SpanContextFromContext(ctx)` added by a handler wrapper. Levels mean action: `ERROR` needs a
person, `WARN` degrades, `INFO` is state change, `DEBUG` is off in production.

**Spans**: `otelhttp` and `otelgrpc` at the edges, a span per outbound call and per DB operation, the
context carried through goroutines explicitly and through queues in message headers
(`propagation.TextMapCarrier`). Exemplars link histograms to traces when the backend supports them.

**Code-layer detectors** are cheap counters placed where "this should not happen" lives: panics
recovered, swallowed error branches, retries exhausted, circuit breaker opened, dead-letter writes,
default branches of exhaustive switches, runtime invariant violations (`app.invariant.violations`
with `invariant` as the attribute, the same `INV-n` ids as the domain model).

## Three Alert Layers

| Layer | Source | Examples | Default severity | Typical count |
|-------|--------|----------|------------------|---------------|
| Product | user journeys → SLI → SLO → burn rate | checkout availability, search latency | page on fast burn, ticket on slow | 2–6 |
| Technology | saturation and dependency health | pool exhausted, consumer lag age, disk < 10 %, GC pause, goroutine growth, restarts, cert expiry, dependency error rate | ticket; page when the runway is under an hour | 10–20 |
| Code | detectors above | panics, swallowed errors by class, retries exhausted, breaker open, DLQ rate, invariant violations | ticket; page for invariant violations | 5–15 |

Every rule carries labels `severity`, `layer`, `maturity` and annotations `summary`, `description`,
`runbook_url`. The design document lists the three layers separately and shows coverage per
component: a component with product alerts only is unprotected in practice.

Burn-rate alerts use two windows per severity so a short spike neither pages nor hides:

| Severity | Budget consumed | Long window | Short window | Burn rate |
|----------|-----------------|-------------|--------------|-----------|
| page | 2 % in 1 h | 1h | 5m | 14.4 |
| page | 5 % in 6 h | 6h | 30m | 6 |
| ticket | 10 % in 3 d | 3d | 6h | 1 |

Expressions, recording rules and the promtool test for each are in `references/alert-rules.md`.

## SLO Maturity Ladder

Alerts are only as honest as the SLO behind them. State the stage in the design document and in
the `maturity` label:

| Stage | What exists | Alerts allowed | Exit criterion |
|-------|-------------|----------------|----------------|
| `none` | no SLI data | technology and code layers only | baseline instrumented |
| `baseline` | SLIs emitted; black-box probes on the key journeys | as above, plus a conservative placeholder burn-rate at `ticket` | 2–4 weeks of data |
| `observed` | percentiles over the observation window | burn-rate at proposed SLO, `ticket` only | owners accept the SLO |
| `agreed` | SLO document signed off | full three layers, pages enabled | — |

Deriving the SLO from a baseline: take the 28-day p99 (latency) or success ratio (availability),
subtract headroom that the owners can live with (a latency target 20 % above observed p99, an
availability target one nine below observed), present the number with the traffic it was measured
on, and let the owner decide. Probes (a blackbox exporter or a small Go probe job) give a signal that
does not depend on the service's own instrumentation being right.

For an existing system without instrumentation: audit first, then propose the baseline set
(RED per route and consumer, saturation per resource, the code-layer detectors), then the ladder.

## Dashboards as Go Code

One dashboard per service, generated by a Go program using the Grafana Foundation SDK and committed
with its rendered JSON. Rows, top to bottom:

1. **Overview** — SLO status and burn rate per journey, deploy marker, `build_info` version
2. **Traffic** — RED per route or consumer: rate, error ratio by `error.type`, duration p50/p95/p99
3. **Dependencies** — outbound RED per dependency, pool usage and wait time
4. **Saturation** — CPU, memory, GC, goroutines, file descriptors, queue depth and age
5. **Detectors** — the code-layer counters, one panel each, zero is the expected value
6. **Runtime and process** — `go.*` and `process.*`

Panel rules: a unit on every panel, legend from the attribute that matters (`{{http_route}}`), series
count bounded by the catalogue budget, a link to the runbook on alerting panels, `$datasource` and
`$service` variables, no panel without a catalogue row. Code in `references/foundation-sdk.md`.

Jsonnet and Grafonnet are not used; when a repository has them, raise it and still produce Go.

## Validation Gates

Run before reporting, in this order; a failure stops the hand-off:

```bash
go build ./... && go vet ./...                         # instrumentation and dashboard code compile
promtool check rules observability/rules/*/alerts.yaml observability/rules/*/recording.yaml
promtool test rules observability/rules/*/tests/*.yaml  # every alert has a firing and a non-firing case
go run ./observability/dashboards -o observability/dashboards/out && jq empty observability/dashboards/out/*.json
```

`promtool` ships with the `prometheus` Homebrew formula this machine installs; `go install ...@latest`
does not work for it (the upstream `go.mod` carries `replace` directives), so when it is missing
elsewhere build it from a shallow clone of the release tag with `go build ./cmd/promtool`. `gcx` (Grafana CLI on this machine) can run PromQL
against a configured datasource to confirm that a query returns series before it goes on a panel;
read-only queries only.

Sandbox rule: artefacts are files in the repository. Nothing deploys to Grafana, Alertmanager or
Prometheus from the agent; deployment instructions go in the hand-off.

## Artefact Layout

```
${PROJECT_DIR}/observability_audit.md        # failure-mode table, ranked gaps (audit mode)
${PROJECT_DIR}/observability_design.md       # signal catalogue, alert layers, SLO stage, dashboard outline
<repo>/observability/
  dashboards/<service>/main.go               # Foundation SDK program
  dashboards/out/<service>.json              # rendered, committed
  rules/<service>/alerts.yaml                # PrometheusRule or plain rule file, per project
  rules/<service>/recording.yaml
  rules/<service>/tests/alerts_test.yaml     # promtool unit tests
  runbooks/<Alertname>.md
```

## Pitfalls

- A histogram with `http.route` set to the raw path explodes; use the router's template.
- `rate()` over a counter that resets on deploy is fine; `increase()` over a gauge is a bug.
- `error.type` from `err.Error()` is a cardinality leak and a secret leak.
- Alerting on cause (`cpu > 90%`) pages for things users never see; the technology layer tickets it,
  the product layer pages.
- A `for:` shorter than two scrape intervals flaps; longer than the burn window hides.
- Dashboards with 60 panels are not read at 3am; six rows, the first one answers "is it us".
- Instrumenting a codebase that has no telemetry bootstrap is a design decision: bring the
  bootstrap as its own catalogue row and work stream, do not sprinkle instruments that nothing exports.
