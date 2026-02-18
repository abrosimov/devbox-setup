---
name: otel-python
description: >
  OpenTelemetry patterns for Python services. SDK setup, auto-instrumentation,
  OTel Metrics API, structlog trace correlation, sampling, configuration,
  and testing. Triggers on: opentelemetry, otel, tracing, span, metrics, instrument,
  TracerProvider, MeterProvider, auto-instrument, FastAPIInstrumentor, SQLAlchemyInstrumentor,
  sampling, OTLP, exporter.
---

# OpenTelemetry for Python

Instrumentation patterns for Python services using OpenTelemetry SDK.

**Stable versions** (Dec 2025): opentelemetry-api 1.39.1, opentelemetry-sdk 1.39.1, opentelemetry-semantic-conventions 0.50b1 (semconv spec 1.39.0). Logs SDK stable.

**Semconv import migration**: `opentelemetry.semconv.resource.ResourceAttributes` is deprecated since v1.25.0. Use the generated modules under `opentelemetry.semconv.attributes` (stable) and `opentelemetry.semconv._incubating.attributes` (incubating) instead.

---

## SDK Initialisation

### TracerProvider

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.attributes.service_attributes import (
    SERVICE_NAME,
    SERVICE_VERSION,
)
from opentelemetry.semconv._incubating.attributes.deployment_attributes import (
    DEPLOYMENT_ENVIRONMENT_NAME,
)

def init_tracer() -> TracerProvider:
    resource = Resource.create({
        SERVICE_NAME: "my-service",
        SERVICE_VERSION: "1.0.0",
        DEPLOYMENT_ENVIRONMENT_NAME: "production",
    })

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

    trace.set_tracer_provider(provider)
    return provider
```

### MeterProvider

```python
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

def init_meter() -> MeterProvider:
    reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)
    return provider
```

### Combined Setup

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider

_tracer_provider: TracerProvider | None = None
_meter_provider: MeterProvider | None = None


def init_otel() -> None:
    global _tracer_provider, _meter_provider
    _tracer_provider = init_tracer()
    _meter_provider = init_meter()


def shutdown_otel() -> None:
    if _tracer_provider:
        _tracer_provider.shutdown()
    if _meter_provider:
        _meter_provider.shutdown()
```

### FastAPI Lifespan Integration

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_otel()
    try:
        yield
    finally:
        shutdown_otel()

app = FastAPI(lifespan=lifespan)
```

---

## Auto-Instrumentation

Python OTel supports automatic instrumentation — library hooks that create spans without code changes.

### FastAPI

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
```

### Flask

```python
from opentelemetry.instrumentation.flask import FlaskInstrumentor

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
```

### HTTPX Client

```python
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

HTTPXClientInstrumentor().instrument()

# All httpx requests now create client spans automatically
async with httpx.AsyncClient() as client:
    resp = await client.get("https://api.example.com/data")
```

### requests

```python
from opentelemetry.instrumentation.requests import RequestsInstrumentor

RequestsInstrumentor().instrument()
```

### SQLAlchemy

```python
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

SQLAlchemyInstrumentor().instrument(engine=engine)
```

### Redis

```python
from opentelemetry.instrumentation.redis import RedisInstrumentor

RedisInstrumentor().instrument()
```

### Celery

```python
from opentelemetry.instrumentation.celery import CeleryInstrumentor

CeleryInstrumentor().instrument()
```

### psycopg

```python
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor

PsycopgInstrumentor().instrument()
```

### All-at-Once (Development Only)

```bash
# Install all instrumentors for detected libraries
opentelemetry-bootstrap -a install

# Run with auto-instrumentation (no code changes)
opentelemetry-instrument python app.py
```

**Production**: Always use programmatic instrumentation (`instrument_app()`) for control over which libraries are instrumented.

---

## Custom Spans

### Creating Spans

```python
tracer = trace.get_tracer("myservice.orders")

def process_order(order_id: str) -> None:
    with tracer.start_as_current_span(
        "ProcessOrder",
        attributes={"order.id": order_id},
    ) as span:
        try:
            validate(order_id)
        except ValidationError as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, "validation failed"))
            raise

        span.set_status(trace.Status(trace.StatusCode.OK))
```

### Span Naming

| Pattern | Example |
|---------|---------|
| `Verb` + `Noun` | `ProcessOrder`, `ValidatePayment` |
| `HTTP Method` + `Route` | `GET /api/v1/orders/{id}` |
| `DB Operation` | `SELECT users`, `INSERT orders` |

### Adding Events

```python
span = trace.get_current_span()
span.add_event("payment.charged", attributes={
    "transaction.id": txn_id,
    "amount": 99.99,
})
```

### Span Links (Cross-Trace References)

```python
# Link to a triggering span from a different trace (e.g., async processing)
link = trace.Link(parent_span_context)
with tracer.start_as_current_span("ProcessMessage", links=[link]) as span:
    process(message)
```

### Decorator Pattern

```python
def traced(name: str | None = None):
    def decorator(func):
        span_name = name or func.__qualname__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name):
                return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name):
                return await func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator

@traced("OrderService.process")
def process(order_id: str) -> None:
    ...
```

---

## OTel Metrics API

### Instrument Types

| Instrument | Use For | Example |
|------------|---------|---------|
| `Counter` | Monotonically increasing counts | Requests total, errors total |
| `Histogram` | Distributions / durations | Request latency, payload size |
| `UpDownCounter` | Values that increase and decrease | Active connections, queue depth |
| `ObservableGauge` | Async point-in-time readings | Memory usage, pool size |

### Synchronous Instruments

```python
meter = metrics.get_meter("myservice.orders")

orders_processed = meter.create_counter(
    name="orders.processed",
    description="Number of orders processed",
    unit="{order}",
)

order_duration = meter.create_histogram(
    name="orders.duration",
    description="Order processing duration",
    unit="s",
)

active_orders = meter.create_up_down_counter(
    name="orders.active",
    description="Number of orders currently being processed",
    unit="{order}",
)
```

### Recording Metrics

```python
def process_order(order: Order) -> None:
    start = time.monotonic()
    attrs = {"order.type": order.type}

    active_orders.add(1, attributes=attrs)
    try:
        _do_process(order)
        orders_processed.add(1, attributes={**attrs, "status": "success"})
    except Exception:
        orders_processed.add(1, attributes={**attrs, "status": "error"})
        raise
    finally:
        active_orders.add(-1, attributes=attrs)
        order_duration.record(time.monotonic() - start, attributes=attrs)
```

### Asynchronous Instruments (Observable)

```python
import psutil

def _observe_memory(observer: metrics.CallbackOptions) -> Iterable[metrics.Observation]:
    mem = psutil.virtual_memory()
    yield metrics.Observation(mem.used, {"type": "used"})
    yield metrics.Observation(mem.available, {"type": "available"})

meter.create_observable_gauge(
    name="process.memory.bytes",
    description="Process memory usage",
    unit="By",
    callbacks=[_observe_memory],
)
```

### Views for Cardinality Control

```python
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.view import View, ExplicitBucketHistogramAggregation

provider = MeterProvider(
    metric_readers=[reader],
    views=[
        # Custom histogram buckets
        View(
            instrument_name="orders.duration",
            aggregation=ExplicitBucketHistogramAggregation(
                boundaries=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
            ),
        ),
        # Drop high-cardinality attribute
        View(
            instrument_name="http.server.request.duration",
            attribute_keys={"http.request.method", "http.response.status_code"},
        ),
    ],
)
```

---

## Trace-Log Correlation with structlog

### Processor for Trace Context

```python
import structlog
from opentelemetry import trace

def otel_trace_processor(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx.is_valid:
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict
```

### Configuration

```python
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        otel_trace_processor,              # <-- add after contextvars
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
```

### stdlib logging Bridge

```python
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# Injects trace_id and span_id into stdlib log records
LoggingInstrumentor().instrument(set_logging_format=True)
```

---

## Sampling

### Recommended Production Setup

```python
from opentelemetry.sdk.trace.sampling import (
    ParentBasedTraceIdRatio,
    ALWAYS_OFF,
    ALWAYS_ON,
)

provider = TracerProvider(
    resource=resource,
    sampler=ParentBasedTraceIdRatio(0.1),  # 10% of root spans
    # Parent decisions are respected automatically
)
```

### Custom Error-Aware Sampler

```python
from opentelemetry.sdk.trace.sampling import (
    Sampler,
    SamplingResult,
    Decision,
    ParentBased,
    TraceIdRatioBased,
)

class AlwaysRecordSampler(Sampler):
    """Wraps a sampler but upgrades DROP to RECORD_ONLY so error spans are still captured."""

    def __init__(self, delegate: Sampler) -> None:
        self._delegate = delegate

    def should_sample(self, *args, **kwargs) -> SamplingResult:
        result = self._delegate.should_sample(*args, **kwargs)
        if result.decision == Decision.DROP:
            return SamplingResult(
                decision=Decision.RECORD_ONLY,
                attributes=result.attributes,
                trace_state=result.trace_state,
            )
        return result

    def get_description(self) -> str:
        return f"AlwaysRecord({self._delegate.get_description()})"

sampler = AlwaysRecordSampler(ParentBased(root=TraceIdRatioBased(0.1)))
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
| `OTEL_PYTHON_LOG_CORRELATION` | `false` | Auto-inject trace IDs into stdlib logs |

### OTLP Ports

| Protocol | Port | Variable Example |
|----------|------|------------------|
| gRPC | 4317 | `OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4317` |
| HTTP/protobuf | 4318 | `OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4318` |

---

## Testing

### InMemorySpanExporter for Traces

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory import InMemorySpanExporter

@pytest.fixture
def trace_exporter():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    yield exporter
    provider.shutdown()

def test_process_order_creates_span(trace_exporter: InMemorySpanExporter) -> None:
    process_order("order-123")

    spans = trace_exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "ProcessOrder"

    attrs = dict(spans[0].attributes)
    assert attrs["order.id"] == "order-123"
```

### InMemoryMetricReader for Metrics

```python
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

@pytest.fixture
def metric_reader():
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(provider)
    yield reader
    provider.shutdown()

def test_order_metrics(metric_reader: InMemoryMetricReader) -> None:
    process_order(Order(id="123", type="standard"))

    data = metric_reader.get_metrics_data()
    metric_names = {
        m.name
        for rm in data.resource_metrics
        for sm in rm.scope_metrics
        for m in sm.metrics
    }
    assert "orders.processed" in metric_names
```

### Testing Auto-Instrumentation

```python
@pytest.fixture
def instrumented_client(trace_exporter, app):
    """Test that HTTP auto-instrumentation captures spans."""
    FastAPIInstrumentor.instrument_app(app)
    with TestClient(app) as client:
        yield client
    FastAPIInstrumentor.uninstrument_app(app)

def test_http_span_created(instrumented_client, trace_exporter) -> None:
    instrumented_client.get("/api/v1/health")
    spans = trace_exporter.get_finished_spans()
    http_spans = [s for s in spans if s.name.startswith("GET")]
    assert len(http_spans) == 1
```

---

## Context Propagation

### Automatic (via Auto-Instrumentation)

When using instrumentors (FastAPI, HTTPX, etc.), context propagation is handled automatically — the `traceparent` header is injected into outgoing requests and extracted from incoming requests.

### Manual Propagation

```python
from opentelemetry.propagate import inject, extract

# Inject into outgoing message headers
headers: dict[str, str] = {}
inject(headers)
message_queue.publish(body=payload, headers=headers)

# Extract from incoming message headers
ctx = extract(carrier=message.headers)
with tracer.start_as_current_span("ProcessMessage", context=ctx) as span:
    process(message)
```

### Async Context (asyncio)

Python `contextvars` are automatically copied into `asyncio.Task` instances. OTel context propagation works with `asyncio` out of the box:

```python
async def handle_request(request: Request) -> Response:
    with tracer.start_as_current_span("HandleRequest"):
        # Context propagates into gather/TaskGroup automatically
        async with asyncio.TaskGroup() as tg:
            tg.create_task(fetch_user(request.user_id))
            tg.create_task(fetch_orders(request.user_id))
```

---

## Metric Registration

### Rule: Scan Before Creating

**Before defining any new metric, search the codebase for the metric name.** Duplicate metric names cause silent overwrites or conflicting descriptions.

```bash
# Before adding a new metric, check it doesn't already exist
grep -r '"orders.processed"' .
grep -r '"orders.duration"' .
```

### Centralised Registry Pattern

Define all metrics in a single file per package/module. Never scatter metric definitions across multiple files.

```python
# src/orders/metrics.py

from opentelemetry import metrics

meter = metrics.get_meter("myservice.orders")

orders_processed = meter.create_counter(
    name="orders.processed",
    description="Number of orders processed",
    unit="{order}",
)

order_duration = meter.create_histogram(
    name="orders.duration",
    description="Order processing duration",
    unit="s",
)

active_orders = meter.create_up_down_counter(
    name="orders.active",
    description="Number of orders currently being processed",
    unit="{order}",
)
```

**Usage in service code:**

```python
# src/orders/service.py

from orders.metrics import orders_processed, order_duration, active_orders

class OrderService:
    def process(self, order: Order) -> None:
        start = time.monotonic()
        active_orders.add(1, attributes={"order.type": order.type})
        try:
            self.__do_process(order)
            orders_processed.add(1, attributes={"order.type": order.type, "status": "success"})
        except Exception:
            orders_processed.add(1, attributes={"order.type": order.type, "status": "error"})
            raise
        finally:
            active_orders.add(-1, attributes={"order.type": order.type})
            order_duration.record(time.monotonic() - start, attributes={"order.type": order.type})
```

**Rules:**
- One `metrics.py` per package that owns the metrics
- All metric instruments are module-level, created at import time
- Other modules in the package import and use them directly
- Never create instruments inside functions or methods

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
| Creating tracer per function call | Module-level `tracer = trace.get_tracer(...)` |
| Creating meter per function call | Module-level `meter = metrics.get_meter(...)` |
| Unbounded attribute values (user IDs as attrs) | Use span events or log correlation instead |
| Missing `span.set_status(ERROR)` on exceptions | Always record exceptions and set error status |
| `span.set_status(ERROR)` for 4xx responses | Only set ERROR for 5xx; 4xx is not a server error |
| Hardcoded exporter endpoints | Use `OTEL_EXPORTER_OTLP_ENDPOINT` env var |
| `SimpleSpanProcessor` in production | Use `BatchSpanProcessor` (Simple is for tests) |
| Not calling `provider.shutdown()` | Flushes pending spans/metrics — always call on exit |
| `opentelemetry-instrument` in production | Use programmatic `instrument_app()` for control |
| Missing W3C propagator setup | Set `TraceContextTextMapPropagator` as global propagator |
