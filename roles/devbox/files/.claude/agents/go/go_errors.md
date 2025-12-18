# Go Errors Reference

Reference document for error handling patterns. Used by Go agents (`software-engineer-go`, `unit-test-writer-go`, `code-reviewer-go`).

---

## Error Strategy Decision Tree

```
Is the error a known, expected condition callers should check?
│
├─ YES → Is it a simple condition (not found, invalid, etc.)?
│        │
│        ├─ YES → Sentinel error (var ErrNotFound = errors.New(...))
│        │
│        └─ NO → Does caller need structured data from the error?
│                │
│                ├─ YES → Custom error type (type ValidationError struct{...})
│                │
│                └─ NO → Sentinel error
│
└─ NO → Just wrap with context: fmt.Errorf("doing X: %w", err)
```

---

## Sentinel Errors

Simple, package-level error values for expected conditions.

### When to Use

- Caller needs to check for specific error condition
- Error represents simple state (not found, already exists, unauthorized)
- No additional context needed beyond "this happened"

### Pattern

```go
package storage

import "errors"

// Sentinel errors — exported, documented
var (
    // ErrNotFound is returned when the requested resource doesn't exist.
    ErrNotFound = errors.New("not found")

    // ErrAlreadyExists is returned when trying to create a resource that exists.
    ErrAlreadyExists = errors.New("already exists")

    // ErrInvalidID is returned when the provided ID format is invalid.
    ErrInvalidID = errors.New("invalid id")
)

func (r *Repository) Get(ctx context.Context, id string) (*User, error) {
    user, err := r.db.QueryRow(ctx, query, id)
    if errors.Is(err, sql.ErrNoRows) {
        return nil, ErrNotFound  // wrap NOT needed — sentinel is the context
    }
    if err != nil {
        return nil, fmt.Errorf("querying user %s: %w", id, err)
    }
    return user, nil
}
```

### Checking Sentinel Errors

```go
user, err := repo.Get(ctx, userID)
if errors.Is(err, storage.ErrNotFound) {
    // handle not found
    return nil, nil  // or return default, etc.
}
if err != nil {
    return nil, fmt.Errorf("getting user: %w", err)
}
```

### BAD vs GOOD

```go
// BAD — string comparison
if err.Error() == "not found" { }

// BAD — direct equality (breaks if wrapped)
if err == storage.ErrNotFound { }

// GOOD — errors.Is handles wrapping
if errors.Is(err, storage.ErrNotFound) { }
```

---

## Custom Error Types

Structured errors that carry additional context.

### When to Use

- Caller needs to extract data from the error (field name, code, etc.)
- Error represents complex failure with multiple attributes
- Need to distinguish error subtypes programmatically

### Basic Pattern

```go
// ValidationError represents a validation failure with field details.
type ValidationError struct {
    Field   string
    Message string
    Value   any
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation failed on %s: %s", e.Field, e.Message)
}

func ValidateUser(u User) error {
    if u.Email == "" {
        return &ValidationError{
            Field:   "email",
            Message: "required",
        }
    }
    if !strings.Contains(u.Email, "@") {
        return &ValidationError{
            Field:   "email",
            Message: "invalid format",
            Value:   u.Email,
        }
    }
    return nil
}
```

### Checking Custom Errors

```go
err := ValidateUser(user)
if err != nil {
    var valErr *ValidationError
    if errors.As(err, &valErr) {
        // Access structured data
        log.Warn().
            Str("field", valErr.Field).
            Str("message", valErr.Message).
            Msg("validation failed")
        return nil, err
    }
    // Unknown error
    return nil, fmt.Errorf("validating user: %w", err)
}
```

### With Error Code

```go
type APIError struct {
    Code       string
    Message    string
    StatusCode int
    Cause      error
}

func (e *APIError) Error() string {
    if e.Cause != nil {
        return fmt.Sprintf("%s: %s: %v", e.Code, e.Message, e.Cause)
    }
    return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

func (e *APIError) Unwrap() error {
    return e.Cause
}

// Usage
func (s *Service) CreateUser(ctx context.Context, req CreateUserRequest) error {
    if exists, _ := s.repo.Exists(ctx, req.Email); exists {
        return &APIError{
            Code:       "USER_EXISTS",
            Message:    "user with this email already exists",
            StatusCode: http.StatusConflict,
        }
    }
    // ...
}

// In handler
var apiErr *APIError
if errors.As(err, &apiErr) {
    w.WriteHeader(apiErr.StatusCode)
    json.NewEncoder(w).Encode(map[string]string{
        "code":    apiErr.Code,
        "message": apiErr.Message,
    })
    return
}
```

### Combining with Sentinel

```go
// Sentinel for simple checks
var ErrValidation = errors.New("validation error")

// Custom type for detailed info
type ValidationError struct {
    Field   string
    Message string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation: %s: %s", e.Field, e.Message)
}

// Implement Is for sentinel compatibility
func (e *ValidationError) Is(target error) bool {
    return target == ErrValidation
}

// Now both work:
// errors.Is(err, ErrValidation)     — simple check
// errors.As(err, &valErr)           — get details
```

### BAD vs GOOD

```go
// BAD — type assertion (breaks if wrapped)
if valErr, ok := err.(*ValidationError); ok { }

// GOOD — errors.As handles wrapping
var valErr *ValidationError
if errors.As(err, &valErr) { }

// BAD — custom error without Error() method
type MyError struct { Message string }  // doesn't implement error

// GOOD — implements error interface
type MyError struct { Message string }
func (e *MyError) Error() string { return e.Message }
```

---

## Error Wrapping

Adding context as errors propagate up the stack.

### Basic Pattern

```go
func (s *Service) ProcessOrder(ctx context.Context, orderID string) error {
    order, err := s.repo.Get(ctx, orderID)
    if err != nil {
        return fmt.Errorf("getting order %s: %w", orderID, err)
    }

    if err := s.validate(order); err != nil {
        return fmt.Errorf("validating order: %w", err)
    }

    if err := s.chargePayment(ctx, order); err != nil {
        return fmt.Errorf("charging payment: %w", err)
    }

    return nil
}
```

### When to Use `%w` vs `%v`

| Situation | Use | Why |
|-----------|-----|-----|
| Internal error propagation | `%w` | Preserve error chain for `errors.Is`/`As` |
| System boundary (API response) | `%v` | Hide internal details, break chain |
| Logging then returning | `%w` | Preserve for caller |

```go
// Internal — preserve chain
func (r *repo) Get(ctx context.Context, id string) (*User, error) {
    row := r.db.QueryRow(ctx, query, id)
    if err := row.Scan(&user); err != nil {
        return nil, fmt.Errorf("scanning user: %w", err)  // %w — internal
    }
    return &user, nil
}

// API boundary — hide internals
func (h *Handler) GetUser(w http.ResponseWriter, r *http.Request) {
    user, err := h.service.Get(r.Context(), userID)
    if err != nil {
        if errors.Is(err, storage.ErrNotFound) {
            http.Error(w, "user not found", http.StatusNotFound)
            return
        }
        // Log full error, return generic message
        h.logger.Error().Err(err).Msg("getting user")
        http.Error(w, "internal error", http.StatusInternalServerError)  // no %w
        return
    }
    // ...
}
```

### Context Guidelines

```go
// BAD — no context
return err

// BAD — redundant context
return fmt.Errorf("error getting user: %w", err)  // "error" is noise

// BAD — too much context
return fmt.Errorf("failed to get user from database in GetUser function: %w", err)

// GOOD — concise, specific
return fmt.Errorf("getting user %s: %w", userID, err)

// GOOD — action + identifier
return fmt.Errorf("parsing config file %s: %w", path, err)
return fmt.Errorf("connecting to %s:%d: %w", host, port, err)
```

### Error Chain Example

```go
// Full chain when error reaches top:
// "processing order abc123: charging payment: creating transaction: connecting to payment gateway: dial tcp: connection refused"

// Each layer adds just its context:
// repo:    "connecting to payment gateway: %w"
// service: "creating transaction: %w"
// handler: "charging payment: %w"
// caller:  "processing order abc123: %w"
```

---

## Stack Traces

Use `github.com/pkg/errors` at error origin for stack traces.

### Setup

```go
import (
    "github.com/rs/zerolog"
    "github.com/rs/zerolog/pkgerrors"
)

func main() {
    // Enable stack trace marshaling
    zerolog.ErrorStackMarshaler = pkgerrors.MarshalStack

    logger := zerolog.New(os.Stderr).With().Timestamp().Logger()
    // ...
}
```

### Capture at Origin

```go
import "github.com/pkg/errors"

// At error ORIGIN — capture stack
func readConfig(path string) (Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return Config{}, errors.Wrap(err, "reading config")  // captures stack
    }
    // ...
}

// When PROPAGATING — use fmt.Errorf
func initApp(configPath string) error {
    cfg, err := readConfig(configPath)
    if err != nil {
        return fmt.Errorf("initializing: %w", err)  // preserves original stack
    }
    // ...
}
```

### Logging with Stack

```go
if err != nil {
    logger.Error().
        Stack().  // includes stack if error has one
        Err(err).
        Str("orderID", orderID).
        Msg("processing failed")
}
```

### When to Capture Stack

| Location | Capture Stack? | Method |
|----------|---------------|--------|
| Error origin in your code | Yes | `errors.Wrap(err, "msg")` |
| Wrapping external error first time | Yes | `errors.Wrap(err, "msg")` |
| Propagating already-wrapped error | No | `fmt.Errorf("msg: %w", err)` |
| Creating new error (no cause) | Optional | `errors.New("msg")` vs `fmt.Errorf("msg")` |

---

## Multi-Error Handling

Collecting multiple errors from batch operations.

### Using errors.Join (Go 1.20+)

```go
func validateAll(items []Item) error {
    var errs []error

    for i, item := range items {
        if err := validate(item); err != nil {
            errs = append(errs, fmt.Errorf("item %d: %w", i, err))
        }
    }

    return errors.Join(errs...)  // nil if errs is empty
}

// Checking joined errors
err := validateAll(items)
if err != nil {
    // errors.Is works through joined errors
    if errors.Is(err, ErrInvalidFormat) {
        // at least one item had invalid format
    }
}
```

### Shutdown Errors

```go
func shutdown(ctx context.Context, components ...io.Closer) error {
    var errs []error

    for _, c := range components {
        if err := c.Close(); err != nil {
            errs = append(errs, err)
        }
    }

    return errors.Join(errs...)
}
```

---

## Error Handling Patterns

### Early Return

```go
// GOOD — handle error, then happy path
func process(data []byte) (*Result, error) {
    if len(data) == 0 {
        return nil, errors.New("empty data")
    }

    parsed, err := parse(data)
    if err != nil {
        return nil, fmt.Errorf("parsing: %w", err)
    }

    validated, err := validate(parsed)
    if err != nil {
        return nil, fmt.Errorf("validating: %w", err)
    }

    return transform(validated), nil
}
```

### Errors as Values

```go
// For repetitive operations, accumulate error state
type errWriter struct {
    w   io.Writer
    err error
}

func (ew *errWriter) write(data []byte) {
    if ew.err != nil {
        return
    }
    _, ew.err = ew.w.Write(data)
}

// Usage
ew := &errWriter{w: w}
ew.write(header)
ew.write(body)
ew.write(footer)
if ew.err != nil {
    return fmt.Errorf("writing response: %w", ew.err)
}
```

### Must Pattern (Init-Time Only)

**CRITICAL SCOPE RESTRICTION**: `Must*` functions are acceptable ONLY at initialization time:
- Package-level `var` declarations
- `init()` functions

**FORBIDDEN in runtime code** — any function called after program starts.

```go
// Must wraps function that returns (T, error), panics on error.
func Must[T any](v T, err error) T {
    if err != nil {
        panic(err)
    }
    return v
}

// ACCEPTABLE — package-level vars, fails at startup
var (
    templates = Must(template.ParseGlob("templates/*.html"))
    config    = Must(LoadConfig("config.yaml"))
)

// ACCEPTABLE — init(), fails at startup
func init() {
    db = Must(sql.Open("postgres", connStr))
}

// FORBIDDEN — runtime code, unpredictable failure
func (s *Service) ProcessRequest(ctx context.Context, req Request) error {
    cfg := Must(parseConfig(req.Data))  // WRONG: panics at runtime
    // ...
}

// REQUIRED — runtime code returns errors
func (s *Service) ProcessRequest(ctx context.Context, req Request) error {
    cfg, err := parseConfig(req.Data)
    if err != nil {
        return fmt.Errorf("parsing config: %w", err)
    }
    // ...
}
```

**Why init-time is acceptable:**
- Program fails immediately, before any real work
- Caught on first test run or deployment
- No user requests affected

**Why runtime is forbidden:**
- Unpredictable failure point
- Caller cannot recover or retry
- Violates Go's error handling contract

---

## Common Mistakes

### Ignoring Errors

```go
// BAD — silent failure
result, _ := doSomething()

// GOOD — explicit handling
result, err := doSomething()
if err != nil {
    return fmt.Errorf("doing something: %w", err)
}
```

### Checking Error String

```go
// BAD — fragile, breaks with wrapping
if strings.Contains(err.Error(), "not found") { }

// GOOD — use sentinel or type
if errors.Is(err, ErrNotFound) { }
```

### Returning err AND value

```go
// BAD — confusing contract
func Get(id string) (*User, error) {
    user, err := fetch(id)
    if err != nil {
        return user, err  // returning partial user?
    }
    return user, nil
}

// GOOD — nil or valid, never both with error
func Get(id string) (*User, error) {
    user, err := fetch(id)
    if err != nil {
        return nil, err
    }
    return user, nil
}
```

### Double Wrapping

```go
// BAD — wrapped twice at same level
if err != nil {
    return fmt.Errorf("operation failed: %w", fmt.Errorf("getting user: %w", err))
}

// GOOD — single wrap with full context
if err != nil {
    return fmt.Errorf("getting user for operation: %w", err)
}
```
