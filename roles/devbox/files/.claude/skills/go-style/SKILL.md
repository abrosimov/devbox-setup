---
name: go-style
description: >
  Go style guide for naming, formatting, comments, and imports. Use when discussing
  naming conventions, formatting rules, comment style, import organization, or
  code style. Triggers on: naming, format, style, comment, import, package name,
  receiver name, variable name, getter, setter.
---

# Go Style Reference

Style guide for naming, formatting, comments, and imports.

---

## Formatting

### Tool

**ALWAYS** use `goimports`, never `gofmt`:

```bash
goimports -local <module-name> -w .
```

Where `<module-name>` is from `go.mod` (e.g., `github.com/org/repo`).

**Why goimports:**
- Organises imports into groups (stdlib, external, local)
- Adds missing imports automatically
- Removes unused imports
- Includes all `gofmt` formatting

### Rules

- Use tabs for indentation, spaces only for alignment
- No rigid line length limit — break lines semantically, not arbitrarily
- Control structures: no parentheses, braces on same line

```go
// GOOD — semantic line breaks
resp, err := client.Do(
    ctx,
    request,
    WithTimeout(30*time.Second),
    WithRetry(3),
)

// BAD — arbitrary 80-char limit breaks
resp, err := client.Do(ctx, request, WithTimeout(30*time.
    Second), WithRetry(3))
```

---

## Naming

### Package Names

- Short, lowercase, single-word: `bytes`, `http`, `json`
- No underscores, no mixedCaps
- Avoid meaningless names: `util`, `common`, `helper`, `misc`, `api`, `types`
- Package name is part of accessor: `bytes.Buffer` not `bytes.ByteBuffer`

```go
// GOOD
package user
package storage
package auth

// BAD
package userService      // mixedCaps
package user_service     // underscore
package util             // meaningless
package common           // meaningless
package helpers          // meaningless
```

### Getters and Setters

Omit `Get` prefix for getters:

```go
// GOOD
func (u *User) Name() string     { return u.name }
func (u *User) SetName(n string) { u.name = n }

// BAD
func (u *User) GetName() string { return u.name }
```

### Receiver Names

Short (1-2 letters), consistent across all methods, reflect type:

```go
// GOOD — "c" for Client, consistent
func (c *Client) Do() error { ... }
func (c *Client) Close() error { ... }

// BAD — generic names
func (this *Client) Do() error { ... }
func (self *Client) Close() error { ... }

// BAD — inconsistent
func (c *Client) Do() error { ... }
func (client *Client) Close() error { ... }
```

### Receiver Type Consistency

**CRITICAL RULE: If ANY method uses pointer receiver, ALL methods must use pointer receiver.**

```go
// ❌ FORBIDDEN — inconsistent receiver types
type Connection struct { addr string }

func (c *Connection) Open() error { }       // pointer
func (c Connection) Address() string { }    // value — WRONG!
func (c *Connection) Close() error { }      // pointer

// ✅ REQUIRED — all pointer receivers
type Connection struct { addr string }

func (c *Connection) Open() error { }       // pointer
func (c *Connection) Address() string { }   // pointer — consistent!
func (c *Connection) Close() error { }      // pointer
```

**Decision tree:**

| Condition | Use pointer receiver |
|-----------|---------------------|
| Method modifies receiver | ✅ Always |
| Type has ANY pointer receiver method | ✅ Always (consistency) |
| Type is large (>64 bytes) | ✅ Avoid copying |
| Type has mutex/sync fields | ✅ Required (can't copy) |
| All methods are read-only AND type is small | ❌ Value is OK |

**Once you choose pointer for ONE method → pointer for ALL methods.**

**Why this matters:**

```go
// Inconsistent receivers cause bugs:
type Counter struct {
    mu    sync.Mutex
    count int
}

func (c *Counter) Increment() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.count++
}

func (c Counter) Value() int {  // ❌ Value receiver
    c.mu.Lock()  // Locks a COPY of the mutex!
    defer c.mu.Unlock()
    return c.count  // Race condition!
}

// FIXED — all pointer receivers
func (c *Counter) Value() int {  // ✅ Pointer receiver
    c.mu.Lock()  // Locks the actual mutex
    defer c.mu.Unlock()
    return c.count  // Safe
}
```

**Method sets matter:**

```go
type Processor struct { ... }

func (p *Processor) Process(data []byte) error { }
func (p Processor) Name() string { }  // ❌ WRONG

// Problem: Interface satisfaction is inconsistent
type Handler interface {
    Process([]byte) error
    Name() string
}

var h Handler = &Processor{}  // OK — pointer has both methods
var h Handler = Processor{}   // FAILS — value only has Name()
```

**Common mistakes:**

| Mistake | Fix |
|---------|-----|
| Getter uses value, setter uses pointer | All pointer |
| Pure getters use value "for efficiency" | Use pointer for consistency |
| Implementing interface on value but state-modifying methods on pointer | All pointer |
| "Read-only" methods use value | Use pointer if ANY method is pointer |

**Real-world example:**

```go
// ❌ INCONSISTENT
type Cache struct {
    items map[string]any
    mu    sync.RWMutex
}

func (c *Cache) Set(key string, val any) {  // pointer (modifies)
    c.mu.Lock()
    defer c.mu.Unlock()
    c.items[key] = val
}

func (c Cache) Get(key string) (any, bool) {  // ❌ value (read-only)
    c.mu.RLock()  // COPIES the mutex — race condition!
    defer c.mu.RUnlock()
    val, ok := c.items[key]
    return val, ok
}

// ✅ CONSISTENT
func (c *Cache) Get(key string) (any, bool) {  // pointer
    c.mu.RLock()  // Locks actual mutex
    defer c.mu.RUnlock()
    val, ok := c.items[key]
    return val, ok
}
```

**Correct pattern for small, immutable types:**

```go
// OK — all value receivers (no state modification, small type)
type Point struct {
    X, Y int
}

func (p Point) Add(other Point) Point {
    return Point{X: p.X + other.X, Y: p.Y + other.Y}
}

func (p Point) Distance() float64 {
    return math.Sqrt(float64(p.X*p.X + p.Y*p.Y))
}

// But if you need to modify:
type MutablePoint struct {
    X, Y int
}

func (p *MutablePoint) Move(dx, dy int) {  // pointer (modifies)
    p.X += dx
    p.Y += dy
}

func (p *MutablePoint) Distance() float64 {  // ✅ pointer (consistency)
    return math.Sqrt(float64(p.X*p.X + p.Y*p.Y))
}
```

### Variable Names

Length correlates with scope distance — short names for short scopes:

```go
// Loop indices, readers: single letter
for i := range items { }
r := bufio.NewReader(f)

// Local variables: short
srv := NewServer()
ctx := context.Background()

// Package-level, exported: descriptive
var DefaultTimeout = 30 * time.Second
```

### Initialisms

Maintain consistent case: `URL`, `HTTP`, `ID`, `API`, `XML`

```go
// GOOD
type HTTPServer struct{}
userID := "123"
xmlAPI := NewXMLAPI()

// BAD
type HttpServer struct{}
userId := "123"
```

### Interface Names

One-method interfaces: method name + `-er` suffix. Match canonical signatures:

```go
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Stringer interface {
    String() string
}
```

### MixedCaps

Always MixedCaps or mixedCaps — never underscores:

```go
const maxLength = 256      // unexported
const MaxLength = 256      // exported
// NEVER: MAX_LENGTH, max_length
```

---

## CRITICAL: This is SERVICE Code — No Doc Comments

**This codebase is a SERVICE, not a library.** Services have no external consumers needing godoc.

**NEVER add doc comments to:**
- Services, handlers, controllers, domain models
- Any function where the name is self-explanatory
- Unexported functions (lowercase)

**Only exception:** Library wrappers in `pkg/` or infrastructure clients (rare).

**Before writing ANY comment, ask:** *"If I delete this, does the code become unclear?"*
- If NO → don't write it
- If YES → rename the function instead

---

## CRITICAL: Comments (ZERO TOLERANCE)

### Inline Comments

- One space before `//` and one space after: `code // comment`
- Comments explain **WHY**, not **WHAT**
- **NEVER** comment obvious code — it adds noise without value

```go
// ❌ FORBIDDEN — describes what code does
i++ // increment i
users := make([]User, 0) // create empty slice of users
// Check if doomed AFTER decrementing
// If we're the last reference, abort and end session
// Verify transaction is stored in context

// ❌ FORBIDDEN — wrong spacing
code// comment
code //comment
code  //  comment

// ✅ CORRECT — explains why
i++ // skip header row
users := make([]User, 0) // nil serialises to null in JSON, need []
// MongoDB doesn't support nested tx, use refcount
```

### CRITICAL: Doc Comments — When Required (ZERO TOLERANCE)

**Library/Infrastructure code** (reusable clients, wrappers, `pkg/`):
- Exported API: Required — describe contract, not implementation
- Unexported: **NEVER**

**Business logic** (services, handlers, domain models, application code):
- Exported or not: **NEVER** — function names and signatures ARE the documentation
- If you need a doc comment to explain what a function does, rename the function

#### How to Distinguish

| Indicator | Library | Business Logic |
|-----------|---------|----------------|
| Could be extracted to separate repo | Yes | No |
| Has external consumers | Yes | No |
| Changes with product requirements | Rarely | Frequently |
| Examples | `mongo.Client`, `kube.Client` | `OrderService`, `UserHandler` |

#### Library Code — Contract Only

Start with the name, describe WHAT not HOW:

```go
// Client represents an HTTP client.
type Client struct { ... }

// Get fetches the resource at the given URL.
func (c *Client) Get(url string) (*Response, error)

// ErrNotFound is returned when the resource doesn't exist.
var ErrNotFound = errors.New("not found")
```

❌ **FORBIDDEN — implementation details:**
```go
// Commit commits the transaction handle.
//
// Behavior:
// - If transaction is doomed: returns ErrTransactionDoomed after decrementing refCount
// - If refCount > 1 after decrement: returns nil (waits for outer handle)
func (h *TxHandle) Commit(ctx context.Context) error {
```

✅ **CORRECT — contract only:**
```go
// Commit commits the transaction. Returns ErrTransactionDoomed if inner handle
// rolled back, ErrHandleReleased if already called. Safe to call multiple times.
func (h *TxHandle) Commit(ctx context.Context) error {
```

#### Unexported = No Doc Comment

❌ **FORBIDDEN:**
```go
// getClient returns the MongoDB client for internal use.
// Used by transaction.go to start sessions.
func (c *Client) getClient(ctx context.Context) (*mongo.Client, error) {
```

✅ **CORRECT:**
```go
func (c *Client) getClient(ctx context.Context) (*mongo.Client, error) {
```

**Never document callers** — "Used by X" becomes a lie when code changes.

#### Business Logic — No Doc Comments

❌ **FORBIDDEN:**
```go
// ProcessOrder processes an order by validating items, calculating totals,
// and persisting to the database.
func (s *OrderService) ProcessOrder(ctx context.Context, order *Order) error {
```

✅ **CORRECT:**
```go
func (s *OrderService) ProcessOrder(ctx context.Context, order *Order) error {
```

The function name and signature tell you everything.

### Boolean Functions (Library Code Only)

Use "reports whether":

```go
// Valid reports whether the token is valid.
func (t *Token) Valid() bool
```

### Package Comments (Library Code Only)

Adjacent to package clause, no blank line:

```go
// Package http provides HTTP client and server implementations.
package http
```

---

## Imports

### Organisation

Group with blank lines: stdlib, then external, then local:

```go
import (
    "context"
    "fmt"
    "net/http"

    "github.com/rs/zerolog"
    "golang.org/x/sync/errgroup"

    "github.com/myorg/myrepo/internal/user"
)
```

**Note:** `goimports -local <module-name>` handles this automatically.

### Blank Imports

Only in main packages or tests:

```go
import _ "image/png"  // register PNG decoder
```

### Avoid Renaming

Only rename to avoid collisions:

```go
import (
    "crypto/rand"
    mrand "math/rand"  // only when collision
)
```

---

## Security

### Crypto Rand

Never use `math/rand` for cryptographic purposes:

```go
// GOOD
import "crypto/rand"
key := make([]byte, 32)
rand.Read(key)

// BAD — predictable
import "math/rand"
```

---

## Quick Reference: Style Violations

| Violation | Fix |
|-----------|-----|
| Using `gofmt` | Use `goimports -local <module-name>` |
| Package name `userService` | Use `user` |
| Package name `util`, `common`, `helpers` | Use meaningful name |
| `GetUser()` getter | Use `User()` |
| Receiver `this`, `self` | Use short type-based name (`u`, `c`) |
| Receiver name inconsistency | Same name across all methods (`c` not `client`) |
| **Mixed pointer/value receivers** | **All pointer if ANY method is pointer** |
| `userId` instead of `userID` | Use `userID` (initialisms in caps) |
| `MAX_LENGTH` constant | Use `MaxLength` or `maxLength` |
| Comment `// increment i` | Delete (obvious) or explain WHY |
| Missing doc comment on exported | Add `// Name ...` comment |
| Import rename without collision | Remove rename |
| `math/rand` for secrets | Use `crypto/rand` |
