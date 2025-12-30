---
name: go-patterns
description: >
  Common Go patterns and idioms. Use when discussing functional options, enums,
  JSON encoding, generics, slice patterns, struct embedding, time handling,
  HTTP clients, HTTP handlers, or build tags. Triggers on: functional options,
  iota, enum, JSON, omitempty, generics, slice, embedding, time handling,
  HTTP client, HTTP handler, middleware, build tags.
---

# Go Patterns Reference

Common patterns and idioms for Go projects.

---

## Functional Options

Pattern for configurable constructors without parameter explosion.

### The Pattern

```go
// Option is a function that configures Server
type Option func(*Server)

// WithTimeout sets the server timeout
func WithTimeout(d time.Duration) Option {
    return func(s *Server) { s.timeout = d }
}

// WithLogger sets the server logger
func WithLogger(l zerolog.Logger) Option {
    return func(s *Server) { s.logger = l }
}

// NewServer creates a server with sensible defaults and optional configuration
func NewServer(addr string, opts ...Option) *Server {
    s := &Server{
        addr:     addr,
        timeout:  30 * time.Second,  // sensible default
        maxConns: 100,               // sensible default
        logger:   zerolog.Nop(),     // sensible default
    }
    for _, opt := range opts {
        opt(s)
    }
    return s
}

// Usage
srv := NewServer("localhost:8080",
    WithTimeout(60*time.Second),
    WithLogger(logger),
)
```

### When to Use

| Situation | Use Functional Options? |
|-----------|------------------------|
| 3+ optional configuration parameters | Yes |
| Most callers use defaults | Yes |
| Need backward-compatible API evolution | Yes |
| 1-2 required parameters only | No — use simple constructor |
| All parameters required | No — use config struct |

### With Validation

```go
// OptionError allows options to return errors
type OptionError func(*Server) error

func WithPort(port int) OptionError {
    return func(s *Server) error {
        if port < 1 || port > 65535 {
            return fmt.Errorf("invalid port: %d", port)
        }
        s.port = port
        return nil
    }
}

func NewServer(opts ...OptionError) (*Server, error) {
    s := &Server{port: 8080}
    for _, opt := range opts {
        if err := opt(s); err != nil {
            return nil, err
        }
    }
    return s, nil
}
```

---

## Enums with iota

Type-safe enumerations in Go.

### Basic Pattern

```go
type Status int

const (
    StatusPending Status = iota  // 0
    StatusActive                 // 1
    StatusCompleted              // 2
    StatusFailed                 // 3
)
```

### With String Method

```go
func (s Status) String() string {
    switch s {
    case StatusPending:
        return "pending"
    case StatusActive:
        return "active"
    case StatusCompleted:
        return "completed"
    case StatusFailed:
        return "failed"
    default:
        return fmt.Sprintf("Status(%d)", s)
    }
}
```

### With Validation

```go
func (s Status) Valid() bool {
    switch s {
    case StatusPending, StatusActive, StatusCompleted, StatusFailed:
        return true
    default:
        return false
    }
}
```

### String-Based Enums (for JSON/API)

```go
type Role string

const (
    RoleAdmin  Role = "admin"
    RoleUser   Role = "user"
    RoleGuest  Role = "guest"
)

func (r Role) Valid() bool {
    switch r {
    case RoleAdmin, RoleUser, RoleGuest:
        return true
    default:
        return false
    }
}
```

---

## JSON Encoding

### Struct Tags

```go
type User struct {
    ID        string    `json:"id"`
    Email     string    `json:"email"`
    Name      string    `json:"name,omitempty"`      // omit if empty
    Age       int       `json:"age,omitempty"`       // omit if zero
    CreatedAt time.Time `json:"created_at"`
    Password  string    `json:"-"`                   // never serialise
}
```

### omitempty Behaviour

| Type | Zero Value | omitempty Omits? |
|------|------------|------------------|
| string | `""` | Yes |
| int, float | `0` | Yes |
| bool | `false` | Yes |
| pointer | `nil` | Yes |
| slice | `nil` | Yes |
| slice | `[]T{}` (empty) | No — use pointer |
| map | `nil` | Yes |
| struct | `T{}` | No — use pointer |
| time.Time | `time.Time{}` | No — use pointer |

### Pointer for Optional Fields

```go
// BAD — can't distinguish "not provided" from "empty"
type UpdateRequest struct {
    Name string `json:"name,omitempty"`  // "" means not provided OR clear?
}

// GOOD — nil means not provided, empty string means clear
type UpdateRequest struct {
    Name *string `json:"name,omitempty"`
}

// Usage
if req.Name != nil {
    user.Name = *req.Name  // explicit update, even if empty
}
```

### Custom Marshaling

```go
type Status int

const (
    StatusActive Status = iota
    StatusInactive
)

func (s Status) MarshalJSON() ([]byte, error) {
    var str string
    switch s {
    case StatusActive:
        str = "active"
    case StatusInactive:
        str = "inactive"
    default:
        return nil, fmt.Errorf("unknown status: %d", s)
    }
    return json.Marshal(str)
}

func (s *Status) UnmarshalJSON(data []byte) error {
    var str string
    if err := json.Unmarshal(data, &str); err != nil {
        return err
    }
    switch str {
    case "active":
        *s = StatusActive
    case "inactive":
        *s = StatusInactive
    default:
        return fmt.Errorf("unknown status: %s", str)
    }
    return nil
}
```

---

## Generics: Use Sparingly

### Type Preference Hierarchy

| Priority | Type | Use When |
|----------|------|----------|
| 1st | Concrete type | Always the default choice |
| 2nd | Interface with methods | Need behaviour abstraction |
| 3rd | Generics | Type safety across multiple types (library code) |
| 4th | `any` | Last resort: serialization/reflection boundaries only |

### Never Use `interface{}`

```go
// FORBIDDEN — legacy syntax
func Process(data interface{}) error

// If you must accept any type (rare), use `any`
func Process(data any) error
```

### When to Use Generics

```go
// JUSTIFIED — stdlib-style utility, preserves type safety
func Keys[K comparable, V any](m map[K]V) []K {
    keys := make([]K, 0, len(m))
    for k := range m {
        keys = append(keys, k)
    }
    return keys
}

// JUSTIFIED — type-safe cache (library code, multiple types)
type Cache[K comparable, V any] struct { ... }
```

### When NOT to Use Generics

```go
// BAD — generic for single type (YAGNI)
func ProcessItems[T Item](items []T) error

// GOOD — concrete type is clearer
func ProcessItems(items []Item) error

// BAD — interface already solves this
func Print[T fmt.Stringer](item T) { fmt.Println(item.String()) }

// GOOD — just use the interface
func Print(item fmt.Stringer) { fmt.Println(item.String()) }
```

### Prefer stdlib Generics

```go
// DON'T write your own
func Contains[T comparable](slice []T, item T) bool

// DO use stdlib
import "slices"
slices.Contains(items, target)
```

---

## Slice Patterns

### Pre-allocation

```go
// BAD — grows slice repeatedly
var ids []string
for _, u := range users {
    ids = append(ids, u.ID)
}

// GOOD — pre-allocate when length is known
ids := make([]string, 0, len(users))
for _, u := range users {
    ids = append(ids, u.ID)
}
```

### Nil vs Empty Slice

```go
// nil slice — idiomatic default
var items []string          // nil, len=0, cap=0
json.Marshal(items)         // null

// empty slice — when JSON must be []
items := []string{}         // not nil, len=0, cap=0
json.Marshal(items)         // []

// Check correctly
if len(items) == 0 { }      // works for both nil and empty
if items == nil { }         // only catches nil
```

### Filtering

```go
// GOOD — filter in place (reuses backing array)
func filterActive(users []User) []User {
    result := users[:0]  // reuse backing array
    for _, u := range users {
        if u.Active {
            result = append(result, u)
        }
    }
    return result
}
```

---

## Struct Embedding

### When to Embed

| Situation | Embed? |
|-----------|--------|
| Implement interface by delegating | Yes |
| True "is-a" relationship | Yes |
| Need all methods of inner type | Yes |
| Only need some methods/fields | No — use regular field |
| Would expose unwanted methods | No — use regular field |

### Interface Satisfaction

```go
// GOOD — embed to satisfy interface by delegation
type LoggingWriter struct {
    io.Writer
    logger zerolog.Logger
}

func (w *LoggingWriter) Write(p []byte) (n int, err error) {
    w.logger.Debug().Int("bytes", len(p)).Msg("writing")
    return w.Writer.Write(p)  // delegate to embedded Writer
}
```

### BAD vs GOOD

```go
// BAD — embedding exposes too much
type UserService struct {
    *sql.DB  // exposes ALL sql.DB methods: Exec, Query, Close, etc.
}

// GOOD — private field, controlled interface
type UserService struct {
    db *sql.DB
}
```

---

## Time Handling

### Duration Constants

```go
const (
    defaultTimeout    = 30 * time.Second
    maxRetryInterval  = 5 * time.Minute
    sessionExpiration = 24 * time.Hour
)

// BAD — magic numbers
time.Sleep(30000000000)

// GOOD — explicit duration
time.Sleep(30 * time.Second)
```

### UTC Internally, Local at Boundaries

```go
func NewSession(duration time.Duration) *Session {
    now := time.Now().UTC()
    return &Session{
        CreatedAt: now,
        ExpiresAt: now.Add(duration),
    }
}

// Convert to local only for display
func (s *Session) ExpiresAtLocal(loc *time.Location) string {
    return s.ExpiresAt.In(loc).Format("2006-01-02 15:04:05")
}
```

---

## HTTP Client Patterns

### Never Use Default Client

```go
// BAD — no timeout, connection leaks possible
resp, err := http.Get(url)

// GOOD — configured client
var httpClient = &http.Client{
    Timeout: 30 * time.Second,
    Transport: &http.Transport{
        MaxIdleConns:        100,
        MaxIdleConnsPerHost: 10,
        IdleConnTimeout:     90 * time.Second,
    },
}
```

### Per-Request Timeout with Context

```go
func (c *APIClient) Get(ctx context.Context, path string) ([]byte, error) {
    ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
    defer cancel()

    req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.baseURL+path, nil)
    if err != nil {
        return nil, fmt.Errorf("creating request: %w", err)
    }

    resp, err := c.httpClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("request failed: %w", err)
    }
    defer resp.Body.Close()

    // Limit response size to prevent memory exhaustion
    body, err := io.ReadAll(io.LimitReader(resp.Body, 10<<20))  // 10MB max
    if err != nil {
        return nil, fmt.Errorf("reading response: %w", err)
    }

    return body, nil
}
```

---

## HTTP Handler Patterns

### Middleware Signature

```go
type Middleware func(http.Handler) http.Handler

func LoggingMiddleware(logger zerolog.Logger) Middleware {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            start := time.Now()
            next.ServeHTTP(w, r)
            logger.Info().
                Str("method", r.Method).
                Str("path", r.URL.Path).
                Dur("duration", time.Since(start)).
                Msg("request completed")
        })
    }
}
```

### Middleware Chaining

```go
func Chain(h http.Handler, middlewares ...Middleware) http.Handler {
    for i := len(middlewares) - 1; i >= 0; i-- {
        h = middlewares[i](h)
    }
    return h
}

handler := Chain(
    myHandler,
    RecoveryMiddleware(logger),
    LoggingMiddleware(logger),
    AuthMiddleware(authService),
)
```

### Response Helpers

```go
func (h *Handler) respondJSON(w http.ResponseWriter, status int, data any) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(data)
}

func (h *Handler) respondError(w http.ResponseWriter, status int, message string) {
    h.respondJSON(w, status, map[string]string{"error": message})
}
```

---

## Build Tags

### Integration Tests

```go
//go:build integration

package storage_test

func TestDatabaseIntegration(t *testing.T) {
    // requires real database
}
```

Run with:
```bash
go test ./...                    # unit tests only
go test -tags=integration ./...  # integration tests
```

### Platform-Specific Code

```go
// file: signal_unix.go
//go:build unix

var shutdownSignals = []os.Signal{syscall.SIGINT, syscall.SIGTERM}

// file: signal_windows.go
//go:build windows

var shutdownSignals = []os.Signal{os.Interrupt}
```

### Multiple Constraints

```go
//go:build linux && amd64           // AND
//go:build linux || darwin          // OR
//go:build !windows                 // NOT
//go:build linux && (amd64 || arm64) && !cgo  // Complex
```
