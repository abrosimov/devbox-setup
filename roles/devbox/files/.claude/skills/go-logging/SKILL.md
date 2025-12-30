---
name: go-logging
description: >
  Go logging patterns with zerolog. Use when discussing logging, zerolog usage,
  structured logging, stack traces, log levels, or error logging. Triggers on:
  logging, zerolog, log, structured log, stack trace, log level, log.Fatal,
  fmt.Println, logger injection.
---

# Go Logging Reference

Logging patterns using zerolog for Go projects.

---

## Core Rules

### No fmt.Print*

**FORBIDDEN**: Never use `fmt.Print`, `fmt.Println`, `fmt.Printf` in production code:

```go
// BAD — unstructured, no levels, no context
fmt.Println("user logged in")
fmt.Printf("processing order %s\n", orderID)

// These are acceptable ONLY in:
// - main() for CLI output
// - Tests
// - One-off scripts
```

### Use rs/zerolog (Injected Instance)

All logging MUST use `github.com/rs/zerolog`. **Never import `log` package directly** — inject logger as dependency:

```go
import "github.com/rs/zerolog"

// GOOD — logger injected as dependency
type OrderService struct {
    logger zerolog.Logger
    db     *sql.DB
}

func NewOrderService(logger zerolog.Logger, db *sql.DB) *OrderService {
    return &OrderService{
        logger: logger.With().Str("component", "order_service").Logger(),
        db:     db,
    }
}

func (s *OrderService) Process(ctx context.Context, orderID string) error {
    s.logger.Info().
        Str("orderID", orderID).
        Msg("processing order")
    // ...
}

// BAD — global logger import
import "github.com/rs/zerolog/log"
log.Info().Msg("something happened")  // no dependency injection
```

### Never log.Fatal

**FORBIDDEN**: Never use `log.Fatal` or any fatal logging:

```go
// BAD — calls os.Exit(1), skips defers, prevents graceful shutdown
logger.Fatal().Err(err).Msg("database connection failed")

// GOOD — return error, let caller decide
func connectDB(ctx context.Context) (*DB, error) {
    db, err := sql.Open("postgres", connStr)
    if err != nil {
        return nil, fmt.Errorf("failed to open database: %w", err)
    }
    return db, nil
}

// In main() — handle error explicitly
func main() {
    logger := zerolog.New(os.Stderr).With().Timestamp().Logger()

    if err := run(logger); err != nil {
        logger.Error().Err(err).Msg("application failed")
        os.Exit(1)
    }
}

func run(logger zerolog.Logger) error {
    db, err := connectDB(ctx)
    if err != nil {
        return fmt.Errorf("failed to connect to database: %w", err)
    }
    defer db.Close()
    // ...
}
```

**Why `log.Fatal` is harmful:**
- Skips all deferred functions (resource leaks, incomplete cleanup)
- Prevents graceful shutdown of connections
- Makes code untestable
- Hides control flow (exit happens inside a "log" call)

---

## Stack Traces

### Setup

**Always configure zerolog to attach stack traces** for error-level logs:

```go
import (
    "github.com/rs/zerolog"
    "github.com/rs/zerolog/pkgerrors"
)

func main() {
    // REQUIRED — enable stack trace marshaling
    zerolog.ErrorStackMarshaler = pkgerrors.MarshalStack

    logger := zerolog.New(os.Stderr).
        With().
        Timestamp().
        Caller().  // adds file:line to all logs
        Logger()

    // ...
}
```

### Error Wrapping with Stack Traces

Use `fmt.Errorf` with `%w` for error wrapping (idiomatic Go). For stack traces, wrap at error origin with `github.com/pkg/errors`:

```go
import (
    "fmt"

    "github.com/pkg/errors"
)

// At error ORIGIN — capture stack trace
func readConfig(path string) (Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return Config{}, errors.Wrap(err, "failed to read config file")  // captures stack
    }
    // ...
}

// When PROPAGATING — use standard fmt.Errorf with %w
func initApp(configPath string) error {
    cfg, err := readConfig(configPath)
    if err != nil {
        return fmt.Errorf("failed to initialise app: %w", err)  // preserves stack from origin
    }
    // ...
}
```

### Logging with Stack

When logging errors, use `.Stack()` to include the trace:

```go
if err != nil {
    logger.Error().
        Stack().  // includes stack trace if error has one
        Err(err).
        Msg("operation failed")
}
```

**Rule:** Use `errors.Wrap` at the point where error originates or crosses system boundaries. Use `fmt.Errorf` with `%w` for propagation within your code.

---

## Unique Log Messages

**Every log message must be unique within a function** to enable fast error localisation:

```go
// BAD — duplicate messages, impossible to tell which branch failed
func ProcessOrder(ctx context.Context, order Order) error {
    if err := validateOrder(order); err != nil {
        s.logger.Error().Err(err).Msg("failed to process order")  // where?
        return err
    }
    if err := chargePayment(ctx, order); err != nil {
        s.logger.Error().Err(err).Msg("failed to process order")  // same message!
        return err
    }
    if err := sendConfirmation(ctx, order); err != nil {
        s.logger.Error().Err(err).Msg("failed to process order")  // same message!
        return err
    }
    return nil
}

// GOOD — unique messages pinpoint exact failure location
func ProcessOrder(ctx context.Context, order Order) error {
    if err := validateOrder(order); err != nil {
        s.logger.Error().Err(err).Str("orderID", order.ID).Msg("order validation failed")
        return fmt.Errorf("failed to validate order: %w", err)
    }
    if err := chargePayment(ctx, order); err != nil {
        s.logger.Error().Err(err).Str("orderID", order.ID).Msg("payment charge failed")
        return fmt.Errorf("failed to charge payment: %w", err)
    }
    if err := sendConfirmation(ctx, order); err != nil {
        s.logger.Error().Err(err).Str("orderID", order.ID).Msg("confirmation email failed")
        return fmt.Errorf("failed to send confirmation: %w", err)
    }
    return nil
}
```

---

## Log Levels

### When to Use Each Level

| Level | Use For |
|-------|---------|
| `Trace` | Very detailed debugging, usually disabled |
| `Debug` | Development debugging information |
| `Info` | Normal operational messages (request started, completed) |
| `Warn` | Recoverable issues, degraded operation |
| `Error` | Failures that need attention but don't crash |
| `Fatal` | **NEVER USE** — return error instead |
| `Panic` | **NEVER USE** — return error instead |

### Examples

```go
// Info — normal operation
s.logger.Info().
    Str("orderID", order.ID).
    Str("status", "processing").
    Msg("order processing started")

// Warn — recoverable issue
s.logger.Warn().
    Str("orderID", order.ID).
    Int("retryCount", retryCount).
    Msg("payment retry scheduled")

// Error — failure requiring attention
s.logger.Error().
    Err(err).
    Stack().
    Str("orderID", order.ID).
    Msg("payment processing failed")

// Debug — development only
s.logger.Debug().
    Interface("request", req).
    Msg("incoming request")
```

---

## Structured Fields

### Always Add Context

```go
// BAD — no context
s.logger.Error().Msg("failed")

// GOOD — rich context for debugging
s.logger.Error().
    Err(err).
    Str("orderID", order.ID).
    Str("userID", user.ID).
    Str("operation", "chargePayment").
    Msg("payment processing failed")
```

### Common Field Patterns

```go
// Request context
logger.Info().
    Str("requestID", requestID).
    Str("method", r.Method).
    Str("path", r.URL.Path).
    Str("remoteAddr", r.RemoteAddr).
    Msg("request received")

// Duration tracking
start := time.Now()
// ... operation ...
logger.Info().
    Dur("duration", time.Since(start)).
    Msg("operation completed")

// With sub-logger for component
componentLogger := logger.With().Str("component", "payment").Logger()
componentLogger.Info().Msg("initialised")
```

---

## Logger Injection Pattern

### Constructor Argument Order

Logger always comes **last** in constructor arguments:

```go
func NewOrderService(
    cfg OrderServiceConfig,      // 1. Config first
    repo *OrderRepository,       // 2. Dependencies middle
    cache *Cache,
    logger zerolog.Logger,       // 3. Logger last
) (*OrderService, error)
```

### Sub-Loggers with Context

Create sub-loggers with component context:

```go
func NewOrderService(logger zerolog.Logger, repo *Repository) *OrderService {
    return &OrderService{
        logger: logger.With().Str("component", "order_service").Logger(),
        repo:   repo,
    }
}
```

### In Tests

Use `zerolog.Nop()` to silence logs in tests:

```go
func TestOrderService(t *testing.T) {
    svc := NewOrderService(zerolog.Nop(), mockRepo)
    // ...
}
```

---

## Quick Reference: Logging Violations

| Violation | Fix |
|-----------|-----|
| `fmt.Println` in production | Use `logger.Info().Msg()` |
| `log.Fatal()` | Return error, handle in `main()` |
| Global `zerolog/log` import | Inject logger as dependency |
| Duplicate log messages | Make each message unique |
| Missing `.Err(err)` | Always include error with `.Err()` |
| Missing context fields | Add relevant `.Str()`, `.Int()` fields |
| No stack trace on errors | Use `.Stack()` with error logs |
| Logger not last in constructor | Reorder: config → deps → logger |
