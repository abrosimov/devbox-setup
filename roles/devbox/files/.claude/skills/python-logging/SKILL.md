---
name: python-logging
description: >
  Python logging patterns with structlog and stdlib. Use when discussing logging,
  structlog usage, structured logging, log levels, context propagation, error logging,
  or performance logging. Triggers on: logging, structlog, log, structured log,
  log level, logger, print statement, context propagation, request ID, log configuration.
---

# Python Logging Reference

Logging patterns using structlog (preferred) and stdlib logging for Python projects.

---

## Core Rules

### No print() in Production

**FORBIDDEN**: Never use `print()` for operational output in production code:

```python
# BAD — unstructured, no levels, no context
print("user logged in")
print(f"processing order {order_id}")

# These are acceptable ONLY in:
# - CLI tools writing to stdout as their interface
# - One-off scripts
# - Tests (prefer logging even there)
```

### Use structlog (Bound Loggers)

All logging MUST use `structlog` with bound loggers. **Never use `print()` or bare `logging.getLogger()`** in application code:

```python
import structlog

# GOOD — bound logger with component context
class OrderService:
    def __init__(self, db: Database) -> None:
        self._logger = structlog.get_logger().bind(component="order_service")
        self._db = db

    def process(self, order_id: str) -> None:
        self._logger.info("processing order", order_id=order_id)

# BAD — stdlib logger without structlog
import logging
logger = logging.getLogger(__name__)
logger.info("something happened")  # unstructured, no bound context
```

---

## Library Choice

| Library | When to Use |
|---------|-------------|
| **structlog** | Application code, services, APIs |
| **stdlib logging** | Library/package code (avoid forcing dependency), simple CLI scripts |

When using stdlib in libraries, follow the **NullHandler pattern**:

```python
import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
```

---

## structlog Configuration

### Production Setup (JSON Output)

```python
import structlog

def configure_logging_production() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
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

### Development Setup (Console Output)

```python
def configure_logging_dev() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),  # coloured, human-readable
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,  # allow reconfiguration during dev
    )
```

### Environment-Based Selection

```python
def configure_logging() -> None:
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        configure_logging_production()
    else:
        configure_logging_dev()
```

---

## Bound Loggers

### Creating and Enriching

```python
class PaymentService:
    def __init__(self, gateway: PaymentGateway) -> None:
        self._logger = structlog.get_logger().bind(component="payment_service")
        self._gateway = gateway

    def charge(self, order_id: str, amount: int, currency: str) -> ChargeResult:
        log = self._logger.bind(order_id=order_id, amount=amount, currency=currency)
        log.info("charging payment")
        try:
            result = self._gateway.charge(amount, currency)
        except GatewayError as e:
            log.error("payment charge failed", error=str(e), exc_info=True)
            raise
        log.info("payment charged", transaction_id=result.transaction_id)
        return result
```

### Progressive Enrichment

```python
def process_request(self, request: Request) -> Response:
    log = self._logger.bind(request_id=request.id, method=request.method)
    user = self._authenticate(request)
    log = log.bind(user_id=user.id)  # enrich with user context
    order = self._load_order(request.order_id)
    log = log.bind(order_id=order.id, order_status=order.status)
    log.info("processing request")
    # all subsequent logs carry request_id, user_id, order_id
```

---

## Context Propagation with contextvars

Use `structlog.contextvars` to propagate context across function calls without passing loggers:

```python
def handle_request(request: Request) -> Response:
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request.id,
        user_id=request.user_id,
        path=request.path,
    )
    # Any logger anywhere in this call chain now includes request_id, user_id, path
    return process(request)

def process(request: Request) -> Response:
    logger = structlog.get_logger()
    logger.info("processing started")  # automatically includes request_id, user_id, path
    return do_work(request.data)
```

### Adding Context Mid-Request

```python
def authenticate(token: str) -> User:
    user = verify_token(token)
    structlog.contextvars.bind_contextvars(user_id=user.id, user_role=user.role)
    return user
```

---

## Log Levels

| Level | Use For | Example |
|-------|---------|---------|
| `DEBUG` | Development diagnostics, disabled in production | Variable values, SQL queries |
| `INFO` | Normal operational events | `"order created"`, `"payment processed"` |
| `WARNING` | Recoverable issues, degraded operation | `"retry scheduled"`, `"fallback activated"` |
| `ERROR` | Failures requiring attention | `"payment charge failed"`, `"API timeout"` |
| `CRITICAL` | System-wide failures, data corruption risk | `"database unreachable"`, `"certificate expired"` |

**Decision tree:**
1. Only useful during development? → `DEBUG`
2. Normal, expected business event? → `INFO`
3. Something went wrong but we recovered? → `WARNING`
4. An operation failed? → `ERROR`
5. Entire system at risk? → `CRITICAL`

**Rules:**
- INFO is the default production level
- DEBUG must never contain PII or secrets
- ERROR means something needs human attention — don't overuse

---

## Log Message Context Framework

Every log message must answer: **WHAT** happened, **WHERE**, **WHY**, and **WHICH** entity.

```python
# BAD — no context
logger.error("HTTP exception occurred")

# GOOD — answers WHAT, WHERE, WHY, WHICH
logger.error(
    "payment charge failed after max retries",
    order_id=order_id,
    user_id=user_id,
    retry_count=3,
    error=str(exc),
    exc_info=True,
)
```

### Message Guidelines

| Rule | Good | Bad |
|------|------|-----|
| Be specific | `"k8s manifest build failed"` | `"build failed"` |
| Include action | `"order validation failed"` | `"invalid order"` |
| Lowercase start | `"processing order"` | `"Processing order"` |
| No trailing punctuation | `"task completed"` | `"task completed."` |

---

## Unique Log Messages

**Every log message must be unique within a function** to enable fast error localisation:

```python
# BAD — duplicate messages, impossible to tell which step failed
def process_order(self, order: Order) -> None:
    try:
        self._validate(order)
    except ValidationError as e:
        self._logger.error("failed to process order", error=str(e))
        raise
    try:
        self._charge_payment(order)
    except PaymentError as e:
        self._logger.error("failed to process order", error=str(e))  # same message!
        raise

# GOOD — unique messages pinpoint exact failure location
def process_order(self, order: Order) -> None:
    try:
        self._validate(order)
    except ValidationError as e:
        self._logger.error("order validation failed", order_id=order.id, error=str(e))
        raise
    try:
        self._charge_payment(order)
    except PaymentError as e:
        self._logger.error("payment charge failed", order_id=order.id, error=str(e))
        raise
```

---

## Error Logging

### Include Stack Traces

```python
try:
    result = self._gateway.charge(order_id, amount)
except GatewayError as e:
    logger.error("payment gateway error", order_id=order_id, error=str(e), exc_info=True)
    raise
```

### Log at Error Boundaries, Not Every Layer

```python
# BAD — logs same error at every layer (duplicate noise)
class Repository:
    def get(self, id: str) -> Item:
        try:
            return self._db.fetch(id)
        except DBError as e:
            logger.error("db fetch failed", error=str(e))  # log #1
            raise

class Service:
    def process(self, id: str) -> None:
        try:
            item = self._repo.get(id)
        except DBError as e:
            logger.error("failed to get item", error=str(e))  # log #2 (duplicate!)
            raise

# GOOD — wrap at lower layer, log once at boundary
class Repository:
    def get(self, id: str) -> Item:
        try:
            return self._db.fetch(id)
        except DBError as e:
            raise RepositoryError(f"fetch item {id}") from e  # wrap, don't log

class Service:
    def process(self, id: str) -> None:
        try:
            item = self._repo.get(id)
        except RepositoryError as e:
            logger.error("item retrieval failed", item_id=id, exc_info=True)  # log once
            raise
```

---

## Performance Logging

### Timing Context Manager

```python
@contextmanager
def log_duration(operation: str, **extra: object) -> Iterator[None]:
    logger = structlog.get_logger()
    start = time.monotonic()
    logger.info(f"{operation} started", **extra)
    try:
        yield
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(f"{operation} failed", duration_seconds=round(elapsed, 3), **extra)
        raise
    else:
        elapsed = time.monotonic() - start
        logger.info(f"{operation} completed", duration_seconds=round(elapsed, 3), **extra)

# Usage
with log_duration("database migration", version="v42"):
    run_migration()
```

---

## Framework Integration

### FastAPI

```python
@app.middleware("http")
async def logging_middleware(request: Request, call_next) -> Response:
    structlog.contextvars.clear_contextvars()
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )
    logger = structlog.get_logger()
    logger.info("request started")
    response = await call_next(request)
    logger.info("request completed", status_code=response.status_code)
    response.headers["X-Request-ID"] = request_id
    return response
```

### Flask

```python
@app.before_request
def bind_request_context() -> None:
    structlog.contextvars.clear_contextvars()
    g.request_id = request.headers.get("X-Request-ID", str(uuid4()))
    structlog.contextvars.bind_contextvars(
        request_id=g.request_id,
        method=request.method,
        path=request.path,
    )
```

---

## Custom Processors

### Filtering Sensitive Data

```python
_SENSITIVE_KEYS = frozenset({"password", "token", "secret", "api_key", "authorization"})

def filter_sensitive_data(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    for key in event_dict:
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "[REDACTED]"
    return event_dict
```

---

## Anti-Patterns

| Violation | Fix |
|-----------|-----|
| `print()` in production | Use `logger.info()` |
| `sys.exit()` in error handler | Raise exception, handle in `main()` |
| f-string in log call | Use keyword arguments: `logger.info("msg", key=val)` |
| Logging secrets/tokens | Redact sensitive fields, use a filtering processor |
| Duplicate log messages in function | Make each message unique |
| Missing `exc_info=True` on errors | Always include traceback for exceptions |
| Logging in tight loops | Log summaries before/after the loop |
| Catching without re-raising | Log and re-raise, or return an error value |
| `logging.info()` (root logger) | Use `structlog.get_logger().bind(component=...)` |
| No request ID propagation | Use `structlog.contextvars` with middleware |
