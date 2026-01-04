---
name: python-style
description: >
  Python style guide for documentation, comments, type hints, and naming. Use when
  discussing docstrings, comments, type annotations, naming conventions, or code
  style. Triggers on: docstring, comment, type hint, naming, PEP 8, documentation,
  type annotation, Python style.
---

# Python Style Reference

Style guide for documentation, comments, type hints, and naming.

---

## Documentation Policy

**Default: NO docstrings.** Type hints and clear names are your primary documentation.

### Library vs Business Logic

**Library/Infrastructure code** (shared clients, SDK wrappers, `lib/`, reusable packages):
- Public API: Docstrings allowed for non-obvious semantics only
- Private (`_method`): Never

**Business logic** (services, handlers, domain models, application code):
- Public or private: **Never** — type hints and names ARE the documentation
- If you need a docstring to explain what a function does, rename the function

| Indicator | Library | Business Logic |
|-----------|---------|----------------|
| Could be extracted to separate package | Yes | No |
| Has external consumers | Yes | No |
| Changes with product requirements | Rarely | Frequently |
| Examples | `MongoClient`, `KubeClient` | `OrderService`, `UserHandler` |

### The Information Test

Before writing a docstring, ask: **"Does this add information beyond the signature?"**

```python
# ❌ FAILS test — signature already says everything
def get_user_by_id(user_id: str) -> User | None:
    """Get user by ID."""  # ← DELETE THIS

# ✅ PASSES test — explains algorithm choice
def sort_users(users: list[User]) -> list[User]:
    """Stable sort by (last_name, first_name) using Timsort."""
```

### When Docstrings ARE Allowed

#### 1. Complex Algorithms

When the implementation uses non-obvious algorithms or logic:

```python
def find_shortest_path(graph: Graph, start: str, end: str) -> list[str]:
    """Dijkstra's algorithm with priority queue optimization.

    Returns empty list if no path exists.
    """
```

#### 2. Non-obvious Return Semantics

When type hints don't express the full meaning:

```python
def fetch_cached(key: str) -> Data | None:
    """Returns None on cache miss, NOT if data is invalid.

    Invalid data raises ValueError. Use get() for validation.
    """
```

### When Docstrings Are FORBIDDEN

Docstrings that repeat the signature must be deleted:

```python
# ❌ FORBIDDEN — redundant
def create_user(name: str, email: str) -> User:
    """Create a user with name and email."""

# ✅ CORRECT — signature is sufficient
def create_user(name: str, email: str) -> User:
    return User(name=name, email=email)

# ❌ FORBIDDEN — obvious from name
class UserService:
    """Service for user operations."""

# ✅ CORRECT — name is self-documenting
class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

# ❌ FORBIDDEN — restates types
def set_email(self, email: str) -> None:
    """Set the user's email address.

    Args:
        email: The new email address.
    """

# ✅ CORRECT — no docstring needed
def set_email(self, email: str) -> None:
    self.email = email
```

### Module-Level Documentation

**Skip module docstrings** for internal modules. File naming should be self-evident:

```python
# ❌ FORBIDDEN — redundant
"""User service module.

Contains UserService class for user operations.
"""

# ✅ CORRECT — file name user_service.py is clear
from .repository import UserRepository

class UserService:
    ...

# ✅ ALLOWED — public API entry point with usage patterns
"""Authentication client for external services.

Usage:
    client = AuthClient(api_key="...")
    token = client.get_token(scope="read")

Thread-safe. Handles token refresh automatically.
"""
```

### Rule Summary

| Element | Docstring? | Reasoning |
|---------|-----------|-----------|
| **Simple functions** | ❌ No | Signature + types tell everything |
| **Public classes** | ❌ No | Name + `__init__` are self-documenting |
| **Internal modules** | ❌ No | File structure is self-documenting |
| **Public API modules** | Rarely | Only for usage patterns, thread-safety notes |
| **Complex algorithms** | ✅ Yes | Algorithm choice not obvious from code |
| **Non-obvious semantics** | ✅ Yes | Type hints can't express all meanings |
| **Private helpers** | ❌ No | Internal implementation details |
| **Test functions** | ❌ No | Test name should be descriptive |

---

## Inline Comments

- Two spaces before `#`, one after (PEP 8)
- Explain **WHY**, not **WHAT**
- Most code should need NO comments — use better names instead

```python
# BAD — describes what code does (obvious from reading)
i += 1  # increment i
users = []  # create empty list
if status == "active":  # check if status is active

# BAD — "why" is already obvious from naming/context
i += 1  # skip header row
cache[key] = value  # store in cache

# GOOD — explains WHY we deviate from the obvious approach
return None  # API returns 404 for missing users instead of empty list

# GOOD — explains external constraints/requirements
time.sleep(0.1)  # API rate limit: 10 requests/sec maximum

# GOOD — explains non-obvious workaround
data = json.loads(text.replace("'", '"'))  # legacy API uses single quotes

# GOOD — explains business rule not encoded in code structure
if retries > 3:
    notify_ops_team()  # SLA requires manual intervention after 3 failures
```

### Better Approach — Eliminate Comments

```python
# BAD — comment explains bad code
i = 0
for row in rows:
    if i == 0:  # skip header
        i += 1
        continue
    process(row)
    i += 1

# GOOD — self-documenting
for row in rows[1:]:
    process(row)

# BAD — comment explains unclear logic
if status == "active":  # only active users count toward license
    license_count += 1

# GOOD — extract to named function
if should_count_toward_license(user):
    license_count += 1

# BAD — comment explains magic number
if file_size > 10485760:  # 10MB in bytes
    use_streaming()

# GOOD — named constant
MAX_IN_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
if file_size > MAX_IN_MEMORY_SIZE:
    use_streaming()
```

**The 90% rule:** If you're writing a comment, first ask: "Can I change the code so the comment isn't needed?"

---

## Type Hints

### Always Use Type Hints

```python
# BAD
def process(data):
    return data.get("value")

# GOOD
def process(data: dict[str, Any]) -> str | None:
    return data.get("value")

# BETTER — use TypedDict for known structures
class UserData(TypedDict):
    name: str
    email: str

def process(data: UserData) -> str:
    return data["name"]
```

### Optional Fields — None vs Defaults

**Default to non-None types with meaningful defaults.** Use `T | None` only when `None` carries specific semantic meaning.

```python
# ✅ GOOD — defaults instead of Optional
class Entity(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: datetime | None = None  # None has special meaning: not deleted
    active: bool = True  # Not Optional — always has value

# ❌ BAD — Optional when default would work
class Entity(BaseModel):
    active: bool | None = None  # What does None mean? Just use True/False
    created_at: datetime | None = None  # Should always be set!
```

### Quick Reference

| Field Type | Default Choice | Use Optional When |
|------------|---------------|-------------------|
| `datetime` | Factory or fixed default | None means "not set" with semantic difference |
| `str` | `""` or meaningful default | Empty string is valid AND distinct from "not provided" |
| `int` | `0` or meaningful default | 0 is valid AND distinct from "not set" |
| `bool` | `True` or `False` | Rarely needed (3-state logic) |
| `list[T]` | `field(default_factory=list)` | Never (empty list is the "not set" state) |
| `dict[K, V]` | `field(default_factory=dict)` | Never (empty dict is the "not set" state) |

### Common Mistakes

```python
# ❌ ANTI-PATTERN: Optional list/dict
class Config(BaseModel):
    tags: list[str] | None = None
    metadata: dict | None = None

# ✅ CORRECT: Default factory
class Config(BaseModel):
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

# ❌ ANTI-PATTERN: Optional string when empty is fine
class User(BaseModel):
    middle_name: str | None = None

# ✅ CORRECT: Empty string default
class User(BaseModel):
    middle_name: str = ""
```

---

## Formatting

- Format with `black` (not the whole file in legacy codebases)
- Follow PEP 8 style guidelines
- Use `ruff` for linting

```bash
# Format code
uv run black src/

# Lint code
uv run ruff check src/

# Type check
uv run mypy src/
```

---

## Quick Reference: Style Violations

| Violation | Fix |
|-----------|-----|
| Docstring repeats signature | Delete the docstring |
| `# increment i` comment | Delete (obvious) |
| Magic number `10485760` | Named constant `MAX_SIZE = 10 * 1024 * 1024` |
| Missing type hints | Add types to all parameters and returns |
| `Optional[list]` | Use `list[T] = Field(default_factory=list)` |
| `Optional[str] = None` when empty is fine | Use `str = ""` |
| Module docstring for internal module | Delete |
| Comment explaining what code does | Improve code instead |
