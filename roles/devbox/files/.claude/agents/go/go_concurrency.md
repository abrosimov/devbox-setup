# Go Concurrency Reference

Reference document for concurrency patterns. Used by Go agents (`software-engineer-go`, `unit-test-writer-go`, `code-reviewer-go`).

---

## Graceful Shutdown

Every production service must handle shutdown gracefully: finish in-flight requests, close connections, flush buffers.

### Basic Pattern

```go
func main() {
    // Create context that cancels on SIGINT/SIGTERM
    ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
    defer stop()

    if err := run(ctx); err != nil && !errors.Is(err, context.Canceled) {
        log.Error().Err(err).Msg("application failed")
        os.Exit(1)
    }
}

func run(ctx context.Context) error {
    logger := zerolog.New(os.Stderr).With().Timestamp().Logger()

    srv, err := NewServer(logger)
    if err != nil {
        return fmt.Errorf("creating server: %w", err)
    }

    // Start server in goroutine
    errCh := make(chan error, 1)
    go func() {
        errCh <- srv.ListenAndServe()
    }()

    // Wait for shutdown signal or server error
    select {
    case err := <-errCh:
        return err
    case <-ctx.Done():
        // Graceful shutdown with timeout
        shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
        defer cancel()

        if err := srv.Shutdown(shutdownCtx); err != nil {
            return fmt.Errorf("shutdown: %w", err)
        }
        return nil
    }
}
```

### With Multiple Components

```go
func run(ctx context.Context) error {
    // Initialize components
    db, err := sql.Open("postgres", connStr)
    if err != nil {
        return fmt.Errorf("opening database: %w", err)
    }

    cache := redis.NewClient(redisOpts)
    srv := NewServer(db, cache)

    // Start server
    errCh := make(chan error, 1)
    go func() {
        errCh <- srv.ListenAndServe()
    }()

    // Wait for signal
    select {
    case err := <-errCh:
        return err
    case <-ctx.Done():
    }

    // Shutdown in reverse order of initialization
    shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    var shutdownErr error

    // 1. Stop accepting new requests
    if err := srv.Shutdown(shutdownCtx); err != nil {
        shutdownErr = errors.Join(shutdownErr, fmt.Errorf("server shutdown: %w", err))
    }

    // 2. Close cache
    if err := cache.Close(); err != nil {
        shutdownErr = errors.Join(shutdownErr, fmt.Errorf("cache close: %w", err))
    }

    // 3. Close database
    if err := db.Close(); err != nil {
        shutdownErr = errors.Join(shutdownErr, fmt.Errorf("database close: %w", err))
    }

    return shutdownErr
}
```

### BAD vs GOOD

```go
// BAD — no graceful shutdown
func main() {
    srv := NewServer()
    log.Fatal(srv.ListenAndServe())  // abrupt termination
}

// BAD — shutdown without timeout
func main() {
    // ...
    <-ctx.Done()
    srv.Shutdown(context.Background())  // could hang forever
}

// GOOD — graceful with timeout
func main() {
    ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
    defer stop()

    if err := run(ctx); err != nil && !errors.Is(err, context.Canceled) {
        os.Exit(1)
    }
}
```

---

## errgroup

Parallel operations with coordinated error handling and cancellation.

### Basic Pattern

```go
import "golang.org/x/sync/errgroup"

func fetchAll(ctx context.Context, urls []string) ([]Response, error) {
    g, ctx := errgroup.WithContext(ctx)
    responses := make([]Response, len(urls))

    for i, url := range urls {
        i, url := i, url  // capture for goroutine
        g.Go(func() error {
            resp, err := fetch(ctx, url)
            if err != nil {
                return fmt.Errorf("fetching %s: %w", url, err)
            }
            responses[i] = resp
            return nil
        })
    }

    if err := g.Wait(); err != nil {
        return nil, err
    }
    return responses, nil
}
```

### With Concurrency Limit

```go
func processItems(ctx context.Context, items []Item) error {
    g, ctx := errgroup.WithContext(ctx)
    g.SetLimit(10)  // max 10 concurrent goroutines

    for _, item := range items {
        item := item
        g.Go(func() error {
            return process(ctx, item)
        })
    }

    return g.Wait()
}
```

### Collecting Results Safely

```go
func fetchUsers(ctx context.Context, ids []string) ([]*User, error) {
    g, ctx := errgroup.WithContext(ctx)
    g.SetLimit(5)

    var mu sync.Mutex
    users := make([]*User, 0, len(ids))

    for _, id := range ids {
        id := id
        g.Go(func() error {
            user, err := fetchUser(ctx, id)
            if err != nil {
                return fmt.Errorf("fetching user %s: %w", id, err)
            }

            mu.Lock()
            users = append(users, user)
            mu.Unlock()
            return nil
        })
    }

    if err := g.Wait(); err != nil {
        return nil, err
    }
    return users, nil
}
```

### BAD vs GOOD

```go
// BAD — manual goroutine management, error handling is complex
func fetchAll(urls []string) ([]Response, error) {
    var wg sync.WaitGroup
    errCh := make(chan error, len(urls))
    responses := make([]Response, len(urls))

    for i, url := range urls {
        wg.Add(1)
        go func(i int, url string) {
            defer wg.Done()
            resp, err := fetch(url)
            if err != nil {
                errCh <- err
                return
            }
            responses[i] = resp
        }(i, url)
    }

    wg.Wait()
    close(errCh)
    // Now what? Collect first error? All errors?
}

// GOOD — errgroup handles coordination
func fetchAll(ctx context.Context, urls []string) ([]Response, error) {
    g, ctx := errgroup.WithContext(ctx)
    responses := make([]Response, len(urls))

    for i, url := range urls {
        i, url := i, url
        g.Go(func() error {
            resp, err := fetch(ctx, url)
            if err != nil {
                return err
            }
            responses[i] = resp
            return nil
        })
    }

    if err := g.Wait(); err != nil {
        return nil, err
    }
    return responses, nil
}
```

---

## sync.Once

Lazy initialization that runs exactly once, safely across goroutines.

### Basic Pattern

```go
type Client struct {
    once   sync.Once
    conn   *Connection
    connErr error
}

func (c *Client) getConnection() (*Connection, error) {
    c.once.Do(func() {
        c.conn, c.connErr = connect()
    })
    return c.conn, c.connErr
}

func (c *Client) Send(data []byte) error {
    conn, err := c.getConnection()
    if err != nil {
        return fmt.Errorf("getting connection: %w", err)
    }
    return conn.Send(data)
}
```

### Singleton Pattern

```go
var (
    instance     *Database
    instanceOnce sync.Once
)

func GetDatabase() *Database {
    instanceOnce.Do(func() {
        instance = &Database{
            pool: createPool(),
        }
    })
    return instance
}
```

### BAD vs GOOD

```go
// BAD — race condition
type Client struct {
    conn *Connection
}

func (c *Client) getConnection() *Connection {
    if c.conn == nil {
        c.conn = connect()  // race: multiple goroutines may call connect()
    }
    return c.conn
}

// BAD — mutex on every access
type Client struct {
    mu   sync.Mutex
    conn *Connection
}

func (c *Client) getConnection() *Connection {
    c.mu.Lock()
    defer c.mu.Unlock()
    if c.conn == nil {
        c.conn = connect()
    }
    return c.conn
}

// GOOD — sync.Once, lock-free after initialization
type Client struct {
    once sync.Once
    conn *Connection
}

func (c *Client) getConnection() *Connection {
    c.once.Do(func() {
        c.conn = connect()
    })
    return c.conn
}
```

---

## sync.WaitGroup

Waiting for a collection of goroutines to finish.

### Basic Pattern

```go
func processAll(items []Item) {
    var wg sync.WaitGroup

    for _, item := range items {
        wg.Add(1)
        go func(item Item) {
            defer wg.Done()
            process(item)
        }(item)
    }

    wg.Wait()
}
```

### Worker Pool

```go
func processWithPool(ctx context.Context, items []Item, workers int) {
    itemCh := make(chan Item)
    var wg sync.WaitGroup

    // Start workers
    for i := 0; i < workers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for item := range itemCh {
                if ctx.Err() != nil {
                    return
                }
                process(item)
            }
        }()
    }

    // Send items
    for _, item := range items {
        select {
        case itemCh <- item:
        case <-ctx.Done():
            break
        }
    }
    close(itemCh)

    wg.Wait()
}
```

### BAD vs GOOD

```go
// BAD — Add after goroutine starts (race condition)
for _, item := range items {
    go func(item Item) {
        wg.Add(1)  // too late! main goroutine may call Wait() before Add()
        defer wg.Done()
        process(item)
    }(item)
}
wg.Wait()

// BAD — Done without Add
go func() {
    defer wg.Done()  // will panic or cause negative counter
    process()
}()

// GOOD — Add before goroutine starts
for _, item := range items {
    wg.Add(1)
    go func(item Item) {
        defer wg.Done()
        process(item)
    }(item)
}
wg.Wait()
```

---

## sync.Map

Concurrent map for specific use cases. **Not a general-purpose replacement for `map` + `sync.Mutex`**.

### When to Use

| Use Case | Use sync.Map? |
|----------|---------------|
| Write once, read many (cache) | Yes |
| Disjoint key sets per goroutine | Yes |
| General read/write from all goroutines | No — use map + mutex |
| Need to iterate frequently | No — use map + RWMutex |

### Pattern

```go
var cache sync.Map

func Get(key string) (*Value, bool) {
    v, ok := cache.Load(key)
    if !ok {
        return nil, false
    }
    return v.(*Value), true
}

func Set(key string, value *Value) {
    cache.Store(key, value)
}

func GetOrCreate(key string, create func() *Value) *Value {
    v, loaded := cache.LoadOrStore(key, create())
    return v.(*Value)
}
```

### BAD vs GOOD

```go
// BAD — sync.Map for general concurrent access
var users sync.Map  // type safety lost, performance may be worse

// GOOD — map + mutex for general case
type UserCache struct {
    mu    sync.RWMutex
    users map[string]*User
}

func (c *UserCache) Get(id string) (*User, bool) {
    c.mu.RLock()
    defer c.mu.RUnlock()
    u, ok := c.users[id]
    return u, ok
}

func (c *UserCache) Set(id string, user *User) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.users[id] = user
}
```

---

## Rate Limiting

Control request rate to external services or incoming requests.

### Basic Rate Limiter

```go
import "golang.org/x/time/rate"

type Client struct {
    limiter *rate.Limiter
    http    *http.Client
}

func NewClient() *Client {
    return &Client{
        limiter: rate.NewLimiter(rate.Limit(10), 20),  // 10 req/sec, burst 20
        http:    &http.Client{Timeout: 30 * time.Second},
    }
}

func (c *Client) Do(ctx context.Context, req *http.Request) (*http.Response, error) {
    if err := c.limiter.Wait(ctx); err != nil {
        return nil, fmt.Errorf("rate limit: %w", err)
    }
    return c.http.Do(req)
}
```

### Per-Key Rate Limiting

```go
type RateLimiter struct {
    mu       sync.Mutex
    limiters map[string]*rate.Limiter
    rate     rate.Limit
    burst    int
}

func NewRateLimiter(r rate.Limit, burst int) *RateLimiter {
    return &RateLimiter{
        limiters: make(map[string]*rate.Limiter),
        rate:     r,
        burst:    burst,
    }
}

func (r *RateLimiter) Allow(key string) bool {
    r.mu.Lock()
    limiter, ok := r.limiters[key]
    if !ok {
        limiter = rate.NewLimiter(r.rate, r.burst)
        r.limiters[key] = limiter
    }
    r.mu.Unlock()

    return limiter.Allow()
}
```

### In HTTP Middleware

```go
func RateLimitMiddleware(limiter *rate.Limiter) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            if !limiter.Allow() {
                http.Error(w, "rate limit exceeded", http.StatusTooManyRequests)
                return
            }
            next.ServeHTTP(w, r)
        })
    }
}
```

---

## Context Cancellation Patterns

### Propagate Context Through Call Chain

```go
// GOOD — context flows through entire chain
func (s *Service) HandleRequest(ctx context.Context, req Request) error {
    user, err := s.userRepo.Get(ctx, req.UserID)
    if err != nil {
        return err
    }

    return s.process(ctx, user, req)
}

// BAD — context lost, operations can't be cancelled
func (s *Service) HandleRequest(ctx context.Context, req Request) error {
    user, err := s.userRepo.Get(context.Background(), req.UserID)  // loses cancellation
    // ...
}
```

### Check Context in Long Operations

```go
func processItems(ctx context.Context, items []Item) error {
    for _, item := range items {
        // Check cancellation periodically
        if err := ctx.Err(); err != nil {
            return err
        }

        if err := process(item); err != nil {
            return err
        }
    }
    return nil
}
```

### Select with Context

```go
func waitForResult(ctx context.Context, resultCh <-chan Result) (Result, error) {
    select {
    case result := <-resultCh:
        return result, nil
    case <-ctx.Done():
        return Result{}, ctx.Err()
    }
}
```
