---
name: distributed-transactions
description: >
  Cross-service data consistency patterns. Covers transactional outbox, transactionally staged
  job drains, idempotency keys, saga pattern (orchestration and choreography), CDC with Debezium,
  dead letter queues, and event sourcing basics for Go, Python, and TypeScript.
  Triggers on: outbox, inbox, saga, idempotency key, exactly-once, CDC, Debezium, dead letter queue,
  DLQ, event sourcing, distributed transaction, eventual consistency, compensation.
---

# Distributed Transactions

Patterns for maintaining data consistency across service boundaries without distributed ACID transactions.

**Core principle:** Avoid distributed transactions (2PC). Instead, use **local transactions + asynchronous messaging** to achieve eventual consistency with reliability guarantees.

---

## Idempotency Keys

An idempotent operation produces the same result regardless of how many times it is called. Critical for safe retries.

### How It Works

1. Client generates a unique key (UUID v4) before the request
2. Client sends key in request header (`Idempotency-Key`)
3. Server checks if key was already processed
4. If yes → return stored result; if no → process and store result
5. Keys expire after 24-48 hours

### Schema

```sql
CREATE TABLE idempotency_keys (
    key         TEXT PRIMARY KEY,
    response    JSONB NOT NULL,
    status_code INTEGER NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Auto-expire old keys
CREATE INDEX idx_idempotency_keys_created_at ON idempotency_keys (created_at);
```

### Go -- Middleware

```go
func IdempotencyMiddleware(repo IdempotencyRepo) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            if r.Method != http.MethodPost {
                next.ServeHTTP(w, r)
                return
            }
            key := r.Header.Get("Idempotency-Key")
            if key == "" {
                next.ServeHTTP(w, r)
                return
            }

            // Check for existing result
            cached, err := repo.Get(r.Context(), key)
            if err == nil {
                w.WriteHeader(cached.StatusCode)
                w.Write(cached.ResponseBody)
                return
            }

            // Wrap response writer to capture result
            rec := &responseRecorder{ResponseWriter: w}
            next.ServeHTTP(rec, r)

            // Store result (ignore errors -- worst case we process twice)
            _ = repo.Store(r.Context(), key, rec.statusCode, rec.body.Bytes())
        })
    }
}
```

### Python -- Decorator

```python
from functools import wraps

def idempotent(fn: Callable) -> Callable:
    @wraps(fn)
    async def wrapper(request: Request, *args, **kwargs):
        key = request.headers.get("Idempotency-Key")
        if not key:
            return await fn(request, *args, **kwargs)

        cached = await idempotency_repo.get(key)
        if cached:
            return JSONResponse(content=cached.body, status_code=cached.status_code)

        response = await fn(request, *args, **kwargs)
        await idempotency_repo.store(key, response.status_code, response.body)
        return response
    return wrapper
```

### TypeScript -- Frontend Key Generation

```typescript
// Generate key ONCE per user action, not per request attempt
function useIdempotentMutation<T>(mutationFn: (key: string, data: T) => Promise<Response>) {
  const keyRef = useRef<string | null>(null);

  return useMutation({
    mutationFn: async (data: T) => {
      // Generate key on first attempt; reuse on retries
      if (!keyRef.current) keyRef.current = crypto.randomUUID();
      return mutationFn(keyRef.current, data);
    },
    onSettled: () => {
      keyRef.current = null; // reset for next user action
    },
  });
}
```

---

## Transactional Outbox Pattern

Write events to an outbox table **inside the same database transaction** as your business data. A separate process relays events to the message broker.

### Why Not Publish Directly?

```
// BROKEN -- if publish succeeds but commit fails, event is orphaned
// If commit succeeds but publish fails, event is lost
BEGIN TX
  INSERT order
COMMIT
PUBLISH event  ← not atomic with commit
```

### Architecture

```
Service ──(tx)──→ [Business Table] + [Outbox Table]
                                          │
                    Relay Process ←────────┘
                         │
                    Message Broker (Kafka/RabbitMQ/SQS)
```

### Outbox Schema

```sql
CREATE TABLE outbox_events (
    id            BIGSERIAL PRIMARY KEY,
    aggregate_type TEXT NOT NULL,
    aggregate_id   UUID NOT NULL,
    event_type     TEXT NOT NULL,
    payload        JSONB NOT NULL,
    published      BOOLEAN NOT NULL DEFAULT false,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_outbox_unpublished ON outbox_events (id) WHERE NOT published;
```

### Go -- Write to Outbox in Transaction

```go
func (s *OrderService) PlaceOrder(ctx context.Context, req PlaceOrderReq) (uuid.UUID, error) {
    var orderID uuid.UUID
    err := pgx.BeginTxFunc(ctx, s.pool, pgx.TxOptions{}, func(tx pgx.Tx) error {
        var err error
        orderID, err = s.orderRepo.Insert(ctx, tx, req)
        if err != nil {
            return fmt.Errorf("insert order: %w", err)
        }
        return s.outboxRepo.Insert(ctx, tx, OutboxEvent{
            AggregateType: "order",
            AggregateID:   orderID,
            EventType:     "order.placed",
            Payload:       req,
        })
    })
    return orderID, err
}
```

### Go -- Polling Relay (Transactionally Staged Job Drain)

```go
func (r *OutboxRelay) Poll(ctx context.Context) error {
    return pgx.BeginTxFunc(ctx, r.pool, pgx.TxOptions{}, func(tx pgx.Tx) error {
        // Lock and fetch unpublished events
        events, err := tx.Query(ctx,
            `SELECT id, aggregate_type, aggregate_id, event_type, payload
             FROM outbox_events
             WHERE NOT published
             ORDER BY id
             LIMIT 100
             FOR UPDATE SKIP LOCKED`)
        if err != nil {
            return fmt.Errorf("query outbox: %w", err)
        }
        defer events.Close()

        var ids []int64
        for events.Next() {
            var e OutboxEvent
            if err := events.Scan(&e.ID, &e.AggregateType, &e.AggregateID, &e.EventType, &e.Payload); err != nil {
                return fmt.Errorf("scan: %w", err)
            }
            if err := r.publisher.Publish(ctx, e); err != nil {
                return fmt.Errorf("publish event %d: %w", e.ID, err)
            }
            ids = append(ids, e.ID)
        }

        if len(ids) > 0 {
            _, err = tx.Exec(ctx,
                `UPDATE outbox_events SET published = true WHERE id = ANY($1)`, ids)
        }
        return err
    })
}
```

### Python -- SQLAlchemy Outbox

```python
async def place_order(self, req: PlaceOrderReq) -> UUID:
    async with self.session.begin() as session:
        order = Order(**req.model_dump())
        session.add(order)
        session.add(OutboxEvent(
            aggregate_type="order",
            aggregate_id=order.id,
            event_type="order.placed",
            payload=req.model_dump(),
        ))
    return order.id
```

### Alternative: CDC with Debezium

Instead of polling, use **Change Data Capture** to stream outbox table changes directly from the PostgreSQL WAL:

```
PostgreSQL WAL ──→ Debezium ──→ Kafka
```

**Advantages over polling:**
- Lower latency (near real-time)
- No polling load on database
- Exactly-once semantics with Kafka Connect offsets

**When to use polling vs CDC:**
- **Polling**: simpler, no extra infrastructure, good for < 1000 events/sec
- **CDC**: lower latency, better throughput, requires Kafka + Debezium infrastructure

---

## Saga Pattern

A saga is a sequence of local transactions. Each step has a **compensation action** that undoes it if a later step fails.

### Orchestration vs Choreography

| Approach | Coordination | Pros | Cons |
|----------|-------------|------|------|
| **Orchestration** | Central coordinator | Clear flow, easy to debug | Single point of coordination |
| **Choreography** | Events between services | Loosely coupled | Hard to track, implicit flow |

**Recommendation:** Start with orchestration. Choreography only when services are truly independent.

### Go -- Orchestrated Saga

```go
type SagaStep struct {
    Name       string
    Execute    func(ctx context.Context) error
    Compensate func(ctx context.Context) error
}

type Saga struct {
    steps []SagaStep
}

func (s *Saga) Run(ctx context.Context) error {
    var completed []SagaStep
    for _, step := range s.steps {
        if err := step.Execute(ctx); err != nil {
            // Compensate in reverse order
            for i := len(completed) - 1; i >= 0; i-- {
                if cErr := completed[i].Compensate(ctx); cErr != nil {
                    log.Error().Err(cErr).Str("step", completed[i].Name).Msg("compensation failed")
                    // TODO: alert, manual intervention needed
                }
            }
            return fmt.Errorf("saga failed at %s: %w", step.Name, err)
        }
        completed = append(completed, step)
    }
    return nil
}

// Usage
saga := &Saga{steps: []SagaStep{
    {Name: "reserve_inventory", Execute: reserveInventory, Compensate: releaseInventory},
    {Name: "charge_payment",    Execute: chargePayment,    Compensate: refundPayment},
    {Name: "create_shipment",   Execute: createShipment,   Compensate: cancelShipment},
}}
err := saga.Run(ctx)
```

### Python -- Orchestrated Saga

```python
@dataclass
class SagaStep:
    name: str
    execute: Callable[[Any], Awaitable[None]]
    compensate: Callable[[Any], Awaitable[None]]

async def run_saga(steps: list[SagaStep], context: Any) -> None:
    completed: list[SagaStep] = []
    for step in steps:
        try:
            await step.execute(context)
            completed.append(step)
        except Exception as exc:
            for prev in reversed(completed):
                try:
                    await prev.compensate(context)
                except Exception as comp_err:
                    logger.error("compensation failed", step=prev.name, error=comp_err)
            raise SagaError(f"saga failed at {step.name}") from exc
```

---

## Dead Letter Queue (DLQ)

Messages that fail processing after max retries go to a DLQ for investigation.

### Error Classification

| Error Type | Action | Example |
|-----------|--------|---------|
| **Transient** | Retry with backoff | Network timeout, 503 |
| **Permanent** | Send to DLQ immediately | Malformed payload, 400 |
| **Poison pill** | Send to DLQ after N retries | Bug in consumer code |

### Go -- Consumer with DLQ

```go
func (c *Consumer) Process(ctx context.Context, msg Message) error {
    for attempt := 1; attempt <= c.maxRetries; attempt++ {
        err := c.handler.Handle(ctx, msg)
        if err == nil {
            return nil
        }
        if isPermanentError(err) {
            return c.sendToDLQ(ctx, msg, err, "permanent_error")
        }
        backoff := time.Duration(attempt*attempt) * 100 * time.Millisecond
        time.Sleep(backoff)
    }
    return c.sendToDLQ(ctx, msg, ErrMaxRetriesExceeded, "max_retries")
}

func (c *Consumer) sendToDLQ(ctx context.Context, msg Message, err error, reason string) error {
    return c.dlqPublisher.Publish(ctx, DLQMessage{
        Original:    msg,
        Error:       err.Error(),
        Reason:      reason,
        FailedAt:    time.Now(),
        RetryCount:  c.maxRetries,
    })
}
```

---

## Idempotent Consumer Pattern

Prevent duplicate processing when messages are delivered more than once.

### Go -- Deduplication Table

```go
func (c *Consumer) HandleIdempotent(ctx context.Context, msg Message) error {
    return pgx.BeginTxFunc(ctx, c.pool, pgx.TxOptions{}, func(tx pgx.Tx) error {
        // Attempt to claim this message ID
        tag, err := tx.Exec(ctx,
            `INSERT INTO processed_messages (message_id, processed_at)
             VALUES ($1, now())
             ON CONFLICT (message_id) DO NOTHING`, msg.ID)
        if err != nil {
            return fmt.Errorf("dedup check: %w", err)
        }
        if tag.RowsAffected() == 0 {
            return nil // already processed, skip
        }
        return c.handler.Handle(ctx, tx, msg)
    })
}
```

### Python -- Deduplication Decorator

```python
async def process_idempotent(self, message_id: str, handler: Callable) -> None:
    async with self.session.begin() as session:
        result = await session.execute(
            text("""INSERT INTO processed_messages (message_id, processed_at)
                    VALUES (:id, now())
                    ON CONFLICT (message_id) DO NOTHING"""),
            {"id": message_id},
        )
        if result.rowcount == 0:
            return  # already processed
        await handler(session)
```

---

## Event Sourcing (When to Consider)

Event sourcing stores **every state change** as an immutable event. Current state is derived by replaying events.

### When It Helps

| Use Case | Why Event Sourcing |
|----------|-------------------|
| **Audit trail required** | Complete history by design |
| **Temporal queries** | "What was the state at time T?" |
| **Complex business rules** | Events capture intent, not just result |
| **CQRS needed** | Natural fit for separate read/write models |

### When to Avoid

| Situation | Why Not |
|-----------|---------|
| Simple CRUD | Massive overkill |
| No audit requirements | Complexity without benefit |
| Team unfamiliar | Steep learning curve |
| Read-heavy, write-light | CRUD + read replicas is simpler |

**Rule of thumb:** If you're considering event sourcing, first try the transactional outbox pattern. It gives you 80% of the benefits with 20% of the complexity.

---

## Decision Tree: Which Pattern?

```
Need cross-service consistency?
├── NO → Use local transaction (see transaction-safety skill)
└── YES
    ├── Can tolerate eventual consistency?
    │   ├── YES → Transactional Outbox + async messaging
    │   └── NO → Consider Saga with orchestration
    └── Need compensation/rollback?
        ├── YES → Saga pattern
        └── NO → Outbox + idempotent consumer
```

> **See also:** `transaction-safety` for local transaction patterns, `reliability-patterns` for retry/circuit breaker, `durable-execution` for Temporal-based saga orchestration.
