---
name: go-errors
description: >
  Go error handling patterns and best practices. Use when discussing error handling,
  sentinel errors, custom error types, error wrapping, stack traces, or error
  classification. Triggers on: error handling, sentinel error, wrap error, errors.Is,
  errors.As, error chain, stack trace, ErrNotFound, custom error type.
---

# Go Errors Reference

Error handling patterns for Go projects.

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

### ALWAYS Use `%w` When Wrapping

**When calling `fmt.Errorf()`, ALWAYS use `%w` to preserve error chains.**

```go
// ✅ ALWAYS correct when wrapping
return fmt.Errorf("fetching user: %w", err)

// ❌ NEVER do this
return fmt.Errorf("fetching user: %v", err)  // Breaks error chain
```

**Why always `%w`:**
- Preserves error chain for `errors.Is()` / `errors.As()`
- Critical for debugging - root cause preserved through entire stack
- Enables observability - logs capture full context
- No downside - chain preserved internally, control what users see separately

**Exception:** Only use `%v` when you explicitly want to discard error context (rare, usually wrong).

### Observability: Logging vs User Responses

**Separating internal observability from external communication.**

At API boundaries, errors typically:
1. Arrive already wrapped (with `%w` through the stack)
2. Get logged with full context
3. Get translated to user-safe messages

```go
func (h *Handler) ProcessOrder(w http.ResponseWriter, r *http.Request) {
    order, err := h.service.CreateOrder(r.Context(), req)
    if err != nil {
        // Classify error type
        if errors.Is(err, ErrInvalidInput) {
            // User error - safe to expose
            respondJSON(w, 400, ErrorResponse{
                Code:    "INVALID_INPUT",
                Message: "Invalid order data",
            })
            return
        }

        // System error - hide internals
        h.logger.Error().
            Err(err).  // Full error chain from %w wrapping
            Str("order_id", req.OrderID).
            Msg("order creation failed")

        respondJSON(w, 500, ErrorResponse{
            Code:    "INTERNAL_ERROR",
            Message: "Unable to process order",
        })
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

**CRITICAL SCOPE RESTRICTION — Stricter than typical Go code.**

**Our rule:** `Must*` acceptable ONLY at initialization:
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

---

## Common Mistakes

### Returning Nil Pointer Without Error

```go
// ❌ BAD — nil pointer without error (silent failure)
func Parse(data []byte) *Config {
    if len(data) == 0 {
        return nil  // Caller can't handle this properly
    }
    // ...
}

// ✅ GOOD — nil with error (explicit failure)
func Parse(data []byte) (*Config, error) {
    if len(data) == 0 {
        return nil, errors.New("empty data")
    }
    // ...
}
```

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

### Breaking Error Chains

```go
// ❌ BAD — throwing away error context
if err != nil {
    return errors.New("operation failed")  // Lost all context!
}

// ❌ BAD — using %v breaks chain
if err != nil {
    return fmt.Errorf("operation failed: %v", err)  // errors.Is() won't work
}

// ✅ GOOD — preserve chain
if err != nil {
    return fmt.Errorf("operation failed: %w", err)
}
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

---

## Nil Pointer Returns

**STRICT RULE: Any function that can return a nil pointer MUST return error.**

**Rationale:** Caller needs to distinguish between success and failure. Even if nil is "expected" for certain inputs, it's still a condition the caller must handle explicitly.

### The Problem

```go
// ❌ FORBIDDEN — nil pointer without error
func ParseData(input []byte) *Result {
    if len(input) == 0 {
        return nil  // Silent failure - caller can't handle properly
    }
    // ...
}

func ConvertRecord(source *SourceRecord) *TargetRecord {
    if source == nil {
        return nil  // Caller loses context about WHY it's nil
    }
    return &TargetRecord{...}
}

// ✅ REQUIRED — nil with error (always)
func ParseData(input []byte) (*Result, error) {
    if len(input) == 0 {
        return nil, errors.New("empty input")
    }
    // ...
    return result, nil
}

func ConvertRecord(source *SourceRecord) (*TargetRecord, error) {
    if source == nil {
        return nil, errors.New("source record is nil")
    }
    return &TargetRecord{...}, nil
}
```

### Why Error Return Is Mandatory

```go
// WITHOUT error — caller has no context
result := ParseData(data)
if result == nil {
    // Is this a bug? Empty input? Invalid data?
    // Can't log properly, can't return meaningful error upstream
    return nil, errors.New("parse failed")  // Lost context!
}

// WITH error — caller can handle appropriately
result, err := ParseData(data)
if err != nil {
    // Clear failure path with context
    log.Warn().Err(err).Msg("skipping invalid data")
    return nil, fmt.Errorf("parsing data: %w", err)
}

// Caller might choose different handling:
if errors.Is(err, ErrEmptyInput) {
    return defaultResult, nil  // Use default for empty
}
if errors.Is(err, ErrInvalidFormat) {
    return nil, err  // Hard failure for invalid
}
```

### Decision Tree (No Exceptions)

| Scenario | Return signature | Example |
|----------|------------------|---------|
| Function can return nil | `(*T, error)` — ALWAYS | `Parse([]byte) (*Config, error)` |
| Function never returns nil, can't fail | `*T` | `NewCache() *Cache` |
| Function never returns nil, can fail | `(*T, error)` | `NewClient(addr string) (*Client, error)` |

### Common Cases

```go
// ✅ Parsing/conversion — can return nil = return error
func ParseConfig(data []byte) (*Config, error)
func DecodeMessage(raw string) (*Message, error)
func TransformRecord(input *InputRecord) (*OutputRecord, error)

// ✅ Database/storage — nil = not found
func FindByID(ctx context.Context, id string) (*User, error) {
    // Returns (nil, ErrNotFound) when not found
}

func LoadDocument(path string) (*Document, error) {
    // Returns (nil, os.ErrNotExist) when file doesn't exist
}

// ✅ Factory/constructor — validates and can fail
func NewConnection(cfg Config) (*Connection, error) {
    if err := cfg.Validate(); err != nil {
        return nil, err
    }
    return &Connection{...}, nil
}

// ✅ Never returns nil — constructor with defaults
func NewCache() *Cache {
    return &Cache{items: make(map[string]any)}
}

func NewBuffer() *Buffer {
    return &Buffer{data: make([]byte, 0, 1024)}
}
```

### Anti-Pattern to Avoid

```go
// ❌ NEVER DO THIS - defeats the purpose
func TransformItem(item *Item) *ProcessedItem {
    if item == nil {
        return nil  // "nil is expected behavior"
    }
    return &ProcessedItem{...}
}

// Later in code:
for _, item := range items {
    processed := TransformItem(item)
    if processed == nil {
        continue  // Silently skipping - why? Bug? Expected?
    }
    // ...
}

// ✅ CORRECT - explicit error handling
func TransformItem(item *Item) (*ProcessedItem, error) {
    if item == nil {
        return nil, errors.New("item is nil")
    }
    return &ProcessedItem{...}, nil
}

// Later in code - clear intent:
for _, item := range items {
    processed, err := TransformItem(item)
    if err != nil {
        log.Warn().Err(err).Msg("skipping invalid item")
        continue  // Explicit choice to skip
    }
    // ...
}
```

### Edge Case: Getter Methods

```go
// Getter methods returning internal state can return nil without error
type Container struct {
    current *Item
}

// OK — getter returning internal field (nil is valid state)
func (c *Container) Current() *Item {
    return c.current  // nil means "no current item"
}

// But if there's ANY logic/transformation → return error
func (c *Container) CurrentProcessed() (*ProcessedItem, error) {
    if c.current == nil {
        return nil, errors.New("no current item")
    }
    return c.current.Process()
}
```
