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

## Comments

### Inline Comments

- One space before `//` and one space after: `code // comment`
- Comments explain **WHY**, not **WHAT**
- Don't comment obvious code — it adds noise without value

```go
// BAD — describes what code does (obvious from reading)
i++ // increment i
users := make([]User, 0) // create empty slice of users

// BAD — wrong spacing
code// comment
code //comment
code  //  comment

// GOOD — explains why
i++ // skip header row
users := make([]User, 0) // nil serialises to null in JSON, need []
```

### Doc Comments

Required for all exported names. Start with the name:

```go
// Client represents an HTTP client.
type Client struct { ... }

// Get fetches the resource at the given URL.
func (c *Client) Get(url string) (*Response, error)

// ErrNotFound is returned when the resource doesn't exist.
var ErrNotFound = errors.New("not found")
```

### Boolean Functions

Use "reports whether":

```go
// Valid reports whether the token is valid.
func (t *Token) Valid() bool
```

### Package Comments

Adjacent to package clause, no blank line:

```go
// Package http provides HTTP client and server implementations.
package http
```

### Comment Sentences

Complete sentences with capitalisation and periods:

```go
// Request represents a request to run a command.
type Request struct { ... }
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
| `userId` instead of `userID` | Use `userID` (initialisms in caps) |
| `MAX_LENGTH` constant | Use `MaxLength` or `maxLength` |
| Comment `// increment i` | Delete (obvious) or explain WHY |
| Missing doc comment on exported | Add `// Name ...` comment |
| Import rename without collision | Remove rename |
| `math/rand` for secrets | Use `crypto/rand` |
