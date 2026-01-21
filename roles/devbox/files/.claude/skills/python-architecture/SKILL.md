---
name: python-architecture
description: >
  Python architecture patterns and design rules. Use when discussing project structure,
  class design, dependency injection, configuration, interface patterns, or layered architecture.
  Triggers on: architecture, structure, dependency injection, interface, protocol, ABC, config.
---

# Python Architecture Reference

Architectural design rules for Python projects.

---

## Project Structure — Package by Feature

Organise code by what it does, not by architectural layer:

```
project/
├── src/
│   └── myapp/
│       ├── __init__.py
│       ├── user/               # Everything user-related together
│       │   ├── __init__.py
│       │   ├── models.py           # User dataclasses/Pydantic models
│       │   ├── service.py          # Business logic
│       │   └── repository.py       # Database operations
│       ├── order/              # Everything order-related together
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── service.py
│       │   └── repository.py
│       ├── auth/               # Authentication
│       │   └── ...
│       └── api/                # HTTP handlers/routes
│           ├── __init__.py
│           └── routes.py
├── tests/
│   ├── user/
│   │   └── test_service.py
│   └── order/
│       └── test_service.py
├── pyproject.toml
└── uv.lock
```

**Benefits:**
- High cohesion — related code lives together
- Low coupling — packages are self-contained
- Easy navigation — find user code in `user/` package

### Adapt to Existing Codebase

**DO NOT impose architectural patterns.** Follow what the codebase already uses:

| If codebase uses... | Follow it |
|---------------------|-----------|
| Layer packages (`/services/`, `/repositories/`) | Add to existing layers |
| Feature packages (`/user/`, `/order/`) | Add to feature packages |
| Flat structure | Keep it flat |
| `*Service`/`*Repository` naming | Use that naming |
| Direct class names | Use direct names |

**Your job is to write code that fits, not to refactor toward a different architecture.**

---

## Class Naming — Be Direct

Name classes after what they ARE:

```python
# GOOD — direct, stdlib style
class User: ...           # The thing itself
class Client: ...         # Like http.client
class Store: ...          # Holds/retrieves things
class Cache: ...          # Caches things
class Writer: ...         # Writes things

# AVOID — implies architectural layers (use only if codebase already uses these)
class UserService: ...    # "Service" is a layer concept
class UserRepository: ... # "Repository" is DDD terminology
class UserEntity: ...     # "Entity" is DDD terminology
class UserDTO: ...        # "DTO" implies transfer between layers
class UserModel: ...      # "Model" implies MVC/DDD separation
```

---

## Interface Patterns

### Protocol (Structural Subtyping)

Use `Protocol` for interfaces — no explicit inheritance required:

```python
from typing import Protocol


class UserRepository(Protocol):
    """Interface for user storage."""

    def find_by_id(self, user_id: str) -> User | None: ...
    def save(self, user: User) -> None: ...


# Implementation doesn't need to inherit
class PostgresUserRepository:
    def find_by_id(self, user_id: str) -> User | None:
        # Implementation
        ...

    def save(self, user: User) -> None:
        # Implementation
        ...


# Type checker verifies structural compatibility
def create_service(repo: UserRepository) -> UserService:
    return UserService(repo)  # PostgresUserRepository works here
```

### ABC (Abstract Base Class)

Use `ABC` when you need shared implementation:

```python
from abc import ABC, abstractmethod


class BaseRepository(ABC):
    """Base with shared implementation."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    @abstractmethod
    def find_by_id(self, entity_id: str) -> Any | None:
        """Subclasses must implement."""
        ...

    def health_check(self) -> bool:
        """Shared implementation."""
        return self._connection.is_alive()


class UserRepository(BaseRepository):
    def find_by_id(self, entity_id: str) -> User | None:
        # Uses self._connection from base
        ...
```

### When to Use Which

| Use Case | Pattern |
|----------|---------|
| Pure interface, no shared code | `Protocol` |
| Shared implementation needed | `ABC` |
| External library you can't modify | `Protocol` |
| Framework extension point | `ABC` |

### Consumer-Side Definition

Define interfaces where they're used, not where implemented:

```python
# In service module — defines what it needs
class UserStore(Protocol):
    def get(self, user_id: str) -> User | None: ...


class UserService:
    def __init__(self, store: UserStore) -> None:
        self.__store = store
```

---

## Dependency Injection

### Constructor Injection (Preferred)

```python
class OrderService:
    def __init__(
        self,
        repository: OrderRepository,
        payment_client: PaymentClient,
        logger: logging.Logger,
    ) -> None:
        self.__repository = repository
        self.__payment_client = payment_client
        self.__logger = logger

    def create_order(self, request: CreateOrderRequest) -> Order:
        # Uses injected dependencies
        ...
```

### Argument Order

**Config → Dependencies → Logger**

```python
def __init__(
    self,
    config: ServiceConfig,           # 1. WHAT (defines behaviour)
    repository: OrderRepository,     # 2. CAPABILITIES (dependencies)
    payment_client: PaymentClient,
    logger: logging.Logger,          # 3. OBSERVABILITY (cross-cutting)
) -> None:
```

### Wiring at Composition Root

```python
# main.py or app factory
def create_app() -> Flask:
    # Create dependencies
    db = create_database_connection(settings.database_url)
    repository = PostgresOrderRepository(db)
    payment_client = StripeClient(settings.stripe_key)
    logger = logging.getLogger("order_service")

    # Wire together
    order_service = OrderService(
        config=ServiceConfig.from_settings(settings),
        repository=repository,
        payment_client=payment_client,
        logger=logger,
    )

    # Create app with injected services
    app = Flask(__name__)
    register_routes(app, order_service)
    return app
```

---

## Visibility: Private by Default

### Underscore Conventions

| Prefix | Meaning | Access |
|--------|---------|--------|
| `name` | Public | Accessible from anywhere |
| `_name` | Protected | Internal use, subclasses may access |
| `__name` | Private | Name-mangled, truly private |

### Leaf Classes vs Base Classes

```python
# LEAF CLASS — not designed for inheritance
class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self.__repo = repo      # Double underscore — truly private
        self.__cache: dict = {}

    def get_user(self, user_id: str) -> User:
        if user_id in self.__cache:
            return self.__cache[user_id]
        # ...

    def __validate(self, user: User) -> None:  # Private method
        # ...


# BASE CLASS — designed for inheritance
class BaseHandler(ABC):
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger  # Single underscore — subclasses can access

    @abstractmethod
    def _process(self, request: Request) -> Response:  # Extension point
        ...

    def handle(self, request: Request) -> Response:
        self._logger.info("handling request")
        return self._process(request)
```

### Rules

| Class Type | Internals | Extension Points |
|------------|-----------|------------------|
| Leaf class (Service, Handler, Factory) | `__` (double) | N/A |
| Base/Abstract class | `__` for truly private | `_` for overridable |
| Mixin | `_` for shared | `_` for hooks |

---

## Configuration

### Pydantic Settings

```python
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings from environment."""

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Usage
settings = Settings()
```

### Config vs Settings

| Type | Purpose | Example |
|------|---------|---------|
| Settings | Environment/external config | `DATABASE_URL`, `API_KEY` |
| Config | Computed/derived config | Timeout values, feature flags |

```python
class ServiceConfig:
    """Derived configuration for service."""

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
        batch_size: int = 100,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.batch_size = batch_size

    @classmethod
    def from_settings(cls, settings: Settings) -> "ServiceConfig":
        return cls(
            timeout=30.0 if settings.debug else 10.0,
            max_retries=1 if settings.debug else 3,
        )
```

---

## Data Classes

### When to Use Which

| Use Case | Pattern |
|----------|---------|
| Simple data container | `@dataclass` |
| API request/response | Pydantic `BaseModel` |
| Config with validation | Pydantic `BaseModel` or `BaseSettings` |
| Immutable value object | `@dataclass(frozen=True)` |

### Dataclass for Internal Data

```python
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class User:
    id: str
    email: str
    name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    roles: list[str] = field(default_factory=list)
```

### Pydantic for External Data

```python
from pydantic import BaseModel, Field, field_validator


class CreateUserRequest(BaseModel):
    """API request with validation."""

    email: str = Field(min_length=5, max_length=255)
    name: str = Field(min_length=1, max_length=100)
    role: str = Field(default="user")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("invalid email format")
        return v.lower()


class UserResponse(BaseModel):
    """API response."""

    id: str
    email: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True  # Allow from ORM objects
```

---

## Layered Architecture

When using layers (if codebase uses this pattern):

```
┌─────────────────────────────────────┐
│           API / Handlers            │  ← HTTP, validation
├─────────────────────────────────────┤
│             Services                │  ← Business logic
├─────────────────────────────────────┤
│           Repositories              │  ← Data access
├─────────────────────────────────────┤
│        Database / External          │  ← Infrastructure
└─────────────────────────────────────┘
```

### Layer Rules

| Layer | Knows About | Returns |
|-------|-------------|---------|
| Handler | Service, Request/Response models | HTTP responses |
| Service | Repository, domain models | Domain models |
| Repository | Database, row models | Domain models |

### Conversion Between Layers

```python
# Repository returns domain model
class UserRepository:
    def find_by_id(self, user_id: str) -> User | None:
        row = self.__session.query(UserRow).get(user_id)
        if row is None:
            return None
        return row.to_domain()


# Handler converts to response
@app.get("/users/{user_id}")
def get_user(user_id: str) -> UserResponse:
    user = user_service.get_user(user_id)
    return UserResponse.from_orm(user)
```

---

## Async Architecture

### Async Service Pattern

```python
class AsyncUserService:
    def __init__(
        self,
        repository: AsyncUserRepository,
        cache: AsyncCache,
    ) -> None:
        self.__repository = repository
        self.__cache = cache

    async def get_user(self, user_id: str) -> User:
        cached = await self.__cache.get(f"user:{user_id}")
        if cached:
            return User.model_validate_json(cached)

        user = await self.__repository.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        await self.__cache.set(f"user:{user_id}", user.model_dump_json())
        return user
```

### Don't Mix Sync and Async

```python
# ❌ BAD — blocking call in async function
async def fetch_user(user_id: str) -> User:
    response = requests.get(f"/users/{user_id}")  # Blocks event loop!
    return User.model_validate(response.json())

# ✅ GOOD — async HTTP client
async def fetch_user(user_id: str) -> User:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"/users/{user_id}") as response:
            data = await response.json()
            return User.model_validate(data)
```

---

## Quick Reference: Architecture Violations

| Violation | Fix |
|-----------|-----|
| Separate `interfaces.py` file | Move interface to consumer file |
| ABC with only 1 implementation | Use concrete class or Protocol |
| Mixing sync/async in same service | Choose one, be consistent |
| Direct DB access in handler | Add repository layer |
| Business logic in handler | Move to service |
| Hard-coded config values | Use Settings/Config classes |
| Global mutable state | Inject dependencies |
| Single underscore in leaf class | Use double underscore `__` |
| Circular imports | Extract shared types to separate module |
| God class with many responsibilities | Split into focused classes |

---

## Java/C# Anti-Patterns to Avoid

### Interface for Every Class

```python
# ❌ WRONG — interface with single implementation
class IUserService(Protocol):
    def get_user(self, user_id: str) -> User: ...

class UserService:  # Only implementation
    def get_user(self, user_id: str) -> User: ...

# ✅ RIGHT — just use the class
class UserService:
    def get_user(self, user_id: str) -> User: ...
```

### Factory Pattern Everywhere

```python
# ❌ WRONG — factory for simple construction
class UserServiceFactory:
    def create(self, repo: UserRepository) -> UserService:
        return UserService(repo)

# ✅ RIGHT — just construct directly
user_service = UserService(repo)
```

### Over-Abstraction

```python
# ❌ WRONG — unnecessary abstraction layers
class AbstractBaseUserRepository(ABC): ...
class BaseUserRepository(AbstractBaseUserRepository): ...
class UserRepository(BaseUserRepository): ...

# ✅ RIGHT — simple, direct
class UserRepository:
    def find_by_id(self, user_id: str) -> User | None: ...
```

---

## Checklist

### Project Structure
- [ ] Code organised by feature, not layer (unless codebase uses layers)
- [ ] Related code lives together
- [ ] No circular imports

### Classes
- [ ] Direct names without layer suffixes (unless codebase uses them)
- [ ] Leaf classes use `__` for private members
- [ ] Base classes use `_` for extension points
- [ ] Dependencies injected via constructor

### Interfaces
- [ ] Protocol used for pure interfaces
- [ ] ABC used only when sharing implementation
- [ ] No interface with single implementation (unless testing needs it)
- [ ] Interfaces defined where consumed

### Configuration
- [ ] Pydantic Settings for environment config
- [ ] No hard-coded values
- [ ] Config passed via constructor, not global
