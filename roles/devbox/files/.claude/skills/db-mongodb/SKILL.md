---
name: db-mongodb
description: >
  MongoDB schema design patterns. Covers embedding vs referencing, compound indexes (ESR rule),
  shard key selection, aggregation pipeline optimisation, change streams, and read/write concerns.
  Triggers on: mongodb, mongo, embedding, referencing, sharding, shard key, aggregation pipeline,
  change stream, document model, ObjectId, replica set, read concern, write concern.
---

# MongoDB Schema Design Patterns

Schema design patterns specific to MongoDB. For application-side patterns, see `database` skill.

---

## Embedding vs Referencing

| Factor | Embed | Reference |
|--------|-------|-----------|
| Data accessed together? | Yes — embed | No — reference |
| Cardinality | One-to-few, one-to-many (bounded) | One-to-many (unbounded), many-to-many |
| Data changes independently? | No — embed | Yes — reference avoids update anomalies |
| Document size | Stays under 16MB | Could grow without bound |
| Read vs write ratio | Read-heavy — embed | Write-heavy — reference (avoid large doc updates) |

### Subset Pattern (Hybrid)

Embed the most-queried fields plus a reference to the full document:

```javascript
// Order with subset of product data
{
    _id: ObjectId("..."),
    items: [
        {
            product_id: ObjectId("..."),   // Reference for full lookup
            name: "Widget",                 // Embedded for display
            price: 29.99,                   // Embedded for calculation
            quantity: 2
        }
    ]
}
```

### Decision Checklist

1. Will the embedded array grow without bound? → **Reference**
2. Is the embedded data updated independently? → **Reference**
3. Do you always read parent + children together? → **Embed**
4. Is the child data shared across parents? → **Reference**

---

## Index Strategies

| Index Type | Use Case | Constraint |
|------------|----------|------------|
| **Compound** | Multi-field queries; ESR rule | Max 32 fields |
| **Partial** | Subset of documents (saves space) | Filter must match queries |
| **TTL** | Auto-expire documents (sessions, logs) | Single-field, date type only |
| **Text** | Basic full-text search | One per collection; prefer Atlas Search |
| **Wildcard** | Unknown/dynamic field names | One query field at a time |
| **Hashed** | Equality lookups, shard keys | No range queries |

### ESR Rule for Compound Indexes

**E**quality fields first → **S**ort fields → **R**ange fields.

```javascript
// Query: status = "active" AND created_at > lastWeek ORDER BY priority
// Index: { status: 1, priority: 1, created_at: 1 }
//         ^Equality    ^Sort        ^Range
```

### Partial Indexes

```javascript
db.orders.createIndex(
    { created_at: 1 },
    { partialFilterExpression: { status: "pending" } }
);
// Only indexes pending orders — much smaller, much faster
```

---

## Shard Key Selection

Three properties of a good shard key:

| Property | Bad Example | Good Example |
|----------|-------------|-------------|
| **High cardinality** | `status` (3 values) | `user_id` (millions) |
| **Even write distribution** | `created_at` (monotonic → one shard) | `hashed(user_id)` |
| **Query isolation** | Random field (scatter-gather) | `tenant_id` (queries route to one shard) |

```javascript
// Hashed: good write distribution
sh.shardCollection("db.orders", { user_id: "hashed" });

// Compound: query isolation + distribution
sh.shardCollection("db.events", { tenant_id: 1, _id: 1 });

// BAD: monotonic timestamp (all writes to one shard)
sh.shardCollection("db.logs", { created_at: 1 });  // DON'T
```

**Shard key is immutable after creation** — choose carefully. Use `analyzeShardKey` (MongoDB 7.0+) to evaluate candidates.

---

## Aggregation Pipeline Optimisation

### Critical Rules

1. **`$match` first** — filters early, uses indexes, reduces documents in pipeline
2. **`$project`/`$unset` early** — reduces document size in memory
3. **`$lookup` requires index** — index the foreign field or it's a nested-loop scan
4. **`$merge`/`$out`** — use for materialised views

### Example

```javascript
db.orders.aggregate([
    { $match: { status: "completed", created_at: { $gte: lastMonth } } },  // Filter first
    { $project: { user_id: 1, total: 1, created_at: 1 } },                // Reduce fields
    { $group: { _id: "$user_id", total_spent: { $sum: "$total" } } },
    { $sort: { total_spent: -1 } },
    { $limit: 100 }
]);
```

**Anti-pattern**: Aggregation without initial `$match` — scans entire collection.

### Materialised Views with $merge

```javascript
db.orders.aggregate([
    { $match: { status: "completed" } },
    { $group: { _id: "$user_id", total_orders: { $sum: 1 }, total_spent: { $sum: "$total" } } },
    { $merge: { into: "user_stats", whenMatched: "replace", whenNotMatched: "insert" } }
]);
```

Schedule with cron for dashboard data.

---

## Change Streams

```javascript
const pipeline = [{ $match: { operationType: { $in: ["insert", "update"] } } }];
const changeStream = collection.watch(pipeline, { fullDocument: "updateLookup" });

changeStream.on("change", (change) => {
    // change.fullDocument contains complete document after update
});
```

**Rules:**
- Always persist resume tokens for fault tolerance
- Use `watch()` (not raw `$changeStream` aggregation) for automatic resume
- Pre/post-images available in MongoDB 6.0+
- Use cases: cache invalidation, search index sync, event-driven architecture

---

## Schema Validation

```javascript
db.createCollection("users", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["email", "name", "created_at"],
            properties: {
                email: { bsonType: "string", pattern: "^.+@.+\\..+$" },
                name: { bsonType: "string", minLength: 1, maxLength: 100 },
                status: { enum: ["active", "inactive", "suspended"] },
                created_at: { bsonType: "date" }
            }
        }
    },
    validationLevel: "strict",
    validationAction: "error"
});
```

Use `validationLevel: "moderate"` during migration periods (validates only inserts and updates that match the schema, skips existing non-conforming documents).

---

## Read/Write Concerns

### Write Concerns

| Level | Durability | Latency | Use |
|-------|-----------|---------|-----|
| `w: 1` | Primary only | Lowest | Non-critical data |
| `w: "majority"` | Majority of replicas | Medium | **Default for production** |
| `w: 0` | Fire-and-forget | Minimal | Metrics, telemetry (acceptable loss) |

### Read Concerns

| Level | Consistency | Latency | Use |
|-------|------------|---------|-----|
| `"local"` | May read rollback-able data | Lowest | Analytics |
| `"majority"` | Only majority-committed | Medium | **Default for production** |
| `"linearizable"` | Strongest consistency | Highest | Financial, uniqueness checks |

**Anti-pattern**: `"linearizable"` without `maxTimeMS` — blocks indefinitely if majority of nodes are down.

---

## When MongoDB Is the Right Choice

- Schema varies significantly per document (IoT, CMS, product catalogues)
- Hierarchical/nested data mapping naturally to documents
- Rapid iteration with weekly schema changes
- Horizontal scaling as a day-one requirement
- Real-time analytics with aggregation pipeline

## When MongoDB Is the Wrong Choice

- Complex transactions across multiple collections
- Highly relational data with many joins
- Strong schema enforcement from day one
- Financial/banking core requiring strict multi-entity ACID
- Data fits naturally in rows/columns with stable relationships

---

## Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| `$where` / stored JavaScript | No index usage, full scan, security risk | Aggregation pipeline expressions |
| Unbounded arrays | Document grows past 16MB, slow updates | Reference pattern |
| No `$match` in aggregation | Full collection scan | Always filter first |
| Random shard key | Scatter-gather on every query | Compound key with query isolation |
| `w: 0` for important data | Data loss on failure | `w: "majority"` |
| Embedding frequently-updated data | Rewrites entire document on each update | Reference pattern |
