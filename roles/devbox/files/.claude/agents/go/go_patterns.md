# Go Patterns Reference

Reference document for common Go patterns. Used by Go agents (`software-engineer-go`, `unit-test-writer-go`, `code-reviewer-go`).

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

// WithMaxConnections sets connection limit
func WithMaxConnections(n int) Option {
    return func(s *Server) { s.maxConns = n }
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

### BAD vs GOOD

```go
// BAD — parameter explosion
func NewServer(addr string, timeout time.Duration, maxConns int,
    logger zerolog.Logger, enableTLS bool, certFile string) *Server

// BAD — config struct for mostly-default usage
type ServerConfig struct {
    Addr     string
    Timeout  time.Duration
    MaxConns int
    // ... 10 more fields most callers don't set
}

// GOOD — functional options
func NewServer(addr string, opts ...Option) *Server
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
type Status int

const (
    StatusPending Status = iota
    StatusActive
    StatusCompleted
    StatusFailed
)

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

// Use at boundaries
func ProcessOrder(status Status) error {
    if !status.Valid() {
        return fmt.Errorf("invalid status: %d", status)
    }
    // ...
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

// Works naturally with JSON
type User struct {
    Name string `json:"name"`
    Role Role   `json:"role"`
}
```

### BAD vs GOOD

```go
// BAD — magic strings
func SetUserRole(role string) error {
    if role == "admin" || role == "user" { ... }
}

// BAD — untyped constants
const (
    RoleAdmin = "admin"
    RoleUser  = "user"
)

// GOOD — typed enum
type Role string
const (
    RoleAdmin Role = "admin"
    RoleUser  Role = "user"
)

func SetUserRole(role Role) error { ... }
```

---

## JSON Encoding

Best practices for struct tags and marshaling.

### Struct Tags

```go
type User struct {
    ID        string    `json:"id"`
    Email     string    `json:"email"`
    Name      string    `json:"name,omitempty"`      // omit if empty
    Age       int       `json:"age,omitempty"`       // omit if zero
    CreatedAt time.Time `json:"created_at"`
    UpdatedAt time.Time `json:"updated_at,omitempty"`
    Password  string    `json:"-"`                   // never serialise
    Internal  string    `json:"-"`                   // never serialise
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

### Time Handling

```go
// Default: RFC3339 format
type Event struct {
    CreatedAt time.Time `json:"created_at"`  // "2024-01-15T10:30:00Z"
}

// Custom format requires custom type
type Date time.Time

func (d Date) MarshalJSON() ([]byte, error) {
    t := time.Time(d)
    if t.IsZero() {
        return []byte("null"), nil
    }
    return []byte(fmt.Sprintf(`"%s"`, t.Format("2006-01-02"))), nil
}

func (d *Date) UnmarshalJSON(data []byte) error {
    s := strings.Trim(string(data), `"`)
    if s == "null" || s == "" {
        return nil
    }
    t, err := time.Parse("2006-01-02", s)
    if err != nil {
        return err
    }
    *d = Date(t)
    return nil
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

### BAD vs GOOD

```go
// BAD — inconsistent naming
type User struct {
    UserID    string `json:"userId"`      // camelCase
    user_name string `json:"user_name"`   // snake_case (also unexported!)
    Email     string `json:"email"`       // lowercase
}

// GOOD — consistent snake_case (common convention)
type User struct {
    ID    string `json:"id"`
    Name  string `json:"name"`
    Email string `json:"email"`
}

// BAD — exposing internal fields
type User struct {
    ID           string `json:"id"`
    PasswordHash string `json:"password_hash"`  // security risk!
}

// GOOD — hide internal fields
type User struct {
    ID           string `json:"id"`
    PasswordHash string `json:"-"`
}
```

---

## Generics: Use Sparingly

Go added generics in 1.18 after deliberate delay. Use them with restraint.

### KISS & YAGNI First

Before writing generic code, ask:
1. Do I have a concrete type that works? Use it
2. Does an interface solve this? Use interface
3. Am I duplicating code for 3+ different types? Maybe generics
4. Is this library code used across the codebase? Maybe generics

### Type Preference Hierarchy

| Priority | Type | Use When |
|----------|------|----------|
| 1st | Concrete type | Always the default choice |
| 2nd | Interface with methods | Need behaviour abstraction |
| 3rd | Generics | Type safety across multiple types (library code) |
| 4th | `any` | Last resort: serialization/reflection boundaries only |

### Never Use `interface{}`

`interface{}` is legacy syntax. Forbidden in new code.

```go
// FORBIDDEN — legacy syntax
func Process(data interface{}) error

// If you must accept any type (rare), use `any`
func Process(data any) error
```

### When `any` is Acceptable

```go
// ACCEPTABLE — JSON unmarshaling to unknown structure
var payload map[string]any
json.Unmarshal(data, &payload)

// ACCEPTABLE — structured logging
logger.Info().Any("metadata", metadata).Msg("processed")

// BAD — lazy API design, define concrete types instead
func HandleEvent(eventType string, payload any) error
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

// BAD — business logic with generics (over-engineering)
type OrderProcessor[T OrderType] struct { ... }

// GOOD — specific domain type
type OrderProcessor struct { ... }

// BAD — interface already solves this
func Print[T fmt.Stringer](item T) { fmt.Println(item.String()) }

// GOOD — just use the interface
func Print(item fmt.Stringer) { fmt.Println(item.String()) }
```

### Prefer stdlib Generics

Before writing generic utilities, check if `slices`, `maps`, or `cmp` packages
already provide what you need:

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
func collectIDs(users []User) []string {
    var ids []string
    for _, u := range users {
        ids = append(ids, u.ID)
    }
    return ids
}

// GOOD — pre-allocate when length is known
func collectIDs(users []User) []string {
    ids := make([]string, 0, len(users))
    for _, u := range users {
        ids = append(ids, u.ID)
    }
    return ids
}

// GOOD — direct assignment when transforming 1:1
func collectIDs(users []User) []string {
    ids := make([]string, len(users))
    for i, u := range users {
        ids[i] = u.ID
    }
    return ids
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

### Slice Copying

```go
// BAD — modifies original
func process(items []string) {
    items[0] = "modified"  // caller's slice is modified!
}

// GOOD — copy if you need to modify
func process(items []string) []string {
    result := make([]string, len(items))
    copy(result, items)
    result[0] = "modified"
    return result
}

// GOOD — document if modification is intentional
// SortInPlace sorts items in place. Modifies the original slice.
func SortInPlace(items []string) {
    slices.Sort(items)
}
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

// GOOD — filter with new slice (preserves original)
func filterActive(users []User) []User {
    result := make([]User, 0, len(users))
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

Embedding promotes fields and methods from embedded type to the outer type.

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

// LoggingWriter satisfies io.Writer
var _ io.Writer = (*LoggingWriter)(nil)
```

### Extending Types

```go
// GOOD — extend with additional behaviour
type CountingReader struct {
    io.Reader
    count int64
}

func (r *CountingReader) Read(p []byte) (n int, err error) {
    n, err = r.Reader.Read(p)
    r.count += int64(n)
    return
}

func (r *CountingReader) Count() int64 {
    return r.count
}
```

### BAD vs GOOD

```go
// BAD — embedding exposes too much
type UserService struct {
    *sql.DB  // exposes ALL sql.DB methods: Exec, Query, Close, etc.
}
// Caller can now do: userService.Exec("DROP TABLE users")

// GOOD — private field, controlled interface
type UserService struct {
    db *sql.DB
}

func (s *UserService) GetUser(id string) (*User, error) {
    return s.db.QueryRow(...)  // controlled access
}

// BAD — embedding for code reuse (not "is-a")
type OrderService struct {
    UserService  // OrderService is NOT a UserService
}

// GOOD — composition via field
type OrderService struct {
    users *UserService
}
```

### Embedded Pointer Pitfall

```go
// DANGER — embedded pointer can be nil
type Client struct {
    *http.Client  // if nil, method calls panic
}

c := &Client{}  // http.Client is nil
c.Do(req)       // PANIC: nil pointer dereference

// SAFE — initialise in constructor
func NewClient() *Client {
    return &Client{
        Client: &http.Client{Timeout: 30 * time.Second},
    }
}

// SAFER — embed value if possible
type Client struct {
    http.Client  // zero value is usable
}
```

### Method Shadowing

```go
type Base struct{}
func (Base) Method() string { return "base" }

type Derived struct {
    Base
}
func (Derived) Method() string { return "derived" }

d := Derived{}
d.Method()      // "derived" — Derived.Method shadows Base.Method
d.Base.Method() // "base" — explicit access to embedded method
```

---

## Time Handling

### Duration Constants

```go
// GOOD — named constants for clarity
const (
    defaultTimeout    = 30 * time.Second
    maxRetryInterval  = 5 * time.Minute
    sessionExpiration = 24 * time.Hour
)

// BAD — magic numbers
time.Sleep(30000000000)           // 30 seconds? 30 nanoseconds?
ctx, cancel := context.WithTimeout(ctx, 30000000000)

// GOOD — explicit duration
time.Sleep(30 * time.Second)
ctx, cancel := context.WithTimeout(ctx, defaultTimeout)
```

### Time Comparison

```go
// GOOD — clear comparison methods
if time.Now().After(deadline) {
    return ErrExpired
}

if time.Now().Before(startTime) {
    return ErrNotYetValid
}

if expiresAt.IsZero() {
    // never expires
}

// BAD — manual subtraction
if time.Now().Sub(deadline) > 0 { }  // less clear than After()
```

### UTC Internally, Local at Boundaries

```go
// GOOD — store and compare in UTC
type Session struct {
    CreatedAt time.Time  // always UTC
    ExpiresAt time.Time  // always UTC
}

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

### Parsing and Formatting

```go
// Standard layouts — use constants
const (
    time.RFC3339     // "2006-01-02T15:04:05Z07:00"
    time.RFC3339Nano // "2006-01-02T15:04:05.999999999Z07:00"
    time.DateOnly    // "2006-01-02"
    time.TimeOnly    // "15:04:05"
)

// Custom layout — use reference time: Mon Jan 2 15:04:05 MST 2006
const customLayout = "2006/01/02 15:04"

t, err := time.Parse(customLayout, "2024/03/15 10:30")
if err != nil {
    return fmt.Errorf("parsing time: %w", err)
}

formatted := t.Format(customLayout)  // "2024/03/15 10:30"
```

### Timezone Pitfalls

```go
// BAD — comparing times from different zones without normalization
t1, _ := time.Parse("2006-01-02 15:04", "2024-03-15 10:00")  // no zone = UTC
t2 := time.Now()  // local zone

if t1.Equal(t2) { }  // may be wrong!

// GOOD — normalize to UTC for comparison
if t1.UTC().Equal(t2.UTC()) { }

// Or use Unix timestamps
if t1.Unix() == t2.Unix() { }
```

### Duration Formatting

```go
// time.Duration.String() is fine for logs
logger.Info().Dur("elapsed", elapsed).Msg("completed")  // "elapsed": "1.5s"

// For human display, format explicitly
func formatDuration(d time.Duration) string {
    if d < time.Minute {
        return fmt.Sprintf("%.1fs", d.Seconds())
    }
    if d < time.Hour {
        return fmt.Sprintf("%.1fm", d.Minutes())
    }
    return fmt.Sprintf("%.1fh", d.Hours())
}
```

---

## HTTP Client Patterns

### Never Use Default Client

```go
// BAD — no timeout, connection leaks possible
resp, err := http.Get(url)
resp, err := http.Post(url, contentType, body)

// These use http.DefaultClient which has no timeout!
```

### Reusable Client with Proper Configuration

```go
// GOOD — configured client as package variable or struct field
var httpClient = &http.Client{
    Timeout: 30 * time.Second,
    Transport: &http.Transport{
        MaxIdleConns:        100,
        MaxIdleConnsPerHost: 10,
        IdleConnTimeout:     90 * time.Second,
        TLSHandshakeTimeout: 10 * time.Second,
    },
}

func FetchUser(ctx context.Context, userID string) (*User, error) {
    req, err := http.NewRequestWithContext(ctx, http.MethodGet, apiURL+userID, nil)
    if err != nil {
        return nil, fmt.Errorf("creating request: %w", err)
    }

    resp, err := httpClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("fetching user: %w", err)
    }
    defer resp.Body.Close()

    // ... handle response
}
```

### Client as Dependency

```go
// GOOD — inject client for testability
type APIClient struct {
    baseURL    string
    httpClient *http.Client
    logger     zerolog.Logger
}

func NewAPIClient(baseURL string, logger zerolog.Logger) *APIClient {
    return &APIClient{
        baseURL: baseURL,
        httpClient: &http.Client{
            Timeout: 30 * time.Second,
            Transport: &http.Transport{
                MaxIdleConnsPerHost: 10,
            },
        },
        logger: logger,
    }
}

// In tests — inject mock server
func TestAPIClient(t *testing.T) {
    srv := httptest.NewServer(mockHandler)
    t.Cleanup(srv.Close)

    client := NewAPIClient(srv.URL, zerolog.Nop())
    // test with mock server
}
```

### Per-Request Timeout with Context

```go
func (c *APIClient) Get(ctx context.Context, path string) ([]byte, error) {
    // Per-request timeout (overrides client timeout if shorter)
    ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
    defer cancel()

    req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.baseURL+path, nil)
    if err != nil {
        return nil, fmt.Errorf("creating request: %w", err)
    }

    resp, err := c.httpClient.Do(req)
    if err != nil {
        if errors.Is(err, context.DeadlineExceeded) {
            return nil, fmt.Errorf("request timed out: %w", err)
        }
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

### Request Headers

```go
func (c *APIClient) doRequest(ctx context.Context, method, path string, body io.Reader) (*http.Response, error) {
    req, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, body)
    if err != nil {
        return nil, err
    }

    // Set common headers
    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("Accept", "application/json")
    req.Header.Set("User-Agent", "myapp/1.0")

    if c.apiKey != "" {
        req.Header.Set("Authorization", "Bearer "+c.apiKey)
    }

    return c.httpClient.Do(req)
}
```

---

## HTTP Handler Patterns

### Middleware Signature

```go
// Standard middleware signature
type Middleware func(http.Handler) http.Handler

// Logging middleware
func LoggingMiddleware(logger zerolog.Logger) Middleware {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            start := time.Now()

            // Wrap response writer to capture status code
            wrapped := &responseWriter{ResponseWriter: w, status: http.StatusOK}

            next.ServeHTTP(wrapped, r)

            logger.Info().
                Str("method", r.Method).
                Str("path", r.URL.Path).
                Int("status", wrapped.status).
                Dur("duration", time.Since(start)).
                Msg("request completed")
        })
    }
}

type responseWriter struct {
    http.ResponseWriter
    status int
}

func (w *responseWriter) WriteHeader(status int) {
    w.status = status
    w.ResponseWriter.WriteHeader(status)
}
```

### Middleware Chaining

```go
// Chain applies middlewares in order
func Chain(h http.Handler, middlewares ...Middleware) http.Handler {
    for i := len(middlewares) - 1; i >= 0; i-- {
        h = middlewares[i](h)
    }
    return h
}

// Usage
handler := Chain(
    myHandler,
    RecoveryMiddleware(logger),
    LoggingMiddleware(logger),
    AuthMiddleware(authService),
)
```

### Request Validation

```go
func (h *Handler) CreateUser(w http.ResponseWriter, r *http.Request) {
    // Limit body size
    r.Body = http.MaxBytesReader(w, r.Body, 1<<20)  // 1MB

    var req CreateUserRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        h.respondError(w, http.StatusBadRequest, "invalid request body")
        return
    }

    // Validate
    if req.Email == "" {
        h.respondError(w, http.StatusBadRequest, "email is required")
        return
    }

    // Process...
}
```

### Response Helpers

```go
func (h *Handler) respondJSON(w http.ResponseWriter, status int, data any) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)

    if err := json.NewEncoder(w).Encode(data); err != nil {
        h.logger.Error().Err(err).Msg("encoding response")
    }
}

func (h *Handler) respondError(w http.ResponseWriter, status int, message string) {
    h.respondJSON(w, status, map[string]string{"error": message})
}

// Usage
func (h *Handler) GetUser(w http.ResponseWriter, r *http.Request) {
    user, err := h.userService.Get(r.Context(), userID)
    if errors.Is(err, ErrNotFound) {
        h.respondError(w, http.StatusNotFound, "user not found")
        return
    }
    if err != nil {
        h.logger.Error().Err(err).Msg("getting user")
        h.respondError(w, http.StatusInternalServerError, "internal error")
        return
    }

    h.respondJSON(w, http.StatusOK, user)
}
```

### Context Values for Request-Scoped Data

```go
type contextKey string

const userContextKey contextKey = "user"

// Middleware sets user in context
func AuthMiddleware(auth AuthService) Middleware {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            token := r.Header.Get("Authorization")
            user, err := auth.ValidateToken(r.Context(), token)
            if err != nil {
                http.Error(w, "unauthorized", http.StatusUnauthorized)
                return
            }

            ctx := context.WithValue(r.Context(), userContextKey, user)
            next.ServeHTTP(w, r.WithContext(ctx))
        })
    }
}

// Handler retrieves user from context
func UserFromContext(ctx context.Context) (*User, bool) {
    user, ok := ctx.Value(userContextKey).(*User)
    return user, ok
}

func (h *Handler) GetProfile(w http.ResponseWriter, r *http.Request) {
    user, ok := UserFromContext(r.Context())
    if !ok {
        h.respondError(w, http.StatusUnauthorized, "not authenticated")
        return
    }
    // use user...
}
```

---

## Build Tags

Conditional compilation for tests, platforms, and feature flags.

### Integration Tests

```go
//go:build integration

package storage_test

import (
    "os"
    "testing"
    "database/sql"

    "github.com/stretchr/testify/require"
)

// These tests require a real database
func TestDatabaseIntegration(t *testing.T) {
    db, err := sql.Open("postgres", os.Getenv("DATABASE_URL"))
    require.NoError(t, err)
    t.Cleanup(func() { db.Close() })

    // integration tests...
}
```

Run with:
```bash
# Unit tests only (default)
go test ./...

# Integration tests only
go test -tags=integration ./...

# Both
go test -tags=integration ./...
```

### Platform-Specific Code

```go
// file: signal_unix.go
//go:build unix

package main

import (
    "os"
    "syscall"
)

var shutdownSignals = []os.Signal{syscall.SIGINT, syscall.SIGTERM}

// file: signal_windows.go
//go:build windows

package main

import "os"

var shutdownSignals = []os.Signal{os.Interrupt}
```

### Feature Flags

```go
//go:build experimental

package feature

// ExperimentalWidget is only available with -tags=experimental
type ExperimentalWidget struct {
    // ...
}
```

### Multiple Constraints

```go
// AND — both conditions required
//go:build linux && amd64

// OR — either condition
//go:build linux || darwin

// NOT — exclude
//go:build !windows

// Complex — Linux on AMD64 or ARM64, but not CGO
//go:build linux && (amd64 || arm64) && !cgo
```

### BAD vs GOOD

```go
// BAD — using file suffix for complex conditions
// file: db_linux_amd64_integration.go  // hard to read, error-prone

// GOOD — build tag at top of file
//go:build linux && amd64 && integration

// BAD — old syntax (still works but deprecated)
// +build integration

// GOOD — new syntax (Go 1.17+)
//go:build integration
```
