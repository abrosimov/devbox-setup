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

## Exception Handling

### Be Specific

```python
# BAD
try:
    do_something()
except Exception:
    pass

# GOOD
try:
    do_something()
except SpecificError as e:
    logger.warning("Expected failure: %s", e)
except UnexpectedError as e:
    raise ProcessingError(f"Failed to process {item}") from e
```

### Custom Exceptions

Create custom exceptions for domain errors:

```python
class DomainError(Exception):
    """Base for domain errors."""

class UserNotFoundError(DomainError):
    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__(f"User not found: {user_id}")
```

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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_http_client(
    retries: int = 5,
    backoff_factor: float = 0.5,
    timeout: tuple[float, float] = (5.0, 30.0),
) -> requests.Session:
    """Create configured HTTP client with retries and timeouts."""
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# Usage — ALWAYS pass timeout
client = create_http_client()
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

## Quick Reference: Pattern Violations

| Violation | Fix |
|-----------|-----|
| No timeout on HTTP request | Add `timeout=(5, 30)` |
| No retry for HTTP calls | Use HTTPAdapter with Retry or tenacity |
| Blocking call in async function | Use aiohttp or asyncio equivalent |
| Hidden dependency in constructor | Inject dependency as parameter |
| Bare `except Exception` | Catch specific exceptions |
| Missing `from e` in exception chaining | Add `raise NewError(...) from e` |
| Resource without context manager | Use `with` statement |
| Breaking existing API | Add new function or optional parameter |
