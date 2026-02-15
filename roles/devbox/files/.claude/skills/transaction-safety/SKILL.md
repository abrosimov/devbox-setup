---
name: transaction-safety
description: >
  Transaction boundaries, isolation levels, savepoints, locking strategies, and connection
  pool management for Go, Python, and TypeScript. Prevents data corruption from improper
  transaction scope, network calls inside transactions, and pool exhaustion.
  Triggers on: transaction, isolation level, savepoint, locking, optimistic lock, pessimistic lock,
  upsert, race condition, connection pool, pgbouncer, deadlock, transaction boundary.
---

# Transaction Safety

Safe transaction patterns across Go, Python, and TypeScript. The foundation for reliable data operations.

---

## The Cardinal Rule: No Side Effects Inside Transactions

**NEVER make external HTTP calls, queue publishes, or other network I/O inside a database transaction.**

Why this destroys systems:
- **Lock contention** -- rows are locked while waiting for a remote service that may take seconds or timeout
- **Connection pool exhaustion** -- connections are held idle while the network call blocks
- **Partial state on rollback** -- if the transaction rolls back, the HTTP call already happened and cannot be undone
- **Cascading failures** -- slow external service → held locks → connection pool drain → entire system stalls

### The Pattern: Collect, Then Execute

```
// BAD -- external call inside transaction
BEGIN TX
  INSERT order
  HTTP POST to payment gateway  ← holds locks while waiting
  UPDATE order status
COMMIT

// GOOD -- separate concerns
BEGIN TX
  INSERT order (status: pending)
  INSERT outbox_event (type: payment_requested)  ← local write only
COMMIT
// After commit: process outbox event → call payment gateway
```

### Go -- Separate Transaction from Side Effects

```go
func (s *OrderService) CreateOrder(ctx context.Context, req CreateOrderReq) error {
    // Phase 1: local DB work only
    var orderID uuid.UUID
    err := pgx.BeginTxFunc(ctx, s.pool, pgx.TxOptions{}, func(tx pgx.Tx) error {
        var err error
        orderID, err = s.repo.InsertOrder(ctx, tx, req)
        if err != nil {
            return fmt.Errorf("insert order: %w", err)
        }
        // Stage the event inside the same transaction
        return s.repo.InsertOutboxEvent(ctx, tx, outbox.Event{
            AggregateID: orderID,
            Type:        "order.created",
            Payload:     req,
        })
    })
    if err != nil {
        return fmt.Errorf("create order tx: %w", err)
    }

    // Phase 2: side effects AFTER commit
    s.notifier.OrderCreated(ctx, orderID) // best-effort, idempotent
    return nil
}
```

### Python -- Keep Transaction Scope Tight

```python
async def create_order(self, req: CreateOrderReq) -> uuid.UUID:
    # Phase 1: DB-only work
    async with self.session.begin() as session:
        order = Order(status=OrderStatus.PENDING, **req.model_dump())
        session.add(order)
        session.add(OutboxEvent(
            aggregate_id=order.id,
            event_type="order.created",
            payload=req.model_dump(),
        ))
    # Phase 2: after commit
    await self.notifier.order_created(order.id)
    return order.id
```

### TypeScript -- Prisma Transaction Boundary

```typescript
async function createOrder(req: CreateOrderReq): Promise<string> {
  // Phase 1: DB-only
  const order = await prisma.$transaction(async (tx) => {
    const order = await tx.order.create({
      data: { status: "PENDING", ...req },
    });
    await tx.outboxEvent.create({
      data: {
        aggregateId: order.id,
        type: "order.created",
        payload: req,
      },
    });
    return order;
  });

  // Phase 2: after commit
  await notifier.orderCreated(order.id);
  return order.id;
}
```

---

## Transaction Isolation Levels

Start with **Read Committed** (PostgreSQL default). Upgrade only when you have a proven need.

| Level | Anomalies Prevented | Anomalies Allowed | Use When |
|-------|---------------------|-------------------|----------|
| **Read Committed** | Dirty reads | Non-repeatable reads, phantom reads | Default for most CRUD |
| **Repeatable Read** | Dirty + non-repeatable reads | Serialisation anomalies (rare) | Read-then-write patterns, reports |
| **Serializable** | All anomalies | Nothing (but more retries) | Financial calculations, inventory |

### Practical Rules

1. **Read Committed** -- fine for 95% of operations. Each statement sees latest committed data
2. **Repeatable Read** -- use when a transaction reads data and then makes decisions based on it (snapshot at transaction start)
3. **Serializable** -- use for correctness-critical operations where you need the database to detect conflicts. **Must handle serialisation errors with retry logic**

### Go -- Serializable with Retry

```go
func (s *InventoryService) Reserve(ctx context.Context, itemID uuid.UUID, qty int) error {
    return retry.Do(func() error {
        return pgx.BeginTxFunc(ctx, s.pool, pgx.TxOptions{
            IsoLevel: pgx.Serializable,
        }, func(tx pgx.Tx) error {
            stock, err := s.repo.GetStock(ctx, tx, itemID)
            if err != nil {
                return fmt.Errorf("get stock: %w", err)
            }
            if stock < qty {
                return ErrInsufficientStock
            }
            return s.repo.DecrementStock(ctx, tx, itemID, qty)
        })
    },
        retry.RetryIf(func(err error) bool {
            // Only retry serialisation failures, not business errors
            var pgErr *pgconn.PgError
            return errors.As(err, &pgErr) && pgErr.Code == "40001"
        }),
        retry.Attempts(3),
        retry.Delay(10*time.Millisecond),
    )
}
```

### Python -- Serializable with Retry

```python
from sqlalchemy import text
from tenacity import retry, retry_if_exception_type, stop_after_attempt

@retry(
    retry=retry_if_exception_type(SerializationError),
    stop=stop_after_attempt(3),
)
async def reserve_stock(self, item_id: UUID, qty: int) -> None:
    async with self.engine.begin() as conn:
        await conn.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
        stock = await self.repo.get_stock(conn, item_id)
        if stock < qty:
            raise InsufficientStockError(item_id, qty, stock)
        await self.repo.decrement_stock(conn, item_id, qty)
```

---

## Savepoints (Nested Transactions)

Use savepoints to partially roll back within a larger transaction.

### Go -- pgx Pseudo-Nested Transactions

```go
err := pgx.BeginTxFunc(ctx, pool, pgx.TxOptions{}, func(tx pgx.Tx) error {
    if err := insertParent(ctx, tx); err != nil {
        return err
    }
    // Savepoint: try optional enrichment, tolerate failure
    spErr := tx.BeginFunc(ctx, func(sp pgx.Tx) error {
        return enrichWithExternalData(ctx, sp)
    })
    if spErr != nil {
        log.Warn().Err(spErr).Msg("enrichment failed, continuing without it")
        // Savepoint rolled back, outer tx continues
    }
    return insertFinalRecord(ctx, tx)
})
```

### Python -- SQLAlchemy begin_nested

```python
async with session.begin():
    session.add(parent)
    try:
        async with session.begin_nested():  # SAVEPOINT
            session.add(optional_enrichment)
            await session.flush()
    except IntegrityError:
        pass  # savepoint rolled back, outer transaction continues
    session.add(final_record)
```

---

## Optimistic Locking

Prevent lost updates without holding database locks. Add a `version` column that increments on every update.

### Schema

```sql
CREATE TABLE orders (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status     TEXT NOT NULL,
    version    INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Go -- Version-Based Update

```go
func (r *OrderRepo) UpdateStatus(ctx context.Context, tx pgx.Tx, id uuid.UUID, newStatus string, expectedVersion int) error {
    tag, err := tx.Exec(ctx,
        `UPDATE orders SET status = $1, version = version + 1, updated_at = now()
         WHERE id = $2 AND version = $3`,
        newStatus, id, expectedVersion,
    )
    if err != nil {
        return fmt.Errorf("update order status: %w", err)
    }
    if tag.RowsAffected() == 0 {
        return ErrConcurrentModification
    }
    return nil
}
```

### Python -- SQLAlchemy Versioned Update

```python
from sqlalchemy.orm import MappedColumn, mapped_column

class Order(Base):
    __tablename__ = "orders"
    id: MappedColumn[uuid.UUID] = mapped_column(primary_key=True)
    status: MappedColumn[str]
    version: MappedColumn[int] = mapped_column(default=1)
    __mapper_args__ = {"version_id_col": version}  # SQLAlchemy auto-checks
```

### TypeScript -- Prisma Optimistic Lock

```typescript
async function updateOrderStatus(id: string, newStatus: string, expectedVersion: number) {
  const result = await prisma.order.updateMany({
    where: { id, version: expectedVersion },
    data: { status: newStatus, version: { increment: 1 } },
  });
  if (result.count === 0) {
    throw new ConcurrentModificationError(id);
  }
}
```

---

## Database-Level Idempotency

### INSERT ON CONFLICT (Upsert)

```sql
-- Idempotent insert: same data, same result
INSERT INTO processed_events (event_id, processed_at)
VALUES ($1, now())
ON CONFLICT (event_id) DO NOTHING;
-- Check: if rows affected = 0, event was already processed
```

### Advisory Locks for Distributed Coordination

```go
// Prevent concurrent processing of the same aggregate
func (r *Repo) TryLock(ctx context.Context, tx pgx.Tx, aggregateID uuid.UUID) (bool, error) {
    var acquired bool
    err := tx.QueryRow(ctx,
        `SELECT pg_try_advisory_xact_lock($1)`,
        hashUUID(aggregateID), // advisory locks use int64
    ).Scan(&acquired)
    return acquired, err
}
```

---

## Connection Pool Management

### Sizing Rules

| Setting | Rule of Thumb | Why |
|---------|--------------|-----|
| **Max connections** | `(2 * CPU cores) + effective_spindle_count` | PostgreSQL recommendation |
| **Min idle** | 2-5 | Avoid cold start latency |
| **Max lifetime** | 30 min | Prevent stale connections |
| **Idle timeout** | 5-10 min | Release unused connections |

### PgBouncer + asyncpg Pitfalls

When using PgBouncer in **transaction pooling mode**:
- **Disable prepared statement cache**: `statement_cache_size=0` in asyncpg
- **Use `NullPool`** in SQLAlchemy (let PgBouncer handle pooling)
- **No session-level state**: `SET` commands, temp tables, advisory locks won't persist across queries

```python
# SQLAlchemy with PgBouncer
engine = create_async_engine(
    dsn,
    poolclass=NullPool,  # PgBouncer handles pooling
    connect_args={"statement_cache_size": 0},  # disable asyncpg prepared statements
)
```

### Go -- pgx Pool Configuration

```go
config, _ := pgxpool.ParseConfig(dsn)
config.MaxConns = 20
config.MinConns = 2
config.MaxConnLifetime = 30 * time.Minute
config.MaxConnIdleTime = 5 * time.Minute
config.HealthCheckPeriod = 1 * time.Minute

pool, err := pgxpool.NewWithConfig(ctx, config)
```

---

## Quick Reference: Transaction Scope Checklist

Before writing a transaction, verify:

- [ ] **No network calls** inside the transaction (HTTP, gRPC, queue publish)
- [ ] **Smallest possible scope** -- begin late, commit early
- [ ] **Isolation level justified** -- default to Read Committed unless proven need
- [ ] **Retry logic** for Repeatable Read / Serializable (handle `40001` errors)
- [ ] **Optimistic locking** if concurrent updates are possible
- [ ] **Side effects staged** via outbox table or post-commit hooks
- [ ] **Connection pool sized** appropriately for expected concurrency

> **See also:** `distributed-transactions` skill for outbox pattern details, `reliability-patterns` for retry strategies, `database` for repository patterns.
