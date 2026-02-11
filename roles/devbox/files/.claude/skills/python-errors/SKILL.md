---
name: python-errors
description: >
  Python error handling patterns and best practices. Use when discussing exception handling,
  custom exceptions, error chaining, error hierarchy, error classification, or gRPC error
  handling and status codes.
  Triggers on: exception, error handling, raise, try except, error chain, custom exception,
  gRPC error, status code, context.abort, error leakage, grpc.StatusCode.
---

# Python Errors Reference

Error handling patterns for Python projects.

---

## Error Strategy Decision Tree

```
Is the error a known, expected condition callers should check?
│
├─ YES → Is it a simple condition (not found, invalid, etc.)?
│        │
│        ├─ YES → Custom exception with clear name (UserNotFoundError)
│        │
│        └─ NO → Does caller need structured data from the error?
│                │
│                ├─ YES → Custom exception with attributes
│                │
│                └─ NO → Simple custom exception
│
└─ NO → Just chain with: raise NewError("context") from err
```

---

## Custom Exceptions

### When to Create

- Caller needs to catch specific error type
- Error represents domain-specific condition
- Need to distinguish from built-in exceptions
- Want to carry additional context

### Basic Pattern

```python
class UserNotFoundError(Exception):
    """User with given ID does not exist."""
    pass


class ValidationError(Exception):
    """Input validation failed."""
    pass


class ServiceError(Exception):
    """External service communication failed."""
    pass
```

### With Attributes

```python
class ValidationError(Exception):
    """Validation failed with field-level details."""

    def __init__(self, field: str, message: str, value: Any = None) -> None:
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"{field}: {message}")


class APIError(Exception):
    """API call failed with status code."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        cause: Exception | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(f"{code}: {message}")
        if cause:
            self.__cause__ = cause
```

### Exception Hierarchy

```python
# Base exception for your package/application
class AppError(Exception):
    """Base exception for application errors."""
    pass


# Domain-specific exceptions inherit from base
class UserError(AppError):
    """User-related errors."""
    pass


class UserNotFoundError(UserError):
    """User does not exist."""
    pass


class UserAlreadyExistsError(UserError):
    """User with this identifier already exists."""
    pass


class AuthenticationError(AppError):
    """Authentication failed."""
    pass


class AuthorisationError(AppError):
    """User lacks permission for this action."""
    pass
```

### Checking Exception Types

```python
try:
    user = user_service.get_user(user_id)
except UserNotFoundError:
    return None  # Expected case
except UserError as e:
    # Catch all user-related errors
    logger.warning("user error", extra={"error": str(e)})
    raise
except AppError as e:
    # Catch all application errors
    logger.error("application error", exc_info=e)
    raise
```

---

## Exception Chaining

**ALWAYS chain exceptions to preserve the original cause.**

### Basic Pattern

```python
def get_user(user_id: str) -> User:
    try:
        return repository.find_by_id(user_id)
    except DatabaseError as err:
        raise ServiceError(f"fetch user {user_id}") from err
```

### Why Chain?

```python
# ❌ BAD — loses original error
try:
    data = parse_config(raw)
except ValueError:
    raise ConfigError("invalid config")  # Original error lost!

# ❌ BAD — loses error context
try:
    data = parse_config(raw)
except ValueError as e:
    raise ConfigError(f"invalid config: {e}")  # String only, no chain

# ✅ GOOD — preserves full chain
try:
    data = parse_config(raw)
except ValueError as err:
    raise ConfigError("invalid config") from err  # Full traceback preserved
```

### Checking Chained Errors

```python
try:
    result = process_order(order_id)
except ServiceError as e:
    # Access the original cause
    if e.__cause__ is not None:
        logger.error(
            "service error with cause",
            exc_info=e.__cause__,
            extra={"order_id": order_id},
        )

    # Check cause type
    if isinstance(e.__cause__, ConnectionError):
        # Handle connection-specific recovery
        pass
```

### Explicit Suppression (Rare)

When you intentionally want to hide the original error:

```python
try:
    data = fetch_sensitive_data()
except InternalError:
    # Suppress cause — don't expose internal details
    raise PublicError("operation failed") from None
```

---

## Error Message Format

### Guidelines

| Rule | Example |
|------|---------|
| Specific context | `"fetch user abc123"` not `"database error"` |
| Include identifiers | `f"process order {order_id}"` |
| No redundant prefixes | `"parse config"` not `"error: failed to parse config"` |
| Lowercase start | `"connect to server"` not `"Connect to server"` |

### Examples

```python
# ❌ BAD — no context
raise ServiceError("failed")

# ❌ BAD — redundant "error" or "failed"
raise ServiceError("error: failed to fetch user")

# ❌ BAD — no identifier
raise UserNotFoundError("user not found")

# ✅ GOOD — specific with identifier
raise UserNotFoundError(f"user {user_id} not found")

# ✅ GOOD — action + context
raise ServiceError(f"fetch order {order_id}")
raise ConfigError(f"parse config file {path}")
```

---

## Exception Handling Patterns

### Early Return / Catch Specific

```python
def process_order(order_id: str) -> ProcessedOrder:
    try:
        order = repository.get(order_id)
    except OrderNotFoundError:
        raise  # Re-raise expected errors
    except DatabaseError as err:
        raise ServiceError(f"fetch order {order_id}") from err

    try:
        validated = validator.validate(order)
    except ValidationError:
        raise  # Let validation errors propagate

    return transformer.process(validated)
```

### Never Catch Bare Exception

```python
# ❌ FORBIDDEN — catches everything including SystemExit, KeyboardInterrupt
try:
    result = do_something()
except:
    pass

# ❌ BAD — too broad, hides bugs
try:
    result = do_something()
except Exception:
    logger.error("something failed")
    return None

# ✅ GOOD — specific exceptions
try:
    result = do_something()
except (ValueError, TypeError) as err:
    raise ProcessingError("invalid data") from err
except ConnectionError as err:
    raise ServiceError("connection failed") from err
```

### Don't Swallow Exceptions

```python
# ❌ BAD — silently ignores error
try:
    send_notification(user_id)
except NotificationError:
    pass  # Error silently swallowed

# ✅ GOOD — log and continue if appropriate
try:
    send_notification(user_id)
except NotificationError as err:
    logger.warning(
        "notification failed, continuing",
        exc_info=err,
        extra={"user_id": user_id},
    )

# ✅ GOOD — or re-raise if critical
try:
    send_notification(user_id)
except NotificationError as err:
    logger.error("notification failed", exc_info=err)
    raise
```

### Context Managers for Cleanup

```python
# ❌ BAD — cleanup may not run
f = open("file.txt")
try:
    data = f.read()
finally:
    f.close()

# ✅ GOOD — context manager ensures cleanup
with open("file.txt") as f:
    data = f.read()

# ✅ GOOD — multiple resources
from contextlib import ExitStack

with ExitStack() as stack:
    db = stack.enter_context(get_db_connection())
    cache = stack.enter_context(get_cache_connection())
    # Both cleaned up even if exception occurs
```

---

## Logging Exceptions

### Always Include exc_info

```python
# ❌ BAD — no stack trace
try:
    result = process(data)
except ProcessingError as e:
    logger.error(f"processing failed: {e}")  # No traceback!

# ✅ GOOD — includes full traceback
try:
    result = process(data)
except ProcessingError as e:
    logger.error("processing failed", exc_info=e)

# ✅ GOOD — with context
try:
    result = process(data)
except ProcessingError as e:
    logger.error(
        "processing failed",
        exc_info=e,
        extra={"data_id": data.id, "user_id": user_id},
    )
```

### Use logger.exception() in Except Blocks

```python
try:
    result = process(data)
except ProcessingError:
    # Automatically includes exc_info=True
    logger.exception("processing failed")
```

---

## Common Mistakes

### Catching and Re-raising Without Chain

```python
# ❌ BAD — loses original traceback
try:
    data = fetch_data()
except FetchError as e:
    raise ProcessingError(str(e))  # Chain broken!

# ✅ GOOD — preserves chain
try:
    data = fetch_data()
except FetchError as err:
    raise ProcessingError("fetch data") from err
```

### Returning None Instead of Raising

```python
# ❌ BAD — caller can't distinguish success from failure
def get_user(user_id: str) -> User | None:
    try:
        return repository.find(user_id)
    except DatabaseError:
        return None  # Was it not found or did DB fail?

# ✅ GOOD — explicit error handling
def get_user(user_id: str) -> User:
    try:
        user = repository.find(user_id)
    except DatabaseError as err:
        raise ServiceError(f"fetch user {user_id}") from err

    if user is None:
        raise UserNotFoundError(f"user {user_id}")

    return user
```

### Using Assert for Runtime Checks

```python
# ❌ BAD — asserts can be disabled with -O flag
def process(data: Data) -> Result:
    assert data is not None  # Disabled in production!
    assert data.is_valid()
    return transform(data)

# ✅ GOOD — explicit validation
def process(data: Data) -> Result:
    if data is None:
        raise ValueError("data is required")
    if not data.is_valid():
        raise ValidationError("data", "invalid data")
    return transform(data)
```

### Catching Exception in __init__

```python
# ❌ BAD — hides construction failures
class Service:
    def __init__(self, config: Config) -> None:
        try:
            self.__client = create_client(config)
        except ClientError:
            self.__client = None  # Service in broken state!

# ✅ GOOD — let it fail
class Service:
    def __init__(self, config: Config) -> None:
        self.__client = create_client(config)  # Fails loudly
```

---

## Exception Hierarchy Design

### Package-Level Base

```python
# mypackage/exceptions.py

class MyPackageError(Exception):
    """Base exception for mypackage."""
    pass


# Functional categories
class ConfigurationError(MyPackageError):
    """Configuration-related errors."""
    pass


class ValidationError(MyPackageError):
    """Validation-related errors."""
    pass


class ServiceError(MyPackageError):
    """External service communication errors."""
    pass


# Specific errors under categories
class MissingConfigError(ConfigurationError):
    """Required configuration is missing."""
    pass


class InvalidConfigError(ConfigurationError):
    """Configuration value is invalid."""
    pass


class FieldValidationError(ValidationError):
    """Single field validation failed."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")
```

### Benefits

```python
# Catch all package errors
except MyPackageError:

# Catch all validation errors
except ValidationError:

# Catch specific error
except FieldValidationError as e:
    print(f"Field {e.field} failed: {e.message}")
```

---

## HTTP/API Error Handling

### Request Errors

```python
import requests
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    Timeout,
    RequestException,
)


def fetch_data(url: str) -> dict:
    try:
        response = requests.get(url, timeout=(5, 30))
        response.raise_for_status()
        return response.json()
    except Timeout as err:
        raise ServiceError(f"timeout fetching {url}") from err
    except ConnectionError as err:
        raise ServiceError(f"connection failed to {url}") from err
    except HTTPError as err:
        if err.response.status_code == 404:
            raise NotFoundError(f"resource not found: {url}") from err
        raise ServiceError(f"HTTP error from {url}") from err
    except RequestException as err:
        raise ServiceError(f"request failed to {url}") from err
```

### API Response Errors

```python
class APIError(Exception):
    """API returned an error response."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(f"[{status_code}] {code}: {message}")


def handle_api_error(response: requests.Response) -> None:
    """Convert API error response to exception."""
    if response.ok:
        return

    try:
        data = response.json()
        raise APIError(
            code=data.get("code", "UNKNOWN"),
            message=data.get("message", "Unknown error"),
            status_code=response.status_code,
        )
    except ValueError:
        raise APIError(
            code="INVALID_RESPONSE",
            message=response.text,
            status_code=response.status_code,
        )
```

---

## gRPC Error Handling

> Cross-reference: `security-patterns` skill for severity tiers. `api-design-proto` skill for error design in API contracts.

### Status Codes — Use the Right One

```python
import grpc

def map_error(err: Exception) -> grpc.StatusCode:
    """Map domain exceptions to gRPC status codes."""
    error_map = {
        UserNotFoundError: (grpc.StatusCode.NOT_FOUND, "resource not found"),
        AlreadyExistsError: (grpc.StatusCode.ALREADY_EXISTS, "resource already exists"),
        ValidationError: (grpc.StatusCode.INVALID_ARGUMENT, "invalid input"),
        AuthenticationError: (grpc.StatusCode.UNAUTHENTICATED, "authentication required"),
        AuthorisationError: (grpc.StatusCode.PERMISSION_DENIED, "insufficient permissions"),
    }
    for exc_type, (code, message) in error_map.items():
        if isinstance(err, exc_type):
            return code, message
    return grpc.StatusCode.INTERNAL, "internal error"
```

### Error Information Leakage (CONTEXT Severity)

**Never expose internal details in gRPC status messages.** Internal errors (DB queries, stack traces, file paths) must be logged server-side and replaced with generic messages for clients.

```python
# BAD — leaks internal details to client
class OrderService(order_pb2_grpc.OrderServiceServicer):
    def GetOrder(self, request, context):
        try:
            order = self.repo.get(request.id)
        except DatabaseError as err:
            context.abort(grpc.StatusCode.INTERNAL, f"database query failed: {err}")
            # Client sees: "database query failed: connection refused to postgres:5432"

# GOOD — log internally, return sanitised status
class OrderService(order_pb2_grpc.OrderServiceServicer):
    def GetOrder(self, request, context):
        try:
            order = self.repo.get(request.id)
        except NotFoundError:
            context.abort(grpc.StatusCode.NOT_FOUND, "order not found")
        except Exception as err:
            logger.error("get order failed", exc_info=err, extra={"order_id": request.id})
            context.abort(grpc.StatusCode.INTERNAL, "internal error")
```

### Rich Error Details

For validation errors, use `google.rpc.BadRequest` detail messages:

```python
from google.rpc import error_details_pb2, status_pb2
from grpc_status import rpc_status

def validation_error(context: grpc.ServicerContext, violations: dict[str, str]) -> None:
    """Abort with structured validation error details."""
    detail = error_details_pb2.BadRequest(
        field_violations=[
            error_details_pb2.BadRequest.FieldViolation(field=f, description=d)
            for f, d in violations.items()
        ]
    )
    status = status_pb2.Status(
        code=grpc.StatusCode.INVALID_ARGUMENT.value[0],
        message="validation failed",
    )
    status.details.add().Pack(detail)
    context.abort_with_status(rpc_status.to_status(status))
```

### Interceptor Error Handling

Errors from interceptors (auth, rate limiting) should use proper status codes:

```python
# BAD — interceptor raising generic exception
def auth_interceptor(continuation, handler_call_details):
    if not validate_token(handler_call_details.invocation_metadata):
        raise Exception("authentication failed")  # Client gets UNKNOWN code

# GOOD — interceptor aborting with proper status
class AuthInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        metadata = dict(handler_call_details.invocation_metadata)
        token = metadata.get("authorization", "")
        if not validate_token(token):
            return grpc.unary_unary_rpc_method_handler(
                lambda req, ctx: ctx.abort(
                    grpc.StatusCode.UNAUTHENTICATED, "invalid or expired token"
                )
            )
        return continuation(handler_call_details)
```

### Streaming Error Handling

```python
class OrderService(order_pb2_grpc.OrderServiceServicer):
    def WatchOrders(self, request, context):
        """Server streaming — handle client disconnection gracefully."""
        try:
            for event in self.event_source.subscribe(request.filter):
                if context.is_active():
                    yield event
                else:
                    # Client disconnected
                    break
        except Exception as err:
            logger.error("watch orders stream failed", exc_info=err)
            context.abort(grpc.StatusCode.INTERNAL, "stream error")
```

---

## Checklist

### Exception Handling
- [ ] Specific exceptions caught, not bare `except:` or `except Exception:`
- [ ] Exceptions chained with `raise ... from err`
- [ ] Exceptions not silently swallowed
- [ ] Context managers used for resource cleanup

### Custom Exceptions
- [ ] Inherit from appropriate base (app-level or built-in)
- [ ] Clear, descriptive names (`UserNotFoundError` not `Error1`)
- [ ] Attributes for structured data when needed
- [ ] Proper `__init__` calling `super().__init__()`

### Logging
- [ ] `exc_info=e` or `logger.exception()` used for errors
- [ ] Entity IDs in `extra={}` for queryability
- [ ] Specific messages, not generic "error occurred"

### Error Messages
- [ ] Include relevant identifiers
- [ ] Lowercase start (unless proper noun)
- [ ] No redundant "error:" or "failed to" prefixes
