---
name: validation
description: >
  Input validation patterns for Go and Python. Covers boundary validation, Pydantic,
  struct tags, sanitisation, error accumulation, and validation layers.
  Triggers on: validation, validate, input validation, sanitise, sanitize, Pydantic,
  validator, boundary, user input, request validation.
---

# Input Validation Patterns

Validation at system boundaries for Go and Python.

---

## Core Principle: Trust Internally, Validate Externally

```
External world (untrusted) → [VALIDATION BOUNDARY] → Internal code (trusted)
```

| Boundary | Validate? | Examples |
|----------|-----------|---------|
| HTTP request input | **YES** | Query params, body, headers |
| CLI arguments | **YES** | Flags, positional args |
| File/config input | **YES** | YAML, JSON, env vars |
| Message queue payload | **YES** | Kafka, RabbitMQ messages |
| Between internal packages | **NO** | Function calls within your service |
| Database reads (own DB) | **NO** | Data you wrote is already valid |

**Anti-pattern:** Validating the same data at every layer. Validate once at the boundary, then trust.

---

## Go Validation Patterns

### Constructor Validation

```go
func NewServer(cfg Config) (*Server, error) {
    if cfg.Port < 1 || cfg.Port > 65535 {
        return nil, fmt.Errorf("invalid port %d: must be 1-65535", cfg.Port)
    }
    if cfg.Timeout <= 0 {
        return nil, errors.New("timeout must be positive")
    }
    return &Server{cfg: cfg}, nil
}
```

### Validation Methods

```go
type CreateUserRequest struct {
    Email string `json:"email"`
    Name  string `json:"name"`
    Age   int    `json:"age"`
}

func (r CreateUserRequest) Validate() error {
    var errs []error
    if r.Email == "" {
        errs = append(errs, errors.New("email is required"))
    }
    if r.Name == "" {
        errs = append(errs, errors.New("name is required"))
    }
    if r.Age < 0 || r.Age > 150 {
        errs = append(errs, fmt.Errorf("invalid age %d", r.Age))
    }
    return errors.Join(errs...)
}
```

### Handler-Level Validation

```go
func (h *Handler) CreateUser(w http.ResponseWriter, r *http.Request) {
    var req CreateUserRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        respondError(w, http.StatusBadRequest, "invalid JSON")
        return
    }
    if err := req.Validate(); err != nil {
        respondError(w, http.StatusUnprocessableEntity, err.Error())
        return
    }
    // req is now trusted — pass to service without re-validation
    user, err := h.service.CreateUser(r.Context(), req)
}
```

---

## Python Validation Patterns

### Pydantic (Preferred)

```python
from pydantic import BaseModel, Field, field_validator

class CreateUserRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=0, le=150)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("invalid email format")
        return v.lower().strip()
```

### dataclass + Manual Validation

```python
@dataclass
class Config:
    host: str
    port: int
    timeout: float

    def __post_init__(self) -> None:
        if not 1 <= self.port <= 65535:
            raise ValueError(f"invalid port {self.port}")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
```

---

## Sanitisation vs Validation

| Concept | Purpose | Example |
|---------|---------|---------|
| **Validation** | Reject invalid input | "age must be >= 0" |
| **Sanitisation** | Transform input to safe form | Strip HTML, normalise whitespace |

**Order:** Sanitise first, then validate the sanitised result.

```python
# Sanitise
email = raw_email.strip().lower()
# Then validate
if not is_valid_email(email):
    raise ValueError("invalid email")
```

---

## Error Accumulation

Collect all validation errors rather than failing on the first:

```python
# Python — Pydantic does this automatically
try:
    request = CreateUserRequest(**data)
except ValidationError as e:
    # e.errors() returns ALL validation failures
    return {"errors": e.errors()}, 422
```

```go
// Go — manual accumulation
func (r Request) Validate() error {
    var errs []error
    if r.Name == "" { errs = append(errs, errors.New("name required")) }
    if r.Age < 0   { errs = append(errs, errors.New("age must be >= 0")) }
    return errors.Join(errs...)  // nil if no errors
}
```

---

## Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| Validating in every layer | Redundant, noisy, inconsistent | Validate at boundary only |
| Trusting external input | Injection, crashes, corruption | Always validate at boundaries |
| Silent coercion | `int("abc")` fails, `int("0")` might be wrong | Explicit validation with clear errors |
| Validation in domain logic | Mixes concerns | Validate in handler/controller layer |
| Custom regex for email/URL | Fragile, incomplete | Use established libraries |
