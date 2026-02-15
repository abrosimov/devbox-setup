---
name: reliability-patterns
description: >
  Resilience primitives for backend and frontend services. Covers retries with backoff and jitter,
  circuit breakers, bulkheads, timeout composition, backpressure, rate limiting, health checks,
  and graceful degradation for Go, Python, and TypeScript.
  Triggers on: retry, circuit breaker, backpressure, timeout, bulkhead, rate limit, health check,
  graceful degradation, resilience, fault tolerance, load shedding, fallback.
---

# Reliability Patterns

Resilience primitives that prevent cascading failures and keep systems running under stress.

---

## Retries with Exponential Backoff and Jitter

**Never retry without backoff. Never backoff without jitter.**

Plain retries cause **retry storms** -- all clients retry at the same instant, overwhelming the recovering service.

### Algorithm

```
sleep = min(cap, base * 2^attempt) * random(0.5, 1.0)
```

- **base**: initial delay (e.g. 100ms)
- **cap**: maximum delay (e.g. 30s)
- **random(0.5, 1.0)**: full jitter prevents synchronised retries

### Rules

| Rule | Why |
|------|-----|
| **Only retry transient errors** | 400 Bad Request will never succeed on retry |
| **Require idempotency** | Retrying a non-idempotent POST can duplicate side effects |
| **Set a retry budget** | Max 3-5 attempts; beyond that, fail and escalate |
| **Propagate context** | Respect parent deadline; don't retry if context is cancelled |

### Go -- avast/retry-go

```go
import "github.com/avast/retry-go/v4"

err := retry.Do(
    func() error {
        resp, err := client.Do(req.WithContext(ctx))
        if err != nil {
            return err
        }
        if resp.StatusCode >= 500 {
            return fmt.Errorf("server error: %d", resp.StatusCode)
        }
        if resp.StatusCode >= 400 {
            return retry.Unrecoverable(fmt.Errorf("client error: %d", resp.StatusCode))
        }
        return nil
    },
    retry.Attempts(3),
    retry.Delay(100*time.Millisecond),
    retry.DelayType(retry.BackOffDelay),
    retry.MaxJitter(200*time.Millisecond),
    retry.Context(ctx),
    retry.LastErrorOnly(true),
)
```

### Python -- tenacity

```python
from tenacity import (
    retry, stop_after_attempt, wait_exponential_jitter,
    retry_if_exception_type,
)

@retry(
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=0.1, max=30, jitter=2),
)
async def call_payment_api(self, payload: dict) -> dict:
    resp = await self.client.post("/charge", json=payload)
    resp.raise_for_status()
    return resp.json()
```

### TypeScript -- Fetch with Backoff

```typescript
async function fetchWithRetry(url: string, options: RequestInit, maxAttempts = 3): Promise<Response> {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      const resp = await fetch(url, options);
      if (resp.status >= 500) throw new RetryableError(resp.status);
      if (resp.status >= 400) throw new NonRetryableError(resp.status);
      return resp;
    } catch (err) {
      if (err instanceof NonRetryableError || attempt === maxAttempts - 1) throw err;
      const delay = Math.min(30_000, 100 * 2 ** attempt) * (0.5 + Math.random() * 0.5);
      await new Promise((r) => setTimeout(r, delay));
    }
  }
  throw new Error("unreachable");
}
```

---

## Circuit Breaker

Prevent calling a service that is known to be failing. Three states:

```
CLOSED ──(failures exceed threshold)──→ OPEN
  ↑                                       │
  │                                  (timeout expires)
  │                                       ↓
  └──(probe succeeds)──── HALF-OPEN ─────┘
                          (probe fails → back to OPEN)
```

| State | Behaviour |
|-------|-----------|
| **Closed** | Normal operation. Track success/failure ratio |
| **Open** | All calls fail immediately. No load on failing service |
| **Half-Open** | Allow one probe request. Success → Closed; Failure → Open |

### Go -- sony/gobreaker

```go
import "github.com/sony/gobreaker/v2"

cb := gobreaker.NewCircuitBreaker[*http.Response](gobreaker.Settings{
    Name:        "payment-api",
    MaxRequests: 1,                    // probes in half-open
    Interval:    30 * time.Second,     // stats reset interval in closed
    Timeout:     10 * time.Second,     // time in open before half-open
    ReadyToTrip: func(counts gobreaker.Counts) bool {
        return counts.ConsecutiveFailures > 5
    },
    OnStateChange: func(name string, from, to gobreaker.State) {
        log.Warn().Str("breaker", name).Str("from", string(from)).Str("to", string(to)).Msg("circuit breaker state change")
    },
})

resp, err := cb.Execute(func() (*http.Response, error) {
    return client.Do(req)
})
```

### Python -- pybreaker

```python
import pybreaker

payment_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=10,  # seconds before half-open
    exclude=[ValueError],  # don't count these as failures
)

@payment_breaker
async def call_payment(payload: dict) -> dict:
    resp = await client.post("/charge", json=payload)
    resp.raise_for_status()
    return resp.json()

# Caller handles CircuitBreakerError for fallback
try:
    result = await call_payment(data)
except pybreaker.CircuitBreakerError:
    result = cached_fallback(data)
```

### TypeScript -- Simple Implementation

```typescript
class CircuitBreaker {
  private failures = 0;
  private lastFailure = 0;
  private state: "closed" | "open" | "half-open" = "closed";

  constructor(
    private readonly threshold: number = 5,
    private readonly resetTimeout: number = 10_000,
  ) {}

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === "open") {
      if (Date.now() - this.lastFailure > this.resetTimeout) {
        this.state = "half-open";
      } else {
        throw new CircuitOpenError();
      }
    }
    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (err) {
      this.onFailure();
      throw err;
    }
  }

  private onSuccess() { this.failures = 0; this.state = "closed"; }
  private onFailure() {
    this.failures++;
    this.lastFailure = Date.now();
    if (this.failures >= this.threshold) this.state = "open";
  }
}
```

---

## Bulkhead Pattern

Isolate failures so one slow dependency doesn't consume all resources.

| Implementation | Mechanism | Use When |
|---------------|-----------|----------|
| **Semaphore** | Limit concurrent calls | Protecting a single endpoint |
| **Thread/goroutine pool** | Dedicated workers per dependency | Multiple external services |
| **Connection pool per service** | Separate DB/HTTP pools | Preventing cross-service pool drain |

### Go -- Semaphore Bulkhead

```go
type Bulkhead struct {
    sem chan struct{}
}

func NewBulkhead(maxConcurrent int) *Bulkhead {
    return &Bulkhead{sem: make(chan struct{}, maxConcurrent)}
}

func (b *Bulkhead) Execute(ctx context.Context, fn func() error) error {
    select {
    case b.sem <- struct{}{}:
        defer func() { <-b.sem }()
        return fn()
    case <-ctx.Done():
        return fmt.Errorf("bulkhead rejected: %w", ctx.Err())
    }
}

// Usage: separate bulkheads per external service
var (
    paymentBulkhead   = NewBulkhead(10)
    inventoryBulkhead = NewBulkhead(20)
)
```

### Python -- asyncio.Semaphore Bulkhead

```python
class Bulkhead:
    def __init__(self, max_concurrent: int) -> None:
        self._sem = asyncio.Semaphore(max_concurrent)

    async def execute(self, fn: Callable[[], Awaitable[T]]) -> T:
        try:
            async with asyncio.timeout(1):  # don't wait forever for a slot
                async with self._sem:
                    return await fn()
        except TimeoutError:
            raise BulkheadRejectedError("no capacity")

payment_bulkhead = Bulkhead(max_concurrent=10)
```

---

## Timeout Composition

Timeouts must be **layered** and **propagated**. A child timeout must be shorter than its parent.

```
Client request timeout: 30s
  └─ Service A handler: 25s (budget for downstream calls)
      ├─ DB query: 5s
      ├─ Service B call: 15s
      │   └─ Service B DB: 5s
      └─ Cache lookup: 2s
```

### Go -- Context Deadline Propagation

```go
func (s *Service) Handle(ctx context.Context, req Request) (Response, error) {
    // Check remaining budget
    deadline, ok := ctx.Deadline()
    if ok && time.Until(deadline) < 100*time.Millisecond {
        return Response{}, fmt.Errorf("insufficient time budget")
    }

    // Tighter timeout for DB
    dbCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()
    data, err := s.repo.Get(dbCtx, req.ID)
    if err != nil {
        return Response{}, fmt.Errorf("db: %w", err)
    }

    // Downstream call inherits remaining parent budget
    enriched, err := s.enricher.Enrich(ctx, data)
    if err != nil {
        return Response{}, fmt.Errorf("enrich: %w", err)
    }

    return enriched, nil
}
```

### Python -- asyncio.timeout Layering

```python
async def handle(self, request: Request) -> Response:
    async with asyncio.timeout(25):  # handler budget
        async with asyncio.timeout(5):  # DB budget
            data = await self.repo.get(request.id)
        async with asyncio.timeout(15):  # downstream budget
            enriched = await self.enricher.enrich(data)
    return enriched
```

### gRPC Automatic Deadline Propagation

gRPC propagates deadlines automatically across service boundaries. When Service A calls Service B with a 10s deadline and 3s has elapsed, Service B sees a 7s remaining deadline. **No manual propagation needed in gRPC.**

---

## Backpressure and Load Shedding

When a service is overwhelmed, choose: **queue (preserve data)** or **shed (preserve latency)**.

| Strategy | Mechanism | Trade-off |
|----------|-----------|-----------|
| **Bounded queue** | Channel/queue with max size | Rejects when full; preserves order |
| **Load shedding** | Reject low-priority requests | Preserves latency for important traffic |
| **Adaptive concurrency** | Dynamically adjust limits based on latency | Self-tuning; complex to implement |

### Go -- Bounded Channel Backpressure

```go
func NewWorkerPool(workers, queueSize int) *WorkerPool {
    wp := &WorkerPool{
        jobs: make(chan Job, queueSize),
    }
    for range workers {
        go wp.worker()
    }
    return wp
}

func (wp *WorkerPool) Submit(ctx context.Context, job Job) error {
    select {
    case wp.jobs <- job:
        return nil
    case <-ctx.Done():
        return fmt.Errorf("backpressure: queue full, context cancelled")
    default:
        return ErrBackpressure // immediate rejection
    }
}
```

### Python -- Semaphore-Based Backpressure

```python
class RateLimitedProcessor:
    def __init__(self, max_concurrent: int = 50) -> None:
        self._sem = asyncio.Semaphore(max_concurrent)
        self._queue: asyncio.Queue[Job] = asyncio.Queue(maxsize=1000)

    async def submit(self, job: Job) -> None:
        try:
            self._queue.put_nowait(job)
        except asyncio.QueueFull:
            raise BackpressureError("queue full, try again later")
```

---

## Health Checks

### Three Probe Types

| Probe | Purpose | Should Check | Should NOT Check |
|-------|---------|-------------|-----------------|
| **Liveness** | Is the process alive? | Process responsiveness | External dependencies |
| **Readiness** | Can it serve traffic? | DB connectivity, cache | Non-critical dependencies |
| **Startup** | Has it finished initialising? | Config loaded, migrations done | N/A |

### Critical Anti-Pattern: Liveness Depending on External Service

```go
// BAD -- if the database is down, Kubernetes restarts ALL pods
// creating a thundering herd that makes recovery impossible
func livenessHandler(w http.ResponseWriter, r *http.Request) {
    if err := db.Ping(r.Context()); err != nil {
        w.WriteHeader(http.StatusServiceUnavailable) // triggers restart!
        return
    }
    w.WriteHeader(http.StatusOK)
}

// GOOD -- liveness checks only process health
func livenessHandler(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK) // if handler runs, process is alive
}

// Readiness checks dependencies (removes from load balancer, not restart)
func readinessHandler(w http.ResponseWriter, r *http.Request) {
    ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
    defer cancel()
    if err := db.Ping(ctx); err != nil {
        w.WriteHeader(http.StatusServiceUnavailable)
        return
    }
    w.WriteHeader(http.StatusOK)
}
```

---

## Graceful Degradation

When a dependency fails, **degrade functionality rather than fail completely**.

| Dependency State | Strategy | Example |
|-----------------|----------|---------|
| **Slow** | Timeout + return cached data | Show stale product prices |
| **Down** | Feature flag disables feature | Hide recommendations widget |
| **Overloaded** | Shed non-critical requests | Skip analytics, serve core flow |

### Implementation: Feature Flags as Kill Switches

```go
func (s *ProductService) GetProduct(ctx context.Context, id string) (*Product, error) {
    product, err := s.repo.Get(ctx, id)
    if err != nil {
        return nil, fmt.Errorf("get product: %w", err)
    }

    // Graceful degradation: skip enrichment if recommendations service is struggling
    if s.flags.IsEnabled("recommendations_enabled") {
        recs, err := s.recService.Get(ctx, id)
        if err != nil {
            log.Warn().Err(err).Msg("recommendations unavailable, degrading gracefully")
            // Continue without recommendations rather than failing
        } else {
            product.Recommendations = recs
        }
    }

    return product, nil
}
```

### Cache-Aside with Stale Fallback

```python
async def get_product(self, product_id: str) -> Product:
    # Try cache first
    cached = await self.cache.get(f"product:{product_id}")
    if cached:
        return Product.model_validate_json(cached)

    try:
        product = await self.repo.get(product_id)
        await self.cache.set(
            f"product:{product_id}",
            product.model_dump_json(),
            ex=300,  # 5 min TTL
        )
        return product
    except DatabaseError:
        # Stale cache fallback
        stale = await self.cache.get(f"product:{product_id}:stale")
        if stale:
            return Product.model_validate_json(stale)
        raise
```

---

## Pattern Combinations

These patterns compose. Common combinations:

| Combination | Why |
|------------|-----|
| **Retry + Circuit Breaker** | Retry transient errors, but stop when service is clearly down |
| **Timeout + Retry** | Don't wait forever, but try again if timeout was a fluke |
| **Bulkhead + Circuit Breaker** | Isolate AND detect failing dependencies |
| **Circuit Breaker + Fallback** | When breaker opens, return cached/default data |
| **Backpressure + Load Shedding** | Queue what you can, drop what you can't |

**Order matters:** Timeout → Retry → Circuit Breaker → Bulkhead (outside to inside)

> **See also:** `transaction-safety` for DB-specific resilience, `distributed-transactions` for cross-service patterns, `durable-execution` for workflow-level reliability.
