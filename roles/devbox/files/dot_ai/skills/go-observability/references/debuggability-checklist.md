# Debuggability Checklist

Read the code as the person on call. Each heuristic lists the pattern, how to find it, and the
signal that closes the gap. Record findings in `observability_audit.md` ranked by "would have hidden
an incident", then cost.

## 1. Swallowed Errors

| Pattern | Find | Signal |
|---------|------|--------|
| `_ = f()` on a call that returns `error` | `ast-grep -p '_ = $F($$$)'` then filter calls returning error via `go vet`/LSP | counter `<app>.<component>.errors{error.type}` + one log line |
| `if err != nil { return }` or `return nil` without log or metric | `ast-grep -p 'if err != nil { return $$$ }'`, inspect bodies with no `log`/`metric` call | same |
| `recover()` without a counter | `grep -rn 'recover()' --include='*.go'` | counter `<app>.panics{error.type}`, log with stack, re-panic or return error |
| `errors.Is(err, context.Canceled)` returning silently | `grep -rn 'context.Canceled\|context.DeadlineExceeded'` | counter with `error.type="context.Canceled"`; cancellations are a signal when they spike |
| `default:` in a switch over an enum that logs nothing | `ast-grep -p 'switch $X { $$$ default: $$$ }'` | counter `<app>.unexpected_branch{where}` |
| Error logged at every layer | grep `log.*err` density per package | one log at the handling boundary with the wrapped chain; others wrap and return |

## 2. Invisible Background Work

| Pattern | Find | Signal |
|---------|------|--------|
| `go func()` in constructors with no stop or metric | `ast-grep -p 'go func() { $$$ }()'` | `UpDownCounter` of running workers; `last_success_timestamp_seconds` gauge per loop |
| `time.NewTicker` loops | `grep -rn 'NewTicker\|time.Tick('` | duration histogram per iteration, last success time, error counter |
| Retry loops | `grep -rn -i 'retry\|backoff'` | `retries_total`, `retries_exhausted_total{error.type}` |
| Queue consumers | handlers of `Consume`, `Receive`, `Poll` | `messaging.process.duration`, depth gauge, age of oldest message, consumed counter |
| Caches | `sync.Map`, `lru`, `ristretto`, `groupcache` | hit/miss counters, size gauge, eviction counter |

## 3. Unmeasured Waits

| Pattern | Find | Signal |
|---------|------|--------|
| `sql.DB` pool, `pgxpool`, Redis pool | `SetMaxOpenConns`, `pgxpool.New` | `db.client.connection.*` via the driver's stats hook (`db.Stats()` observable gauges) |
| `semaphore.Weighted`, buffered channel as limiter | `grep -rn 'semaphore\|make(chan' ` | wait-time histogram, in-use updowncounter |
| Timeouts configured, hits not counted | `context.WithTimeout`, `http.Client{Timeout`} | counter with `error.type="DeadlineExceeded"` per operation |
| Locks held across I/O | `mu.Lock()` followed by a call with `ctx` | lock wait histogram when contention is suspected; otherwise a finding, not a metric |

## 4. Broken Correlation

| Pattern | Find | Signal / fix |
|---------|------|--------------|
| `context.Background()` or `context.TODO()` on a request path | `grep -rn 'context.Background()\|context.TODO()' --include='*.go'`, exclude `main` and tests | pass the request context; `context.WithoutCancel` when the work must outlive the request |
| Goroutines started without the parent context | see 2 | pass `ctx`; the span continues |
| Messages published without trace headers | publisher code | inject with `otel.GetTextMapPropagator().Inject(ctx, carrier)`; extract on consume |
| Log lines without `trace_id` | `slog` handler setup | handler wrapper adding `trace_id`, `span_id` from `trace.SpanContextFromContext` |
| Outbound HTTP without `otelhttp.NewTransport` | `http.Client{` without `Transport: otelhttp` | wrap the transport |

## 5. Unbounded Labels

| Pattern | Find | Fix |
|---------|------|-----|
| `WithLabelValues(id)`, attribute from a path or id | `grep -rn 'WithLabelValues\|attribute.String('` and inspect arguments | route template, error class, enum; ids go to logs and spans |
| `r.URL.Path` as a label | `grep -rn 'URL.Path'` near metrics | router's route template (`chi.RouteContext`, `mux.CurrentRoute`, gin `FullPath()`) |
| `err.Error()` as a label | `grep -rn 'err.Error()' ` near metrics | typed error name or class |

## 6. Health That Lies

| Pattern | Check | Fix |
|---------|-------|-----|
| One `/health` for liveness and readiness | handler returns 200 unconditionally | `/livez` process-only; `/readyz` checks the dependencies the service cannot work without, with a per-check gauge |
| No `build_info` | no gauge with version/commit | `build_info{version, commit, go_version} = 1` at startup |
| Readiness flips on every dependency hiccup | readiness checks optional dependencies | only hard dependencies gate readiness; optional ones are gauges |

## 7. Logs That Cannot Be Queried

| Pattern | Find | Fix |
|---------|------|-----|
| Ids inside the message text | `Sprintf(".*%s.*", id)` into a log call | `slog.String("order_id", id)`, message constant |
| `ERROR` for expected conditions (validation failures, 404) | grep `Error(` in handlers | `INFO` or `WARN`; `ERROR` means a person acts |
| Multi-line or free-form messages | log calls with `\n` or long format strings | one line, attributes |
| Secrets in attributes | `token`, `password`, `authorization` near log calls | redact at the logger (`slog.LogValuer`) |

## Failure-Mode Table

The audit's deliverable, one row per component and failure:

| Component | Failure | Detect today | Localise today | Gap class | Proposed signal | Layer | Cost |
|-----------|---------|--------------|----------------|-----------|-----------------|-------|------|

Gap classes: `blind` (nothing would show), `late` (shows after users complain), `noisy` (shows but
buried), `unlocalised` (shows but not where), `covered`. Cost is `trivial` (one counter), `small`
(one component), `design` (needs a telemetry bootstrap or a schema change).
