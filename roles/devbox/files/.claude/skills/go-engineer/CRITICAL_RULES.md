# Go Critical Rules - Quick Reference

## 🚨 Rule 1: Nil Pointer Returns

**Can return nil? → MUST return error.**

### ❌ FORBIDDEN

```go
func Parse(data []byte) *Config {
    if len(data) == 0 {
        return nil  // Caller can't handle this
    }
    return &Config{...}
}
```

### ✅ REQUIRED

```go
func Parse(data []byte) (*Config, error) {
    if len(data) == 0 {
        return nil, errors.New("empty data")
    }
    return &Config{...}, nil
}
```

### Why?

Caller needs context:

```go
// Without error - ambiguous
result := Parse(data)
if result == nil {
    // Is this a bug? Empty input? Can't tell!
}

// With error - explicit
result, err := Parse(data)
if err != nil {
    log.Warn().Err(err).Msg("skipping")
    continue  // Clear intent
}
```

---

## 🚨 Rule 2: Receiver Consistency

**One pointer method? → ALL methods pointer.**

### ❌ FORBIDDEN

```go
type Cache struct {
    items map[string]any
    mu    sync.RWMutex
}

func (c *Cache) Set(k, v any) { }    // pointer
func (c Cache) Get(k string) any { } // value - WRONG!
```

### ✅ REQUIRED

```go
func (c *Cache) Set(k, v any) { }    // pointer
func (c *Cache) Get(k string) any { } // pointer - consistent!
```

### Why?

1. **Race conditions** with mutexes:
   ```go
   func (c Cache) Get(k string) any {
       c.mu.RLock()  // Locks a COPY!
       defer c.mu.RUnlock()
       return c.items[k]  // Race condition
   }
   ```

2. **Interface satisfaction**:
   ```go
   var h Handler = Cache{}   // Fails
   var h Handler = &Cache{}  // OK
   ```

---

## Decision Trees

### Nil Pointers

```
Can function return nil pointer?
├─ YES → (*T, error) — ALWAYS
└─ NO  → *T or (*T, error) based on fallibility
```

### Receivers

```
Does type have ANY pointer receiver method?
├─ YES → All methods pointer
└─ NO  → Can use value (if type is small & immutable)
```

---

## Exceptions

### Nil Pointers: Getter Methods Only

```go
type Container struct {
    current *Item
}

// OK - simple getter, nil is valid state
func (c *Container) Current() *Item {
    return c.current
}

// NOT OK - has logic → needs error
func (c *Container) CurrentProcessed() (*ProcessedItem, error) {
    if c.current == nil {
        return nil, errors.New("no current item")
    }
    return c.current.Process()
}
```

### Receivers: Small Immutable Types Only

```go
type Point struct { X, Y int }

// OK - all value receivers (no state change, small type)
func (p Point) Add(other Point) Point { }
func (p Point) Distance() float64 { }

// NOT OK if you add any pointer method
func (p *Point) Move(dx, dy int) {  // Now pointer
    p.X += dx
    // ALL other methods must be pointer now!
}
```

---

## Red Flags

🚨 **STOP coding if you see:**

1. `func Something() *Type` with no `error`
2. `func (t Type) ...` mixed with `func (t *Type) ...`
3. `return nil` without accompanying error

---

## Validation

```bash
# Run before committing
./skills/go-engineer/validate_code.sh

# Or install as git hook
ln -s ../../skills/go-engineer/validate_code.sh .git/hooks/pre-commit
```

---

## Common Patterns

### Parsing

```go
func Parse(input []byte) (*Config, error)        // ✅
func Decode(raw string) (*Message, error)        // ✅
func Transform(in *Input) (*Output, error)       // ✅
```

### Database

```go
func FindByID(ctx context.Context, id string) (*User, error) {
    // ...
    if errors.Is(err, sql.ErrNoRows) {
        return nil, ErrNotFound  // ✅ nil with error
    }
    return user, nil
}
```

### Constructors

```go
func NewClient(cfg Config) (*Client, error)      // ✅ validates
func NewCache() *Cache                           // ✅ never nil
```

### Services

```go
type Service struct { mu sync.Mutex, db *sql.DB }

func (s *Service) Process() error        // ✅ all pointer
func (s *Service) Status() string        // ✅ all pointer
func (s *Service) Close() error          // ✅ all pointer
```

---

## When In Doubt

1. **Can return nil?** → Add `error` return
2. **One pointer method?** → Make all methods pointer
3. **Not sure?** → Prefer `(*T, error)` and pointer receivers

**Err on the side of explicitness.**
