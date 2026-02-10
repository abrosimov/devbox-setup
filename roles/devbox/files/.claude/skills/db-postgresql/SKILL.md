---
name: db-postgresql
description: >
  PostgreSQL schema design patterns. Covers partitioning, index types, JSONB, advisory locks,
  materialised views, RLS, zero-downtime DDL, connection pooling, and EXPLAIN analysis.
  Triggers on: postgresql, postgres, pg, partitioning, JSONB, pgx, BRIN, GIN, GiST,
  advisory lock, materialised view, materialized view, row level security, RLS, PgBouncer.
---

# PostgreSQL Schema Design Patterns

Schema design patterns specific to PostgreSQL. For application-side patterns (pgx, sqlx, repositories, transactions), see `database` skill.

---

## Partitioning Strategies

**Declarative partitioning** (PG 10+) is the standard. Choose based on query patterns:

| Strategy | Use When | Example |
|----------|----------|---------|
| **Range** | Time-series, event logs, financial data | Partition `events` BY RANGE (`created_at`) monthly |
| **List** | Categorical data, tenant IDs, regions | Partition `orders` BY LIST (`country_code`) |
| **Hash** | Even write distribution, no natural key | Partition `sessions` BY HASH (`user_id`) 16 partitions |
| **Composite** | Two-level pruning needed | Range by month, then hash by tenant |

**Rules:**
- Target 10-50 partitions initially; keep each partition > 10,000 rows
- Thousands of tiny partitions cause planning overhead
- Always include partition key in WHERE clauses — queries without it scan ALL partitions
- Include partition key in all indexes for optimal pruning
- Don't partition tables under 10M rows — overhead exceeds benefit

---

## Index Types

| Index | When to Use | When NOT to Use |
|-------|-------------|-----------------|
| **B-tree** (default) | Equality and range (`=`, `<`, `>`, `BETWEEN`, `IS NULL`, `ORDER BY`) | Multi-value columns (arrays, JSONB) |
| **GIN** | JSONB containment `@>`, array ops, full-text `@@`, trigram `%` | Columns with frequent writes (high write overhead, bloat) |
| **GiST** | Geometric/spatial, range types, exclusion constraints | When GIN fits and space is acceptable |
| **BRIN** | Very large tables with physically ordered data (timestamps, auto-inc) | Randomly ordered data — needs physical correlation |
| **Hash** | Pure equality lookups only (`=`) | Range queries, ORDER BY — no support |

**Concrete patterns:**

```sql
-- Time-series: BRIN for range scans (tiny index, fast on ordered data)
CREATE INDEX idx_events_created_brin ON events USING brin (created_at);

-- JSONB document queries: GIN with jsonb_path_ops (smaller, faster for @>)
CREATE INDEX idx_items_metadata ON items USING gin (metadata jsonb_path_ops);

-- JSONB specific field: B-tree expression index (not GIN)
CREATE INDEX idx_items_status ON items ((metadata->>'status'));

-- Partial index on hot path
CREATE INDEX idx_orders_pending ON orders (created_at) WHERE status = 'pending';
```

**Anti-pattern**: GIN on entire JSONB column, then querying a single scalar field — planner won't use GIN for `metadata->>'status' = 'active'`. Use expression B-tree instead.

---

## JSONB Patterns

### When to Use

- Flexible/semi-structured edges (user preferences, feature flags, integration metadata)
- Data that varies per record with no fixed schema
- Rapid prototyping where schema evolves weekly

### When NOT to Use

- Data queried, filtered, or joined on frequently — promote to typed columns
- Relationships between entities
- Stable, known structure — use proper columns

### Indexing Strategy

```sql
-- For containment queries (does JSONB contain X?)
CREATE INDEX idx_metadata_gin ON items USING gin (metadata jsonb_path_ops);

-- For specific field lookups (treat like a regular column)
CREATE INDEX idx_metadata_status ON items ((metadata->>'status'));

-- Partial index on a JSONB field
CREATE INDEX idx_active_items ON items ((metadata->>'status'))
    WHERE (metadata->>'status') = 'active';
```

Use `jsonb_path_ops` over default `jsonb_ops` — smaller and faster for `@>` queries.

---

## Advisory Locks

Application-level locks not tied to any row:

```sql
-- Session-level: held until explicit release or disconnect
SELECT pg_advisory_lock(hashtext('process_payments'));
SELECT pg_advisory_unlock(hashtext('process_payments'));

-- Transaction-level: auto-released on commit/rollback
SELECT pg_advisory_xact_lock(hashtext('user:' || user_id::text));

-- Non-blocking: returns false instead of waiting
SELECT pg_try_advisory_lock(hashtext('singleton_job'));
```

**Use cases**: Singleton cron jobs, deduplicating concurrent operations, distributed mutex.

---

## Queue Pattern with SKIP LOCKED

```sql
-- Worker picks up tasks without blocking others
SELECT * FROM tasks
    WHERE status = 'pending'
    ORDER BY created_at
    LIMIT 10
    FOR UPDATE SKIP LOCKED;
```

Prefer `SKIP LOCKED` over advisory locks for job queues. Workers process different rows concurrently without contention.

---

## Materialised Views

```sql
CREATE MATERIALIZED VIEW mv_daily_stats AS
    SELECT date_trunc('day', created_at) AS day, count(*), sum(amount)
    FROM orders GROUP BY 1;

-- Required for CONCURRENTLY refresh
CREATE UNIQUE INDEX idx_mv_daily_stats_day ON mv_daily_stats (day);

-- Non-blocking refresh (requires unique index)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_stats;
```

**Rules:**
- Always create a unique index so you can use `CONCURRENTLY`
- Automate refresh with `pg_cron`
- Only one refresh runs at a time per view
- `CONCURRENTLY` only updates changed rows — faster for incremental changes
- Suitable for dashboards, reports, aggregated reads — NOT real-time data

---

## Row-Level Security (Multi-Tenancy)

```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON orders
    USING (tenant_id = current_setting('app.tenant_id')::uuid);

-- Application sets context per request
SET app.tenant_id = 'tenant-uuid-here';
```

**Rules:**
- RLS is a safety net, not the primary access control mechanism
- Application code should always include `tenant_id` in queries
- Index `tenant_id` as first column in composite indexes: `(tenant_id, created_at)`
- Table owner bypasses RLS — use `FORCE ROW LEVEL SECURITY` if owner queries too

---

## Zero-Downtime DDL

### Safe Operations

```sql
-- Adding column with default (PG 11+, no table rewrite)
SET lock_timeout = '5s';
ALTER TABLE users ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';

-- Creating index without blocking writes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users (email);

-- Adding constraint without full table lock
ALTER TABLE users ADD CONSTRAINT ck_users_age CHECK (age >= 0) NOT VALID;
ALTER TABLE users VALIDATE CONSTRAINT ck_users_age;
```

### Expand-and-Contract for Risky Changes

1. **Expand**: Add new column (backward-compatible)
2. **Migrate**: Backfill data, deploy code that writes to both
3. **Contract**: Drop old column after all readers updated

**Always set `lock_timeout`** before DDL. If the lock cannot be acquired in 5s, retry rather than blocking all traffic.

---

## Connection Pooling

### PgBouncer vs In-Process Pool

| Aspect | PgBouncer | pgx/asyncpg pool |
|--------|-----------|-------------------|
| Scope | Shared across all instances | Per-process |
| Mode | Transaction (recommended) | Connection-level |
| Best for | Multiple services, microservices | Single monolith |
| Prepared statements | Problematic in transaction mode | Full support |

### Pool Sizing

```
optimal_connections = (CPU_cores * 2) + effective_spindle_count
```

- SSD with data in RAM: spindle = 0 → 4-core = 8 connections
- SSD with data exceeding RAM: spindle = 1 → 4-core = 9 connections
- Each PostgreSQL connection costs ~5-10MB RAM (full OS process)
- Reserve 20% of `max_connections` for admin/monitoring

---

## EXPLAIN Analysis

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT ...;
```

| Red Flag | Meaning | Fix |
|----------|---------|-----|
| `Seq Scan` on large table | No usable index | Add index on filter columns |
| `Nested Loop` with large outer | O(N*M) | Ensure inner has index; consider Hash Join |
| `Sort` with high cost | In-memory or disk sort | Add index matching ORDER BY |
| `Rows Removed by Filter` >> `Rows` | Index not selective | More selective or compound index |
| `Buffers: shared read` high | Cache misses | Increase `shared_buffers` or add BRIN |

Use `pg_stat_statements` to find slow queries in production.
