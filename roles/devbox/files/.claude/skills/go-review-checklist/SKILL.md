---
name: go-review-checklist
description: >
  Go code review checklist, verification checkpoints, and review patterns.
  Used by code-reviewer-go agent. Covers enumeration, verification, counter-evidence,
  backward compatibility, and domain compliance checks.
  Triggers on: go review, code review go, review checklist, verification checkpoint.
---

# Go Review Checklist

## Step 3: Exhaustive Enumeration (NO EVALUATION YET)

**This phase is about LISTING, not JUDGING. Do not skip items. Do not optimise.**

### 3-Pre: Lint Suppression Audit

**Before any other enumeration**, scan for newly added suppression directives:
```bash
# Find all new suppression directives in the diff
git diff $DEFAULT_BRANCH...HEAD -U0 -- '*.go' | grep -n '^\+.*nolint'
```

**Every new suppression is a finding.** For each one:
- Does it have a specific linter name? (`//nolint:errcheck` not `//nolint`)
- Does it have a justification comment?
- Was the user asked before adding it? (Check PR comments/commit messages)
- Can the underlying issue be fixed instead?

Flag unjustified suppressions as **HIGH severity** — they indicate the engineer took a shortcut instead of fixing the code.

### 3A: Error Handling Inventory

Run this search and record EVERY match:
```bash
# Find all error handling sites in changed files
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "return.*err\|if err != nil\|errors\.\|fmt\.Errorf"
```

Create an inventory table:
```
| Line | File | Pattern | Has Context Wrapping? | Verified? |
|------|------|---------|----------------------|-----------|
| 45   | user.go | return err | NO | |
| 67   | user.go | return fmt.Errorf("...: %w", err) | YES | |
| ... | ... | ... | ... | |

Total error handling sites found: ___
```

### 3B: Identifier Inventory

List ALL new or changed identifiers (variables, fields, functions, types):
```
| Identifier | Type | Location | What It Represents | Ambiguous? |
|------------|------|----------|-------------------|------------|
| Context | field | user.go:23 | request context | YES - conflicts with context.Context |
| userID | var | user.go:45 | user identifier | NO |
| ... | ... | ... | ... | ... |

Total new identifiers: ___
```

### 3C: Public Function Inventory

List ALL public functions in changed files and their test coverage:
```bash
# Find public functions in changed files
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | grep -v _test.go | xargs grep -n "^func [A-Z]\|^func (.*) [A-Z]"
```

```
| Function | File:Line | Test Exists? | Test Location | Error Paths Tested? |
|----------|-----------|--------------|---------------|-------------------|
| GetUser | user.go:45 | YES | user_test.go:23 | NO - only happy path |
| SaveUser | user.go:89 | NO | - | - |
| ... | ... | ... | ... | ... |

Total public functions: ___
Functions without tests: ___
```

### 3D: Skipped Test Inventory

Find ALL skipped tests:
```bash
grep -rn "t\.Skip\|s\.T()\.Skip\|suite\.T()\.Skip" *_test.go
```

```
Skipped tests found: ___
List: ___
```

## Step 4: Individual Verification

**Now evaluate EACH enumerated item. Do NOT batch. Do NOT assume consistency.**

### Error Handling Verification

For EACH error handling site in your inventory:
- [ ] Is the error checked (no `_` ignoring)?
- [ ] Is context added? `fmt.Errorf("doing X: %w", err)`
- [ ] Is sentinel error handling correct? `errors.Is()` / `errors.As()`

Mark each row: pass, fail, ? (needs discussion)

**Ultrathink trigger**: If you have >5 error handling sites, pause and invoke:
> "Let me think harder about each error handling site individually to ensure I haven't missed any issues due to pattern matching."

### Error Handling Rules

```go
// BAD: ignoring error
result, _ := doSomething()

// BAD: no context
if err != nil {
    return err
}

// GOOD
if err != nil {
    return fmt.Errorf("processing user %s: %w", userID, err)
}
```

### Nil Safety --- Two-Tier Approach

**Tier 1: Startup singletons** --- Trust caller, no validation

```go
// GOOD: Singleton constructor --- trust caller
func NewOrderService(repo *OrderRepository, cache *Cache, logger zerolog.Logger) *OrderService {
    return &OrderService{repo: repo, cache: cache, logger: logger}
}

// BAD: Unnecessary nil validation for singleton
func NewOrderService(repo *OrderRepository, cache *Cache, logger zerolog.Logger) (*OrderService, error) {
    if repo == nil {
        return nil, errors.New("repo required")  // Over-engineering
    }
    // ...
}
```

**Tier 2: Per-request objects** --- Validate user input

```go
// GOOD: Per-request constructor --- validate
func NewOrderFromRequest(r *http.Request) (*Order, error) {
    userID := r.FormValue("user_id")
    if userID == "" {
        return nil, errors.New("user_id required")
    }
    return &Order{UserID: userID}, nil
}
```

**NEVER add nil receiver checks inside methods:**

```go
// BAD: nil receiver check (always wrong)
func (s *Service) Process() error {
    if s == nil || s.client == nil {
        return errors.New("not initialised")
    }
    return s.client.Call()
}

// GOOD: trust invariants
func (s *Service) Process() error {
    return s.client.Call()
}
```

**Review checklist for nil safety:**
- [ ] Singleton constructors: NO nil validation for pointer deps?
- [ ] Per-request constructors: YES validation for user-derived inputs?
- [ ] NO nil receiver checks inside methods?
- [ ] Singleton returns single value `*T` (not `(*T, error)`) when no semantic validation?

**Classification guide:**

| Constructor Type | Returns | Nil Handling |
|------------------|---------|--------------|
| `NewUserService(repo *Repo, ...)` | `*UserService` | Trust caller |
| `NewOrderFromRequest(r *Request)` | `(*Order, error)` | Validate input |
| `NewConfigFromEnv()` | `(*Config, error)` | Validate env vars |

### Constructor Return Signatures

- **No arguments** -> return `*T` without error
- **With arguments** -> return `(*T, error)` or `*T` depending on validation needs

```go
// GOOD --- no args, no error
func NewCache() *Cache

// GOOD --- needs validation, returns error
func NewServer(cfg ServerConfig) (*Server, error)

// GOOD --- no validation needed, no error
func NewLogger(cfg LoggerConfig) *Logger

// FLAG --- no args but returns error (unnecessary)
func NewCache() (*Cache, error)
```

### Config Parameters --- Value vs Pointer

| Object Lifecycle | Config Passing | Rationale |
|-----------------|----------------|-----------|
| Few instances (singleton, service, server) | **Value always** | Copy cost negligible for long-lived objects |
| Frequently constructed (per-request) | Pointer | Reduces copy overhead |

```go
// FLAG: pointer for singleton config
func NewServer(cfg *ServerConfig)  // Server is singleton --- use value

// GOOD: singleton/few instances --- value
func NewServer(cfg ServerConfig)

// GOOD: frequently constructed --- pointer
func NewRequest(cfg *RequestConfig)
```

### Dependencies --- Always Pointers

All dependencies passed to constructors must be pointers.

**Constructor argument order:**
1. **Config** (if exists) --- always first
2. **Dependencies** --- as pointers, in the middle
3. **Logger** --- always last

```go
// GOOD --- correct order: config, dependencies (pointers), logger
func NewService(cfg ServiceConfig, repo *Repository, cache *Cache, logger zerolog.Logger) (*Service, error)

// FLAG --- wrong order
func NewService(repo *Repository, cfg ServiceConfig, logger zerolog.Logger)  // config must be first

// FLAG --- dependency by value
func NewService(cfg ServiceConfig, repo Repository, logger zerolog.Logger)  // repo should be *Repository

// FLAG --- logger not last
func NewService(cfg ServiceConfig, logger zerolog.Logger, repo *Repository)  // logger must be last
```

### Concurrency Issues

- Are shared resources protected by mutex?
- Are channels properly closed?
- Are goroutine leaks possible?
- Is context cancellation respected?

```go
// BAD: goroutine leak
go func() {
    result := <-ch  // blocks forever if ch never receives
    process(result)
}()

// GOOD
go func() {
    select {
    case result := <-ch:
        process(result)
    case <-ctx.Done():
        return
    }
}()
```

### Resource Management

- Are `defer` statements used for cleanup?
- Is `defer` in the right place (after error check)?
- Are resources closed in correct order?

```go
// BAD: defer before error check
func readFile(path string) error {
    f, err := os.Open(path)
    defer f.Close()  // panics if err != nil
    if err != nil {
        return err
    }
}

// GOOD
func readFile(path string) error {
    f, err := os.Open(path)
    if err != nil {
        return err
    }
    defer f.Close()
}
```

## Step 5: Formal Logic Validation

For each changed function/method:

**Boolean Logic**
- Is the condition inverted? (`if canDo` vs `if !canDo`)
- Are `&&` / `||` operators correct?
- Are comparisons correct? (`>` vs `>=`, `==` vs `!=`)

**State & Status Checks**
- Does the code check for the RIGHT states?
- Are there states that should be included but aren't?

**Boundary Conditions**
- Off-by-one errors in loops or slices
- Empty slice/map handling
- Integer overflow for `int` operations

**Control Flow**
- Early returns --- do they cover all cases?
- Switch statements --- is `default` case handled?
- Type assertions --- is the `ok` value checked?

```go
// BAD: unchecked type assertion
val := x.(string)  // panics if x is not string

// GOOD
val, ok := x.(string)
if !ok {
    return errors.New("expected string")
}
```

## Step 6: Verification Checkpoints

**DO NOT proceed to final report until ALL checkpoints are complete.**

### Checkpoint A: Error Handling
```
Total error returns found: ___
Error returns WITH context wrapping: ___
Error returns WITHOUT context: ___
  Line numbers: ___
Errors ignored with `_`: ___
  Line numbers: ___

VERDICT: [ ] PASS  [ ] FAIL --- issues documented above
```

### Checkpoint B: Test Coverage
```
Public functions in changed files: ___
Functions with dedicated tests: ___
Functions with ZERO test coverage: ___
  List: ___
Skipped tests found: ___
  List: ___

VERDICT: [ ] PASS  [ ] FAIL --- issues documented above
```

### Checkpoint C: Naming Clarity
```
New identifiers introduced: ___
Identifiers with potential ambiguity: ___
  List with reasoning: ___

VERDICT: [ ] PASS  [ ] FAIL --- issues documented above
```

### Checkpoint D: Nil Safety
```
Constructors that validate dependencies: ___
Constructors missing validation: ___
Methods with nil receiver checks (anti-pattern): ___

VERDICT: [ ] PASS  [ ] FAIL --- issues documented above
```

### Checkpoint E: Architecture (see `go-architecture` skill)
```
Interfaces defined in consumer file (not interfaces.go): ___
Interfaces in wrong location (separate file): ___
  List: ___

Project structure:
  - Follows existing codebase patterns: YES/NO
  - Imposes new architectural pattern unnecessarily: ___
    List violations: ___

Struct naming:
  - Uses layer-suffix naming when codebase uses direct names: ___
    Examples (UserService should be User, UserRepository should be Store): ___
  - Uses direct names when codebase uses layer suffixes: ___
    Examples (should follow existing *Service/*Repository pattern): ___

Struct separation:
  - Unnecessary separation (same fields, no technical reason): ___
    List: ___ (should use one struct with tags)
  - Missing separation when needed (DB types differ, security fields): ___
    List: ___

Constructor patterns:
  - Argument order correct (config, deps, logger): ___
  - Dependencies passed as pointers: ___
  - Config passed by value for singletons: ___
  - Multiple public constructors (should be single entry point): ___
    List: ___

Type safety:
  - Raw strings for IDs with confusion risk (should be typed): ___
  - Typed wrappers for single-purpose strings (unnecessary): ___
  - Typed IDs with unnecessary conversions: ___

DTO vs Domain Object (see `go-architecture` skill):
  - Structs with exported fields AND methods with invariants: ___
    List: ___  (should unexport fields, add getters)
  - Domain objects correctly using unexported fields + getters: ___

Composition (semantic separation):
  - Types mixing semantically different responsibilities: ___
    List: ___  (should split into focused types)

External dependencies in tests:
  - Tests skipped with "requires DB/integration": ___

Receiver consistency:
  - Types with mixed pointer/value receivers (CRITICAL VIOLATION): ___
    List: ___
  - Justification for value receivers (all read-only, small type <64 bytes): ___

VERDICT: [ ] PASS  [ ] FAIL --- issues documented above
```

### Checkpoint E.5: Receiver Consistency (CRITICAL)

**CRITICAL RULE: Any structure can have either only pointer receivers or only value receivers. Never mix them.**

**Search for all method receivers in changed files:**
```bash
# Find all method definitions
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | grep -v _test.go | xargs grep -n "^func (.*) [A-Z]"

# Group by type to verify consistency
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | grep -v _test.go | xargs grep "^func (" | awk -F'[()]' '{print $2}' | sort | uniq -c
```

**For EACH type with methods, verify receiver consistency:**

```
Type: ______________
File: ______________

All methods for this type:
| Method | Receiver | Line | Pointer/Value |
|--------|----------|------|---------------|
| Method1 | (t *Type) | file.go:42 | pointer |
| Method2 | (t Type) | file.go:67 | value |
| Method3 | (t *Type) | file.go:89 | pointer |

Receiver consistency check:
- [ ] All pointer receivers
- [ ] All value receivers
- [ ] MIXED RECEIVERS (VIOLATION)
  Violations: Method2 uses value, others use pointer

Decision criteria verification:
- [ ] Does ANY method modify receiver? -> ALL must be pointer
- [ ] Does type have mutex/sync.* fields? -> ALL must be pointer (can't copy)
- [ ] Is type large (>64 bytes)? -> Should use ALL pointer (avoid copying)
- [ ] All methods read-only AND type is small (<64 bytes)? -> Can use ALL value

Total types reviewed: ___
Types with mixed receivers (BLOCKING): ___
```

**Common violations to flag:**

```go
// VIOLATION - mixed receivers (race condition!)
type Cache struct {
    items map[string]any
    mu    sync.RWMutex
}

func (c *Cache) Set(key string, val any) {  // pointer
    c.mu.Lock()
    defer c.mu.Unlock()
    c.items[key] = val
}

func (c Cache) Get(key string) (any, bool) {  // value --- COPIES mutex!
    c.mu.RLock()  // Locks COPY, not original --- race condition
    defer c.mu.RUnlock()
    val, ok := c.items[key]
    return val, ok
}

// VIOLATION - inconsistent receivers (interface satisfaction issue)
type Processor struct { state int }

func (p *Processor) Process(data []byte) error { }  // pointer
func (p Processor) Name() string { }  // value

// Problem: *Processor satisfies interface, Processor does not
type Handler interface {
    Process([]byte) error
    Name() string
}

var h Handler = &Processor{}  // OK
var h Handler = Processor{}   // FAILS --- value only has Name()

// CORRECT - all pointer receivers
func (c *Cache) Set(key string, val any) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.items[key] = val
}

func (c *Cache) Get(key string) (any, bool) {  // pointer
    c.mu.RLock()  // Locks actual mutex
    defer c.mu.RUnlock()
    val, ok := c.items[key]
    return val, ok
}
```

**Special case: Small immutable value types (rare, must justify)**

```go
// ACCEPTABLE - all value receivers, small immutable type
type Point struct {
    X, Y int  // 16 bytes total
}

func (p Point) Add(other Point) Point {  // Returns new Point, doesn't modify
    return Point{X: p.X + other.X, Y: p.Y + other.Y}
}

func (p Point) Distance() float64 {
    return math.Sqrt(float64(p.X*p.X + p.Y*p.Y))
}

// Justification: Truly immutable (no mutation methods), small (16 bytes)
```

**Review output format:**

```
**Receiver Consistency Violation** --- BLOCKING

**Type**: Cache
**Location**: internal/cache/cache.go

**Issue**: Mixed pointer and value receivers

| Method | Line | Receiver Type |
|--------|------|---------------|
| Set    | 42   | pointer       |
| Get    | 67   | value         |
| Delete | 89   | pointer       |

**Why Wrong**:
- Type has sync.RWMutex field (line 15)
- Value receiver on Get() copies the mutex
- Locking the copy doesn't protect the original data
- This creates a race condition

**Fix**: Change Get() to use pointer receiver:
```go
func (c *Cache) Get(key string) (any, bool) {  // Change to pointer
    c.mu.RLock()
    defer c.mu.RUnlock()
    val, ok := c.items[key]
    return val, ok
}
```

**Rule**: If ANY method uses pointer -> ALL methods must use pointer
```

**VERDICT: [ ] PASS  [ ] FAIL --- mixed receivers are BLOCKING**

---

### Checkpoint F: API Surface (Minimal Export)

**Run this search to find all exported identifiers in changed files:**
```bash
# Find exported types, functions, methods, constants, variables
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | grep -v _test.go | xargs grep -n "^type [A-Z]\|^func [A-Z]\|^func (.*) [A-Z]\|^const [A-Z]\|^var [A-Z]"
```

For EACH exported identifier, ask:
1. "Will code **outside this package** use this?"
2. "Is this **intended public API** or implementation detail?"

If NO to either -> flag as over-exported.

```
Exported identifiers in changed files: ___

Over-exported (should be unexported):
  - Struct fields that should be private: ___
    List: ___
  - Helper functions exported unnecessarily: ___
    List: ___
  - Internal/intermediate types exported: ___
    List: ___
  - Interfaces only used within package: ___
    List: ___

VERDICT: [ ] PASS  [ ] FAIL --- issues documented above
```

**Common API Surface Violations:**
```go
// FLAG: Exported struct fields (should be unexported with getter if needed)
type Client struct {
    BaseURL    string        // should be baseURL
    HTTPClient *http.Client  // should be httpClient
}

// FLAG: Exported helper function (only used internally)
func BuildCacheKey(id string) string { ... }  // should be buildCacheKey

// FLAG: Exported interface only used within package
type UserRepository interface { ... }  // should be userRepository if only used here

// FLAG: Exported internal type
type ValidationResult struct { ... }  // if only used within package, unexport
```

### Checkpoint G: Test Quality --- Error Assertions

**Search for error string comparisons in tests:**
```bash
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*_test.go' | xargs grep -n "err\.Error()\|Contains.*err\|Equal.*err.*Error\|strings\.Contains.*err"
```

```
Error assertions in test files: ___

String-based error checks (MUST FIX):
  - Contains(err.Error(), "..."): ___
    List with line numbers: ___
  - Equal(..., err.Error()): ___
    List: ___
  - strings.Contains(err.Error(), ...): ___
    List: ___

Correct error assertions found:
  - ErrorIs usage: ___
  - ErrorAs usage: ___

Missing sentinel errors in production code:
  - Errors returned with errors.New/fmt.Errorf inline that should be package-level sentinels: ___
    List: ___

VERDICT: [ ] PASS  [ ] FAIL --- issues documented above
```

**Error Assertion Rules:**
```go
// BAD --- fragile, breaks if message changes, doesn't handle wrapped errors
s.Require().Contains(err.Error(), "not found")
s.Require().Equal("user not found", err.Error())
s.Require().True(strings.Contains(err.Error(), "failed"))

// GOOD --- robust, handles error wrapping
s.Require().ErrorIs(err, ErrNotFound)
s.Require().ErrorAs(err, &validationErr)

// ACCEPTABLE (rare) --- only for external errors without sentinel
s.Require().ErrorContains(err, "connection refused")  // external library error
```

**Why string comparison is wrong:**
| Problem | Consequence |
|---------|-------------|
| Message changes break tests | Refactoring error text causes false failures |
| Doesn't handle wrapping | `fmt.Errorf("context: %w", err)` won't match |
| Not type-safe | Typos in expected string silently pass |
| Tests implementation | Error type is contract, message is detail |

### Checkpoint H: Export-for-Testing Anti-patterns

**Search for testing-related exports:**
```bash
# Find export_test.go files
git diff $DEFAULT_BRANCH...HEAD --name-only | grep "export_test.go"

# Find suspicious test helpers in production code
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | grep -v _test.go | xargs grep -n "TestHelper\|ForTest\|// exported for test\|// export for test"
```

```
export_test.go files found: ___
  - Justified (documented reason): ___
  - Unjustified (should test via public API): ___
  - Using ForTests suffix (required): YES/NO
    Missing ForTests suffix: ___

Suspicious exports for testing:
  - Functions with "Test" or "ForTest" in name: ___
  - Comments suggesting export for testing: ___
  - Public fields that seem test-only: ___

Split test files (FORBIDDEN):
  - Files named *_internal_test.go: ___
    List: ___

VERDICT: [ ] PASS  [ ] FAIL --- issues documented above
```

**Anti-patterns to Flag:**
```go
// FLAG: Exported just for tests (should be unexported, test via public API)
func ValidateInput(s string) error { ... }  // should be validateInput

// FLAG: Test helper in production code
func (s *Service) TestHelper_GetState() map[string]any { ... }

// FLAG: Field exported for test assertions
type Service struct {
    Cache map[string]any  // should be cache; test behaviour, not internals
}

// FLAG: Unjustified export_test.go
// file: export_test.go
var InternalFunc = internalFunc  // ask: why not test via public API?
```

**When export_test.go IS justified (rare):**
- Complex internal algorithm that genuinely needs direct testing
- Performance-critical internal function with specific edge cases
- Must document WHY public API testing is insufficient

### Checkpoint I: Security

> Uses three-tier severity model: **CRITICAL** (never acceptable), **GUARDED** (dev OK with guards), **CONTEXT** (needs judgment). See `security-patterns` skill for full reference.

**Search for security-sensitive patterns:**
```bash
# CRITICAL: SQL injection
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "fmt.Sprintf.*SELECT\|fmt.Sprintf.*INSERT\|fmt.Sprintf.*UPDATE\|fmt.Sprintf.*DELETE\|Query(.*+\|Exec(.*+"

# CRITICAL: Command injection
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "exec.Command\|os.StartProcess"

# CRITICAL: Timing-unsafe comparisons on secrets
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n '== .*token\|== .*secret\|== .*key\|== .*hash\|== .*password\|!= .*token'

# CRITICAL: math/rand in security context
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n '"math/rand"'

# CRITICAL: Sensitive data in logs
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "log.*password\|log.*token\|log.*secret\|log.*key\|log.*credential"

# CRITICAL: Hardcoded secrets
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "password.*=.*\"\|token.*=.*\"\|secret.*=.*\"\|apikey.*=.*\""

# CRITICAL: Weak hashing for security purposes
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n '"crypto/md5"\|"crypto/sha1"\|md5.New\|sha1.New'

# GUARDED: TLS skip / insecure transport
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "InsecureSkipVerify\|WithInsecure\|grpc.WithTransportCredentials(insecure"

# GUARDED: gRPC reflection (dev-only)
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "reflection.Register"

# GUARDED: text/template (no auto-escaping)
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n '"text/template"'

# CONTEXT: File path construction
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "filepath.Join.*\+\|os.Open.*\+\|ioutil.ReadFile.*\+"

# CONTEXT: HTTP redirect handling
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "http.Redirect\|w.Header().Set.*Location"

# CONTEXT: gRPC error leakage
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n 'fmt.Errorf.*grpc\|status.Errorf.*%v\|status.Errorf.*%s'
```

```
Security issues found: ___

CRITICAL --- automatic FAIL if found in any context:
  SQL Injection (string concat in queries):
    List with line numbers: ___
  Command Injection (user input in exec.Command / bash -c):
    List: ___
  Timing-unsafe comparison (== on token/secret/hash):
    List: ___
    FIX: use crypto/subtle.ConstantTimeCompare
  math/rand in security context:
    List: ___
    FIX: use crypto/rand
  Sensitive data in logs:
    List: ___
  Hardcoded secrets:
    List: ___
  Weak hashing for passwords/tokens (md5/sha1):
    List: ___
    FIX: use argon2id or bcrypt for passwords, sha256+ for integrity

GUARDED --- FAIL unless dev-only with proper guard:
  InsecureSkipVerify / grpc.WithInsecure():
    List: ___
    Guard check: [ ] build tag  [ ] config flag  [ ] env check
  gRPC reflection.Register:
    List: ___
    Guard check: [ ] build tag  [ ] config flag  [ ] env check
  text/template (no XSS auto-escaping):
    List: ___
    FIX: use html/template for user-facing output

  GUARDED check procedure:
    For each GUARDED finding:
    1. Is it in a _test.go file? -> OK
    2. Is it behind a build tag (//go:build dev)? -> OK
    3. Is it behind a config/env check? -> OK if env is validated
    4. None of the above? -> FLAG as unguarded, recommend isolation

CONTEXT --- needs judgment:
  Path traversal (user input in file paths):
    List: ___
    filepath.Clean + HasPrefix validation present: YES/NO
  HTTP redirect (open redirect risk):
    List: ___
    URL validated against allowlist: YES/NO
  SSRF (user-controlled URLs):
    List: ___
    Host allowlist present: YES/NO
  gRPC error leakage (internal details in status):
    List: ___
    FIX: use status.Error() not fmt.Errorf; sanitise before returning

Authentication/Authorization:
  - Auth checks before sensitive operations: ___
  - Missing auth middleware/interceptor: ___
    List: ___

VERDICT: [ ] PASS  [ ] FAIL --- issues documented above
```

**Security Rules:**

```go
// CRITICAL: SQL injection via string concatenation
query := "SELECT * FROM users WHERE id = '" + userID + "'"  // BAD
db.Query("SELECT * FROM users WHERE id = $1", userID)       // GOOD

// CRITICAL: Command injection
cmd := exec.Command("sh", "-c", "echo " + userInput)  // BAD
cmd := exec.Command("echo", userInput)                 // GOOD

// CRITICAL: Timing-unsafe comparison
if token == expectedToken {  // BAD --- timing side-channel
if subtle.ConstantTimeCompare([]byte(token), []byte(expectedToken)) == 1 {  // GOOD

// CRITICAL: Insecure random
import "math/rand"     // BAD for tokens/keys
import "crypto/rand"   // GOOD

// CONTEXT: Path traversal
filePath := filepath.Join(baseDir, userInput)  // BAD without validation
filePath := filepath.Join(baseDir, userInput)
if !strings.HasPrefix(filepath.Clean(filePath), filepath.Clean(baseDir)) {
    return errors.New("invalid path")  // GOOD
}

// CRITICAL: Logging sensitive data
log.Info().Str("password", password).Msg("user login")       // BAD
log.Info().Str("password", "[REDACTED]").Msg("user login")   // GOOD

// CONTEXT: SSRF
resp, _ := http.Get(userProvidedURL)         // BAD without allowlist
if !isAllowedHost(userProvidedURL) {         // GOOD
    return errors.New("URL not allowed")
}

// CONTEXT: gRPC error leakage
return fmt.Errorf("query failed: %v", err)                   // BAD --- leaks internals
return status.Error(codes.Internal, "operation failed")       // GOOD

// GUARDED: InsecureSkipVerify --- dev-only with guard
// BAD: no guard
tlsConfig := &tls.Config{InsecureSkipVerify: true}
// GOOD: guarded by config
if cfg.DevMode {
    tlsConfig = &tls.Config{InsecureSkipVerify: true}
}
```

### Checkpoint J: No Runtime Panics

**Search for panic usage in runtime code:**
```bash
# Find panic calls
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "panic("

# Find Must* function calls
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "Must[A-Z]\|must("

# Find direct type assertions (without comma-ok)
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "\.\([A-Za-z]*\)$"
```

```
Panic/Must usage found: ___

For EACH occurrence, verify location:
  File:Line | Location Type | VERDICT
  _________ | _____________ | _______
  (package-level var / init() = OK, runtime function = FAIL)

Direct type assertions without comma-ok:
  List with line numbers: ___
  All in init-time context: YES/NO
```

**Rules:**
- `panic()` and `Must*()` are ONLY acceptable in:
  - Package-level `var` declarations
  - `init()` functions
- **FORBIDDEN** in any runtime code (handlers, methods, functions called after startup)
- Type assertions must use comma-ok form in runtime code

```go
// ACCEPTABLE --- package-level, fails at startup
var config = must(LoadConfig("config.yaml"))

func init() {
    if err := validate(); err != nil {
        panic(err)  // OK: program hasn't started
    }
}

// FORBIDDEN --- runtime code
func (s *Service) Handle(req Request) error {
    cfg := must(parse(req.Data))  // WRONG: panics at runtime
    val := x.(string)             // WRONG: panics if wrong type
}

// REQUIRED --- runtime code returns errors
func (s *Service) Handle(req Request) error {
    cfg, err := parse(req.Data)
    if err != nil {
        return fmt.Errorf("parsing: %w", err)
    }
    val, ok := x.(string)
    if !ok {
        return errors.New("expected string")
    }
}
```

**VERDICT: [ ] PASS  [ ] FAIL --- runtime panics found**

### Checkpoint K: Scope Verification (Plan Contracts)

**If plan.md exists**, verify using structured contracts:

```bash
# Check if plan exists for this task
ls {PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md 2>/dev/null
```

**Step 1: Review Contract Verification**

Read the **Review Contract** section in plan.md. For EACH row, verify the implementation satisfies the pass criteria:

```
## Review Contract Compliance
| FR | AC | Implementation Evidence | PASS/FAIL |
|----|-----|----------------------|-----------|
| (fill from each Review Contract row) |
```

**Step 2: SE Verification Contract Check**

Read the **SE Verification Contract** section. Confirm the SE marked all rows as verified:

```
SE Verification Contract:
  - Rows marked verified: ___/___
  - Unverified rows: ___ (list)
  - Verdict: [ ] COMPLETE  [ ] INCOMPLETE
```

**Step 3: Assumption Register Check**

Read the **Assumption Register**. Flag any unresolved assumptions:

```
Unresolved assumptions:
  - A-__: ___ (Impact: ___)
  Verdict: [ ] ALL RESOLVED  [ ] UNRESOLVED --- flag to user
```

**Step 4: Test Mandate Coverage**

Read the **Test Mandate** section. Confirm each mandatory scenario has a corresponding test:

```
Test Mandate Coverage:
  - Mandatory scenarios: ___
  - Tests found: ___
  - Missing: ___ (list)
  Verdict: [ ] COVERED  [ ] GAPS --- flag to test writer
```

**Step 5: Scope Check (Plan vs Spec vs Implementation)**

```
Features implemented NOT in plan: ___
  SE additions --- classify each:
  | Addition | Category | Verdict |
  |----------|----------|---------|
  | Error wrapping | Production necessity | OK |
  | New endpoint | Product feature | FLAG |

Features in plan NOT implemented: ___
```

**Classification guide:**
- **Production necessity** (OK): Error handling, logging, timeouts, retries, input validation, resource cleanup
- **Product feature** (FLAG): New endpoints, new fields, new business logic, UI changes

```
VERDICT: [ ] PASS  [ ] FAIL --- contract compliance documented above
```

### Checkpoint L: AC Technical Feasibility

**For EACH acceptance criterion**, verify it describes a REAL problem that can actually occur.

**This prevents wasting time on theoretical issues that can't happen in the code.**

```bash
# Find ACs in the plan
grep -n "AC-\|acceptance\|must.*panic\|must.*recover\|resilient" {PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/plan.md {PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/spec.md 2>/dev/null
```

For each AC that claims a failure mode exists:

```
AC-__: "<Description of failure mode>"

1. What specific code would cause this failure?
   Location: _______________

2. Trace the code path:
   - Function called: _________
   - API used: _________
   - Does this API have this failure mode? (check Go docs)

3. Is this failure realistic?
   - [ ] YES --- traced to specific code that can fail this way -> VALID AC
   - [ ] NO --- the APIs used don't have this failure mode -> INVALID AC
   - [ ] THEORETICAL --- defence-in-depth only -> Downgrade to Consider
```

**Example Analysis:**
```
AC-47: "Panic in one linter doesn't crash entire command"

1. What code would panic?
   - runLinter() calls exec.CommandContext()

2. Trace code path:
   - exec.CommandContext returns ([]byte, error) --- does NOT panic
   - json.Marshal returns ([]byte, error) --- does NOT panic on simple structs
   - No realistic panic sources exist

3. Is this failure realistic?
   - [x] NO --- external process failures return error, not panic

Verdict: **INVALID AC** --- panics can't occur in this code path.
Action: Flag AC for removal or clarify as "defence against future bugs in our code"
```

**Language-specific terms in specs/plans are red flags:**
- "panic" --- Go-specific, often incorrectly applied
- "exception" --- Not a Go concept
- "thread" --- Go uses goroutines
- "retry with backoff" --- Implementation detail, not requirement

```
ACs verified as realistic: ___
ACs identified as unrealistic/theoretical: ___
  List with analysis: ___

VERDICT: [ ] PASS  [ ] FAIL --- unrealistic ACs flagged for discussion
```

### Checkpoint M: Test Scenario Completeness

**Tests exist does not mean tests are adequate. Verify tests cover the PROBLEM DOMAIN, not just what SE implemented.**

For each function with tests:

```
Function: _______________
Claim (from function name/docs): _______________

1. Problem domain scenarios (BEFORE looking at tests):
   - Scenario A: ___
   - Scenario B: ___
   - Scenario C: ___
   - ...

2. Which scenarios are tested?
   | Scenario | Has Test? | Test Location |
   |----------|-----------|---------------|
   | A        | YES/NO    | file:line     |
   | B        | YES/NO    |               |
   | ...      |           |               |

3. Missing scenarios (CRITICAL GAPS):
   - _______________
```

**For filesystem operations specifically:**
| Entry Type | Tested? | If NO, flag as gap |
|------------|---------|-------------------|
| Regular files | | |
| Empty directories | | |
| **Non-empty directories** | | **Most commonly missed** |
| Symbolic links | | |
| Nested structures | | |

**Common scenario gaps to check:**
- SE assumes "directory contains files" -> Tester should test directories, symlinks
- SE assumes "API returns valid JSON" -> Tester should test malformed, empty, huge responses
- SE assumes "IDs are non-empty" -> Tester should test empty, whitespace, very long IDs

```
Functions with test coverage gaps: ___
  List gaps by function: ___

VERDICT: [ ] PASS  [ ] FAIL --- scenario gaps documented above
```

### Checkpoint N: Comment Quality (BLOCKING)

**Search for narration comments:**
```bash
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "// [A-Z][a-z].*the\|// Check\|// Verify\|// Create\|// Start\|// Get\|// Set\|// If\|// When\|// First\|// Then\|// Loop\|// Return\|// ---\|// ==="
```

**Search for doc comments on unexported functions:**
```bash
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n -B1 "^func [a-z]\|^func (.*) [a-z]" | grep "//"
```

**Search for doc comments on business logic (services, handlers):**
```bash
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | grep -v _test.go | xargs grep -n "^// \w\+\s" | grep -i "service\|handler\|controller\|repository"
```

```
Inline comment violations (MUST FIX --- blocking):
  - Step-by-step narration ("Check if...", "If we're the last..."): ___
    List with line numbers: ___
  - Obvious assertions ("Verify X is stored", "Create new Y"): ___
    List: ___
  - Section dividers ("// --- Tests ---", "// ====="): ___
    List: ___

Doc comment violations (MUST FIX --- blocking):
  - Doc comments on unexported functions: ___
    List: ___
  - Doc comments on business logic (services, handlers): ___
    List: ___
  - Implementation details in library doc comments (refCount, internal flags): ___
    List: ___
  - Caller references ("Used by X"): ___
    List: ___

Acceptable comments found:
  - WHY explanations (business rules, constraints): ___
  - External references (RFCs, issue numbers): ___
  - Contract-only doc comments on library exports: ___

VERDICT: [ ] PASS  [ ] FAIL --- comment violations are blocking issues
```

**Rules:**
```go
// FORBIDDEN --- narration inline comment
// Check if doomed AFTER decrementing
// If we're the last reference, abort and end session

// FORBIDDEN --- doc comment on unexported
// getClient returns the MongoDB client for internal use.
func (c *Client) getClient(ctx context.Context) (*mongo.Client, error) {

// FORBIDDEN --- doc comment on business logic
// ProcessOrder processes an order by validating items.
func (s *OrderService) ProcessOrder(ctx context.Context, order *Order) error {

// FORBIDDEN --- implementation details in library doc
// Commit commits. If refCount > 1, waits. If refCount == 0, commits.
func (h *TxHandle) Commit(ctx context.Context) error {

// ACCEPTABLE --- contract-only library doc
// Commit commits the transaction. Returns ErrTransactionDoomed if doomed.
func (h *TxHandle) Commit(ctx context.Context) error {
```

### Checkpoint O: Complexity Review (see `philosophy` skill - Prime Directive)

**Apply Occam's Razor --- code should reduce complexity, not increase it.**

```
Unnecessary abstractions:
  - Interfaces with only one implementation (not for testing): ___
    List: ___
  - Factory/builder for simple object construction: ___
    List: ___
  - Wrapper types that add no value: ___
    List: ___

Premature generalisation:
  - Generic solutions for single use case: ___
    List: ___
  - Configuration for things that never change: ___
    List: ___
  - "Flexible" code paths never exercised: ___
    List: ___

Cognitive load issues:
  - Clever code that requires explanation: ___
    List: ___
  - Deep nesting (>3 levels): ___
    List: ___
  - Functions doing multiple unrelated things: ___
    List: ___

Reversal test failures (would removing this improve the system?):
  - Files that could be deleted: ___
  - Functions that could be inlined: ___
  - Abstractions that could be removed: ___

VERDICT: [ ] PASS  [ ] FAIL --- complexity issues documented above
```

### Checkpoint P: Log Message Quality

**Search for log statements:**
```bash
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | grep -v _test.go | xargs grep -n "\.Info()\|\.Error()\|\.Warn()\|\.Debug()\|\.Trace()"
```

For EACH log statement, verify:

```
| Line | File | Has Entity ID? | Has .Err()? | Message Specific? | Verified |
|------|------|----------------|-------------|-------------------|----------|
| 45   | service.go | YES (order_id) | YES | YES | pass |
| 67   | handler.go | NO | N/A | NO ("error occurred") | fail |
```

**Checklist:**
- [ ] Error logs include `.Err(err)` before `.Msg()`?
- [ ] Logs include relevant entity IDs via `.Str("<entity>_id", ...)`?
- [ ] Message is specific (not "operation failed", "error occurred", "HTTP exception")?
- [ ] Message uses lowercase start (Go convention)?
- [ ] No duplicate messages in same function?
- [ ] Stack trace included for errors? `.Stack().Err(err)`

**Common Violations:**

```go
// Missing .Err()
logger.Error().Msg("operation failed")  // No error object!

// Missing entity ID
logger.Error().Err(err).Msg("payment failed")  // Which payment?

// Vague message
logger.Error().Err(err).Msg("HTTP exception occurred")  // What? Where?

// Missing context
logger.Info().Msg("task started")  // Which task?

// Capitalized message (Go convention: lowercase)
logger.Info().Msg("Processing order")  // Should be "processing order"
```

```
Error logs without .Err(): ___
  List: ___
Logs missing entity IDs: ___
  List: ___
Vague/generic messages: ___
  List: ___
Duplicate messages in same function: ___
  List: ___

VERDICT: [ ] PASS  [ ] FAIL --- logging issues documented above
```

### Checkpoint Q: SE Self-Review Verification

**Check if SE completed pre-handoff self-review items:**

```
SE Self-Review items SE should have verified:
- [ ] Plan's Implementation Checklist completed?
- [ ] Error context wrapping verified?
- [ ] Formatting tools run (goimports)?
- [ ] Log messages have entity IDs?
- [ ] No narration comments?
- [ ] Production necessities (timeouts, retries, validation)?

Items SE should have caught themselves (from their checklist):
  - [ ] ___
  - [ ] ___

SE missed items from their checklist: ___
```

**Note**: If SE consistently misses self-review items, flag this pattern. The goal is to shift verification left --- catch issues during implementation, not review.

```
VERDICT: [ ] PASS  [ ] FAIL --- SE should have caught these in self-review
```

---

## Go-Specific Issues (Report Template Section)

Use this template section within the review report:

```
## Go-Specific Issues
### Error Handling
- [ ] file.go:42 - Error ignored on line X
- [ ] file.go:87 - Missing error context

### Concurrency
- [ ] worker.go:23 - Possible goroutine leak

### Nil Safety
- [ ] service.go:15 - Nil check missing

### Architecture (see `go-architecture` skill)
- [ ] service/interfaces.go - Interfaces in separate file (move to consumer)
- [ ] internal/service/user.go - Imposes layer-based structure on feature-based codebase
- [ ] internal/user/user_service.go - Uses layer suffix when codebase uses direct names
- [ ] user.go:25 - Unnecessary struct separation (UserDTO has same fields as User, use one struct with tags)
- [ ] service.go:40 - Constructor arg order wrong (logger before deps)
- [ ] user.go:10 - Raw string for UserID with confusion risk (multiple ID types, should be typed)
- [ ] config.go:5 - Typed wrapper for single-purpose string (unnecessary, no confusion risk)
- [ ] user_test.go:1 - Test skipped "requires MongoDB" (should mock)

### API Surface (Over-exported)
- [ ] client.go:15 - Struct fields exported (BaseURL, HTTPClient should be unexported)
- [ ] utils.go:30 - Helper function exported (buildKey should be unexported)
- [ ] types.go:10 - Internal type exported (validationResult should be unexported)
- [ ] repo.go:5 - Interface exported but only used within package (should be unexported)

### Test Error Assertions
- [ ] user_test.go:45 - String comparison: `Contains(err.Error(), "not found")` -> use `ErrorIs`
- [ ] service_test.go:78 - Missing sentinel error in production code for testability

### Export-for-Testing
- [ ] export_test.go - Unjustified export (test via public API instead)
- [ ] service.go:20 - Field exported for test assertions (Cache should be cache)

### Security
- [ ] handler.go:45 - SQL injection: string concatenation in query
- [ ] service.go:78 - Path traversal: user input in filepath without validation
- [ ] client.go:23 - SSRF: user-controlled URL without allowlist
- [ ] auth.go:56 - Sensitive data logged (password field)
- [ ] config.go:12 - Hardcoded secret (API key in source)

### Distributed Systems
- [ ] client.go:30 - HTTP call without timeout
- [ ] service.go:55 - Wrong transaction pattern (data fetch inside tx, should be before)
- [ ] service.go:78 - Reliable side effect without outbox (email must use outbox)
- [ ] api.go:92 - Missing retry for idempotent operation

## Test Review
### Coverage Gaps
- [ ] handler.go:GetUser - No test for empty ID
- [ ] service.go:Process - Error path not tested

### Test Quality Issues
- [ ] handler_test.go:45 - Weak assertion (NotNil instead of Equal)
- [ ] service_test.go:89 - Test copies implementation logic

## Logic Review
### <function name>
- **Intent**: <what it should do per ticket>
- **Implementation**: <what it actually does>
- **Issues**: <any logical errors found>

## Backward Compatibility
### Breaking Changes
- [ ] api.go:GetUser - Signature changed without wrapper migration

### Deprecation Process
- [ ] Branch 1 (mark deprecated): YES/NO
- [ ] Branch 2 (remove usages): YES/NO
- [ ] Branch 3 (remove code): YES/NO

## Formatting Issues
- [ ] file.go - Not formatted with goimports
- [ ] file.go:23 - Wrong comment spacing (need one space before/after //)

## Questions for Developer
1. <specific question about ambiguous logic>
2. <verification question about edge case>
```

---

## What to Look For

**High-Priority (Unnecessary Complexity --- see `philosophy` skill)**
Apply the Prime Directive --- code should reduce complexity, not increase it:
- Interfaces with only one implementation (not needed for mocking)
- Factory patterns for simple object construction
- Generic solutions where specific would suffice
- Configuration for values that never change
- Wrapper/adapter types that add no value
- Deep nesting (>3 levels of indentation)
- Functions doing multiple unrelated things
- Clever code that requires mental gymnastics to understand

**High-Priority (Logging Quality)**
- Error logs without `.Err(err)` (missing error object)
- Logs without entity identifiers (order_id, user_id, etc.)
- Vague messages: "error occurred", "operation failed", "HTTP exception"
- Duplicate messages in same function (can't identify which branch failed)
- Capitalized messages (Go convention: lowercase start)
- Missing `.Stack()` on error logs

**High-Priority (Compile-Time Safety)**
Prefer compilation errors over runtime errors:
- Raw `string` for IDs instead of typed IDs (`type UserID string`)
- `interface{}` used (use `any` if absolutely necessary, prefer concrete types)
- Missing interface compliance check (`var _ Interface = (*Type)(nil)`)
- Positional struct literals instead of named fields
- `runtime.GOOS` checks instead of build tags
- `default` case hiding missing enum variants (use `exhaustive` linter)
- Unchecked type assertions (`x.(T)` without comma-ok)
- `var` for values that should be `const`

**High-Priority (API Surface)**
Keep exports minimal --- unexport by default:
- Struct fields exported when they should be private (use getters if needed)
- Helper functions exported unnecessarily (only used within package)
- Internal/intermediate types exported (implementation details)
- Interfaces exported but only used within the package
- Code exported just to make testing easier (anti-pattern)
- Multiple public constructors (should be single entry point)

**High-Priority (Object Design)**
- Exported fields on types with invariant-dependent methods (should unexport fields)
- Types mixing semantically different responsibilities (should split)
- Domain objects without behaviour (should have methods, not external functions operating on data)

**High-Priority (Go-Specific)**
- Unchecked errors
- Nil pointer dereferences
- Goroutine leaks
- Race conditions
- Unchecked type assertions (use comma-ok form)
- **Mixed pointer/value receivers on same type (CRITICAL)** --- see Checkpoint E.5

**High-Priority (Distributed Systems)**
- HTTP calls without context/timeout
- Wrong transaction pattern for external calls:
  - Data fetch inside transaction (should be BEFORE)
  - Reliable side effect after commit without outbox (should use outbox)
  - Outbox insert outside transaction (should be IN transaction)
  - Complex saga without durable workflow (should use Temporal)
- Missing retries for idempotent HTTP operations (must implement retry with backoff)
- Unbounded response body reads (must use `io.LimitReader`)
- Missing idempotency keys for non-idempotent operations

**High-Priority (Security)**
- SQL injection: string concatenation or fmt.Sprintf in queries (use parameterized queries)
- Command injection: user input in exec.Command arguments (pass args separately, avoid shell)
- Path traversal: user input in file paths without validation (use filepath.Clean + prefix check)
- SSRF: user-controlled URLs without allowlist validation
- Sensitive data in logs: passwords, tokens, secrets, API keys
- Hardcoded secrets in source code (use environment variables or secret manager)
- Missing authentication/authorization checks on sensitive endpoints

**High-Priority (Logic Errors)**
- Inverted boolean conditions
- Wrong comparison operators
- Missing or extra states in status checks

**High-Priority (Test Gaps)**
- Missing tests for error paths
- Tests that copy implementation logic
- Missing edge case coverage (nil, empty, boundary values)
- Concurrent code without race detector tests

**High-Priority (Test Quality --- Error Assertions)**
- String-based error comparison (`Contains(err.Error(), ...)`, `Equal(..., err.Error())`)
- Missing `ErrorIs`/`ErrorAs` usage for error checking
- Missing sentinel errors in production code (inline `errors.New` that should be package-level)
- `ErrorContains` used when sentinel error should exist

**High-Priority (Test Infrastructure)**
- Split test files (`*_internal_test.go` pattern --- forbidden)
- Missing `ForTests` suffix on exports in `export_test.go`
- Mock data used where code validates/parses (certificates, URLs, JSON need realistic data)
- Missing helper methods for complex test object construction

**High-Priority (Backward Compatibility)**
- Function signature changes without wrapper migration
- Deprecation and removal in same branch
- Missing tests for deprecated functions
- Breaking changes to exported types/constants

**High-Priority (Scope Violations)**
- Plan contains features NOT in spec (planner added "nice to have")
- Implementation contains features NOT in plan (SE added product features)
- SE additions that are product features disguised as "production necessities"
- Missing features from spec that should be in plan
- Missing features from plan that should be in implementation

**Medium-Priority (Requirement Gaps)**
- Acceptance criteria not implemented
- Implemented behaviour differs from ticket
- Missing error handling mentioned in ticket

**High-Priority (Comment Quality --- BLOCKING)**
- Narration comments describing code flow ("Check if doomed", "If we're the last reference", "Verify X is stored")
- Step-by-step pseudocode comments ("First get user, then validate, then save")
- Section divider comments ("// --- Tests ---", "// ======")
- Obvious assertions in tests ("// Start first transaction", "// Create nested transaction")
- Doc comments on unexported functions (`// getClient returns...`)
- Doc comments on business logic (services, handlers, domain) --- names are documentation
- Implementation details in library doc comments (refCount, internal flags, step-by-step behavior)
- Caller references in doc comments ("Used by X" --- becomes stale)

**Medium-Priority (Formatting)**
- Code not formatted with `goimports -local <module-name>`
- Wrong comment spacing (must be `code // comment`)
