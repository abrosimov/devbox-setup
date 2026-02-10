---
name: db-mysql
description: >
  MySQL/InnoDB schema design patterns. Covers clustered index implications, composite index
  ordering, covering indexes, gh-ost migrations, utf8mb4, UUID in BINARY(16), and isolation levels.
  Triggers on: mysql, innodb, clustered index, gh-ost, pt-online-schema-change, utf8mb4,
  covering index, prefix index, galera, InnoDB Cluster.
---

# MySQL Schema Design Patterns (InnoDB)

Schema design patterns specific to MySQL with InnoDB engine. For application-side patterns, see `database` skill.

---

## Clustered Index: The Most Important Fact

InnoDB stores table data **physically ordered by primary key**. The PK IS the table.

| Implication | Detail |
|-------------|--------|
| Every secondary index stores a copy of the PK value | Large PKs bloat ALL indexes |
| Random PK values cause page splits | Pages fill to ~50% instead of ~94%, nearly doubling storage |
| Sequential inserts append to B-tree end | Fast, compact, no page splits |
| PK range scans are extremely fast | Physical locality = fewer disk reads |

**Consequence**: PK design is the single most impactful decision in MySQL schema design.

---

## Primary Key Strategy

| Approach | Storage | Index Performance | Distributed-Safe |
|----------|---------|-------------------|-----------------|
| `BIGINT AUTO_INCREMENT` | 8 bytes | Optimal (sequential) | No |
| `CHAR(36)` UUID | 36 bytes | Terrible (string comparison + random) | Yes but wasteful |
| `BINARY(16)` UUIDv4 | 16 bytes | Bad (random inserts, page splits) | Yes |
| `BINARY(16)` UUIDv7 | 16 bytes | Good (time-sorted, sequential-ish) | Yes |

**Recommendation**: `BINARY(16)` with UUIDv7 for distributed-ready. `BIGINT AUTO_INCREMENT` for single-node performance.

Store UUIDs as `BINARY(16)`, convert in application code. Never use `CHAR(36)`.

---

## Index Design

### Composite Index Ordering (Leftmost Prefix Rule)

Index on `(country, city, name)` supports:

| Query | Uses Index? |
|-------|-------------|
| `WHERE country = 'US'` | Yes |
| `WHERE country = 'US' AND city = 'NYC'` | Yes |
| `WHERE city = 'NYC'` | No (skips leftmost) |
| `WHERE country = 'US' ORDER BY city` | Yes (index for sort) |

**Column ordering rule**: Equality columns first → range columns → ORDER BY columns.

### Covering Indexes

All needed columns in the index — InnoDB reads only the index, never touches table data:

```sql
-- Query: SELECT email, name FROM users WHERE status = 'active'
CREATE INDEX idx_covering ON users (status, email, name);
```

### Prefix Indexes

For long strings — saves space but cannot be used for ORDER BY or covering:

```sql
CREATE INDEX idx_email_prefix ON users (email(20));
```

### Limits

Keep composite indexes to 3-4 columns max. More columns = more write overhead with diminishing query benefit.

---

## Character Set: utf8mb4 ALWAYS

MySQL's `utf8` is broken — it's actually 3-byte UTF-8 that cannot store emoji or many CJK characters.

```sql
CREATE TABLE users (
    ...
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

Set at server, database, table, AND column levels. Never use `utf8` — always `utf8mb4`.

---

## Zero-Downtime Schema Changes

### Tools

| Tool | Mechanism | Best For |
|------|-----------|----------|
| **gh-ost** | Tails binlog (triggerless), async | Large modern production; throttling support |
| **pt-online-schema-change** | DML triggers, synchronous | Legacy environments, tables with foreign keys |

Both create a shadow table, copy data in chunks, then atomically rename. gh-ost is preferred — no triggers means no contention with application writes.

### Safe Native DDL (MySQL 8.0+)

```sql
-- Instant: adding column (goes to end of row)
ALTER TABLE users ADD COLUMN bio TEXT, ALGORITHM=INSTANT;

-- Online: adding index without blocking writes
ALTER TABLE users ADD INDEX idx_email (email), ALGORITHM=INPLACE, LOCK=NONE;
```

**Use gh-ost** for anything that isn't `ALGORITHM=INSTANT` or `ALGORITHM=INPLACE, LOCK=NONE`.

---

## Partitioning

| Strategy | Use | Notes |
|----------|-----|-------|
| **RANGE** | Time-series, logs | `PARTITION BY RANGE (YEAR(created_at))` |
| **HASH** | Even distribution | `PARTITION BY HASH(user_id) PARTITIONS 16` |
| **KEY** | Like hash, MySQL picks function | `PARTITION BY KEY(id) PARTITIONS 8` |

**MySQL-specific constraints:**
- Partitioned tables CANNOT have foreign keys
- Partition key must be part of every unique index (including PK)
- The PK must include the partition key

**Consequence**: If you use UUIDv7 as PK and partition by `created_at`, the PK must be `(id, created_at)`.

---

## Transaction Isolation Levels

| Level | Default | Phantom Reads | Non-Repeatable Reads | Use |
|-------|---------|---------------|---------------------|-----|
| **REPEATABLE READ** | Yes | Prevented (gap locks) | Prevented | Default OLTP |
| **READ COMMITTED** | No | Possible | Possible | InnoDB Cluster / Galera |
| **SERIALIZABLE** | No | Prevented | Prevented | Financial (high contention cost) |

**Trade-off**: REPEATABLE READ holds snapshot for entire transaction — safe but extra overhead on long transactions. For InnoDB Cluster/Galera, use READ COMMITTED.

---

## Virtual Buckets

```sql
ALTER TABLE orders ADD COLUMN bucket_id SMALLINT
    AS (ABS(CRC32(id)) % 1024) STORED;
CREATE INDEX idx_orders_bucket ON orders (bucket_id, created_at);
```

---

## Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| `CHAR(36)` for UUIDs | 36 bytes bloats every secondary index | `BINARY(16)` |
| `utf8` charset | Cannot store emoji, CJK characters | `utf8mb4` |
| UUIDv4 as PK | Random inserts cause page splits | UUIDv7 or AUTO_INCREMENT |
| FK on partitioned tables | Not supported by MySQL | Remove FK, enforce in application |
| `SELECT *` with large BLOB/TEXT | Reads entire row from clustered index | Select specific columns |
| Stored procedures for business logic | Untestable, undeployable, vendor lock-in | Application code |
| Triggers | Invisible side effects, replication issues | Application code |
