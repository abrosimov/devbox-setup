---
name: db-clickhouse
description: >
  ClickHouse analytics database patterns. Triggers on: clickhouse, mergetree, olap, analytical database, time-series aggregation.
---

# ClickHouse Patterns

## Table Engines

### MergeTree Family

| Engine | Use Case | Deduplication |
|--------|----------|---------------|
| **MergeTree** | General-purpose, append-only logs | None |
| **ReplacingMergeTree** | Latest version of record (ORDER BY key) | On merge (eventual) |
| **SummingMergeTree** | Pre-aggregated metrics (SUM) | Sums numeric columns on merge |
| **AggregatingMergeTree** | Pre-aggregated with custom functions | Merges AggregateFunction columns |
| **CollapsingMergeTree** | Update/delete via sign column (-1/+1) | Collapses rows with opposite signs |
| **VersionedCollapsingMergeTree** | CollapsingMergeTree + version column | Safer collapsing with explicit version |

### Decision Matrix

```
Immutable logs, no updates → MergeTree
Latest version only (user profiles) → ReplacingMergeTree(version_column)
Real-time metrics aggregation → SummingMergeTree
Complex aggregations (quantiles, uniq) → AggregatingMergeTree
Frequent updates/deletes → VersionedCollapsingMergeTree(sign, version)
```

## Materialised Views

Real-time aggregation pipeline:

```sql
-- Source table (MergeTree)
CREATE TABLE events (
    timestamp DateTime,
    user_id UInt64,
    event_type String,
    amount Decimal(10, 2)
) ENGINE = MergeTree()
ORDER BY (user_id, timestamp);

-- Aggregated target (SummingMergeTree)
CREATE TABLE daily_revenue (
    date Date,
    user_id UInt64,
    total_amount SimpleAggregateFunction(sum, Decimal(10, 2))
) ENGINE = SummingMergeTree()
ORDER BY (date, user_id);

-- Materialised view (inserts into target on every insert to source)
CREATE MATERIALIZED VIEW daily_revenue_mv TO daily_revenue AS
SELECT
    toDate(timestamp) AS date,
    user_id,
    sum(amount) AS total_amount
FROM events
GROUP BY date, user_id;
```

## Data Pipelines

Kafka → Materialised View → MergeTree:

```sql
-- Kafka engine table (reads from Kafka topic)
CREATE TABLE events_queue (
    timestamp DateTime,
    user_id UInt64,
    event_type String,
    payload String
) ENGINE = Kafka()
SETTINGS
    kafka_broker_list = 'localhost:9092',
    kafka_topic_list = 'events',
    kafka_group_name = 'clickhouse_consumer',
    kafka_format = 'JSONEachRow';

-- Materialised view moves data from Kafka to MergeTree
CREATE MATERIALIZED VIEW events_consumer TO events AS
SELECT
    timestamp,
    user_id,
    event_type,
    JSONExtractString(payload, 'data') AS data
FROM events_queue;
```

## Partition Strategy

Partition by month for time-series data:

```sql
CREATE TABLE logs (
    timestamp DateTime,
    level String,
    message String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)  -- Monthly partitions
ORDER BY (timestamp, level);
```

**Partition pruning**: Query filters on `timestamp` will skip entire partitions.

**Partition management**:
```sql
-- Drop old partitions
ALTER TABLE logs DROP PARTITION '202401';

-- Detach/attach for maintenance
ALTER TABLE logs DETACH PARTITION '202402';
ALTER TABLE logs ATTACH PARTITION '202402';
```

**Guidelines**:
- 10-300 partitions per table (too many = overhead, too few = no pruning benefit)
- Partition by month for most time-series (day for very high volume)
- Never partition by unbounded cardinality (user_id, session_id)

## Primary Key Design

**NOT a uniqueness constraint** — determines:
1. **Sort order** on disk
2. **Compression efficiency** (sorted data compresses better)
3. **Index granularity** (sparse index every 8192 rows by default)

```sql
CREATE TABLE events (
    user_id UInt64,
    timestamp DateTime,
    event_type String,
    data String
) ENGINE = MergeTree()
ORDER BY (user_id, timestamp);  -- Primary key
```

**Query optimisation**:
- Fast: `WHERE user_id = 123` (first column in key)
- Fast: `WHERE user_id = 123 AND timestamp > '2024-01-01'` (prefix of key)
- Slow: `WHERE timestamp > '2024-01-01'` (not a prefix)
- Slow: `WHERE event_type = 'click'` (not in key)

**Key design rules**:
1. Put filtering columns first (user_id before timestamp)
2. Put high-cardinality columns before low-cardinality (user_id before event_type)
3. Maximum 3-5 columns (more = larger index)

## Query Optimisation

### PREWHERE

Filters before decompression (faster for selective queries):

```sql
-- Good: PREWHERE on cheap column, WHERE on expensive
SELECT *
FROM events
PREWHERE user_id = 123  -- Filters before decompression
WHERE JSONExtractString(data, 'field') = 'value';  -- Filters after
```

ClickHouse often applies PREWHERE automatically for single-column filters.

### Sampling

Fast approximate queries on large tables:

```sql
CREATE TABLE events (
    timestamp DateTime,
    user_id UInt64
) ENGINE = MergeTree()
ORDER BY user_id
SAMPLE BY intHash32(user_id);  -- Enable sampling

-- Query 10% of data
SELECT count()
FROM events SAMPLE 0.1
WHERE timestamp > now() - INTERVAL 1 DAY;
```

### Approximate Functions

Trade accuracy for speed:

```sql
-- Exact (slow on billions of rows)
SELECT uniq(user_id) FROM events;

-- Approximate (fast, ~2% error)
SELECT uniqCombined(user_id) FROM events;

-- Approximate quantiles
SELECT quantilesTDigest(0.5, 0.95, 0.99)(response_time) FROM logs;
```

## Anti-Patterns

### Too Many Parts

Each insert creates a new "part" (data file). Background merges combine parts.

**Problem**: Too many parts = slow queries, "Too many parts" error.

**Solutions**:
- Batch inserts (1000+ rows per INSERT)
- Use Buffer engine for micro-batching
- Increase `max_insert_block_size` setting

### SELECT *

ClickHouse is column-oriented — reading all columns is expensive.

```sql
-- Bad: reads all columns from disk
SELECT * FROM events WHERE user_id = 123;

-- Good: reads only needed columns
SELECT timestamp, event_type FROM events WHERE user_id = 123;
```

### JOINs on Non-Distributed Tables

In a cluster, JOIN requires shuffling data across nodes.

**Solutions**:
- Denormalise (duplicate data to avoid JOINs)
- Use dictionaries for dimension tables
- Use GLOBAL JOIN (broadcasts right table to all nodes)

```sql
-- Bad in distributed queries (each shard reads both tables)
SELECT * FROM events e
JOIN users u ON e.user_id = u.id;

-- Better: broadcast small table
SELECT * FROM events e
GLOBAL JOIN users u ON e.user_id = u.id;

-- Best: use dictionary
SELECT
    event_type,
    dictGet('users_dict', 'username', user_id) AS username
FROM events;
```

## Cluster Patterns

### Distributed Table

Proxy to shards:

```sql
-- On each shard: local table
CREATE TABLE events_local (
    timestamp DateTime,
    user_id UInt64
) ENGINE = MergeTree()
ORDER BY (user_id, timestamp);

-- On all nodes: distributed table
CREATE TABLE events AS events_local
ENGINE = Distributed(cluster_name, database, events_local, rand());
```

**Queries**:
- Read from `events` → queries all shards, merges results
- Write to `events` → distributes across shards (sharding key: `rand()`)

**Sharding key patterns**:
- `rand()` — uniform distribution
- `intHash64(user_id)` — same user always on same shard (for JOINs)

### Replication

ReplicatedMergeTree for high availability:

```sql
CREATE TABLE events_local (
    timestamp DateTime,
    user_id UInt64
) ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/events', '{replica}')
ORDER BY (user_id, timestamp);
```

Requires ZooKeeper for coordination. Automatic deduplication on insert (idempotent).
