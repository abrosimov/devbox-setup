---
name: db-cockroachdb
description: >
  CockroachDB schema design patterns. Covers multi-region, hash-sharded indexes, transaction
  retry handling, online DDL, global vs local indexes, and differences from PostgreSQL.
  Triggers on: cockroachdb, crdb, cockroach, multi-region, distributed sql, hash-sharded,
  regional by row, global table, serializable, transaction retry.
---

# CockroachDB Schema Design Patterns

Schema design patterns specific to CockroachDB. For application-side patterns, see `database` skill.

---

## How CockroachDB Differs from PostgreSQL

| Aspect | PostgreSQL | CockroachDB |
|--------|-----------|-------------|
| Architecture | Single-node (replicas read-only) | Distributed, every node reads AND writes |
| Storage | Heap (rows not ordered by PK) | Pebble/LSM (rows ordered by PK, like InnoDB) |
| Replication | Streaming (async/sync) | Raft consensus (synchronous, 3x) |
| Default isolation | READ COMMITTED | SERIALIZABLE |
| Schema changes | DDL takes locks | Online DDL, non-blocking |
| Horizontal scaling | Manual (Citus) | Built-in, automatic rebalancing |
| Wire protocol | Native | PostgreSQL-compatible |

**Critical**: PK-ordered storage means random UUIDs cause performance problems (like MySQL InnoDB). Use time-sorted keys.

---

## Primary Key Design

```sql
-- Good: UUIDv7 (time-sorted, distributed-safe)
CREATE TABLE orders (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ...
);

-- Good: hash-sharded auto-increment (distributes sequential writes)
CREATE TABLE events (
    id INT DEFAULT unique_rowid() PRIMARY KEY
        USING HASH WITH (bucket_count = 16),
    ...
);

-- BAD: plain SERIAL (creates hotspot on single range)
CREATE TABLE logs (
    id SERIAL PRIMARY KEY,  -- All writes hit one range leader
    ...
);
```

**Rule**: Never use bare `SERIAL`/`INT` auto-increment — it creates write hotspots. Use UUIDv7 or hash-sharded indexes.

---

## Multi-Region Patterns

### Setup

```sql
ALTER DATABASE mydb SET PRIMARY REGION = 'us-east1';
ALTER DATABASE mydb ADD REGION 'eu-west1';
ALTER DATABASE mydb ADD REGION 'ap-southeast1';
```

### Table Locality

| Pattern | How It Works | Use Case |
|---------|-------------|----------|
| **REGIONAL BY ROW** | Each row has `crdb_region` column; data lives in home region | User data with regional affinity |
| **GLOBAL** | Replicated to all regions; fast reads everywhere, slow writes | Reference data, config, feature flags |
| **REGIONAL** (default) | Entire table in one region | Tables used by one region only |

```sql
-- User data: fast reads/writes in home region
ALTER TABLE users SET LOCALITY REGIONAL BY ROW;

-- Config: fast reads everywhere (writes replicate to all regions)
ALTER TABLE feature_flags SET LOCALITY GLOBAL;
```

### Locality-Optimised Search

For unique lookups (`WHERE id = $1`) on REGIONAL BY ROW tables, CockroachDB searches the local region first — avoids cross-region latency when the row is local.

---

## Index Design

| Index Type | Scope | Use |
|-----------|-------|-----|
| **Local** | Per-region in REGIONAL BY ROW tables | Default; fast for queries including region |
| **Global** | Spans all regions | Unique constraints across regions |
| **Hash-sharded** | Distributes sequential key writes | High-write on monotonic columns |

**Rule**: Minimise global indexes — each write requires cross-region consensus.

```sql
-- Hash-sharded index on monotonic column
CREATE INDEX idx_events_created ON events (created_at)
    USING HASH WITH (bucket_count = 16);

-- Global unique index (cross-region consensus on write)
CREATE UNIQUE INDEX idx_users_email ON users (email) USING HASH;
```

---

## Transaction Retry Handling

CockroachDB uses serializable isolation. Transaction retries (`SQLSTATE 40001`) are **expected**, not exceptional:

```go
// Go pattern
for retries := 0; retries < maxRetries; retries++ {
    tx, err := pool.Begin(ctx)
    if err != nil {
        return fmt.Errorf("beginning transaction: %w", err)
    }

    err = doWork(ctx, tx)
    if err != nil {
        tx.Rollback(ctx)
        if isCRDBRetryError(err) {
            continue
        }
        return fmt.Errorf("executing work: %w", err)
    }

    if err := tx.Commit(ctx); err != nil {
        if isCRDBRetryError(err) {
            continue
        }
        return fmt.Errorf("committing: %w", err)
    }
    return nil
}
```

### Reducing Retries

- Use `SELECT FOR UPDATE` to preemptively lock rows
- Keep transactions short (fewer conflicts)
- Avoid hot rows (use hash-sharded indexes)
- Use CockroachDB client libraries with built-in retry logic

---

## Online DDL

CockroachDB schema changes are **non-blocking by default**:

| Operation | Blocking in PG? | Blocking in CRDB? |
|-----------|-----------------|-------------------|
| `ADD COLUMN` | No (PG 11+) | No |
| `DROP COLUMN` | Brief lock | No |
| `ADD INDEX` | Yes (without CONCURRENTLY) | No |
| `ALTER PRIMARY KEY` | Not supported online | **Yes, online** |
| `ADD CONSTRAINT` | Lock + validation | No (online validation) |

**Key differences from PostgreSQL:**
- No need for `CONCURRENTLY` keyword — always concurrent
- No need for `lock_timeout` — no risk of blocking application queries
- Schema changes are transactional and can be rolled back
- Primary keys can be changed online

---

## Connection Pooling

- Use PgBouncer or application-level pooling (pgx pool) — same as PostgreSQL
- Connection count matters less (distributed; each node handles connections independently)
- CockroachDB Serverless handles connection management automatically
- For self-hosted: set pool size per node, not globally
- Use the PostgreSQL connection pool sizing formula per node

---

## When CockroachDB Is the Right Choice

- Geo-distributed applications with data locality requirements
- Strong consistency across regions (financial, inventory)
- Survivability during region outages (automatic failover)
- Growing beyond single-node PostgreSQL
- Teams wanting PostgreSQL compatibility without managing replication

## When CockroachDB Is Overkill

- Single-region applications (PostgreSQL is simpler and faster)
- Early-stage products without geo-distribution needs
- Analytical/OLAP workloads (not optimised)
- Applications relying on PostgreSQL extensions (PostGIS, pg_trgm — partial support)
- Raw single-node performance (PG is faster per-node)

---

## Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| Bare `SERIAL` PK | Write hotspot on single range | UUIDv7 or hash-sharded |
| Too many global indexes | Every write requires cross-region consensus | Use local indexes where possible |
| Long transactions | More serialisation conflicts → more retries | Keep transactions short |
| No retry logic | `40001` errors crash the application | Always implement retry loop |
| Treating it like single-node PG | Ignoring distributed implications | Design for distribution |
| Stored procedures | Same problems as PG, plus distributed overhead | Application code |
