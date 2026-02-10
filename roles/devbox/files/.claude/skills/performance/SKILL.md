---
name: performance
description: >
  Performance profiling and optimisation patterns for Go and Python. Covers pprof,
  benchmarks, cProfile, py-spy, database performance, memory management, and bottleneck identification.
  Triggers on: performance, profiling, benchmark, pprof, cProfile, py-spy, optimise, optimize,
  bottleneck, memory leak, allocation, N+1, slow query.
---

# Performance Patterns

Profiling and optimisation for Go and Python.

---

## Golden Rule: Measure First

> "Premature optimisation is the root of all evil." — Knuth

**Never optimise without profiling.** Intuition about performance bottlenecks is wrong ~80% of the time.

| Step | Action |
|------|--------|
| 1. Reproduce | Create a reproducible benchmark/scenario |
| 2. Measure | Profile with proper tools |
| 3. Identify | Find the actual bottleneck (not the suspected one) |
| 4. Fix | Optimise the bottleneck only |
| 5. Verify | Re-measure to confirm improvement |

---

## Go Profiling

### pprof

```go
import _ "net/http/pprof"

// In main(), alongside your server:
go func() {
    log.Println(http.ListenAndServe("localhost:6060", nil))
}()
```

```bash
# CPU profile (30 seconds)
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30

# Memory profile
go tool pprof http://localhost:6060/debug/pprof/heap

# Goroutine dump
go tool pprof http://localhost:6060/debug/pprof/goroutine

# Inside pprof:
(pprof) top 20
(pprof) web         # Visual graph
(pprof) list MyFunc # Source-level annotation
```

### Benchmarks

```go
func BenchmarkProcess(b *testing.B) {
    data := setupTestData()
    b.ResetTimer()  // Exclude setup time
    for i := 0; i < b.N; i++ {
        Process(data)
    }
}

// Run with memory stats
// go test -bench=BenchmarkProcess -benchmem -count=5
```

### Memory Optimisation

| Technique | When | Example |
|-----------|------|---------|
| `sync.Pool` | Frequent alloc/free of same type | Buffer pools, temporary objects |
| Pre-allocated slices | Known or estimable size | `make([]T, 0, expectedLen)` |
| Avoid pointer indirection | Small structs (<64 bytes) | Value receivers, embedded structs |
| String interning | Many duplicate strings | `sync.Map` for canonical strings |

---

## Python Profiling

### cProfile

```python
import cProfile
import pstats

with cProfile.Profile() as pr:
    result = process_data(large_dataset)

stats = pstats.Stats(pr)
stats.sort_stats("cumulative")
stats.print_stats(20)
```

### py-spy (Production-Safe Sampling)

```bash
# Attach to running process
py-spy top --pid 12345

# Generate flame graph
py-spy record -o profile.svg --pid 12345

# Profile a script
py-spy record -o profile.svg -- python my_script.py
```

### Memory Profiling

```bash
# memory_profiler — line-by-line
pip install memory_profiler
python -m memory_profiler script.py

# tracemalloc — built-in
python -c "
import tracemalloc
tracemalloc.start()
# ... your code ...
snapshot = tracemalloc.take_snapshot()
for stat in snapshot.statistics('lineno')[:10]:
    print(stat)
"
```

### Python Memory Patterns

| Technique | When | Example |
|-----------|------|---------|
| Generators | Processing large sequences | `yield` instead of building list |
| `__slots__` | Many instances of same class | Saves ~40% memory per instance |
| `weakref` | Caches that shouldn't prevent GC | Observer patterns, caches |
| Streaming I/O | Large file processing | `for line in file:` not `file.readlines()` |

---

## Database Performance

| Issue | Detection | Fix |
|-------|-----------|-----|
| **N+1 queries** | Log shows N similar queries in loop | Batch fetch, JOIN, eager loading |
| **Missing index** | EXPLAIN shows sequential scan | Add index on filtered/joined columns |
| **Connection exhaustion** | Timeouts under load | Configure pool size, connection limits |
| **Long transactions** | Lock contention, deadlocks | Minimise transaction scope |
| **Large result sets** | High memory, slow response | Pagination, streaming, LIMIT |

---

## HTTP Performance

| Technique | Impact | Implementation |
|-----------|--------|----------------|
| Connection pooling | Avoid TCP handshake overhead | Configure HTTP client pool size |
| Keep-alive | Reuse connections | Default in most clients |
| Compression | Reduce bandwidth | `Accept-Encoding: gzip` |
| Caching | Eliminate redundant work | `Cache-Control`, ETags |
| Timeouts | Prevent resource exhaustion | Connect + read + total timeouts |

---

## When NOT to Optimise

| Situation | Action |
|-----------|--------|
| "This might be slow" | Measure first, then decide |
| Code runs once (migration, setup) | Don't optimise |
| Readability vs 5% speedup | Keep readable |
| Hot path in tight loop | YES, optimise this |
| p99 latency exceeds SLA | YES, profile and fix |
