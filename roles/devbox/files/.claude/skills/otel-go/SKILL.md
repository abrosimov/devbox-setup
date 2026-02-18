---
name: otel-go
description: >
  OpenTelemetry patterns for Go services. SDK setup, middleware instrumentation,
  OTel Metrics API, trace-log correlation with zerolog, sampling, configuration,
  and testing. Triggers on: opentelemetry, otel, tracing, span, metrics, instrument,
  TracerProvider, MeterProvider, otelhttp, otelgrpc, otelpgx, sampling, OTLP, exporter.
---

# OpenTelemetry for Go

Instrumentation patterns for Go services using OpenTelemetry SDK.

**Stable versions**: OTel API v1.38+, SDK v1.38+, Logs Bridge API v0.14 (beta).

---

## SDK Initialisation

### TracerProvider

```go
import (
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.39.0"
)

func initTracer(ctx context.Context) (func(context.Context) error, error) {
    exporter, err := otlptracegrpc.New(ctx)
    if err != nil {
        return nil, fmt.Errorf("creating trace exporter: %w", err)
    }

    tp := sdktrace.NewTracerProvider(
        sdktrace.WithBatcher(exporter),
        sdktrace.WithResource(serviceResource()),
        sdktrace.WithSampler(
            sdktrace.ParentBased(sdktrace.TraceIDRatioBased(0.1)),
        ),
    )
    otel.SetTracerProvider(tp)
    otel.SetTextMapPropagator(propagation.TraceContext{})

    return tp.Shutdown, nil
}
```

### MeterProvider

```go
import (
    "go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetricgrpc"
    sdkmetric "go.opentelemetry.io/otel/sdk/metric"
)

func initMeter(ctx context.Context) (func(context.Context) error, error) {
    exporter, err := otlpmetricgrpc.New(ctx)
    if err != nil {
        return nil, fmt.Errorf("creating metric exporter: %w", err)
    }

    mp := sdkmetric.NewMeterProvider(
        sdkmetric.WithReader(sdkmetric.NewPeriodicReader(exporter)),
        sdkmetric.WithResource(serviceResource()),
    )
    otel.SetMeterProvider(mp)

    return mp.Shutdown, nil
}
```

### Shared Resource

```go
func serviceResource() *resource.Resource {
    r, _ := resource.Merge(
        resource.Default(),
        resource.NewWithAttributes(
            semconv.SchemaURL,
            semconv.ServiceName("my-service"),
            semconv.ServiceVersion("1.0.0"),
            semconv.DeploymentEnvironmentName("production"),
        ),
    )
    return r
}
```

### Combined Setup

```go
func initOTel(ctx context.Context) (func(context.Context) error, error) {
    shutdownTracer, err := initTracer(ctx)
    if err != nil {
        return nil, err
    }

    shutdownMeter, err := initMeter(ctx)
    if err != nil {
        shutdownTracer(ctx)
        return nil, err
    }

    shutdown := func(ctx context.Context) error {
        return errors.Join(shutdownTracer(ctx), shutdownMeter(ctx))
    }
    return shutdown, nil
}

func main() {
    ctx := context.Background()

    shutdown, err := initOTel(ctx)
    if err != nil {
        log.Fatal().Err(err).Msg("OTel init failed")
    }
    defer shutdown(ctx)

    // ... start server
}
```

---

## Middleware Instrumentation

### HTTP Server (otelhttp)

```go
import "go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"

mux := http.NewServeMux()
mux.HandleFunc("/api/v1/orders", handleOrders)

handler := otelhttp.NewHandler(mux, "my-server",
    otelhttp.WithMessageEvents(otelhttp.ReadEvents, otelhttp.WriteEvents),
)
```

### HTTP Client (otelhttp)

```go
client := &http.Client{
    Transport: otelhttp.NewTransport(http.DefaultTransport),
}
```

### gRPC Server (otelgrpc)

```go
import "go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"

srv := grpc.NewServer(
    grpc.StatsHandler(otelgrpc.NewServerHandler()),
)
```

### gRPC Client (otelgrpc)

```go
conn, err := grpc.NewClient(addr,
    grpc.WithStatsHandler(otelgrpc.NewClientHandler()),
)
```

### PostgreSQL (otelpgx)

```go
import "github.com/exaring/otelpgx"

cfg, _ := pgxpool.ParseConfig(connStr)
cfg.ConnConfig.Tracer = otelpgx.NewTracer()

pool, err := pgxpool.NewWithConfig(ctx, cfg)
```

### SQL / GORM (otelsql / otelgorm)

```go
// database/sql
import "github.com/XSAM/otelsql"

db, err := otelsql.Open("postgres", dsn,
    otelsql.WithAttributes(semconv.DBSystemPostgreSQL),
)

// GORM
import "go.opentelemetry.io/contrib/instrumentation/github.com/gorm.io/gorm/otelgorm"

db, err := gorm.Open(postgres.Open(dsn))
db.Use(otelgorm.NewPlugin())
```

### Redis (redisotel)

```go
import "github.com/redis/go-redis/extra/redisotel/v9"

rdb := redis.NewClient(&redis.Options{Addr: "localhost:6379"})
redisotel.InstrumentTracing(rdb)
redisotel.InstrumentMetrics(rdb)
```

---

## Custom Spans

### Creating Spans

```go
var tracer = otel.Tracer("myservice/orders")

func ProcessOrder(ctx context.Context, orderID string) error {
    ctx, span := tracer.Start(ctx, "ProcessOrder",
        trace.WithAttributes(attribute.String("order.id", orderID)),
    )
    defer span.End()

    if err := validate(ctx, orderID); err != nil {
        span.RecordError(err)
        span.SetStatus(codes.Error, "validation failed")
        return fmt.Errorf("validating order %s: %w", orderID, err)
    }

    span.SetStatus(codes.Ok, "")
    return nil
}
```

### Span Naming

| Pattern | Example |
|---------|---------|
| `Verb` + `Noun` | `ProcessOrder`, `ValidatePayment` |
| `HTTP Method` + `Route` | `GET /api/v1/orders/{id}` |
| `DB Operation` | `SELECT users`, `INSERT orders` |

### Adding Events

```go
span.AddEvent("payment.charged",
    trace.WithAttributes(
        attribute.String("transaction.id", txnID),
        attribute.Float64("amount", 99.99),
    ),
)
```

### Span Links (Cross-Trace References)

```go
// Link to a triggering span from a different trace (e.g., async processing)
ctx, span := tracer.Start(ctx, "ProcessMessage",
    trace.WithLinks(trace.Link{SpanContext: parentSpanCtx}),
)
```

---

## OTel Metrics API

### Instrument Types

| Instrument | Use For | Example |
|------------|---------|---------|
| `Int64Counter` | Monotonically increasing counts | Requests total, errors total |
| `Float64Histogram` | Distributions / durations | Request latency, payload size |
| `Int64UpDownCounter` | Values that increase and decrease | Active connections, queue depth |
| `Int64ObservableGauge` | Async point-in-time readings | Memory usage, goroutine count |

### Synchronous Instruments

```go
var meter = otel.Meter("myservice/orders")

var (
    ordersProcessed metric.Int64Counter
    orderDuration   metric.Float64Histogram
    activeOrders    metric.Int64UpDownCounter
)

func initMetrics() error {
    var err error

    ordersProcessed, err = meter.Int64Counter("orders.processed",
        metric.WithDescription("Number of orders processed"),
        metric.WithUnit("{order}"),
    )
    if err != nil {
        return fmt.Errorf("creating orders counter: %w", err)
    }

    orderDuration, err = meter.Float64Histogram("orders.duration",
        metric.WithDescription("Order processing duration"),
        metric.WithUnit("s"),
        metric.WithExplicitBucketBoundaries(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
    )
    if err != nil {
        return fmt.Errorf("creating duration histogram: %w", err)
    }

    activeOrders, err = meter.Int64UpDownCounter("orders.active",
        metric.WithDescription("Number of orders currently being processed"),
        metric.WithUnit("{order}"),
    )
    if err != nil {
        return fmt.Errorf("creating active orders gauge: %w", err)
    }

    return nil
}
```

### Recording Metrics

```go
func ProcessOrder(ctx context.Context, order Order) error {
    start := time.Now()
    activeOrders.Add(ctx, 1, metric.WithAttributes(
        attribute.String("order.type", order.Type),
    ))
    defer func() {
        activeOrders.Add(ctx, -1, metric.WithAttributes(
            attribute.String("order.type", order.Type),
        ))
        orderDuration.Record(ctx, time.Since(start).Seconds(), metric.WithAttributes(
            attribute.String("order.type", order.Type),
        ))
    }()

    // ... process order

    ordersProcessed.Add(ctx, 1, metric.WithAttributes(
        attribute.String("order.type", order.Type),
        attribute.String("status", "success"),
    ))
    return nil
}
```

### Asynchronous Instruments (Observable)

```go
// Register a callback that reads current goroutine count
_, err := meter.Int64ObservableGauge("runtime.goroutines",
    metric.WithDescription("Number of active goroutines"),
    metric.WithUnit("{goroutine}"),
    metric.WithInt64Callback(func(_ context.Context, o metric.Int64Observer) error {
        o.Observe(int64(runtime.NumGoroutine()))
        return nil
    }),
)
```

### Views for Cardinality Control

```go
mp := sdkmetric.NewMeterProvider(
    sdkmetric.WithReader(reader),
    // Drop high-cardinality attribute from a specific metric
    sdkmetric.WithView(sdkmetric.NewView(
        sdkmetric.Instrument{Name: "http.server.request.duration"},
        sdkmetric.Stream{
            AttributeFilter: attribute.NewDenyKeysFilter("http.target"),
        },
    )),
    // Custom histogram buckets
    sdkmetric.WithView(sdkmetric.NewView(
        sdkmetric.Instrument{Name: "orders.duration"},
        sdkmetric.Stream{
            Aggregation: sdkmetric.AggregationExplicitBucketHistogram{
                Boundaries: []float64{0.01, 0.05, 0.1, 0.5, 1, 5},
            },
        },
    )),
)
```

---

## Trace-Log Correlation

### zerolog Integration

```go
import (
    "github.com/rs/zerolog"
    "go.opentelemetry.io/otel/trace"
)

// Middleware: inject trace/span IDs into zerolog context
func TraceLogMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        ctx := r.Context()
        spanCtx := trace.SpanContextFromContext(ctx)

        logger := zerolog.Ctx(ctx)
        if spanCtx.IsValid() {
            logger = logger.With().
                Str("trace_id", spanCtx.TraceID().String()).
                Str("span_id", spanCtx.SpanID().String()).
                Logger()
        }
        ctx = logger.WithContext(ctx)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}
```

### slog with OTel Bridge

```go
import "go.opentelemetry.io/contrib/bridges/otelslog"

// Use otelslog handler to send slog records as OTel log records
handler := otelslog.NewHandler("my-service")
logger := slog.New(handler)
```

### Manual Span Context Extraction

```go
// For any logger — extract IDs from context
func traceFields(ctx context.Context) map[string]string {
    spanCtx := trace.SpanContextFromContext(ctx)
    if !spanCtx.IsValid() {
        return nil
    }
    return map[string]string{
        "trace_id": spanCtx.TraceID().String(),
        "span_id":  spanCtx.SpanID().String(),
    }
}
```

---

## Sampling

### Recommended Production Setup

```go
sampler := sdktrace.ParentBased(
    sdktrace.TraceIDRatioBased(0.1), // Sample 10% of root spans
    // Parent decisions are respected automatically:
    // - Remote sampled parent → sample
    // - Remote unsampled parent → don't sample
    // - Local sampled parent → sample
    // - Local unsampled parent → don't sample
)

tp := sdktrace.NewTracerProvider(
    sdktrace.WithSampler(sampler),
)
```

### Always Record Errors

```go
// Custom sampler: always record spans with errors
type errorAwareSampler struct {
    base sdktrace.Sampler
}

func (s *errorAwareSampler) ShouldSample(p sdktrace.SamplingParameters) sdktrace.SamplingResult {
    result := s.base.ShouldSample(p)
    // Upgrade "Drop" to "RecordOnly" so errors are still captured
    if result.Decision == sdktrace.Drop {
        return sdktrace.SamplingResult{
            Decision:   sdktrace.RecordOnly,
            Tracestate: result.Tracestate,
        }
    }
    return result
}

func (s *errorAwareSampler) Description() string {
    return "ErrorAwareSampler"
}
```

---

## Configuration via Environment Variables

All OTel SDK configuration can be overridden via environment variables. **Prefer env vars over code** for deployment flexibility.

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_SERVICE_NAME` | `unknown_service` | Service name in resource |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP endpoint |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `grpc` | `grpc` or `http/protobuf` |
| `OTEL_TRACES_SAMPLER` | `parentbased_always_on` | Sampler type |
| `OTEL_TRACES_SAMPLER_ARG` | (none) | Sampler argument (e.g., `0.1` for ratio) |
| `OTEL_RESOURCE_ATTRIBUTES` | (none) | `key=value,key=value` pairs |
| `OTEL_LOG_LEVEL` | `info` | SDK internal logging |

### OTLP Ports

| Protocol | Port | Variable Example |
|----------|------|------------------|
| gRPC | 4317 | `OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4317` |
| HTTP/protobuf | 4318 | `OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4318` |

---

## Testing

### InMemoryExporter for Traces

```go
import (
    "go.opentelemetry.io/otel/sdk/trace/tracetest"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

func setupTestTracer(t *testing.T) (*tracetest.InMemoryExporter, *sdktrace.TracerProvider) {
    t.Helper()
    exporter := tracetest.NewInMemoryExporter()
    tp := sdktrace.NewTracerProvider(
        sdktrace.WithSyncer(exporter), // synchronous for tests
    )
    t.Cleanup(func() { tp.Shutdown(context.Background()) })
    return exporter, tp
}

func TestProcessOrder_CreatesSpan(t *testing.T) {
    exporter, tp := setupTestTracer(t)
    otel.SetTracerProvider(tp)

    err := ProcessOrder(context.Background(), "order-123")
    require.NoError(t, err)

    spans := exporter.GetSpans()
    require.Len(t, spans, 1)
    assert.Equal(t, "ProcessOrder", spans[0].Name)

    // Check attributes
    attrs := spans[0].Attributes
    found := false
    for _, a := range attrs {
        if a.Key == "order.id" && a.Value.AsString() == "order-123" {
            found = true
        }
    }
    assert.True(t, found, "expected order.id attribute")
}
```

### InMemoryExporter for Metrics

```go
import (
    sdkmetric "go.opentelemetry.io/otel/sdk/metric"
    "go.opentelemetry.io/otel/sdk/metric/metricdata"
    "go.opentelemetry.io/otel/sdk/metric/metricdata/metricdatatest"
)

func setupTestMeter(t *testing.T) (*sdkmetric.ManualReader, *sdkmetric.MeterProvider) {
    t.Helper()
    reader := sdkmetric.NewManualReader()
    mp := sdkmetric.NewMeterProvider(sdkmetric.WithReader(reader))
    t.Cleanup(func() { mp.Shutdown(context.Background()) })
    return reader, mp
}

func TestOrderMetrics(t *testing.T) {
    reader, mp := setupTestMeter(t)
    otel.SetMeterProvider(mp)

    // ... exercise code that records metrics

    var rm metricdata.ResourceMetrics
    err := reader.Collect(context.Background(), &rm)
    require.NoError(t, err)

    // Find and assert on specific metrics
    for _, sm := range rm.ScopeMetrics {
        for _, m := range sm.Metrics {
            if m.Name == "orders.processed" {
                // Assert on data points
            }
        }
    }
}
```

---

## Context Propagation

### Always Pass ctx

```go
// GOOD — context flows through entire call chain
func (s *Service) Handle(ctx context.Context, req Request) (*Response, error) {
    user, err := s.auth.Verify(ctx, req.Token)   // propagates trace
    if err != nil { return nil, err }

    order, err := s.repo.Get(ctx, req.OrderID)    // propagates trace
    if err != nil { return nil, err }

    return s.process(ctx, user, order)             // propagates trace
}

// BAD — breaks trace propagation
func (s *Service) Handle(req Request) (*Response, error) {
    user, err := s.auth.Verify(context.Background(), req.Token)  // new root span!
    // ...
}
```

### Async Work (Goroutines)

```go
// Create a span link for async work rather than parent-child
func (s *Service) EnqueueAsync(ctx context.Context, task Task) {
    spanCtx := trace.SpanContextFromContext(ctx)

    go func() {
        ctx := context.Background()
        ctx, span := tracer.Start(ctx, "ProcessAsync",
            trace.WithLinks(trace.Link{SpanContext: spanCtx}),
        )
        defer span.End()

        s.process(ctx, task)
    }()
}
```

---

## Metric Registration

### Rule: Scan Before Creating

**Before defining any new metric, search the codebase for the metric name.** Duplicate metric names cause silent overwrites or panics depending on the registry.

```bash
# Before adding a new metric, check it doesn't already exist
grep -r '"orders.processed"' .
grep -r '"orders.duration"' .
```

### Centralised Registry Pattern

Define all metrics in a single file per package. Never scatter metric definitions across multiple files.

```go
// internal/orders/metrics.go

package orders

import (
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/metric"
)

var meter = otel.Meter("myservice/orders")

var (
    OrdersProcessed metric.Int64Counter
    OrderDuration   metric.Float64Histogram
    ActiveOrders    metric.Int64UpDownCounter
)

func InitMetrics() error {
    var err error

    OrdersProcessed, err = meter.Int64Counter("orders.processed",
        metric.WithDescription("Number of orders processed"),
        metric.WithUnit("{order}"),
    )
    if err != nil {
        return fmt.Errorf("creating orders.processed counter: %w", err)
    }

    OrderDuration, err = meter.Float64Histogram("orders.duration",
        metric.WithDescription("Order processing duration"),
        metric.WithUnit("s"),
        metric.WithExplicitBucketBoundaries(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
    )
    if err != nil {
        return fmt.Errorf("creating orders.duration histogram: %w", err)
    }

    ActiveOrders, err = meter.Int64UpDownCounter("orders.active",
        metric.WithDescription("Number of orders currently being processed"),
        metric.WithUnit("{order}"),
    )
    if err != nil {
        return fmt.Errorf("creating orders.active gauge: %w", err)
    }

    return nil
}
```

**Rules:**
- One `metrics.go` per package that owns the metrics
- All metric vars are package-level, initialised via an `InitMetrics()` function
- Call `InitMetrics()` from the service constructor or startup sequence
- Other files in the package import and use the vars directly

### Naming Convention

```
{service}.{subsystem}.{name}[.{unit_suffix}]

orders.processed           # Counter — total orders processed
orders.duration            # Histogram — processing time
orders.active              # UpDownCounter — currently in-flight
payments.charge.duration   # Histogram — payment charge time
payments.errors            # Counter — payment failures
```

| Rule | Good | Bad |
|------|------|-----|
| Dotted namespace | `orders.processed` | `orders_processed`, `OrdersProcessed` |
| No type suffix | `orders.processed` | `orders.processed.total`, `orders.processed_counter` |
| Bounded attributes only | `order.type` (3-5 values) | `order.id` (unbounded) |
| Consistent across package | All start with `orders.` | Mixed `order.`, `orders.`, `ord.` |

---

## Common Anti-Patterns

| Anti-Pattern | Fix |
|--------------|-----|
| `context.Background()` in request handlers | Pass `r.Context()` / incoming `ctx` |
| Creating tracer per function call | Package-level `var tracer = otel.Tracer(...)` |
| Creating meter per function call | Package-level `var meter = otel.Meter(...)` |
| Unbounded attribute values (user IDs as attrs) | Use span events or log correlation instead |
| Missing `span.End()` | Always `defer span.End()` immediately after `Start` |
| Ignoring `Shutdown()` errors | Log shutdown errors for diagnostics |
| `span.SetStatus(codes.Error, ...)` for 4xx | Only set ERROR for 5xx; 4xx is not a server error |
| Hardcoded exporter endpoints | Use `OTEL_EXPORTER_OTLP_ENDPOINT` env var |
| `sdktrace.WithSyncer` in production | Use `sdktrace.WithBatcher` (Syncer is for tests) |
| Not setting `propagation.TraceContext{}` | Required for W3C traceparent propagation |
