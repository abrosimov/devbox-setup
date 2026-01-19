---
name: python-patterns
description: >
  Common Python patterns and idioms. Use when discussing dataclasses, Pydantic,
  async/await, HTTP clients, repository pattern, dependency injection, exception
  handling, or context managers. Triggers on: dataclass, Pydantic, BaseModel, async,
  await, asyncio, HTTP client, requests, tenacity, repository, service, dependency
  injection.
---

# Python Patterns Reference

Common patterns and idioms for Python projects.

---

## Dataclasses

Use dataclasses for simple data containers:

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class User:
    id: int
    name: str
    email: str
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    tags: list[str] = field(default_factory=list)
```

### When to Use Dataclasses

| Situation | Use Dataclass? |
|-----------|---------------|
| Simple data container | Yes |
| No validation needed | Yes |
| Immutable data | Yes (with `frozen=True`) |
| Needs validation | No — use Pydantic |
| Needs serialization | No — use Pydantic |

---

## Pydantic

Use Pydantic for validation and serialization:

```python
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    name: str
    email: EmailStr

    class Config:
        extra = "forbid"  # reject unknown fields


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### Pydantic Settings

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    debug: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Exception Handling: Philosophy and Patterns

Based on **[PEP 20 (Zen of Python)](https://peps.python.org/pep-0020/)**, **[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)**, and Python's **[EAFP principle](https://realpython.com/python-lbyl-vs-eafp/)**.

---

### Core Principles (from PEP 20)

> **"Errors should never pass silently."**
> **"Unless explicitly silenced."**
> **"Explicit is better than implicit."**

These principles mean: catch specific exceptions explicitly, or let them crash.

---

### Python's Exception Philosophy: EAFP

**EAFP: "Easier to Ask for Forgiveness than Permission"**

Python's official philosophy (from Python glossary) prefers try/except over pre-checks.

```python
# ❌ LBYL (Look Before You Leap) — not Pythonic
if key in data:
    value = data[key]
else:
    value = None

# ✅ EAFP (Easier to Ask for Forgiveness) — Pythonic
try:
    value = data[key]
except KeyError:
    value = None

# ✅ EVEN BETTER — use built-in method
value = data.get(key)  # Returns None if missing
```

**Why EAFP?**
1. **Avoids race conditions** — between check and use
2. **More performant** — when success is common
3. **More Pythonic** — idiomatic Python style
4. **Clearer intent** — happy path first

**When LBYL is appropriate:**
- Pre-validating user input at API boundaries
- Checking configuration before expensive operations
- Preventing operations with side effects

---

### Anti-Pattern: Broad Exception Catching

**From [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html):**

> Never use catch-all `except:` statements, or catch `Exception` or `StandardError`, unless you are creating an isolation point in the program where exceptions are not propagated but are recorded and suppressed instead.

```python
# ❌ ANTI-PATTERN — violates "Errors should never pass silently"
try:
    histogram.labels(**labels, status="error").observe(duration)
except Exception:  # 🚨 WRONG — swallows bugs
    logger.error("Failed to record metric", exc_info=True)
```

**Why this is dangerous:**
1. **Masks programming errors** — `TypeError`, `AttributeError`, `NameError` indicate bugs
2. **Violates PEP 20** — "Errors should never pass silently"
3. **Hides root cause** — error happens far from source
4. **False sense of safety** — looks robust but fragile
5. **Catches too much** — even `KeyboardInterrupt`, `SystemExit`

**What gets caught by `except Exception:`**
- `TypeError` — programming error, should crash
- `AttributeError` — programming error, should crash
- `ValueError` — might be expected, might be a bug
- `KeyError` — might be expected, might be a bug
- `RuntimeError` — usually unexpected
- And ~50+ other exception types

---

### The Right Approach: Be Specific

**From Google Python Style Guide:** Minimize the amount of code in a try/except block.

```python
# ✅ OPTION 1: Let it crash (best for internal infrastructure)
# If there's a bug in metrics code, we want to know immediately in development
histogram.labels(**labels, status="error").observe(duration)

# ✅ OPTION 2: Catch only expected exceptions
try:
    histogram.labels(**labels, status="error").observe(duration)
except ValueError as e:  # Only if invalid label values are genuinely expected
    logger.warning("Invalid metric labels", extra={"labels": labels})
    raise MetricsConfigError(f"Invalid labels: {labels}") from e
except KeyError as e:  # Only if missing required label is expected
    logger.error("Missing required metric label", extra={"labels": labels})
    raise MetricsConfigError(f"Missing label: {e}") from e
# Programming errors (TypeError, AttributeError) crash immediately
```

---

### Exception Handling by Layer

**Principle:** Catch at boundaries, let crash internally.

#### 1. Presentation Layer (API Endpoints, CLI)

**DO catch exceptions here** — convert to user-facing responses:

```python
@app.post("/items")
def create_item(data: ItemCreate) -> ItemResponse:
    try:
        item = item_service.create(data)
        return ItemResponse.from_domain(item)
    except ItemAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Let unexpected exceptions propagate to global error handler
```

**Global error handler** (isolation point) can catch `Exception`:

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception", extra={"path": request.url.path})
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )
```

#### 2. Service Layer (Business Logic)

**DON'T catch exceptions** unless you can handle them meaningfully:

```python
# ❌ BAD — pointless catch and re-raise
class ItemService:
    def create(self, data: ItemCreate) -> Item:
        try:
            return self.repo.save(Item(**data.model_dump()))
        except Exception as e:
            logger.error("Failed to create item")
            raise  # Why catch if you're just re-raising?

# ✅ GOOD — no try/catch, let exceptions propagate
class ItemService:
    def create(self, data: ItemCreate) -> Item:
        if self.repo.exists_by_name(data.name):
            raise ItemAlreadyExistsError(data.name)
        return self.repo.save(Item(**data.model_dump()))
```

**When to catch in service layer:**
- Transform infrastructure exceptions to domain exceptions
- Implement retry logic for transient failures
- Clean up resources (use context managers instead)

#### 3. Repository Layer (Data Access)

**Transform infrastructure exceptions to domain exceptions:**

```python
class PostgresItemRepository:
    def save(self, item: Item) -> Item:
        try:
            self.db.execute(INSERT_ITEM_SQL, item.model_dump())
            return item
        except psycopg2.IntegrityError as e:
            # Transform infrastructure exception to domain exception
            if "unique_name" in str(e):
                raise ItemAlreadyExistsError(item.name) from e
            raise DatabaseError("Failed to save item") from e
        except psycopg2.OperationalError as e:
            # Infrastructure failure
            raise DatabaseError("Database connection failed") from e
        # Let other exceptions (programming errors) crash
```

**Note:** Always use `raise ... from e` to preserve exception chain.

---

### Exception Handling Decision Tree

```
Can you handle this exception meaningfully?
├─ YES → Catch specific exception, handle, maybe re-raise
└─ NO
    ├─ Is this a boundary (API endpoint, job handler, global handler)?
    │   ├─ YES → Catch, log, return error state
    │   └─ NO → Don't catch, let it propagate
    └─ Is this an expected domain error?
        ├─ YES → Catch, transform to domain exception with `from e`
        └─ NO → Don't catch, let it crash
```

---

### Custom Exceptions

**From Google Python Style Guide:** Exception names should end in `Error` and inherit from existing exception class.

```python
# ✅ GOOD — domain exceptions
class DomainError(Exception):
    """Base class for domain errors."""

class ItemNotFoundError(DomainError):
    def __init__(self, item_id: str):
        self.item_id = item_id
        super().__init__(f"Item not found: {item_id}")

class ItemAlreadyExistsError(DomainError):
    def __init__(self, item_name: str):
        self.item_name = item_name
        super().__init__(f"Item already exists: {item_name}")

class InvalidItemStateError(DomainError):
    def __init__(self, item_id: str, current_state: str, required_state: str):
        self.item_id = item_id
        self.current_state = current_state
        self.required_state = required_state
        super().__init__(
            f"Item {item_id} is in {current_state} state, "
            f"but {required_state} required"
        )
```

**When to use custom exceptions:**
- Domain errors that callers need to handle differently
- Need to attach context (IDs, states) for debugging
- Transform infrastructure exceptions to domain language

**When to use built-in exceptions:**
- `ValueError` — invalid argument value (e.g., negative count)
- `TypeError` — wrong argument type
- `RuntimeError` — generic runtime error
- `NotImplementedError` — abstract method not implemented

---

### Exception Context: Always Use `from`

**From PEP 20:** *"Explicit is better than implicit."*

Always preserve exception chain with `raise ... from e`:

```python
# ❌ BAD — loses original exception
try:
    result = self.api.fetch(item_id)
except requests.RequestException as e:
    raise APIError("Failed to fetch item")  # Original error lost!

# ✅ GOOD — preserves exception chain
try:
    result = self.api.fetch(item_id)
except requests.RequestException as e:
    raise APIError(f"Failed to fetch item {item_id}") from e
```

**Benefits:**
- Preserves full traceback
- Shows root cause in logs
- Helps debugging in production
- Follows PEP 20's "Explicit is better than implicit"

---

### EAFP vs LBYL Examples

```python
# Example 1: Dictionary access
# ❌ LBYL
if "key" in data:
    value = data["key"]
else:
    value = default

# ✅ EAFP
try:
    value = data["key"]
except KeyError:
    value = default

# ✅ BEST — built-in method
value = data.get("key", default)


# Example 2: File operations
# ❌ LBYL — race condition between check and open
if os.path.exists(path):
    with open(path) as f:
        content = f.read()
else:
    content = None

# ✅ EAFP — no race condition
try:
    with open(path) as f:
        content = f.read()
except FileNotFoundError:
    content = None


# Example 3: Attribute access
# ❌ LBYL
if hasattr(obj, "method"):
    result = obj.method()
else:
    result = None

# ✅ EAFP
try:
    result = obj.method()
except AttributeError:
    result = None
```

---

### When NOT to Use EAFP

LBYL is appropriate for:

1. **Validating user input at API boundaries**
```python
# ✅ LBYL for validation (explicit, clear error messages)
def create_item(data: dict[str, Any]) -> Item:
    if "name" not in data:
        raise ValueError("Missing required field: name")
    if not isinstance(data["name"], str):
        raise TypeError("Field 'name' must be string")
    # ... proceed with valid data
```

2. **Preventing side effects**
```python
# ✅ LBYL when operation has side effects
if not self.is_ready():
    raise NotReadyError("System not initialized")
# Proceed only if ready
self.execute_operation()
```

3. **Clear error messages for users**
```python
# ✅ LBYL for user-facing validation
if amount <= 0:
    raise ValueError("Amount must be positive")
if amount > account.balance:
    raise InsufficientFundsError(f"Insufficient funds: {account.balance}")
```

---

### Quick Reference: Exception Anti-Patterns

| Anti-Pattern | Fix | PEP 20 Principle |
|--------------|-----|------------------|
| `except Exception:` in business logic | Catch specific exceptions only | "Errors should never pass silently" |
| Catch and log without re-raising | Let it propagate OR re-raise with context | "Explicit > implicit" |
| Empty except block | Never — at minimum log and re-raise | "Errors should never pass silently" |
| Catching to return `None` | Use explicit error handling or EAFP | "Explicit > implicit" |
| `raise NewError()` without `from e` | Use `raise NewError() from e` | "Explicit > implicit" |
| LBYL for common operations | Use EAFP (try/except) | Python idiom |
| Broad try block | Minimize code in try | Google Style Guide |
| Defensive catching in utilities | Remove — let caller handle | Fail fast |

---

## Dependency Injection

Design for testability:

```python
# BAD — hard to test
class UserService:
    def __init__(self):
        self.db = Database()  # hidden dependency

# GOOD — injectable
class UserService:
    def __init__(self, db: Database):
        self.db = db

# Usage
service = UserService(db=PostgresDB())

# In tests
service = UserService(db=MockDB())
```

---

## Context Managers

Always use for resources:

```python
# Files
with open("file.txt") as f:
    data = f.read()

# Database connections
with db.connection() as conn:
    conn.execute(query)

# Custom resources
from contextlib import contextmanager

@contextmanager
def managed_resource():
    resource = acquire_resource()
    try:
        yield resource
    finally:
        resource.release()
```

---

## Async Code

### Async/Await

Use async for I/O-bound operations:

```python
import asyncio
import aiohttp

async def fetch_user(session: aiohttp.ClientSession, user_id: str) -> dict:
    async with session.get(f"/users/{user_id}") as response:
        return await response.json()

async def fetch_all_users(user_ids: list[str]) -> list[dict]:
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_user(session, uid) for uid in user_ids]
        return await asyncio.gather(*tasks)
```

### Avoid Blocking Calls

Never use blocking I/O in async functions:

```python
# BAD
async def get_data():
    response = requests.get(url)  # blocks event loop!

# GOOD
async def get_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

---

## HTTP Clients

ALWAYS use timeouts and retries for HTTP requests.

### Basic Pattern with requests.Session

```python
import requests
from typing import Final
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class HTTPClientFactory:
    """Factory for creating configured HTTP clients with retries and timeouts."""

    __DEFAULT_RETRIES: Final = 5
    __DEFAULT_BACKOFF: Final = 0.5
    __DEFAULT_TIMEOUT: Final[tuple[float, float]] = (5.0, 30.0)
    __RETRY_STATUS_CODES: Final[frozenset[int]] = frozenset({429, 500, 502, 503, 504})

    @classmethod
    def create(
        cls,
        retries: int = __DEFAULT_RETRIES,
        backoff_factor: float = __DEFAULT_BACKOFF,
        timeout: tuple[float, float] = __DEFAULT_TIMEOUT,
    ) -> requests.Session:
        """Create configured HTTP client with retries and timeouts."""
        retry_strategy = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=list(cls.__RETRY_STATUS_CODES),
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session


# Usage — ALWAYS pass timeout
client = HTTPClientFactory.create()
response = client.get(url, timeout=(5, 30))
response.raise_for_status()
```

### Using tenacity for More Control

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import requests

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=10),
    retry=retry_if_exception_type((requests.RequestException, requests.Timeout)),
    reraise=True,
)
def fetch_user(client: requests.Session, user_id: str) -> dict:
    response = client.get(
        f"{API_URL}/users/{user_id}",
        timeout=(5, 30),
    )
    if response.status_code >= 500:
        raise requests.RequestException(f"Server error: {response.status_code}")
    response.raise_for_status()
    return response.json()
```

### Common Mistakes

```python
# BAD — no timeout (can hang forever)
response = requests.get(url)

# BAD — no retry for transient failures
response = requests.get(url, timeout=30)

# BAD — single timeout value (use tuple for connect + read)
response = requests.get(url, timeout=30)

# GOOD — separate connect and read timeouts + retry
response = client.get(url, timeout=(5, 30))
```

---

## Repository Pattern

```python
from abc import ABC, abstractmethod

class UserRepository(ABC):
    @abstractmethod
    def get(self, user_id: str) -> User | None:
        ...

    @abstractmethod
    def save(self, user: User) -> None:
        ...

class PostgresUserRepository(UserRepository):
    def __init__(self, db: Database):
        self.db = db

    def get(self, user_id: str) -> User | None:
        row = self.db.fetch_one("SELECT * FROM users WHERE id = %s", user_id)
        return User(**row) if row else None
```

---

## Service Layer

```python
class UserService:
    def __init__(self, repo: UserRepository, email_client: EmailClient):
        self.repo = repo
        self.email_client = email_client

    def register(self, data: UserCreate) -> User:
        user = User(
            id=generate_id(),
            name=data.name,
            email=data.email,
        )
        self.repo.save(user)
        self.email_client.send_welcome(user.email)
        return user
```

---

## Backward Compatibility

NEVER break existing consumers. All changes MUST be backward compatible.

### Adding New Functionality

```python
# GOOD — new optional parameter with default
def connect(addr: str, timeout: float = 30.0) -> Client:
    ...

# GOOD — new function alongside existing one
def connect_with_retry(addr: str, retries: int = 3) -> Client:
    ...
```

### Deprecation Process (3 Separate Branches)

**Branch 1: Mark as Deprecated**
```python
import warnings
from functools import wraps

def deprecated(reason: str, version: str):
    """Mark function as deprecated with warning."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated since {version}: {reason}.",
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator


@deprecated(reason="Use get_user_by_id instead", version="2.0.0")
def get_user(user_id: str) -> User:
    return get_user_by_id(user_id)
```

**Branch 2: Remove All Usages**
- Find all callers of deprecated function
- Migrate them to the new function
- Do NOT remove the deprecated function yet

**Branch 3: Remove Deprecated Code**
- Only after all usages are migrated and deployed
- Remove the deprecated function

---

## Exception Message Format

Exception messages should be clear, specific, and include context for debugging.

### Structure

```python
raise ExceptionType(f"<action> <entity>: <reason> (actual={actual}, expected={expected})")
```

### Examples

```python
# ❌ BAD — No context
raise ValueError("invalid value")

# ❌ BAD — No actual/expected values
raise ValueError("temperature out of range")

# ❌ BAD — Missing entity identifier
raise OrderNotFoundError("order not found")

# ✅ GOOD — Clear context with values
raise ValueError(f"temperature {temp} below absolute zero (min=-273.15)")

# ✅ GOOD — Domain exception with identifiers
raise OrderNotFoundError(f"order '{order_id}' not found in workspace '{workspace_id}'")

# ✅ GOOD — Chained with context
raise ProcessingError(
    f"validate order '{order_id}' failed: {validation_errors}"
) from e
```

### Guidelines

| Aspect | Rule |
|--------|------|
| Include actual value | Yes, when not sensitive |
| Include expected constraint | Yes, when applicable |
| Include entity identifier | Always (order_id, user_id, etc.) |
| Use `from e` for chaining | Always when re-raising |
| Sentence case | Lowercase start (for consistency) |

---

## Structured Logging (Standard Library)

Use Python's standard `logging` module with JSON formatter and context injection.

### Log Message Context Framework

Every log message must answer:

| Question | How to Provide | Example |
|----------|----------------|---------|
| WHAT happened? | Message string | `"deployment build failed"` |
| WHERE? | Auto-injected + `extra=` | `request_id`, component context |
| WHY? | `exc_info=` + message detail | `exc_info=e`, reason in message |
| WHICH entity? | `extra={}` dict | `deployment_id`, `workspace_id` |

### Anti-patterns

```python
# ❌ BAD — No context (What? Which deployment?)
logger.error("Deployment failed")

# ❌ BAD — Missing entity identifier
logger.error("Error building deployment", exc_info=e)

# ❌ BAD — Vague message
logger.error("HTTP exception occurred")

# ❌ BAD — Missing exc_info for exceptions
except Exception as e:
    logger.error(f"Failed: {e}")  # No stack trace!
```

### Correct Patterns

```python
# ✅ GOOD — Full context with entity IDs
logger.error(
    f"deployment build failed: {error_reason}",
    exc_info=e,
    extra={
        "deployment_id": deployment_id,
        "workspace_id": workspace_id,
    }
)

# ✅ GOOD — Info with relevant identifiers
logger.info(
    f"starting deployment task for deployment '{deployment_id}'",
    extra={"deployment_id": deployment_id}
)

# ✅ GOOD — Warning with actionable context
logger.warning(
    f"retry scheduled for payment processing",
    extra={
        "order_id": order_id,
        "retry_count": retry_count,
        "max_retries": max_retries,
    }
)
```

### Exception Logging Rules

| Scenario | Pattern |
|----------|---------|
| Caught exception, re-raising | `logger.error("msg", exc_info=e, extra={...})` then `raise` |
| Caught exception, handling | `logger.warning("msg", exc_info=True, extra={...})` |
| Expected condition (not error) | `logger.info("msg", exc_info=True, extra={...})` |

```python
# Re-raising with full context
except requests.RequestException as e:
    logger.error(
        f"HuggingFace API request failed for repo '{repo_id}'",
        exc_info=e,
        extra={"repo_id": repo_id, "endpoint": endpoint}
    )
    raise HuggingFaceClientError(f"API request failed for repo '{repo_id}'") from e

# Handling expected condition
except DuplicateKeyError:
    logger.info(
        f"experiment '{name}' already exists, returning existing",
        exc_info=True,
        extra={"experiment_name": name}
    )
    return self.get_by_name(name)
```

### Message Formatting Guidelines

| Rule | Example |
|------|---------|
| Lowercase start | `"starting deployment..."` not `"Starting deployment..."` |
| Include entity in message | `"deployment '{id}' failed"` not just `"deployment failed"` |
| Be specific about action | `"k8s manifest build failed"` not `"build failed"` |
| No trailing punctuation | `"operation completed"` not `"operation completed."` |

### Logger Instantiation

```python
# Preferred — module-level with __name__
logger = logging.getLogger(__name__)

# Alternative — centralized logger name
logger = logging.getLogger("general_logger")
```

### Context Auto-Injection

These fields are automatically injected by `ContextLoggerFilter`:
- `request_id` — correlation ID for request tracing
- `user_id` — authenticated user
- `tenant_id` — multi-tenant workspace identifier

**Always add domain-specific IDs via `extra=`:**
- `deployment_id`, `workspace_id`, `model_id`, `experiment_id`, etc.

---

## Quick Reference: Pattern Violations

| Violation | Fix |
|-----------|-----|
| `except Exception:` in business logic | Catch specific exceptions or let crash |
| Missing `from e` in exception chaining | Add `raise NewError(...) from e` |
| LBYL for common operations | Use EAFP (try/except) |
| Broad try block | Minimize code in try/except |
| No timeout on HTTP request | Add `timeout=(5, 30)` |
| No retry for HTTP calls | Use HTTPAdapter with Retry or tenacity |
| Blocking call in async function | Use aiohttp or asyncio equivalent |
| Hidden dependency in constructor | Inject dependency as parameter |
| Resource without context manager | Use `with` statement |
| Breaking existing API | Add new function or optional parameter |
| Log without entity context | Add `extra={"entity_id": id}` |
| Log exception without `exc_info=` | Add `exc_info=e` or `exc_info=True` |
| Vague log message | Be specific: action + entity + reason |
