# Go Agent Validation Tests

This file contains test scenarios to verify the Go software engineer agent follows critical rules.

## Test 1: Nil Pointer Returns Must Have Error

### Test Case 1.1: Parser Function

**Prompt:**
```
Write a Go function that parses a JSON config file and returns a Config pointer.
Handle the case where the input is empty.
```

**Expected Signature:**
```go
func ParseConfig(data []byte) (*Config, error)
```

**Must NOT generate:**
```go
func ParseConfig(data []byte) *Config  // ❌ WRONG - can return nil without error
```

**Validation:**
- ✅ Function signature includes `error` return
- ✅ Empty input returns `(nil, error)` not just `nil`
- ✅ Success case returns `(config, nil)`

---

### Test Case 1.2: Conversion Function

**Prompt:**
```
Write a Go function that converts an external record to an internal format.
Handle nil input appropriately.
```

**Expected Signature:**
```go
func ConvertRecord(ext *ExternalRecord) (*InternalRecord, error)
```

**Must NOT generate:**
```go
func ConvertRecord(ext *ExternalRecord) *InternalRecord  // ❌ WRONG
```

**Validation:**
- ✅ Function signature includes `error` return
- ✅ Nil input returns `(nil, errors.New("input is nil"))`
- ✅ Caller can handle error explicitly

---

### Test Case 1.3: Database Query

**Prompt:**
```
Write a Go function that fetches a user by ID from a database.
Return nil if the user is not found.
```

**Expected Signature:**
```go
func FindUserByID(ctx context.Context, id string) (*User, error)
```

**Expected Implementation:**
```go
if errors.Is(err, sql.ErrNoRows) {
    return nil, ErrUserNotFound  // ✅ nil with error
}
```

**Must NOT generate:**
```go
func FindUserByID(ctx context.Context, id string) *User  // ❌ WRONG
if errors.Is(err, sql.ErrNoRows) {
    return nil  // ❌ WRONG - silent nil
}
```

**Validation:**
- ✅ Returns `(*User, error)` not `*User`
- ✅ Not found case returns `(nil, ErrNotFound)` not just `nil`
- ✅ Caller can distinguish "not found" from other errors

---

## Test 2: Receiver Type Consistency

### Test Case 2.1: Service with State

**Prompt:**
```
Write a Go type called Cache with these methods:
- Set(key, value) to store data
- Get(key) to retrieve data
- Clear() to remove all data
```

**Expected:**
```go
type Cache struct {
    items map[string]any
    mu    sync.RWMutex
}

func (c *Cache) Set(key string, val any) {  // pointer
    // ...
}

func (c *Cache) Get(key string) (any, bool) {  // pointer (consistent!)
    // ...
}

func (c *Cache) Clear() {  // pointer (consistent!)
    // ...
}
```

**Must NOT generate:**
```go
func (c *Cache) Set(key string, val any) {  // pointer
    // ...
}

func (c Cache) Get(key string) (any, bool) {  // ❌ WRONG - value receiver
    // ...
}
```

**Validation:**
- ✅ ALL methods use pointer receiver
- ✅ No mixing of `(c *Cache)` and `(c Cache)`
- ✅ If type has mutex, ALL methods are pointer receivers

---

### Test Case 2.2: Type with Modifying Method

**Prompt:**
```
Write a Go type called Connection with:
- Open() to establish connection
- Address() getter to return the address
- Close() to close connection
```

**Expected:**
```go
type Connection struct {
    addr   string
    client *net.Conn
}

func (c *Connection) Open() error {     // pointer (modifies state)
    // ...
}

func (c *Connection) Address() string { // pointer (consistency!)
    return c.addr
}

func (c *Connection) Close() error {    // pointer (consistency!)
    // ...
}
```

**Must NOT generate:**
```go
func (c *Connection) Open() error {     // pointer
    // ...
}

func (c Connection) Address() string {  // ❌ WRONG - value receiver
    return c.addr
}
```

**Validation:**
- ✅ Since `Open()` and `Close()` modify state → pointer receiver
- ✅ Therefore `Address()` MUST also use pointer receiver (consistency)
- ✅ No "optimization" for read-only methods with value receivers

---

### Test Case 2.3: Small Immutable Type

**Prompt:**
```
Write a Go type called Point with X and Y coordinates.
Add methods to calculate distance from origin and add two points.
```

**Expected (all value receivers OK):**
```go
type Point struct {
    X, Y int
}

func (p Point) Distance() float64 {  // value (immutable, small)
    return math.Sqrt(float64(p.X*p.X + p.Y*p.Y))
}

func (p Point) Add(other Point) Point {  // value (immutable, small)
    return Point{X: p.X + other.X, Y: p.Y + other.Y}
}
```

**Validation:**
- ✅ All methods use value receivers (type is small and immutable)
- ✅ No methods modify the receiver
- ✅ Type has no mutexes or large fields

---

## Test 3: Combined Validation

### Test Case 3.1: Real-World Service

**Prompt:**
```
Write a Go service called UserService with:
- FetchUser(id) that queries a database and returns a user pointer
- UpdateUser(user) that saves user data
- GetCachedUser(id) that returns cached user or nil if not cached
```

**Expected:**
```go
type UserService struct {
    db    *sql.DB
    cache *Cache
}

// ✅ Can return nil → must return error
func (s *UserService) FetchUser(ctx context.Context, id string) (*User, error) {
    // ...
    if errors.Is(err, sql.ErrNoRows) {
        return nil, ErrUserNotFound  // ✅ nil with error
    }
    return user, nil
}

// ✅ Pointer receiver (consistency - UpdateUser modifies state)
func (s *UserService) UpdateUser(ctx context.Context, user *User) error {
    // ...
}

// ✅ Pointer receiver (consistency)
// ✅ Can return nil → must return error
func (s *UserService) GetCachedUser(id string) (*User, error) {
    user, ok := s.cache.Get(id)
    if !ok {
        return nil, ErrNotInCache  // ✅ nil with error
    }
    return user.(*User), nil
}
```

**Must NOT generate:**
```go
// ❌ WRONG - returns *User without error
func (s *UserService) FetchUser(ctx context.Context, id string) *User

// ❌ WRONG - value receiver on getter, pointer on modifier
func (s UserService) GetCachedUser(id string) (*User, error)
func (s *UserService) UpdateUser(ctx context.Context, user *User) error
```

**Validation:**
- ✅ All pointer-returning methods include `error` return
- ✅ All methods use same receiver type (all pointer)
- ✅ Nil cases return `(nil, error)` not just `nil`

---

## Running Validation

### Manual Test Process

1. Present each prompt to the Go software engineer agent
2. Verify generated code matches "Expected" patterns
3. Confirm NO code matches "Must NOT generate" patterns
4. Check all validation points pass

### Automated Test (Future)

```bash
# Run validation suite
./scripts/validate_go_agent.sh

# Expected output:
# ✅ Test 1.1: Nil pointer returns - PASS
# ✅ Test 1.2: Conversion functions - PASS
# ✅ Test 2.1: Receiver consistency - PASS
# ✅ Test 2.2: Mixed receivers - PASS
# ✅ Test 3.1: Combined validation - PASS
```

---

## Red Flags (Agent Violations)

### 🚨 Critical Violations

1. **Function returning `*T` that can return nil** without `error` return
   ```go
   func Parse(data []byte) *Config  // 🚨 RED FLAG
   ```

2. **Mixed pointer/value receivers on same type**
   ```go
   func (c *Cache) Set(k, v any) { }  // pointer
   func (c Cache) Get(k string) any   // 🚨 RED FLAG - value receiver
   ```

3. **Returning `nil` without error context**
   ```go
   if input == nil {
       return nil  // 🚨 RED FLAG - no error
   }
   ```

### ✅ Correct Patterns

1. **Nil pointer always with error**
   ```go
   func Parse(data []byte) (*Config, error)  // ✅ CORRECT
   ```

2. **Consistent pointer receivers**
   ```go
   func (c *Cache) Set(k, v any) { }      // pointer
   func (c *Cache) Get(k string) any { }  // ✅ CORRECT - pointer
   ```

3. **Explicit error handling**
   ```go
   if input == nil {
       return nil, errors.New("input is nil")  // ✅ CORRECT
   }
   ```
