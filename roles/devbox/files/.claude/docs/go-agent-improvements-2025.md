# Go Agent Improvements - 2025

## Summary

Critical improvements to Go software engineer agent and skills to enforce production code quality standards.

**Date:** 2025-12-30
**Impact:** High - Prevents production bugs from silent nil returns and race conditions

---

## Problems Identified

### 1. Nil Pointer Returns Without Error

**Issue:** Agent was generating functions that return `*T` without `error`, leading to silent failures.

```go
// ❌ Agent might generate this
func nodeFromK8s(n *corev1.Node, clusterName ClusterName) *Node {
    if n == nil {
        return nil  // Silent nil - caller can't handle properly
    }
    return &Node{...}
}

// Caller code is ambiguous:
node := nodeFromK8s(k8sNode, cluster)
if node == nil {
    // Is this an error? Expected? How to log?
    continue  // Silent skip - might hide bugs
}
```

**Root Cause:** No explicit guidance on when to return error with pointer types.

---

### 2. Inconsistent Receiver Types (Pointer vs Value)

**Issue:** Agent was mixing pointer and value receivers on the same type, causing race conditions and interface satisfaction issues.

```go
// ❌ Agent might generate this
type Client struct {
    mu    sync.Mutex
    state string
}

func (c *Client) Connect() error { }     // pointer
func (c Client) Status() string { }      // value - WRONG!
func (c *Client) Close() error { }       // pointer

// Problem 1: Race condition
func (c Client) Status() string {
    c.mu.Lock()  // Locks a COPY of the mutex!
    defer c.mu.Unlock()
    return c.state  // Race!
}

// Problem 2: Interface satisfaction
var h Handler = Client{}   // Fails - value only has Status()
var h Handler = &Client{}  // OK - pointer has all methods
```

**Root Cause:** Only receiver **name** consistency was enforced, not receiver **type** consistency.

---

## Solutions Implemented

### 1. Nil Pointer Returns Rule

**Added to:** `skills/go-errors/SKILL.md`

**Strict Rule:** Any function that can return a nil pointer MUST return error.

**No exceptions.** Even if nil is "expected" for certain inputs, caller needs explicit error to handle it properly.

```go
// ✅ Correct pattern
func ParseData(input []byte) (*Result, error) {
    if len(input) == 0 {
        return nil, errors.New("empty input")
    }
    return &Result{...}, nil
}

// Caller can now handle explicitly:
result, err := ParseData(data)
if err != nil {
    log.Warn().Err(err).Msg("skipping invalid data")
    continue  // Explicit choice with context
}
```

**Decision tree:**
- Can return nil → `(*T, error)` — ALWAYS
- Never returns nil, can't fail → `*T`
- Never returns nil, can fail → `(*T, error)`

**Edge case:** Getter methods returning internal state fields can return `*T` without error:

```go
type Container struct {
    current *Item
}

// OK - getter returning field (nil is valid state)
func (c *Container) Current() *Item {
    return c.current
}

// But if there's logic/transformation → return error
func (c *Container) CurrentProcessed() (*ProcessedItem, error) {
    if c.current == nil {
        return nil, errors.New("no current item")
    }
    return c.current.Process()
}
```

---

### 2. Receiver Type Consistency Rule

**Added to:** `skills/go-style/SKILL.md`

**Critical Rule:** If ANY method uses pointer receiver, ALL methods must use pointer receiver.

```go
// ✅ Correct pattern
type Cache struct {
    items map[string]any
    mu    sync.RWMutex
}

func (c *Cache) Set(key string, val any) {     // pointer
    c.mu.Lock()
    defer c.mu.Unlock()
    c.items[key] = val
}

func (c *Cache) Get(key string) (any, bool) {  // pointer (consistent!)
    c.mu.RLock()
    defer c.mu.RUnlock()
    val, ok := c.items[key]
    return val, ok
}
```

**Decision tree:**
- Method modifies receiver → ✅ Pointer
- Type has ANY pointer receiver method → ✅ All pointer (consistency)
- Type is large (>64 bytes) → ✅ Pointer
- Type has mutex/sync fields → ✅ Pointer (required)
- All methods read-only AND type is small → Value is OK

**Once pointer for ONE method → pointer for ALL methods.**

---

## Files Modified

### 1. `skills/go-errors/SKILL.md`

**Added section:** "Nil Pointer Returns" (after "Double Wrapping")

- Strict rule: can return nil → must return error
- Why error is mandatory (caller needs context)
- Decision tree with no exceptions
- Common cases (parsing, DB queries, constructors)
- Anti-patterns to avoid
- Edge case: getter methods

**Added to "Common Mistakes":** "Returning Nil Pointer Without Error" (first item)

---

### 2. `skills/go-style/SKILL.md`

**Added section:** "Receiver Type Consistency" (after "Receiver Names")

- Critical rule: one pointer → all pointers
- Decision tree for receiver types
- Why it matters (race conditions, method sets)
- Real-world examples (Cache with mutex)
- Correct pattern for small immutable types

**Updated "Quick Reference":** Added violation for mixed receivers

---

### 3. `skills/go-engineer/SKILL.md`

**Added section:** "Critical Rules (Zero Tolerance)" (before "Error Handling")

- Nil pointer returns → must return error (with examples)
- Receiver consistency → one pointer = all pointers (with examples)
- Front-and-center visibility for most critical rules

---

### 4. Validation Assets Created

**`skills/go-engineer/validation_tests.md`**
- Comprehensive test scenarios for both rules
- Test cases for parsers, conversions, DB queries, services
- Red flags checklist
- Expected vs forbidden patterns

**`skills/go-engineer/validate_code.sh`**
- Automated validation script (git pre-commit hook compatible)
- Checks for functions returning pointer without error
- Detects mixed receiver types on same type
- Flags obvious nil returns without error context

---

## Impact

### Before

```go
// Agent could generate:
func ConvertRecord(r *Record) *Result {
    if r == nil { return nil }  // Silent nil
    return &Result{...}
}

type Service struct { mu sync.Mutex }
func (s *Service) Start() { }        // pointer
func (s Service) Status() string { } // value - race!
```

### After

```go
// Agent now generates:
func ConvertRecord(r *Record) (*Result, error) {
    if r == nil {
        return nil, errors.New("record is nil")
    }
    return &Result{...}, nil
}

type Service struct { mu sync.Mutex }
func (s *Service) Start() { }        // pointer
func (s *Service) Status() string { } // pointer - consistent!
```

---

## Validation

### Manual Testing

Use test scenarios in `validation_tests.md`:

```bash
# Present prompts to agent, verify:
1. Functions returning pointers include error
2. All methods use consistent receiver types
3. Nil cases return (nil, error) not just nil
```

### Automated Validation

```bash
# Run validation script (can be used as pre-commit hook)
./skills/go-engineer/validate_code.sh

# Or install as git hook:
ln -s ../../skills/go-engineer/validate_code.sh .git/hooks/pre-commit
```

---

## Examples Domain-Agnostic

All examples use generic domain concepts:
- `ParseData`, `ConvertRecord`, `TransformItem`
- `Cache`, `Connection`, `Service`, `Container`
- `User`, `Config`, `Item`, `Record`

No Kubernetes, AWS, or other specific domain knowledge required.

---

## Key Takeaways

1. **Zero tolerance for nil pointer without error**
   - Caller always needs context to handle nil properly
   - Even "expected" nil is an error condition
   - Exception: Simple getter methods returning internal fields

2. **Zero tolerance for mixed receivers**
   - One pointer method → all pointer methods
   - Prevents race conditions with mutexes
   - Ensures consistent interface satisfaction
   - Exception: Small immutable types with all value receivers

3. **Front-and-center enforcement**
   - Added to go-engineer as "Critical Rules"
   - Added to error handling as "Common Mistakes"
   - Added validation tests and scripts
   - Updated quick reference guides

---

## Maintenance

These rules should be:
1. **Non-negotiable** - enforce in code reviews
2. **Tested regularly** - run validation tests on agent outputs
3. **Kept visible** - "Critical Rules" section stays at top
4. **Used as examples** - reference in PR reviews when violations occur

---

## Related References

- [Effective Go - Pointers vs Values](https://go.dev/doc/effective_go#pointers_vs_values)
- [Go Code Review Comments - Receiver Type](https://go.dev/wiki/CodeReviewComments#receiver-type)
- [Go FAQ - When should I use a pointer to an interface?](https://go.dev/doc/faq#nil_error)
