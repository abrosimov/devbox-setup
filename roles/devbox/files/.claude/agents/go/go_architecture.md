# Go Architecture Reference

Reference document for architectural design rules. Used by Go agents (`software-engineer-go`, `unit-test-writer-go`, `code-reviewer-go`, `implementation-planner-go`).

---

## Interface Design

### Consumer-Side Definition

Define interfaces in the package that **uses** them, not the package that implements them:

```go
// In consumer package — defines what it needs
type UserGetter interface {
    Get(ctx context.Context, id string) (*User, error)
}

func NewHandler(users UserGetter) *Handler {
    return &Handler{users: users}
}

// In implementation package — returns concrete type
func NewUserStore() *UserStore { ... }
```

### Same-File Placement

**NEVER create separate `interfaces.go` files.** Define interfaces in the same file where they are used:

```go
// BAD — separate interfaces.go file
// internal/service/interfaces.go
type UserRepository interface { ... }
type OrderRepository interface { ... }

// GOOD — interface in the file that uses it
// internal/service/user_service.go
type UserRepository interface {
    FindByID(ctx context.Context, id UserID) (*User, error)
    Insert(ctx context.Context, user *User) error
}

type UserService struct {
    repo   UserRepository
    logger zerolog.Logger
}
```

**Why same-file placement:**
- **Locality** — Interface visible where needed
- **Minimal scope** — Only exists where consumed
- **Easy refactoring** — Change interface and consumer together
- **Discourages over-abstraction** — Define only what you need

**Anti-patterns:**
| Anti-pattern | Problem |
|--------------|---------|
| `interfaces.go` file | Interfaces divorced from usage |
| `types.go` with interfaces | Same problem |
| Interface in implementation package | Tight coupling |
| Shared interface package | Unnecessary coupling |

**Exception:** Public API interfaces for external packages may live in dedicated files.

### Small Interfaces

One or two methods is common and idiomatic:

```go
type Reader interface {
    Read(p []byte) (n int, err error)
}

type ReadCloser interface {
    Reader
    Closer
}
```

### Return Concrete Types

Return structs, accept interfaces. Allows adding methods without breaking consumers.

---

## Layer Separation

### The Three Entity Layers

Every application has three distinct entity types that MUST remain separate:

| Layer | Entities | Purpose | Location |
|-------|----------|---------|----------|
| **API** | DTOs, Request/Response | External contract, serialization | `internal/handler/`, `internal/api/` |
| **Domain** | Business entities | Core business rules, validation | `internal/domain/`, `internal/service/` |
| **DBAL** | Repository models | Persistence concerns, queries | `internal/repository/`, `internal/store/` |

### Conversion Flow

```
Inbound:   API → Domain → DBAL
Outbound:  DBAL → Domain → API
```

**Direct conversion between API and DBAL is FORBIDDEN.**

### Entity Definition by Layer

```go
// API layer — internal/handler/user_dto.go
type CreateUserRequest struct {
    Email    string `json:"email"`
    Name     string `json:"name"`
    Password string `json:"password"`  // accepted but never stored directly
}

func (r CreateUserRequest) ToDomain() *domain.User {
    return &domain.User{
        Email: domain.Email(r.Email),
        Name:  r.Name,
    }
}

// Domain layer — internal/domain/user.go
type UserID string
type Email string

type User struct {
    ID           UserID
    Email        Email
    Name         string
    PasswordHash []byte  // internal, never in API
    CreatedAt    time.Time
}

// DBAL layer — internal/repository/user_model.go
type UserModel struct {
    ID           string     `db:"id"`
    Email        string     `db:"email"`
    PasswordHash []byte     `db:"password_hash"`
    DeletedAt    *time.Time `db:"deleted_at"`  // soft delete, not in domain
}

func (m UserModel) ToDomain() *domain.User { ... }
func (UserModel) FromDomain(u *domain.User) UserModel { ... }
```

### Why Layer Separation Matters

| Problem | Consequence |
|---------|-------------|
| API struct in DB layer | DB schema changes break API |
| DB struct in API response | Internal fields leak |
| No domain layer | Business logic scattered |
| Direct API↔DBAL | Tight coupling, untestable |

### Conversion Method Placement

| Conversion | Method Location |
|------------|-----------------|
| API → Domain | API struct: `func (r Request) ToDomain()` |
| Domain → API | API struct: `func (Response) FromDomain(e)` |
| Domain → DBAL | DBAL struct: `func (Model) FromDomain(e)` |
| DBAL → Domain | DBAL struct: `func (m Model) ToDomain()` |

---

## Constructor Patterns

### Return Signatures

| Constructor Type | Return Signature |
|-----------------|------------------|
| No arguments | `func NewCache() *Cache` |
| Args, no validation needed | `func NewLogger(cfg LoggerConfig) *Logger` |
| Args, validation needed | `func NewServer(cfg ServerConfig) (*Server, error)` |
| Dependencies (always validate) | `func NewService(repo Repository) (*Service, error)` |

```go
// No args — no error
func NewCache() *Cache {
    return &Cache{items: make(map[string]item)}
}

// Config needs validation — return error
func NewServer(cfg ServerConfig) (*Server, error) {
    if cfg.Port < 1 || cfg.Port > 65535 {
        return nil, errors.New("invalid port")
    }
    return &Server{cfg: cfg}, nil
}

// Dependency needs validation — return error
func NewService(repo Repository) (*Service, error) {
    if repo == nil {
        return nil, errors.New("repo is required")
    }
    return &Service{repo: repo}, nil
}
```

### Argument Order

**Config → Dependencies (pointers) → Logger**

```go
// GOOD — correct order
func NewOrderService(
    cfg OrderServiceConfig,      // 1. Config first
    repo *OrderRepository,       // 2. Dependencies as pointers
    cache *Cache,
    logger zerolog.Logger,       // 3. Logger last
) (*OrderService, error)

// BAD — wrong order
func NewService(repo *Repository, cfg Config, logger zerolog.Logger)  // config not first
func NewService(cfg Config, logger zerolog.Logger, repo *Repository)  // logger not last
func NewService(cfg Config, repo Repository)                          // dependency not pointer
```

### Config Value vs Pointer

| Object Lifecycle | Config Passing |
|-----------------|----------------|
| Few instances (singleton, service) | **Value always** |
| Frequently constructed (per-request) | Pointer |

### Dependencies Always Pointers

All dependencies passed to constructors must be pointers:
- Enables nil validation
- Makes dependency relationship explicit
- Avoids copying large structs

---

## Nil Safety

### Validate at Boundaries, Trust Internally

**NEVER add nil receiver checks inside methods.** Validate at construction:

```go
// BAD — nil check inside method
func (s *Service) Process() error {
    if s == nil || s.client == nil {
        return errors.New("not initialized")
    }
    return s.client.Call()
}

// GOOD — constructor validates, methods trust
func NewService(client Client) (*Service, error) {
    if client == nil {
        return nil, errors.New("client is required")
    }
    return &Service{client: client}, nil
}

func (s *Service) Process() error {
    return s.client.Call()  // guaranteed non-nil by constructor
}
```

### Nil Safety Rules

1. **Constructors validate** all dependencies, return error if nil
2. **Constructors never return** `nil, nil` — always `nil, err` or `val, nil`
3. **Methods trust invariants** established by constructor
4. **No redundant checks** inside methods for what constructor guarantees

---

## Type Safety: Compile-Time over Runtime

### Typed IDs

```go
// BAD — wrong ID type passed silently
func GetUser(id string) (*User, error)
func GetOrder(id string) (*Order, error)
user, _ := GetUser(orderID)  // compiles, fails at runtime

// GOOD — compiler catches type mismatch
type UserID string
type OrderID string
func GetUser(id UserID) (*User, error)
func GetOrder(id OrderID) (*Order, error)
user, _ := GetUser(orderID)  // ERROR: cannot use OrderID as UserID
```

### Type Conversion Rules

| When | Convert? |
|------|----------|
| Same types | Never |
| Literal to defined type | Implicit (no conversion) |
| Underlying type required | Yes |
| Cross defined types | Yes (through underlying) |

```go
// UNNECESSARY conversions (remove these)
userID == UserID(otherUserID)     // both are UserID
GetUser(UserID("literal"))        // literal works directly
users[UserID(id)]                 // if id is already UserID

// NECESSARY conversions
strings.Contains(string(name), "-")  // stdlib needs string
UserID(stringVar)                    // string → UserID
```

### Exhaustive Switch

Use `exhaustive` linter. Avoid `default` that hides missing cases:

```go
// BAD — default hides missing cases
switch status {
case StatusActive:
    return "active"
default:
    return "unknown"  // hides StatusPending, StatusFailed...
}

// GOOD — exhaustive, linter catches missing
switch status {
case StatusActive:
    return "active"
case StatusPending:
    return "pending"
case StatusFailed:
    return "failed"
}
```

---

## Distributed Systems

### Transaction Patterns

**NEVER make external calls inside database transactions.**

| Scenario | Pattern |
|----------|---------|
| Need external data FOR transaction | Fetch BEFORE transaction |
| Side effect after commit, failure OK | Call AFTER transaction |
| Side effect must be reliable | Transactional Outbox |
| Multi-step distributed transaction | Durable Workflow (Temporal) |

```go
// WRONG — HTTP inside transaction
tx, _ := db.BeginTx(ctx, nil)
user, _ := userService.Get(ctx, id)  // BAD: HTTP inside tx
tx.Insert(&order)
tx.Commit()

// RIGHT — fetch before, commit, then optional call
user, err := userService.Get(ctx, id)  // Fetch BEFORE
if err != nil { return err }

tx, _ := db.BeginTx(ctx, nil)
tx.Insert(&order)
if err := tx.Commit(); err != nil { return err }

analytics.Track(ctx, "order.created", order.ID)  // After commit (best effort)
```

### HTTP Client Requirements

| Requirement | Implementation |
|-------------|----------------|
| Timeout | `context.WithTimeout` + `http.Client.Timeout` |
| Retry | Exponential backoff for idempotent requests |
| Body limit | `io.LimitReader(resp.Body, maxSize)` |
| Context | `http.NewRequestWithContext` |

```go
// REQUIRED pattern
ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
defer cancel()

req, _ := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
resp, err := client.Do(req)
if err != nil { return err }
defer resp.Body.Close()

body, _ := io.ReadAll(io.LimitReader(resp.Body, 10<<20))  // 10MB max
```

---

## Testing Philosophy

### Mock External Dependencies

**NEVER skip testing code that uses databases, HTTP clients, or queues.**

```go
// BAD — skipping with excuse
// "Not tested (requires MongoDB): Client, Collection"

// GOOD — mock the interface
type OrderRepository interface {
    FindByID(ctx context.Context, id OrderID) (*Order, error)
}

func (s *OrderServiceTestSuite) TestGetOrder_NotFound() {
    s.mockRepo.EXPECT().
        FindByID(mock.Anything, OrderID("unknown")).
        Return(nil, repository.ErrNotFound)

    order, err := s.svc.GetOrder(ctx, "unknown")

    s.Require().ErrorIs(err, ErrOrderNotFound)
    s.Require().Nil(order)
}
```

### Unit vs Integration Tests

| Test Type | Tests | Mocks |
|-----------|-------|-------|
| **Unit** | Business logic | External dependencies mocked |
| **Integration** | Actual DB/network calls | Real infrastructure |

Unit tests are required. Integration tests are a separate concern (often separate repo/CI stage).

### What to Test vs Skip

| Component | Test? | How |
|-----------|-------|-----|
| Service using repository | Yes | Mock repository |
| Repository implementation | Yes | Mock DB driver/collection |
| Thin driver wrapper | Skip | No business logic |
| Transaction coordination | Yes | Mock, verify commit/rollback |

---

## Quick Reference: Architecture Violations

| Violation | Fix |
|-----------|-----|
| `interfaces.go` file | Move interface to consumer file |
| API struct passed to repository | Convert through domain |
| DB struct in API response | Convert through domain |
| Nil check inside method | Move to constructor |
| `string` for ID | Define `type XxxID string` |
| HTTP call inside transaction | Move before/after transaction |
| Test skipped "requires database" | Mock the database interface |
| Config pointer for singleton | Use value |
| Dependency passed by value | Use pointer |
| Logger not last in constructor | Reorder arguments |
