---
name: python-monolith
description: >
  Flask-OpenAPI3 monolith patterns for layered DI architecture. Covers handler-service-repository
  layers, dependency injection, SQLAlchemy session management, feature module structure.
  Triggers on: Flask, flask-openapi3, monolith, APIBlueprint, APIView, DI, dependency injection,
  provider, container, layered architecture, Flask service layer.
---

# Flask-OpenAPI3 Monolith Patterns

Architecture patterns for Flask-OpenAPI3 applications following a layered dependency injection architecture.

---

## Layered Architecture

```
Request → Handler (Flask route) → Service (business logic) → Repository (data access) → Database
```

| Layer | Responsibility | Depends On |
|-------|---------------|------------|
| **Handler** | HTTP concerns (request/response, status codes, validation) | Service |
| **Service** | Business logic, orchestration, domain rules | Repository, external services |
| **Repository** | Data access, queries, persistence | SQLAlchemy session |

**Rules:**
- Handlers never access repositories directly
- Services never import Flask (no `request`, no `abort`)
- Repositories return domain objects, not SQLAlchemy models directly

---

## Feature Module Structure

```
app/
├── features/
│   ├── users/
│   │   ├── __init__.py
│   │   ├── handlers.py      # Flask routes (APIBlueprint)
│   │   ├── service.py        # Business logic
│   │   ├── repository.py     # Data access
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   └── providers.py      # DI provider functions
│   └── orders/
│       └── ...
├── core/
│   ├── database.py           # Session factory, base model
│   ├── container.py          # DI container
│   └── exceptions.py         # Domain exceptions
└── app.py                    # Application factory
```

---

## Dependency Injection

### Provider Pattern

```python
# features/users/providers.py
from app.core.database import get_session

def provide_user_repository() -> UserRepository:
    return UserRepository(session=get_session())

def provide_user_service() -> UserService:
    return UserService(
        repository=provide_user_repository(),
        email_service=provide_email_service(),
    )
```

### Constructor Injection

```python
# features/users/service.py
class UserService:
    def __init__(
        self,
        repository: UserRepository,
        email_service: EmailService,
    ) -> None:
        self._repository = repository
        self._email_service = email_service

    def create_user(self, data: CreateUserRequest) -> User:
        user = self._repository.create(data)
        self._email_service.send_welcome(user.email)
        return user
```

---

## Flask-OpenAPI3 Patterns

### APIBlueprint Handlers

```python
from flask_openapi3 import APIBlueprint

bp = APIBlueprint("users", __name__, url_prefix="/api/v1/users")

@bp.post("/", responses={"201": UserResponse, "422": ErrorResponse})
def create_user(body: CreateUserRequest) -> tuple[UserResponse, int]:
    service = provide_user_service()
    user = service.create_user(body)
    return UserResponse.from_domain(user), 201
```

### Schema Patterns

```python
from pydantic import BaseModel, Field

class CreateUserRequest(BaseModel):
    email: str = Field(..., description="User email address")
    name: str = Field(..., min_length=1, max_length=255)

class UserResponse(BaseModel):
    id: str
    email: str
    name: str

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        return cls(id=str(user.id), email=user.email, name=user.name)
```

---

## SQLAlchemy Session Management

```python
# core/database.py
from sqlalchemy.orm import Session, sessionmaker

SessionLocal = sessionmaker(bind=engine)

def get_session() -> Session:
    """Get a session scoped to the current request."""
    return SessionLocal()
```

**Rules:**
- One session per request
- Commit in handler layer after service succeeds
- Rollback on exception (use try/finally or context manager)
- Never pass sessions across feature boundaries

---

## Testing Patterns

```python
# Inject test dependencies via providers
def test_create_user(test_session):
    repo = UserRepository(session=test_session)
    service = UserService(repository=repo, email_service=MockEmailService())

    user = service.create_user(CreateUserRequest(email="test@example.com", name="Test"))

    assert user.email == "test@example.com"
    assert test_session.query(UserModel).count() == 1
```

---

## Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| Business logic in handlers | Untestable without Flask context | Move to service layer |
| Direct DB queries in handlers | Bypasses business rules | Use repository |
| Global session object | Not thread-safe | Session per request |
| Circular imports between features | Tight coupling | Communicate via domain events or shared interfaces |
| Fat models with business logic | Mixes persistence and domain | Separate domain objects from ORM models |
