---
name: go-anti-patterns
description: >
  Comprehensive reference for Java/C# patterns to avoid in Go. Use when reviewing
  interface design, constructor patterns, or detecting over-engineering. Triggers on:
  interface definition, wrapper, factory, builder, service locator, DI container,
  abstraction, premature optimization, YAGNI violation.
---

# Go Anti-Patterns Reference

Quick reference for detecting and avoiding Java/C# patterns transplanted to Go.

---

## Quick Decision Trees

### Should I Create an Interface?

```
Do I need an interface?
│
├─ Do I have 2+ implementations RIGHT NOW?
│  ├─ YES → Create interface in CONSUMER package ✅
│  └─ NO → Continue...
│
├─ Is external library unmockable AND I need mocking for tests?
│  ├─ YES (e.g., *mongo.Collection, no interface provided)
│  │  └─ Create adapter interface in MY package ✅
│  └─ NO → Continue...
│
├─ Single-method behavior abstraction?
│  ├─ YES → Use function type instead ✅
│  │        type Strategy func(input Input) Output
│  └─ NO → Continue...
│
├─ Am I creating this "for testing" or "for flexibility"?
│  ├─ YES → DON'T create interface ❌
│  └─ NO → Continue...
│
└─ Default: Use concrete type, refactor to interface WHEN you add implementation #2
```

### Where Should Interface Be Defined?

```
Where to define this interface?
│
├─ Am I creating adapter for unmockable external library?
│  ├─ YES → Define in MY package (where I use it) ✅
│  │        Example: mongoCollection for *mongo.Collection
│  └─ NO → Continue...
│
├─ Do I have 2+ implementations in MY package (I'm provider)?
│  ├─ YES → Export interface from MY package ✅
│  │        Rare case - usually stdlib or library packages
│  └─ NO → Continue...
│
├─ Am I the CONSUMER (using implementations from other packages)?
│  ├─ YES → Define private interface in MY package/file ✅
│  │        Go idiom: "Accept interfaces, return concrete types"
│  └─ NO → Continue...
│
└─ Are you defining interface WITH implementation in same package?
   └─ YES → WRONG - violates Go idiom ❌
            Interface should be in consumer package
```

---

## Anti-Patterns Catalog

### 1. Provider-Side Interface Definition

**Java/C# habit**: Define interface alongside implementation in provider package

**Problem**: Violates "accept interfaces, return concrete types" and "define interfaces where consumed"

```go
// ❌ WRONG - interface defined with implementation (provider-side)
// File: internal/health/strategy.go
package health

type HealthStrategy interface {  // Provider defines interface
    DetermineStatus(node kube.Node) Status
}

type LabelStrategy struct{}

func (s *LabelStrategy) DetermineStatus(node kube.Node) Status {
    // implementation
}

// File: internal/pipeline/kube_reader/reader.go
package kube_reader

import "internal/health"

type KubeStateReader struct {
    strategy health.HealthStrategy  // Consumer must import interface + impl
}

func NewKubeStateReader(strategy health.HealthStrategy, logger Logger) *KubeStateReader {
    return &KubeStateReader{strategy: strategy}
}
```

**Why this is wrong**:
- Consumer must import both interface and implementation from same package
- Interface is "owned" by provider, not consumer
- Violates "accept interfaces, return concrete types"
- Harder to evolve - implementation package controls the contract

**Fix - Option 1: Consumer-side interface**

```go
// ✅ RIGHT - consumer defines private interface
// File: internal/pipeline/kube_reader/reader.go
package kube_reader

// Consumer defines what it needs
type healthStrategy interface {  // Private, defined where used
    DetermineStatus(node kube.Node) health.Status
}

type KubeStateReader struct {
    strategy healthStrategy  // Interface defined in same file
}

func NewKubeStateReader(strategy healthStrategy, logger Logger) *KubeStateReader {
    return &KubeStateReader{strategy: strategy}
}

// File: internal/health/strategy.go
package health

// Provider just returns concrete type
type LabelStrategy struct{}

func (s *LabelStrategy) DetermineStatus(node kube.Node) Status {
    // implementation
}

// Usage - implicit interface satisfaction
reader := kube_reader.NewKubeStateReader(&health.LabelStrategy{}, logger)
```

**Fix - Option 2: Function type (simpler)**

```go
// ✅ RIGHT - function type for single-method behavior
// File: internal/pipeline/kube_reader/reader.go
package kube_reader

type HealthStrategyFunc func(node kube.Node) health.Status

type KubeStateReader struct {
    strategy HealthStrategyFunc
}

func NewKubeStateReader(strategy HealthStrategyFunc, logger Logger) *KubeStateReader {
    return &KubeStateReader{strategy: strategy}
}

// File: internal/health/strategy.go
package health

func LabelStrategy(node kube.Node) Status {
    // Just a function, no struct needed
}

// Usage
reader := kube_reader.NewKubeStateReader(health.LabelStrategy, logger)
```

**Go idiom**: "Interfaces are defined by the consumer, not the provider"

---

### 2. Premature Interface Abstraction

**Java/C# habit**: Abstract every dependency "for testability" and "flexibility"

**Problem**: Creating interfaces with only 1 implementation when no immediate need for #2

```go
// ❌ QUESTIONABLE - correct placement, but premature abstraction
// File: internal/pipeline/coordinator.go (consumer)
package pipeline

type kubeStateFetcher interface {  // Defined where used (correct placement!)
    FetchState(ctx context.Context) ([]ClusterNodeSnapshot, error)
}

type mongoStateFetcher interface {
    FetchOpenRecords(ctx context.Context) ([]OpenRecord, error)
}

type stateComparator interface {
    Compare(snapshots []ClusterNodeSnapshot, records []OpenRecord, now time.Time) []HealthOperation
}

type operationWriter interface {
    Write(ctx context.Context, operations []HealthOperation) error
}

type Coordinator struct {
    kubeReader  kubeStateFetcher   // Only ONE impl: *KubeStateReader
    mongoReader mongoStateFetcher  // Only ONE impl: *MongoStateReader
    comparator  stateComparator    // Only ONE impl: *Comparator
    mongoWriter operationWriter    // Only ONE impl: *MongoWriter
}

func NewCoordinator(
    cfg Config,
    kubeReader kubeStateFetcher,
    mongoReader mongoStateFetcher,
    comp stateComparator,
    mongoWriter operationWriter,
    logger Logger,
) (*Coordinator, error) {
    // Defensive nil checks for every interface
    if kubeReader == nil { return nil, ErrNilKubeReader }
    if mongoReader == nil { return nil, ErrNilMongoReader }
    if comp == nil { return nil, ErrNilComparator }
    if mongoWriter == nil { return nil, ErrNilMongoWriter }

    return &Coordinator{ /* ... */ }, nil
}

// Only these implementations exist:
var _ kubeStateFetcher = (*kube_reader.KubeStateReader)(nil)
var _ mongoStateFetcher = (*mongo_reader.MongoStateReader)(nil)
var _ stateComparator = (*comparator.Comparator)(nil)
var _ operationWriter = (*mongo_writer.MongoWriter)(nil)
```

**Why it's premature**:
- Interface placement is correct (consumer-side), but abstraction adds no value
- Only 1 implementation exists for each interface
- No plan or requirement for implementation #2
- Can test with concrete types using table-driven tests or lightweight implementations
- Adds indirection (harder to navigate code, find implementations)
- Defensive nil checks add ceremony

**Fix: Use concrete types**

```go
// ✅ RIGHT - use concrete types until you have 2+ implementations
package pipeline

type Coordinator struct {
    kubeReader  *kube_reader.KubeStateReader
    mongoReader *mongo_reader.MongoStateReader
    comparator  *comparator.Comparator
    mongoWriter *mongo_writer.MongoWriter
    logger      Logger
}

func NewCoordinator(
    cfg Config,
    kubeReader *kube_reader.KubeStateReader,
    mongoReader *mongo_reader.MongoStateReader,
    comp *comparator.Comparator,
    mongoWriter *mongo_writer.MongoWriter,
    logger Logger,
) *Coordinator {
    // No error return needed - nil pointer panics are caught in tests
    return &Coordinator{
        config:      cfg,
        kubeReader:  kubeReader,
        mongoReader: mongoReader,
        comparator:  comp,
        mongoWriter: mongoWriter,
        logger:      logger,
    }
}
```

**When consumer-side interface with 1 impl IS justified**:
- ✅ Testing genuinely needs mocking AND concrete type is hard to test (slow DB, external API)
- ✅ Actively working on implementation #2 (not "might need someday")
- ✅ Breaking a dependency cycle

**Rule**: Wait until you add implementation #2, even for consumer-side interfaces (YAGNI)

---

### 3. Stateless Struct with Constructor Factory

**Java/C# habit**: Everything is a class, so everything gets a factory method

**Problem**: Unnecessary constructor for zero-state structs

```go
// ❌ WRONG - constructor factory for zero-field struct
type Comparator struct{}  // No fields, no state!

func NewComparator() *Comparator {
    return &Comparator{}  // Just allocates empty struct
}

func (c *Comparator) Compare(snapshots []ClusterNodeSnapshot, records []OpenRecord, now time.Time) []HealthOperation {
    // Pure function - uses no struct state
    // Could be package-level function
}

// Usage
comp := NewComparator()  // Unnecessary allocation
coordinator := NewCoordinator(kubeReader, mongoReader, comp, mongoWriter, logger)
```

**Why this is wrong**:
- Constructor adds no value for zero-state struct
- No fields to initialize, no validation to perform
- Allocates empty struct for no reason
- Adds ceremony without benefit

**Fix - Option 1: Package-level function**

```go
// ✅ RIGHT - package-level function
func Compare(snapshots []ClusterNodeSnapshot, records []OpenRecord, now time.Time) []HealthOperation {
    // Same logic, simpler API
}

// Usage
operations := comparator.Compare(snapshots, records, now)
```

**Fix - Option 2: Global instance (if you need method dispatch)**

```go
// ✅ ALSO RIGHT - global instance if you need method dispatch
type Comparator struct{}

var DefaultComparator = &Comparator{}  // No constructor needed

func (c *Comparator) Compare(snapshots []ClusterNodeSnapshot, records []OpenRecord, now time.Time) []HealthOperation {
    // ...
}

// Usage
coordinator := NewCoordinator(kubeReader, mongoReader, comparator.DefaultComparator, mongoWriter, logger)
```

**When constructor is justified**:
- ✅ Struct has fields that need initialization
- ✅ Constructor performs validation
- ✅ Constructor sets up complex state (connections, goroutines, etc.)
- ❌ Struct has zero fields

**Rule**: If struct has zero fields, consider package function or global instance instead of constructor

---

### 4. Single-Method Interface

**Java/C# habit**: Interfaces are the only abstraction mechanism (no first-class functions)

**Problem**: Over-complicates simple behavior abstraction

```go
// ❌ WRONG - single-method interface with stateless implementation
type HealthStrategy interface {
    DetermineStatus(node kube.Node) Status
}

type LabelStrategy struct{}  // No fields!

func NewLabelStrategy() *LabelStrategy {
    return &LabelStrategy{}
}

func (s *LabelStrategy) DetermineStatus(node kube.Node) Status {
    nodeStatus, hasNodeStatus := node.Labels[labelNodeStatus]
    gpuPresent, hasGPUPresent := node.Labels[labelGPUPresent]

    switch {
    case !hasNodeStatus:
        return StatusUnhealthy
    case nodeStatus != nodeStatusReady:
        return StatusUnhealthy
    case !hasGPUPresent:
        return StatusUnhealthy
    case gpuPresent != "true":
        return StatusUnhealthy
    default:
        return StatusHealthy
    }
}

// Usage
strategy := NewLabelStrategy()  // Allocate empty struct
reader := NewKubeStateReader(strategy, logger)
```

**Why this is wrong**:
- Unnecessary ceremony: empty struct + constructor + method vs simple function
- Memory overhead: allocating struct to hold zero state
- Less idiomatic: Go has first-class functions, use them

**Fix: Function type**

```go
// ✅ RIGHT - function type
type HealthStrategy func(node kube.Node) Status

var LabelStrategy HealthStrategy = func(node kube.Node) Status {
    nodeStatus, hasNodeStatus := node.Labels[labelNodeStatus]
    gpuPresent, hasGPUPresent := node.Labels[labelGPUPresent]

    switch {
    case !hasNodeStatus:
        return StatusUnhealthy
    case nodeStatus != nodeStatusReady:
        return StatusUnhealthy
    case !hasGPUPresent:
        return StatusUnhealthy
    case gpuPresent != "true":
        return StatusUnhealthy
    default:
        return StatusHealthy
    }
}

// Usage - simpler, no allocation, no constructor
reader := NewKubeStateReader(LabelStrategy, logger)
```

**When single-method interface is justified**:
- ✅ Standard library pattern (`io.Reader`, `http.Handler`, `sort.Interface`)
- ✅ Multiple implementations with **different state** (not stateless)
- ✅ External package defines the interface (you're implementing it)
- ❌ All implementations are stateless
- ❌ Custom interface you control

**Rule**: Single-method interfaces should be function types unless you need different state per implementation

---

### 5. Builder Pattern for Simple Objects

**Java/C# habit**: Use Builder pattern for complex object construction

**Problem**: Builder adds unnecessary ceremony for simple value objects

```go
// ❌ WRONG - builder for simple filter/query objects
type FilterBuilder struct {
    filter Filter
}

func NewFilterBuilder() *FilterBuilder {
    return &FilterBuilder{
        filter: Filter{conditions: make([]filterCondition, 0)},
    }
}

func (b *FilterBuilder) Eq(field string, value any) *FilterBuilder {
    b.filter.conditions = append(b.filter.conditions, filterCondition{
        field: field,
        op:    opEq,
        value: value,
    })
    return b
}

func (b *FilterBuilder) Gt(field string, value any) *FilterBuilder {
    b.filter.conditions = append(b.filter.conditions, filterCondition{
        field: field,
        op:    opGt,
        value: value,
    })
    return b
}

// ... 7 more methods (Ne, Gte, Lt, Lte, In, NotIn, Exists, Regex)

func (b *FilterBuilder) Build() Filter {
    return b.filter
}

// Usage - verbose
filter := NewFilterBuilder().
    Eq("status", "active").
    Gt("age", 18).
    Lt("score", 100).
    Build()
```

**Why this is wrong**:
- Filter is a simple value object (slice of conditions)
- No validation between fields, no invariants to maintain
- Struct literal is clearer and more direct
- Builder adds unnecessary type (`FilterBuilder`) and ceremony

**Fix - Option 1: Direct construction**

```go
// ✅ RIGHT - direct struct literal
filter := Filter{
    conditions: []filterCondition{
        {field: "status", op: opEq, value: "active"},
        {field: "age", op: opGt, value: 18},
        {field: "score", op: opLt, value: 100},
    },
}
```

**Fix - Option 2: Helper functions**

```go
// ✅ ALSO RIGHT - simple helper functions if you want DRY
func Eq(field string, value any) filterCondition {
    return filterCondition{field: field, op: opEq, value: value}
}

func Gt(field string, value any) filterCondition {
    return filterCondition{field: field, op: opGt, value: value}
}

func Lt(field string, value any) filterCondition {
    return filterCondition{field: field, op: opLt, value: value}
}

// Usage - clearer than builder
filter := Filter{
    conditions: []filterCondition{
        Eq("status", "active"),
        Gt("age", 18),
        Lt("score", 100),
    },
}
```

**When Builder Pattern IS justified**:
- ✅ Enforce creation constraints (prevent invalid intermediate states)
- ✅ Complex cross-field validation during construction
- ✅ Building truly immutable objects (though Go doesn't enforce)
- ✅ Object has 10+ required fields with specific ordering
- ❌ Simple value object with 2-5 fields
- ❌ Easily constructed with struct literal
- ❌ No cross-field validation
- ❌ Query/filter/update objects

**Rule**: Don't create builders for simple value objects. Use struct literals and helper functions.

---

### 6. Functional Options for <3 Parameters

**Java/C# habit**: Use builder or options pattern for all configuration

**Problem**: Functional options add ceremony for small parameter counts, especially test-only config

```go
// ❌ WRONG - functional options for 2 parameters only used in tests
type ClientOption func(*Client)

func WithSessionFactory(f func() (mongoSession, error)) ClientOption {
    return func(c *Client) { c.sessionFactory = f }
}

func WithCollectionFactory(f func(name string) mongoCollection) ClientOption {
    return func(c *Client) { c.collectionFactory = f }
}

func NewClient(cfg Config, mongoClient *mongo.Client, logger Logger, opts ...ClientOption) *Client {
    c := &Client{
        config: cfg,
        client: mongoClient,
        logger: logger,
    }

    // Set defaults (production behavior)
    c.sessionFactory = func() (mongoSession, error) {
        return c.client.StartSession()
    }
    c.collectionFactory = func(name string) mongoCollection {
        return c.client.Database(c.config.DatabaseName).Collection(name)
    }

    // Apply options (only ever used in tests!)
    for _, opt := range opts {
        opt(c)
    }

    return c
}

// Production usage - passes zero options
client := NewClient(cfg, mongoClient, logger)

// Test usage - only place options are used
client := NewClient(cfg, fakeClient, logger,
    WithSessionFactory(mockSessionFactory),
    WithCollectionFactory(mockCollectionFactory),
)
```

**Why this is wrong**:
- Options only used in tests, not production
- Production code pays performance overhead (option iteration, variadic allocation)
- Test concerns pollute production API
- Adds complexity for 2 parameters

**Fix: Separate test constructor**

```go
// ✅ RIGHT - separate test constructor
func NewClient(cfg Config, mongoClient *mongo.Client, logger Logger) *Client {
    return &Client{
        config:            cfg,
        client:            mongoClient,
        logger:            logger,
        sessionFactory:    func() (mongoSession, error) { return mongoClient.StartSession() },
        collectionFactory: func(name string) mongoCollection {
            return mongoClient.Database(cfg.DatabaseName).Collection(name)
        },
    }
}

// Test-specific constructor with explicit parameters
func NewClientForTesting(
    cfg Config,
    mongoClient *mongo.Client,
    logger Logger,
    sessionFactory func() (mongoSession, error),
    collectionFactory func(name string) mongoCollection,
) *Client {
    c := NewClient(cfg, mongoClient, logger)
    if sessionFactory != nil {
        c.sessionFactory = sessionFactory
    }
    if collectionFactory != nil {
        c.collectionFactory = collectionFactory
    }
    return c
}

// Production code - clean and simple
client := NewClient(cfg, mongoClient, logger)

// Test code - explicit about test setup
client := NewClientForTesting(cfg, fakeClient, logger, mockSession, mockCollection)
```

**When functional options ARE justified**:
- ✅ 3+ optional configuration parameters
- ✅ Most callers use defaults (not all callers use all options)
- ✅ Need backward-compatible API evolution
- ✅ Production code benefits from the flexibility
- ❌ 1-2 optional parameters (use pointers or config struct)
- ❌ All parameters required (use config struct)
- ❌ Options only for testing (separate test constructor)

**Rule**: Don't use functional options for test-only config or <3 parameters

---

### 7. Mixed Pointer and Value Receivers

**Java/C# habit**: Methods are always on reference types, no receiver type distinction exists

**Problem**: Mixing pointer and value receivers on the same type causes race conditions, interface satisfaction issues, and violates Go method sets

```go
// ❌ WRONG - mixed receivers causing race condition
type Counter struct {
    mu    sync.Mutex
    count int
}

func (c *Counter) Increment() {  // pointer receiver
    c.mu.Lock()
    defer c.mu.Unlock()
    c.count++
}

func (c Counter) Value() int {  // ❌ value receiver — COPIES the struct!
    c.mu.Lock()  // Locks a COPY of the mutex, not the original!
    defer c.mu.Unlock()
    return c.count  // Race condition — reading without proper lock
}

// ❌ WRONG - mixed receivers causing interface issues
type Connection struct {
    addr string
    open bool
}

func (c *Connection) Open() error {  // pointer receiver
    c.open = true
    return nil
}

func (c Connection) Address() string {  // ❌ value receiver
    return c.addr
}

// Problem: Interface satisfaction is inconsistent
type Connector interface {
    Open() error
    Address() string
}

var conn Connector = &Connection{}  // ✓ Works - pointer has both methods
var conn Connector = Connection{}   // ✗ FAILS - value only has Address()
```

**Why this is wrong:**
- **Race conditions**: Value receiver copies the entire struct including mutexes
  - Locking a copy doesn't protect the original data
  - sync.Mutex, sync.RWMutex CANNOT be copied safely
- **Method sets differ**: `*T` and `T` have different method sets
  - `*T` includes both pointer and value receiver methods
  - `T` only includes value receiver methods
  - Breaks interface satisfaction unexpectedly
- **Copying overhead**: Value receiver copies large structs unnecessarily
- **Violates Go idiom**: Receiver type should be consistent for a type

**Fix: All pointer receivers**

```go
// ✅ CORRECT - consistent pointer receivers
type Counter struct {
    mu    sync.Mutex
    count int
}

func (c *Counter) Increment() {  // pointer receiver
    c.mu.Lock()
    defer c.mu.Unlock()
    c.count++
}

func (c *Counter) Value() int {  // ✅ pointer receiver — consistent!
    c.mu.Lock()  // Locks the ACTUAL mutex
    defer c.mu.Unlock()
    return c.count  // Safe — proper synchronization
}

// ✅ CORRECT - all pointer receivers for consistency
type Connection struct {
    addr string
    open bool
}

func (c *Connection) Open() error {  // pointer receiver
    c.open = true
    return nil
}

func (c *Connection) Address() string {  // ✅ pointer receiver — consistent!
    return c.addr
}
```

**Decision tree for receiver type:**

```
Choose receiver type for first method:
│
├─ Does method modify receiver?
│  └─ YES → Use pointer, ALL future methods MUST be pointer
│
├─ Does type contain sync.Mutex, sync.RWMutex, or other sync.* types?
│  └─ YES → MUST use pointer (cannot copy), ALL methods MUST be pointer
│
├─ Is type large (>64 bytes)?
│  └─ YES → Should use pointer (avoid copying), ALL methods MUST be pointer
│
├─ Do you plan to add modifying methods later?
│  └─ YES → Use pointer now, saves refactoring later
│
└─ All methods are read-only AND type is small (<64 bytes)?
   └─ YES → Can use value receivers for ALL methods
      Examples: Point{X, Y int}, Color{R, G, B byte}
```

**CRITICAL RULE**: Once you choose pointer for ONE method → ALL methods must use pointer

**Real-world example of race condition:**

```go
// ❌ DANGEROUS - subtle race condition
type Cache struct {
    items map[string]any
    mu    sync.RWMutex
}

func (c *Cache) Set(key string, val any) {  // pointer receiver
    c.mu.Lock()
    defer c.mu.Unlock()
    c.items[key] = val
}

func (c Cache) Get(key string) (any, bool) {  // ❌ value receiver
    c.mu.RLock()  // Locks a COPY of c.mu!
    defer c.mu.RUnlock()
    val, ok := c.items[key]  // Concurrent map read — RACE!
    return val, ok
}

// What actually happens:
// Thread 1: cache.Set("key", "value")  → locks cache.mu
// Thread 2: cache.Get("key")           → locks COPY of cache.mu (different mutex!)
//                                       → reads cache.items while Thread 1 writes
//                                       → RACE DETECTED by -race flag

// ✅ FIXED - all pointer receivers
func (c *Cache) Get(key string) (any, bool) {  // pointer receiver
    c.mu.RLock()  // Locks the ACTUAL c.mu
    defer c.mu.RUnlock()
    val, ok := c.items[key]  // Safe — properly synchronized
    return val, ok
}
```

**Common mistakes:**

| Mistake | Fix |
|---------|-----|
| Getter uses value, setter uses pointer | All pointer receivers |
| "Read-only methods should use value for efficiency" | Use pointer for consistency |
| Implementing interface on value but state-modifying methods on pointer | All pointer receivers |
| "Small struct, value is fine" when ANY method mutates | All pointer receivers |

**Only acceptable use of all value receivers:**

```go
// ✅ ACCEPTABLE - small, truly immutable value type
type Point struct {
    X, Y int  // 16 bytes total, no sync fields
}

func (p Point) Add(other Point) Point {  // Returns NEW Point, doesn't modify
    return Point{X: p.X + other.X, Y: p.Y + other.Y}
}

func (p Point) Distance() float64 {  // Read-only, no state modification
    return math.Sqrt(float64(p.X*p.X + p.Y*p.Y))
}

// Justification for all value receivers:
// - Truly immutable (no mutation methods ever)
// - Small size (16 bytes, cheap to copy)
// - No sync fields
// - No plans to add mutation methods
// Examples: time.Time, color.RGBA, image.Point
```

**When value receivers ARE justified (rare):**
- ✅ Small immutable types (<64 bytes, no sync fields): `Point`, `Color`, `Range`
- ✅ No mutation methods exist OR planned
- ✅ Type semantics are "value-like" (like `time.Time`)
- ❌ Type has ANY pointer receiver method → ALL must be pointer
- ❌ Type has sync.Mutex/sync.RWMutex → ALL must be pointer
- ❌ Type is large (>64 bytes) → ALL must be pointer

**Rule**: Default to pointer receivers. Only use all value receivers for small, immutable, value-semantic types.

---

## Valid Patterns Often Confused as Anti-Patterns

### Adapter Interface for Unmockable External Library

```go
// ✅ CORRECT - adapter pattern for testing
type mongoCollection interface {
    FindOne(ctx context.Context, filter any, opts ...options.Lister[options.FindOneOptions]) *mongo.SingleResult
    Find(ctx context.Context, filter any, opts ...options.Lister[options.FindOptions]) (*mongo.Cursor, error)
    InsertOne(ctx context.Context, document any, opts ...options.Lister[options.InsertOneOptions]) (*mongo.InsertOneResult, error)
    // ... other methods needed from *mongo.Collection
}

// Compile-time verification that *mongo.Collection satisfies interface
var _ mongoCollection = (*mongo.Collection)(nil)

type Collection[E any, P EntityPtr[E]] struct {
    coll mongoCollection  // For mocking in tests
}
```

**Why this is valid**:
- MongoDB driver provides NO interface (only `*mongo.Collection` concrete type)
- You can't mock `*mongo.Collection` without an interface
- This is the **adapter pattern** for testing, not "decoupling for decoupling's sake"
- Interface defined in YOUR package (where it's consumed)

**When it WOULD be anti-pattern**:
- ❌ Library already provides interface (`io.Reader`, `http.RoundTripper`)
- ❌ Library has good test utilities (`httptest.Server`, `sqlmock`)
- ❌ You're wrapping "for future flexibility" without testing need

---

### Service Locator for Lightweight Stateless Components

```go
// ✅ VALID - service locator for lightweight components
type Collection[E any, P EntityPtr[E]] struct {
    name string  // Only state - collection name
}

func GetCollection[E any, P EntityPtr[E]](name string) *Collection[E, P] {
    return &Collection[E, P]{name: name}
}

func (c *Collection[E, P]) prepareOp(ctx context.Context) (*Tx, mongoCollection, error) {
    // Retrieve heavy client on-demand
    client := provider.GuaranteedValueOf[Client]()
    coll := client.collection(c.name)
    return tx, coll, nil
}
```

**Why this is valid**:
- Keeps `Collection` stateless and lightweight (only holds `name`)
- Avoids injecting heavy `Client` into every collection instance
- Reduces memory overhead (many collections, one client)
- Infrastructure services (DB client, logger, metrics) are good candidates

**When it WOULD be anti-pattern**:
- ❌ Hiding business dependencies that should be explicit
- ❌ Using for all dependencies (constructor parameter explosion)
- ❌ Runtime panics if not registered (could return error)

---

### Type Inference Generic Constraints

```go
// ✅ CORRECT - enables type inference
type EntityPtr[E any] interface {
    *E
    Entity
}

type Collection[E any, P EntityPtr[E]] struct {
    name string
}

// Usage: write Collection[User] instead of Collection[User, *User]
coll := GetCollection[User]("users")  // P inferred as *User
user, err := coll.FindByID(ctx, id)   // Returns *User (not User)
```

**Why this is valid**:
- Provides better ergonomics: `Collection[User]` vs `Collection[User, *User]`
- Type inference automatically deduces `P = *User`
- Compile-time guarantee that `*E` implements `Entity`
- Not over-abstraction - the constraint serves a concrete technical purpose

---

## Red Flags by Agent Role

### For Software Engineer

Before creating any of these, STOP and review:

- [ ] Interface with only 1 implementation → Use concrete type (unless adapter)
- [ ] Interface in provider package → Move to consumer or use function type
- [ ] Constructor for zero-field struct → Use package function or global var
- [ ] Builder for simple object (<5 fields, no validation) → Use struct literal
- [ ] Functional options for <3 params → Use pointers or separate test constructor
- [ ] Single-method interface → Use function type
- [ ] **Mixed pointer/value receivers** → ALL methods must use same receiver type

### For Code Reviewer

Detect and flag these patterns:

- [ ] **Provider-side interface**: Interface defined in same package as implementation
- [ ] **Premature abstraction**: Interface with only 1 implementation (check for adapter pattern)
- [ ] **Stateless constructor**: `NewX()` returning `&X{}` where `X` is `struct{}`
- [ ] **Builder ceremony**: Builder for simple value objects
- [ ] **Test-only options**: Functional options only used in test code
- [ ] **Function disguised as interface**: Single-method interface with stateless impls
- [ ] **Mixed receivers (CRITICAL)**: Type has both pointer and value receivers

### For Test Writer

Testing strategy guidelines:

- [ ] **Don't suggest**: "Create interface for easier testing" (use concrete types)
- [ ] **Do use**: Test-local interfaces (define in `_test.go` file only)
- [ ] **Do use**: Adapter pattern for unmockable libraries (e.g., `mongoCollection`)
- [ ] **Do use**: In-memory implementations of concrete types
- [ ] **Avoid**: Creating production interfaces just for testing

### For Implementation Planner

Planning-level awareness:

- [ ] **Don't plan**: Provider-side interfaces (let consumer define if needed)
- [ ] **Don't plan**: Interfaces with single implementation (use concrete types)
- [ ] **Don't plan**: "For future flexibility" abstractions (YAGNI)
- [ ] **Do specify**: Concrete types and data flow
- [ ] **Do note**: If 2+ implementations are actually planned (then consumer defines interface)

---

## Summary

**Key Go Idioms**:
- "Accept interfaces, return concrete types"
- "Define interfaces where consumed, not where implemented"
- "A little copying is better than a little dependency"
- "Clear is better than clever"
- "Don't abstract until you have 2+ implementations" (YAGNI)

**When in doubt**: Use concrete types. Refactor to interface when you add implementation #2.
