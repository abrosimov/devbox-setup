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

> **See also:** `philosophy.md` "DTO vs Domain Object" for when to use public vs private fields based on invariants.

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

**If using sqlx with direct mapping (same types), one struct is fine:**
```go
// Direct mapping works — one struct
type User struct {
    ID    string `json:"id" db:"id"`
    Email string `json:"email" db:"email"`
    Name  string `json:"name" db:"name"`
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

### Case 4: Versioned APIs

When you support multiple API versions with different shapes:

```go
// v1 response
type UserV1 struct {
    ID   string `json:"id"`
    Name string `json:"name"`
}

// v2 response — different structure
type UserV2 struct {
    ID        string `json:"id"`
    FirstName string `json:"first_name"`
    LastName  string `json:"last_name"`
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

### Conversion Functions Are Bug Magnets

Every conversion point is where bugs hide:

```go
// BUG WAITING TO HAPPEN
func toPublic(u UserRow) UserPublic {
    return UserPublic{
        ID:    u.ID,
        Email: u.Email,
        // Name: u.Name,  // OOPS — forgot this, silent data loss
    }
}
```

**One struct = compiler catches all field references.** Multiple structs with conversion = manual field mapping that can drift.

### Anti-Patterns

```go
// BAD — same data, three structs, three packages (no technical reason)
internal/
├── domain/
│   └── user.go          // type User struct { ID, Email, Name }
├── repository/
│   └── user.go          // type UserModel struct { ID, Email, Name } — same!
└── handler/
    └── user.go          // type UserDTO struct { ID, Email, Name } — same again!

// Problems:
// - 3x maintenance burden
// - Conversion functions everywhere
// - Easy to forget fields during conversion
// - Compiler can't catch missing fields across packages

// GOOD — one package, one struct (when fields are identical)
internal/
└── user/
    ├── user.go   // type User struct { ID, Email, Name }
    └── store.go  // func (s *Store) ByID(...) (*User, error)
```

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

An invariant is a condition that must remain true for the object to behave correctly. If external code can mutate fields and break method behaviour, you have invariants.

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
    // External mutation of these fields would break Connect()
    return c.connector.dial(ctx, c.endpoint, c.credentials)
}
```

### Why Unexport Fields for Domain Objects?

```go
// If fields are exported, caller can break invariants:
conn := GetConnection()
conn.Endpoint = "garbage"           // mutates state
client, err := conn.Connect(ctx)    // behaviour broken — uses corrupted endpoint

// With unexported fields, invariants are protected:
conn := GetConnection()
// conn.endpoint not accessible — can only use Connect()
client, err := conn.Connect(ctx)    // always uses valid state from construction
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

### The Problem: Mixed Responsibilities

When a type handles multiple distinct concerns, it creates coupling problems:

```go
// PROBLEMATIC — mixed responsibilities
type ResourceClient struct {
    apiClient    api.Interface       // talks to external API
    credStore    credentials.Store   // fetches credentials
    restConfig   *rest.Config        // connection config
}

// Every consumer needs the full client, even if they only need one capability
// Testing requires mocking all three concerns
// Changes to credential logic affect API logic
```

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

### Benefits

| Benefit | Explanation |
|---------|-------------|
| Independent testing | Test API logic without credential mocking |
| Clear ownership | Each type is expert on one thing |
| Flexible evolution | Change credential logic without touching API code |
| Reduced coupling | Consumers depend only on what they need |

### When NOT to Split

Don't split if:
- Responsibilities **always go together** and have same lifecycle
- Split would just add indirection without benefit
- The "two responsibilities" are actually one cohesive concept

---

## Constructor Patterns

### Return Signatures — "Can It Fail?" Rule

**The decision is not about arguments — it's about failure modes.**

| Can construction fail? | Return signature |
|------------------------|------------------|
| **No failure possible** | `func NewCache() *Cache` |
| **Validation can fail** | `func NewServer(cfg Config) (*Server, error)` |
| **Environment can fail** | `func NewFromEnv() (*Client, error)` |

```go
// ✅ GOOD — no args, no error
func NewCache() *Cache {
    return &Cache{items: make(map[string]item)}
}

// ✅ GOOD — no args, but reads env (can fail)
func NewFromEnv() (*Client, error) {
    apiKey := os.Getenv("API_KEY")
    if apiKey == "" {
        return nil, errors.New("API_KEY not set")
    }
    return &Client{apiKey: apiKey}, nil
}

// ✅ GOOD — has args, no validation needed
func NewLogger(w io.Writer) *Logger {
    return &Logger{w: w}  // io.Writer guaranteed non-nil by type system
}

// ✅ GOOD — config validation needed
func NewServer(cfg ServerConfig) (*Server, error) {
    if cfg.Port < 1 || cfg.Port > 65535 {
        return nil, errors.New("invalid port")
    }
    return &Server{cfg: cfg}, nil
}

// ✅ GOOD — dependency validation needed
func NewService(repo Repository) (*Service, error) {
    if repo == nil {
        return nil, errors.New("repo is required")
    }
    return &Service{repo: repo}, nil
}
```

**Error Hierarchy Principle:**
- **Startup failure** (constructor error) > **Runtime failure** (method error)
- Validate configuration at construction, not on every method call

### Argument Order

**Config → Dependencies (pointers) → Logger**

**This is our convention** (not stdlib, but enforced for consistency).

```go
func NewOrderService(
    cfg OrderServiceConfig,      // 1. WHAT (defines behaviour)
    repo *OrderRepository,       // 2. CAPABILITIES (external dependencies)
    cache *Cache,
    logger zerolog.Logger,       // 3. OBSERVABILITY (cross-cutting)
) (*OrderService, error)
```

**Rationale:**

1. **Config first** — Validates "what" before acquiring "how"
   - Fail fast on invalid config before expensive dependency checks
   - Aligns with Error Hierarchy: startup validation before runtime

2. **Dependencies middle** — External capabilities grouped together
   - Easy to see what external systems this depends on
   - Pointer types enable nil validation

3. **Logger last** — Cross-cutting concern, often optional
   - Consistent position makes it easy to add/remove
   - Can use `zerolog.Nop()` as default

**Benefit:** Every constructor in codebase has same pattern — reduce cognitive load.

```go
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
        return errors.New("not initialised")
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

### Typed Identifiers — Decision Tree

**Philosophy: Catch confusion at compile-time.**

Typed wrappers provide compile-time safety, but **not every string needs a type**.

#### Step 1: Will This Type Be Confused With Another?

```
Do I have multiple similar types that could be swapped?
│
├─ YES → Step 2
└─ NO → Use plain type (string, int, etc.)
```

#### Step 2: Is the Confusion Risk Real or Theoretical?

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

// ❌ OVER-ENGINEERING — no confusion possible
type APIEndpoint string  // What else would an endpoint be?
type DatabaseName string  // Only one database referenced
```

#### The Trade-Off:

| Typed Wrapper | Benefit | Cost |
|---------------|---------|------|
| Adds type safety | Catch swapped params at compile-time | Conversions needed (`string(userID)`) |
| Documents intent | Code self-documents ID types | More types to maintain |

**When in doubt:** Start without wrapper, add if you make a swap mistake.

### String() Method

Defined types work with `%s`/`%v` without `String()`. Add `String()` only when:

- Type used with `fmt.Stringer` interfaces
- Part of public API
- Other domain types implement it (consistency)

```go
// If you add String(), verify compliance:
var _ fmt.Stringer = UserID("")
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
| `types.go` file | Move types to files with related logic |
| `errors.go` file | Move errors to files with functions returning them |
| Unnecessary struct separation (same fields) | Use one struct with tags (`json`, `db`) |
| Struct naming with layer suffix (`UserService`, `UserRepository`) | Use direct name (`User`, `Store`) unless codebase already uses suffixes |
| Imposing architectural pattern on existing code | Follow codebase's existing structure |
| Nil check inside method | Move to constructor |
| `string` for ID with confusion risk | Define `type XxxID string` |
| Typed wrapper for single-purpose string | Use plain `string` (no confusion risk) |
| HTTP call inside transaction | Move before/after transaction |
| Test skipped "requires database" | Mock the database interface |
| Config pointer for singleton | Use value |
| Dependency passed by value | Use pointer |
| Logger not last in constructor | Reorder arguments |
| Exported fields on type with invariant methods | Unexport fields, add getters |
| Monolithic type mixing semantic concerns | Split into focused types + coordinator |
| Many public constructors | Single entry point constructor |
