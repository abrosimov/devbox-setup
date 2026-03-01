---
name: python-monolith
description: >
  Flask-OpenAPI3 monolith patterns for layered DI architecture. Covers handler-service-repository
  layers, dependency injection, SQLAlchemy session management, feature module structure.
  Triggers on: Flask, flask-openapi3, monolith, APIBlueprint, APIView, DI, dependency injection,
  provider, container, layered architecture, Flask service layer.
---

# Flask-OpenAPI3 Monolith Patterns

Architecture conventions for Flask-OpenAPI3 applications in this codebase.

---

## Layered Architecture

```
Request → Handler (Flask route) → Service (business logic) → Repository (data access) → Database
```

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

Use provider functions per feature module. Each provider wires the dependency chain: `provider → service(repository, ...)`. Handlers call providers to get service instances.

### Session Rules

- One session per request
- Commit in handler layer after service succeeds
- Rollback on exception (use try/finally or context manager)
- Never pass sessions across feature boundaries

---

## Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| Business logic in handlers | Untestable without Flask context | Move to service layer |
| Direct DB queries in handlers | Bypasses business rules | Use repository |
| Global session object | Not thread-safe | Session per request |
| Circular imports between features | Tight coupling | Communicate via domain events or shared interfaces |
| Fat models with business logic | Mixes persistence and domain | Separate domain objects from ORM models |
