---
name: observability
description: >
  Observability patterns for logging, metrics, tracing, and OpenTelemetry architecture
  in both Go and Python. Covers semantic conventions, cardinality management, Collector
  patterns, distributed tracing, and RED/USE metrics. Triggers on: logging, metrics,
  tracing, observability, zerolog, prometheus, opentelemetry, semantic conventions,
  cardinality, collector, distributed tracing, RED metrics, USE metrics.
---

# Observability Patterns

Logging, metrics, and tracing patterns for production systems.

---

## Logging Philosophy

### Log Messages Are for Humans, Fields Are for Machines

```python
# ❌ BAD — entity ID only in message (not queryable)
logger.info(f"Processing order {order_id}")

# ✅ GOOD — entity ID in both (readable AND queryable)
logger.info(
    f"processing order {order_id}",
    extra={"order_id": order_id, "user_id": user_id},
)
```

```go
// ❌ BAD — entity ID only in message
log.Info().Msgf("Processing order %s", orderID)

// ✅ GOOD — entity ID in both
log.Info().
    Str("order_id", orderID).
    Str("user_id", userID).
    Msgf("processing order %s", orderID)
```

### Log Levels

| Level | Use For | Example |
|-------|---------|---------|
| DEBUG | Development, troubleshooting | Request/response details |
| INFO | Normal operations | Request started, completed |
| WARN | Recoverable issues | Retry succeeded, fallback used |
| ERROR | Failures requiring attention | Request failed, operation aborted |

---

## Structured Logging

### Go (zerolog)

```go
import "github.com/rs/zerolog"

// Setup
logger := zerolog.New(os.Stderr).
    With().
    Timestamp().
    Caller().
    Logger()

// Basic logging
logger.Info().
    Str("order_id", orderID).
    Int("item_count", len(items)).
    Msg("processing order")

// Error logging with stack trace
logger.Error().
    Err(err).
    Stack().
    Str("order_id", orderID).
    Msg("order processing failed")

// With context
ctx := logger.With().Str("request_id", reqID).Logger().WithContext(ctx)
log := zerolog.Ctx(ctx)
log.Info().Msg("handling request")
```

### Python (structlog or logging)

```python
import logging
import structlog

# Standard logging with extra
logger = logging.getLogger(__name__)

logger.info(
    "processing order",
    extra={
        "order_id": order_id,
        "item_count": len(items),
    },
)

# Error with exception
try:
    process(order)
except ProcessingError as e:
    logger.error(
        "order processing failed",
        exc_info=e,
        extra={"order_id": order_id},
    )

# Structlog alternative
log = structlog.get_logger()
log.info("processing order", order_id=order_id, item_count=len(items))
```

---

## Log Message Guidelines

### Format Rules

| Rule | Good | Bad |
|------|------|-----|
| Lowercase start | `"processing order"` | `"Processing order"` |
| No trailing punctuation | `"request completed"` | `"Request completed."` |
| Present tense action | `"processing order"` | `"processed order"` |
| Specific message | `"payment declined"` | `"error occurred"` |
| Include identifier | `"order {id} shipped"` | `"order shipped"` |

### What to Log

| Event | Log Level | Required Fields |
|-------|-----------|-----------------|
| Request received | INFO | request_id, path, method |
| Request completed | INFO | request_id, status, duration_ms |
| External call start | DEBUG | service, endpoint |
| External call end | DEBUG | service, endpoint, status, duration_ms |
| Retry attempt | WARN | attempt, max_attempts, error |
| Operation failed | ERROR | operation, error, entity_id |

### What NOT to Log

- Passwords, tokens, API keys
- Full request/response bodies (use DEBUG only)
- PII without redaction
- Health check requests (too noisy)
- Successful routine operations at INFO (use DEBUG)

---

## Error Logging

### Always Include Context

```go
// ❌ BAD — no context
log.Error().Err(err).Msg("failed")

// ❌ BAD — generic message
log.Error().Err(err).Msg("operation failed")

// ✅ GOOD — specific message with entity
log.Error().
    Err(err).
    Stack().
    Str("order_id", orderID).
    Str("user_id", userID).
    Msg("payment processing failed")
```

```python
# ❌ BAD — no context
logger.error("failed")

# ❌ BAD — no exc_info
logger.error(f"operation failed: {e}")

# ✅ GOOD — full context
logger.error(
    "payment processing failed",
    exc_info=e,
    extra={"order_id": order_id, "user_id": user_id},
)
```

### Error vs Exception

```python
# Use logger.exception() in except blocks (auto-includes traceback)
try:
    process(data)
except ProcessingError:
    logger.exception("processing failed")  # Includes full traceback

# Use logger.error() with exc_info when you have the exception
except ProcessingError as e:
    logger.error("processing failed", exc_info=e, extra={...})
```

---

## Request Tracing

### Correlation IDs

```go
// Middleware to add request ID
func RequestIDMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        requestID := r.Header.Get("X-Request-ID")
        if requestID == "" {
            requestID = uuid.New().String()
        }

        ctx := r.Context()
        logger := zerolog.Ctx(ctx).With().Str("request_id", requestID).Logger()
        ctx = logger.WithContext(ctx)

        w.Header().Set("X-Request-ID", requestID)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}
```

```python
# Flask middleware
@app.before_request
def add_request_id():
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    g.request_id = request_id
    g.logger = logger.bind(request_id=request_id)


@app.after_request
def add_request_id_header(response):
    response.headers["X-Request-ID"] = g.request_id
    return response
```

### Propagate to External Calls

```go
func (c *Client) Call(ctx context.Context, req Request) (*Response, error) {
    httpReq, _ := http.NewRequestWithContext(ctx, "POST", c.url, body)

    // Propagate request ID
    if requestID := ctx.Value("request_id"); requestID != nil {
        httpReq.Header.Set("X-Request-ID", requestID.(string))
    }

    return c.client.Do(httpReq)
}
```

---

## Metrics (Prometheus)

### Counter vs Gauge vs Histogram

| Type | Use For | Example |
|------|---------|---------|
| Counter | Monotonically increasing | Requests total, errors total |
| Gauge | Values that go up/down | Active connections, queue size |
| Histogram | Distributions | Request duration, response size |

### Go

```go
import "github.com/prometheus/client_golang/prometheus"

var (
    requestsTotal = prometheus.NewCounterVec(
        prometheus.CounterOpts{
            Name: "http_requests_total",
            Help: "Total HTTP requests",
        },
        []string{"method", "path", "status"},
    )

    requestDuration = prometheus.NewHistogramVec(
        prometheus.HistogramOpts{
            Name:    "http_request_duration_seconds",
            Help:    "HTTP request duration in seconds",
            Buckets: prometheus.DefBuckets,
        },
        []string{"method", "path"},
    )
)

func init() {
    prometheus.MustRegister(requestsTotal, requestDuration)
}

// Usage in middleware
func metricsMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()

        // Wrap response writer to capture status
        ww := &responseWriter{ResponseWriter: w, status: 200}
        next.ServeHTTP(ww, r)

        duration := time.Since(start).Seconds()
        requestsTotal.WithLabelValues(r.Method, r.URL.Path, strconv.Itoa(ww.status)).Inc()
        requestDuration.WithLabelValues(r.Method, r.URL.Path).Observe(duration)
    })
}
```

### Python

```python
from prometheus_client import Counter, Histogram, Gauge

requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)

active_connections = Gauge(
    "active_connections",
    "Number of active connections",
)


# Usage
@app.before_request
def before_request():
    g.start_time = time.time()


@app.after_request
def after_request(response):
    duration = time.time() - g.start_time
    requests_total.labels(
        method=request.method,
        path=request.path,
        status=response.status_code,
    ).inc()
    request_duration.labels(
        method=request.method,
        path=request.path,
    ).observe(duration)
    return response
```

### Metric Naming Conventions

```
<namespace>_<subsystem>_<name>_<unit>

http_requests_total              # Counter
http_request_duration_seconds    # Histogram
db_connections_active            # Gauge
cache_hits_total                 # Counter
queue_messages_pending           # Gauge
```

### Label Best Practices

| DO | DON'T |
|----|-------|
| Low cardinality labels (method, status) | High cardinality (user_id, request_id) |
| Bounded values (HTTP methods) | Unbounded values (email addresses) |
| Consistent naming across services | Different names for same concept |

---

## Distributed Tracing (OpenTelemetry)

### Go

```go
import (
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/trace"
)

var tracer = otel.Tracer("myservice")

func ProcessOrder(ctx context.Context, orderID string) error {
    ctx, span := tracer.Start(ctx, "ProcessOrder")
    defer span.End()

    span.SetAttributes(
        attribute.String("order.id", orderID),
    )

    // Child span for sub-operation
    if err := validateOrder(ctx, orderID); err != nil {
        span.RecordError(err)
        span.SetStatus(codes.Error, "validation failed")
        return err
    }

    return nil
}

func validateOrder(ctx context.Context, orderID string) error {
    ctx, span := tracer.Start(ctx, "validateOrder")
    defer span.End()
    // ...
}
```

### Python

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


def process_order(order_id: str) -> None:
    with tracer.start_as_current_span("ProcessOrder") as span:
        span.set_attribute("order.id", order_id)

        try:
            validate_order(order_id)
        except ValidationError as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            raise


def validate_order(order_id: str) -> None:
    with tracer.start_as_current_span("validateOrder"):
        # ...
```

---

## Health Checks

### Liveness vs Readiness

| Check | Purpose | What to Check |
|-------|---------|---------------|
| Liveness | Is the process alive? | Process responds |
| Readiness | Can it serve traffic? | Dependencies available |

### Go

```go
func livenessHandler(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("ok"))
}

func readinessHandler(w http.ResponseWriter, r *http.Request) {
    // Check dependencies
    if err := db.Ping(r.Context()); err != nil {
        w.WriteHeader(http.StatusServiceUnavailable)
        w.Write([]byte("database unavailable"))
        return
    }

    if err := cache.Ping(r.Context()); err != nil {
        w.WriteHeader(http.StatusServiceUnavailable)
        w.Write([]byte("cache unavailable"))
        return
    }

    w.WriteHeader(http.StatusOK)
    w.Write([]byte("ok"))
}
```

### Python

```python
@app.route("/healthz")
def liveness():
    return "ok", 200


@app.route("/readyz")
def readiness():
    try:
        db.session.execute("SELECT 1")
    except Exception:
        return "database unavailable", 503

    try:
        cache.ping()
    except Exception:
        return "cache unavailable", 503

    return "ok", 200
```

---

## Checklist

### Logging
- [ ] Structured logging with fields (not string interpolation only)
- [ ] Entity IDs in `extra`/fields (queryable)
- [ ] Error logs include `exc_info`/`Stack()` and context
- [ ] No sensitive data in logs
- [ ] Consistent log levels across services

### Metrics
- [ ] Request count and duration metrics
- [ ] Error rate metrics
- [ ] Low cardinality labels only
- [ ] Consistent naming conventions

### Tracing
- [ ] Request ID propagated through calls
- [ ] Spans for significant operations
- [ ] Errors recorded on spans
- [ ] Semantic conventions used for attributes
- [ ] Trace-log correlation configured

### Health Checks
- [ ] Liveness endpoint (process alive)
- [ ] Readiness endpoint (dependencies available)
- [ ] No health check logging (too noisy)

---

## Semantic Conventions

OpenTelemetry defines standard attribute names. **Always use semconv** — custom names fragment queries.

### Stable Conventions

| Domain | Key Attributes | Status |
|--------|---------------|--------|
| HTTP | `http.request.method`, `http.response.status_code`, `url.scheme`, `url.path` | Stable |
| Database | `db.system`, `db.namespace`, `db.operation.name`, `db.query.text` | Stable |
| RPC/gRPC | `rpc.system`, `rpc.service`, `rpc.method`, `rpc.grpc.status_code` | Stable |
| Messaging | `messaging.system`, `messaging.operation.type`, `messaging.destination.name` | Development |

### Resource Attributes

Every service **must** set:

```
service.name        = "order-service"
service.version     = "1.2.0"
deployment.environment.name = "production"
```

### Naming Rules

| Rule | Good | Bad |
|------|------|-----|
| Use semconv names | `http.request.method` | `method`, `http_method` |
| Lowercase dotted namespace | `order.type` | `OrderType`, `order_type` |
| Use standard units | `s` (seconds), `By` (bytes) | `ms`, `milliseconds` |

---

## Cardinality Management

High cardinality attributes cause metric explosion. Default limit: **2000 time series per metric**.

### Bounded vs Unbounded

| Bounded (SAFE) | Unbounded (DANGER) |
|----------------|--------------------|
| HTTP method (GET, POST, ...) | User ID |
| Status code class (2xx, 4xx, 5xx) | Request path with IDs |
| Region (us-east-1, eu-west-1) | Email address |
| Order type (standard, express) | Session ID |
| Error category | Full error message |

### Strategies

1. **Attribute allowlists** (OTel Views): Drop attributes you don't need
2. **Bucket status codes**: `2xx`, `3xx`, `4xx`, `5xx` instead of individual codes
3. **Parameterise paths**: `/api/v1/users/{id}` not `/api/v1/users/abc123`
4. **Move high-cardinality to spans**: User IDs belong in trace attributes, not metric labels

### OTel Views for Cardinality

See `otel-go` and `otel-python` skills for language-specific View configuration.

---

## Span Status Rules

| HTTP Status | Span Status (Server) | Span Status (Client) |
|-------------|---------------------|---------------------|
| 1xx, 2xx, 3xx | `UNSET` | `UNSET` |
| 4xx | `UNSET` (not a server error) | `ERROR` |
| 5xx | `ERROR` | `ERROR` |

**Key rule**: A 400 Bad Request is the **client's** fault, not the server's. Server spans should NOT be marked ERROR for 4xx.

```go
// GOOD
if resp.StatusCode >= 500 {
    span.SetStatus(codes.Error, "server error")
}
// Leave 4xx as UNSET on server side
```

```python
# GOOD
if response.status_code >= 500:
    span.set_status(trace.Status(trace.StatusCode.ERROR, "server error"))
# Leave 4xx as UNSET on server side
```

---

## Distributed Tracing Patterns

### Context Propagation

All services must propagate W3C `traceparent` header. OTel middleware handles this automatically for HTTP/gRPC.

For **async messaging** (queues, events), inject/extract manually:

```
Producer → inject(headers) → Message Queue → extract(headers) → Consumer
```

### Span Links vs Parent-Child

| Relationship | When |
|-------------|------|
| **Parent-child** | Synchronous call chain (HTTP, gRPC) |
| **Span link** | Async processing, batch jobs, fan-out |

Use span links when:
- A message consumer processes a message from a queue
- A batch job processes items from multiple requests
- A cron job triggered by an external event

### Trace Boundaries

| Boundary | Action |
|----------|--------|
| HTTP/gRPC ingress | Auto-instrumentation creates root span |
| HTTP/gRPC egress | Auto-instrumentation propagates context |
| Queue publish | Inject trace context into message headers |
| Queue consume | Extract trace context, create linked span |
| Cron/background job | New trace with link to trigger (if any) |

---

## RED and USE Metrics

### RED (Request-oriented)

For request-driven services (APIs, web servers):

| Metric | What | OTel Instrument |
|--------|------|-----------------|
| **R**ate | Requests per second | `Counter` (http.server.request.count) |
| **E**rrors | Failed requests per second | `Counter` with error attribute |
| **D**uration | Latency distribution | `Histogram` (http.server.request.duration) |

### USE (Resource-oriented)

For infrastructure and resource monitoring:

| Metric | What | OTel Instrument |
|--------|------|-----------------|
| **U**tilisation | % of resource capacity used | `ObservableGauge` |
| **S**aturation | Amount of queued/waiting work | `ObservableGauge` or `UpDownCounter` |
| **E**rrors | Resource error count | `Counter` |

### Recommended Instruments per Service

| What to Measure | Instrument | Name Pattern |
|-----------------|-----------|--------------|
| Request count | Counter | `{service}.requests` |
| Request duration | Histogram | `{service}.request.duration` |
| Error count | Counter | `{service}.errors` |
| Active connections | UpDownCounter | `{service}.connections.active` |
| Queue depth | ObservableGauge | `{service}.queue.depth` |
| Pool utilisation | ObservableGauge | `{service}.pool.utilisation` |

---

## OTel Collector Architecture

### Agent-Gateway Pattern (Recommended)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│ App + OTel   │────▶│  Collector   │────▶│    Collector      │
│   SDK        │     │  (Agent)     │     │    (Gateway)      │
│              │     │  per host    │     │    centralised    │
└──────────────┘     └──────────────┘     └──────────────────┘
                                                    │
                                          ┌─────────┼─────────┐
                                          ▼         ▼         ▼
                                       Jaeger   Prometheus   Loki
```

- **Agent**: Sidecar or DaemonSet, handles batching/retry/auth
- **Gateway**: Centralised, handles tail sampling, routing, enrichment
- **SDK exports to agent** on localhost (fast, reliable)

### Collector Pipeline

```yaml
# Collector config structure
receivers:    # How data enters (otlp, prometheus, filelog)
processors:   # Transform, filter, batch, enrich
exporters:    # Where data goes (otlp, prometheus, loki)

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, tail_sampling]
      exporters: [otlp/jaeger]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheusremotewrite]
```

### Key Processors

| Processor | Purpose |
|-----------|---------|
| `batch` | Batch telemetry for efficient export |
| `memory_limiter` | Prevent OOM on collector |
| `attributes` | Add/remove/rename attributes |
| `filter` | Drop unwanted telemetry |
| `tail_sampling` | Sample based on full trace (gateway only) |
| `resource` | Enrich resource attributes |

---

## OTel vs Prometheus Direct

| Aspect | OTel Metrics API | Prometheus Client |
|--------|-----------------|-------------------|
| Vendor lock-in | None (OTLP export) | Prometheus format |
| Auto-instrumentation | Yes (library hooks) | Manual only |
| Trace correlation | Built-in exemplars | Limited |
| Push vs Pull | Push (OTLP) | Pull (scrape) |
| Multi-signal | Traces + Metrics + Logs | Metrics only |

**Recommendation**: Use OTel Metrics API for new services. Use Prometheus client only when integrating with existing Prometheus-only infrastructure.

See `otel-go` and `otel-python` skills for language-specific implementation patterns.

> **See also:** `reliability-patterns` for health check probes (liveness/readiness/startup), circuit breaker state monitoring, and resilience metrics. `deployment-patterns` for probe configuration in Kubernetes.
