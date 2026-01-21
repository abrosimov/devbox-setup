---
name: observability
description: >
  Observability patterns for logging, metrics, and tracing in both Go and Python.
  Triggers on: logging, metrics, tracing, observability, zerolog, prometheus, opentelemetry.
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

### Health Checks
- [ ] Liveness endpoint (process alive)
- [ ] Readiness endpoint (dependencies available)
- [ ] No health check logging (too noisy)
