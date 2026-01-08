---
name: go-architecture
description: >
  Go architecture patterns and design rules. Use when discussing interface design,
  project structure, struct separation, constructor patterns, nil safety, type safety,
  or distributed systems patterns. Triggers on: interface, constructor, nil safety,
  project structure, package, DTO, domain object, type safety, typed ID, transaction.
---

# Go Architecture Reference

Architectural design rules for Go projects.

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
| `types.go` file | Types divorced from behaviour, god file |
| `errors.go` file | Errors lose context, unclear which function returns what |
| Interface in implementation package | Tight coupling |
| Shared interface package | Unnecessary coupling |

**Exception:** API/DTO packages where types ARE the product (generated clients, protobuf) may use collection files.

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

## Project Structure — Package by Feature

Organize code by what it does, not by architectural layer:

```
project/
├── cmd/
│   └── appname/
│       └── main.go
├── internal/
│   ├── user/           # Everything user-related together
│   │   ├── user.go         # User struct, validation, core logic
│   │   └── store.go        # Database operations
│   ├── order/          # Everything order-related together
│   │   ├── order.go
│   │   └── store.go
│   ├── auth/           # Authentication
│   │   └── auth.go
│   └── server/         # HTTP server, routes
│       └── server.go
├── pkg/                # Only if meant to be imported by external projects
├── go.mod
└── go.sum
```

**Benefits:**
- High cohesion — related code lives together
- Low coupling — packages are self-contained
- Easy navigation — find user code in `user/` package
- Matches Kubernetes, Docker, and major Go projects

### Adapt to Existing Codebase

**DO NOT impose architectural patterns.** Follow what the codebase already uses:

| If codebase uses... | Follow it |
|---------------------|-----------|
| Layer packages (`/service/`, `/repository/`) | Add to existing layers |
| Feature packages (`/user/`, `/order/`) | Add to feature packages |
| Flat structure | Keep it flat |
| `*Service`/`*Repository` naming | Use that naming |
| Direct struct names | Use direct names |

**Your job is to write code that fits, not to refactor toward a different architecture.**

---

## Struct Naming — Be Direct

Name structs after what they ARE, not what layer they belong to:

```go
// GOOD — direct, Go-stdlib style
type User struct { ... }           // The thing itself
type Client struct { ... }         // Like http.Client
type Store struct { ... }          // Like blob.Store — holds/retrieves things
type Cache struct { ... }          // Like sync.Map — caches things
type Writer struct { ... }         // Like io.Writer — writes things

// AVOID — implies architectural layers (use only if codebase already uses these)
type UserService struct { ... }    // "Service" is a layer concept
type UserRepository struct { ... } // "Repository" is DDD terminology
type UserEntity struct { ... }     // "Entity" is DDD terminology
type UserDTO struct { ... }        // "DTO" implies transfer between layers
type UserModel struct { ... }      // "Model" implies MVC/DDD separation
```

---

## Struct Separation — Only When Necessary

**Default: One struct with multiple tags** — simplest, least bug-prone.

**Separate structs only when there's actual technical reason.**

### When ONE Struct is Sufficient

Use a single struct when:
- DB columns map directly to Go types (string↔string, int↔int)
- No security-sensitive fields to hide
- You control the API contract (not generated)
- Same fields needed everywhere

```go
// Simple case — one struct, multiple tags
type Order struct {
    ID        string    `json:"id" db:"id"`
    UserID    string    `json:"user_id" db:"user_id"`
    Amount    int       `json:"amount" db:"amount"`
    Status    string    `json:"status" db:"status"`
    CreatedAt time.Time `json:"created_at" db:"created_at"`
}

// Used in store
func (s *Store) ByID(ctx context.Context, id string) (*Order, error)

// Used in HTTP response — same struct
json.NewEncoder(w).Encode(order)
```

### Case 1: Database Types Differ (Object-Relational Impedance)

When DB uses types that don't directly map to your application types:

```go
// Database row — uses DB-specific types
type UserRow struct {
    ID          pgtype.UUID    `db:"id"`
    Email       sql.NullString `db:"email"`
    Preferences []byte         `db:"preferences"`  // JSON blob
    DeletedAt   sql.NullTime   `db:"deleted_at"`
    Version     int            `db:"version"`      // optimistic locking
}

// Application — clean Go types
type User struct {
    ID          string
    Email       string
    Preferences Preferences  // typed struct
}

// Conversion at store boundary
func (r UserRow) ToUser() (*User, error) {
    var prefs Preferences
    if err := json.Unmarshal(r.Preferences, &prefs); err != nil {
        return nil, err
    }
    return &User{
        ID:          r.ID.String(),
        Email:       r.Email.String,
        Preferences: prefs,
    }, nil
}
```

### Case 2: Security-Sensitive Fields

When some fields must never appear in API responses:

```go
// Full struct — used internally and for DB
type User struct {
    ID           string    `json:"id" db:"id"`
    Email        string    `json:"email" db:"email"`
    PasswordHash []byte    `json:"-" db:"password_hash"`  // json:"-" hides it
    IsAdmin      bool      `json:"-" db:"is_admin"`       // internal flag
}

// Option A: Use json:"-" tag (simplest)
// Works if you always use json.Marshal

// Option B: Separate public struct (when you need explicit control)
type UserPublic struct {
    ID    string `json:"id"`
    Email string `json:"email"`
}

func (u *User) Public() UserPublic {
    return UserPublic{ID: u.ID, Email: u.Email}
}
```

### Case 3: Generated/External Contracts

When API types are generated or externally controlled:

```go
// Generated by protoc — cannot modify
type pb.UserResponse struct {
    UserId string `protobuf:"bytes,1,opt,name=user_id"`
    Email  string `protobuf:"bytes,2,opt,name=email"`
}

// Your application type
type User struct {
    ID    string
    Email string
}

// Conversion at RPC boundary
func UserToProto(u *User) *pb.UserResponse {
    return &pb.UserResponse{
        UserId: u.ID,
        Email:  u.Email,
    }
}
```

### Decision Framework

| Reason to Separate | Separate? | Example |
|--------------------|-----------|---------|
| DB uses `sql.Null*`, `pgtype.*` | ✅ Yes | `UserRow` ↔ `User` |
| JSON blob in DB, typed struct in app | ✅ Yes | `[]byte` ↔ `Preferences` |
| Hide sensitive fields from API | ✅ Yes | `User` with `json:"-"` or `UserPublic` |
| Protobuf/OpenAPI generated types | ✅ Yes | `pb.User` ↔ `User` |
| Versioned public APIs | ✅ Yes | `UserV1` ↔ `UserV2` |
| Direct type mapping (string↔string) | ❌ No | One struct with tags |
| Same fields everywhere | ❌ No | One struct |
| Internal service, you control API | ❌ No | One struct |

---

## DTO vs Domain Object

### The Distinction

| Aspect | DTO (Data Transfer Object) | Domain Object |
|--------|---------------------------|---------------|
| **Fields** | Exported (for serialization) | Unexported + getters |
| **Methods** | Pure only: `ToDomain()`, `Validate()` | Any, including stateful operations |
| **Invariants** | None — just carries data | Has invariants that must be protected |
| **Example** | `CreateUserRequest`, `UserResponse` | `User`, `Order`, `Connection` |

### The Decision Rule

**Does the struct have methods with invariants?**

- **NO invariants** (pure transformations, validation) → DTO with exported fields OK
- **HAS invariants** (methods depend on fields being valid/consistent) → Domain object, unexport fields

### What Are Invariants?

An invariant is a condition that must remain true for the object to behave correctly:

```go
// DTO — no invariants, pure methods only
type CreateOrderRequest struct {
    CustomerID string   `json:"customer_id"`
    Items      []Item   `json:"items"`
}

func (r CreateOrderRequest) ToDomain() *domain.Order { ... }  // pure transformation
func (r CreateOrderRequest) Validate() error { ... }          // pure validation

// Domain Object — HAS invariants
type Connection struct {
    endpoint    Endpoint           // Connect() depends on this being valid
    credentials *Credentials       // Connect() needs matching credentials
    connector   *Connector         // injected capability
}

func (c *Connection) Endpoint() Endpoint { return c.endpoint }
func (c *Connection) Connect(ctx context.Context) (*Client, error) {
    // This method has INVARIANTS:
    // - endpoint must be valid
    // - credentials must match endpoint
    return c.connector.dial(ctx, c.endpoint, c.credentials)
}
```

### Quick Reference

| Struct Type | Exported Fields? | Allowed Methods |
|-------------|------------------|-----------------|
| API DTO | ✅ Yes | `ToDomain()`, `Validate()`, getters |
| Config struct | ✅ Yes | `Validate()`, getters |
| Domain object | ❌ No (use getters) | Any — including stateful operations |
| Service/Client | ❌ No | Any — typically has dependencies |

---

## Composition — When to Split Types

### When to Split

Split when responsibilities have **different semantics or lifecycles**:

| Signal | Meaning |
|--------|---------|
| Different external systems | API client vs credential store vs cache |
| Different change reasons | Auth logic changes ≠ API logic changes |
| Different test requirements | One needs network mocks, other needs DB mocks |
| Awkward dependencies | Unrelated code needs pointer to this type |

### The Pattern: Focused Types + Coordinator

```go
// BETTER — separated by semantic boundary
type APIClient struct {
    client api.Interface  // ONLY external API operations
}

type CredentialFetcher struct {
    store credentials.Store  // ONLY credential operations
}

// Coordinator composes focused types
type ResourceManager struct {
    api   *APIClient
    creds *CredentialFetcher
}

func NewResourceManager(cfg Config) (*ResourceManager, error) {
    // Single entry point creates and wires internal components
    api := newAPIClient(cfg.APIEndpoint)
    creds := newCredentialFetcher(cfg.CredStore)
    return &ResourceManager{api: api, creds: creds}, nil
}
```

---

## Constructor Patterns

### Return Signatures — "Can It Fail?" Rule

| Can construction fail? | Return signature |
|------------------------|------------------|
| **No failure possible** | `func NewCache() *Cache` |
| **Validation can fail** | `func NewServer(cfg Config) (*Server, error)` |
| **Environment can fail** | `func NewFromEnv() (*Client, error)` |

### Argument Order

**Config → Dependencies (pointers) → Logger**

```go
func NewOrderService(
    cfg OrderServiceConfig,      // 1. WHAT (defines behaviour)
    repo *OrderRepository,       // 2. CAPABILITIES (external dependencies)
    cache *Cache,
    logger zerolog.Logger,       // 3. OBSERVABILITY (cross-cutting)
) (*OrderService, error)
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

### Two-Tier Validation Philosophy

| Object Type | Lifecycle | Input Source | Nil Handling |
|-------------|-----------|--------------|--------------|
| Service/Client/Singleton | Program lifetime | Programmer wiring | Trust caller, panic on nil |
| Request/DTO/Short-lived | Per-request | User/runtime data | Validate, return error |

### Tier 1: Startup Singletons — Trust Caller

For objects wired once at startup by programmer code:

```go
// Constructor trusts caller — no validation for pointer deps
func NewUserService(repo *UserRepository, cache *Cache, logger zerolog.Logger) *UserService {
    return &UserService{repo: repo, cache: cache, logger: logger}
}

// Usage in main.go — programmer responsibility
func main() {
    repo := postgres.NewUserRepository(db)
    cache := redis.NewCache(client)
    svc := NewUserService(repo, cache, logger)  // nil here = programming error
}
```

**Rationale:**
- Dependencies wired by programmer, not user input
- Nil = programming error (bug in wiring code)
- Panic at startup = fail fast, caught by CI/CD and tests
- Follows `regexp.MustCompile` philosophy from stdlib

### Tier 2: Per-Request Objects — Validate

For objects constructed from user/external input:

```go
// Constructor validates — returns error
func NewPaymentRequest(userID, amount string) (*PaymentRequest, error) {
    if userID == "" {
        return nil, errors.New("user_id required")
    }
    amt, err := strconv.ParseInt(amount, 10, 64)
    if err != nil {
        return nil, fmt.Errorf("invalid amount: %w", err)
    }
    return &PaymentRequest{UserID: userID, Amount: amt}, nil
}
```

**Rationale:**
- Input from users/external systems
- Invalid input is expected, not exceptional
- Caller needs to handle gracefully (4xx, retry, etc.)

### Methods Always Trust Invariants

Regardless of tier, methods never check nil:

```go
// NEVER do this — methods trust constructor/caller
func (s *Service) Process() error {
    if s == nil || s.repo == nil {  // ❌ FORBIDDEN
        return errors.New("not initialized")
    }
    return s.repo.Call()
}

// ALWAYS do this — trust invariants
func (s *Service) Process() error {
    return s.repo.Call()  // ✅ Trust caller/constructor
}
```

### Nil Safety Rules

1. **Startup singletons**: Caller guarantees valid pointers
2. **Per-request objects**: Constructor validates user input
3. **Methods always trust** that struct is properly initialized
4. **Nil dereference in singleton = panic** — caught in tests
5. **Nil/invalid in per-request = error** — caller handles gracefully

---

## Type Safety: Compile-Time over Runtime

### Typed Identifiers — Decision Tree

**Philosophy: Catch confusion at compile-time.**

#### Step 1: Will This Type Be Confused With Another?

| Scenario | Risk | Typed? |
|----------|------|--------|
| `Transfer(fromAccount, toAccount string)` | HIGH — easy to swap | ✅ `type AccountID string` |
| `Payment(userID, orderID, merchantID string)` | HIGH — 3 similar params | ✅ Type all three |
| `GetUser(id string)` in user package | LOW — obvious context | ❌ Plain `string` |
| Internal helper with one ID type | LOW — limited scope | ❌ Plain `string` |

#### Examples:

```go
// ✅ HIGH RISK — multiple similar IDs
type UserID string
type OrderID string
type AccountID string

func ProcessPayment(user UserID, order OrderID, account AccountID) error
// Compiler catches: ProcessPayment(orderID, userID, accountID)  // ← Won't compile!

// ❌ LOW RISK — single ID type in package
package user

func Get(id string) (*User, error)  // Only user IDs exist here, no confusion
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

---

## Quick Reference: Architecture Violations

| Violation | Fix |
|-----------|-----|
| `interfaces.go` file | Move interface to consumer file |
| `types.go` file | Move types to files with related logic |
| `errors.go` file | Move errors to files with functions returning them |
| Unnecessary struct separation (same fields) | Use one struct with tags (`json`, `db`) |
| Struct naming with layer suffix | Use direct name unless codebase uses suffixes |
| Imposing architectural pattern on existing code | Follow codebase's existing structure |
| Nil check inside method | Move to constructor |
| `string` for ID with confusion risk | Define `type XxxID string` |
| Typed wrapper for single-purpose string | Use plain `string` |
| HTTP call inside transaction | Move before/after transaction |
| Test skipped "requires database" | Mock the database interface |
| Config pointer for singleton | Use value |
| Dependency passed by value | Use pointer |
| Logger not last in constructor | Reorder arguments |
| Exported fields on type with invariant methods | Unexport fields, add getters |
| Monolithic type mixing semantic concerns | Split into focused types + coordinator |
| Many public constructors | Single entry point constructor |

---

## Java/C# Anti-Patterns to Avoid

These patterns work in Java/C# but are over-engineering in Go.

### Provider-Side Interface Definition

**Problem**: Interface defined alongside implementation, violating "accept interfaces, return concrete types"

```go
// ❌ WRONG - provider-side interface
// File: internal/health/strategy.go
package health

type HealthStrategy interface {  // Provider defines interface
    DetermineStatus(node kube.Node) Status
}

type LabelStrategy struct{}
func (s *LabelStrategy) DetermineStatus(node kube.Node) Status { ... }

// Consumer must import both interface and implementation
import "internal/health"
type Reader struct { strategy health.HealthStrategy }

// ✅ RIGHT - consumer-side interface
// File: internal/reader/reader.go
type healthStrategy interface {  // Consumer defines what it needs
    DetermineStatus(node kube.Node) health.Status
}

type Reader struct { strategy healthStrategy }

// File: internal/health/strategy.go
type LabelStrategy struct{}  // Just return concrete type
func (s *LabelStrategy) DetermineStatus(node kube.Node) Status { ... }
```

**Go idiom**: "Interfaces defined by consumer, not provider"

### Premature Interface Abstraction

**Problem**: Creating interface with only 1 implementation when no immediate need for #2

```go
// ❌ QUESTIONABLE - correct placement, but only 1 implementation
type kubeStateFetcher interface {
    FetchState(ctx context.Context) ([]ClusterNodeSnapshot, error)
}

type Coordinator struct {
    kubeReader kubeStateFetcher  // Only *KubeStateReader implements this
}

// ✅ RIGHT - use concrete type
type Coordinator struct {
    kubeReader *kube_reader.KubeStateReader
}
```

**When consumer-side interface with 1 impl IS justified**:
- Testing genuinely needs mocking AND concrete type is hard to test
- Actively working on implementation #2
- Breaking a dependency cycle

**Rule**: Wait until you add implementation #2, even for consumer-side interfaces

### Valid: Adapter Interface for Unmockable Library

```go
// ✅ CORRECT - adapter for unmockable external library
type mongoCollection interface {
    FindOne(ctx context.Context, filter any, ...) *mongo.SingleResult
    Find(ctx context.Context, filter any, ...) (*mongo.Cursor, error)
    // ... methods needed from *mongo.Collection
}

var _ mongoCollection = (*mongo.Collection)(nil)
```

**Why valid**: MongoDB provides no interface, you need it for testing

**See**: `go-anti-patterns` skill for comprehensive anti-patterns reference
