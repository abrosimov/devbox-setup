---
name: python-concurrency
description: >
  Python concurrency patterns and primitives. Use when discussing asyncio, threading,
  multiprocessing, concurrent.futures, GIL, event loop, TaskGroup, gather, thread pool,
  process pool, queues, or graceful shutdown in Python. Triggers on: asyncio, threading,
  multiprocessing, concurrent.futures, GIL, event loop, TaskGroup, gather, ThreadPoolExecutor,
  ProcessPoolExecutor, Queue, semaphore, graceful shutdown python, async context manager.
---

# Python Concurrency Reference

Concurrency and parallelism patterns for Python projects.

---

## When to Use Which

| Workload Type | Recommended Approach | Why |
|---------------|---------------------|-----|
| I/O-bound (HTTP, DB, files) | `asyncio` | Single thread, no GIL contention, scales to thousands of tasks |
| I/O-bound (simple, few tasks) | `threading` / `ThreadPoolExecutor` | Simpler than asyncio for small workloads |
| CPU-bound (data processing) | `multiprocessing` / `ProcessPoolExecutor` | Bypasses GIL with separate processes |
| Mixed I/O + CPU | `asyncio` + `ProcessPoolExecutor` | Async for I/O, offload CPU to processes |

### The GIL (Global Interpreter Lock)

The GIL allows only one thread to execute Python bytecode at a time:

- **Threading does NOT speed up CPU-bound work** — threads take turns, not run in parallel
- **Threading DOES speed up I/O-bound work** — threads release the GIL while waiting for I/O
- **Multiprocessing bypasses the GIL** — each process has its own interpreter and GIL

```python
# BAD — threading for CPU-bound work (no speedup due to GIL)
with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(cpu_heavy_function, data))  # still sequential!

# GOOD — multiprocessing for CPU-bound work
with ProcessPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(cpu_heavy_function, data))  # true parallelism
```

---

## asyncio

### TaskGroup (Python 3.11+, Preferred)

`TaskGroup` provides structured concurrency: all tasks complete (or are cancelled) before the group exits.

```python
async def fetch_all(urls: list[str]) -> list[dict]:
    results: list[dict] = []
    async with asyncio.TaskGroup() as tg:
        for url in urls:
            tg.create_task(fetch_and_collect(url, results))
    return results
```

**TaskGroup vs gather:**

| Feature | `asyncio.gather` | `asyncio.TaskGroup` |
|---------|------------------|---------------------|
| Error handling | `return_exceptions=True` to collect | Raises `ExceptionGroup` |
| Cancellation | Manual | Automatic — cancels remaining on first failure |
| Structured concurrency | No | Yes |
| Python version | 3.4+ | 3.11+ |

**Handling ExceptionGroup:**

```python
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(operation_a())
        tg.create_task(operation_b())
except* ValueError as eg:
    for exc in eg.exceptions:
        logger.error("validation error", exc_info=exc)
except* OSError as eg:
    for exc in eg.exceptions:
        logger.error("OS error", exc_info=exc)
```

### gather (Legacy Pattern)

```python
# Only when you need return_exceptions=True behaviour
results = await asyncio.gather(*coros, return_exceptions=True)
for result in results:
    if isinstance(result, Exception):
        logger.error("task_failed", error=str(result))
```

### Semaphore for Concurrency Limiting

```python
async def fetch_with_limit(urls: list[str], max_concurrent: int = 10) -> list[dict]:
    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited_fetch(url: str) -> dict:
        async with semaphore:
            return await fetch_url(url)

    return await asyncio.gather(*[limited_fetch(url) for url in urls])
```

### Running Blocking Code in asyncio

```python
async def read_file_async(path: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _read_file_sync, path)

# For CPU-bound work, use ProcessPoolExecutor
async def compute_async(data: list[float]) -> float:
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor() as pool:
        return await loop.run_in_executor(pool, cpu_heavy_function, data)
```

### Timeouts

```python
# Always use timeouts for external calls
async with asyncio.timeout(30):
    result = await external_service.call()

# Or with wait_for (older API)
result = await asyncio.wait_for(coro, timeout=30.0)
```

---

## Threading

### ThreadPoolExecutor

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_all(urls: list[str], max_workers: int = 10) -> list[dict]:
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(fetch_url, url): url for url in urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                results.append(future.result())
            except Exception:
                logger.error("fetch failed", url=url, exc_info=True)
    return results
```

### Lock and RLock

```python
# Lock — basic mutual exclusion
class Counter:
    def __init__(self) -> None:
        self._value = 0
        self._lock = threading.Lock()

    def increment(self) -> None:
        with self._lock:
            self._value += 1

# RLock — when same thread needs to acquire lock multiple times
class TreeNode:
    def __init__(self) -> None:
        self._lock = threading.RLock()

    def total(self) -> int:
        with self._lock:
            return self.value + sum(child.total() for child in self.children)
```

### Event for Signalling

```python
shutdown_event = threading.Event()

def worker(event: threading.Event) -> None:
    while not event.is_set():
        do_work()
        event.wait(timeout=1.0)  # sleep but wake immediately on signal
    cleanup()
```

---

## Multiprocessing

### ProcessPoolExecutor (Preferred)

```python
from concurrent.futures import ProcessPoolExecutor

def process_batch(items: list[Any], max_workers: int = 4) -> list[Any]:
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(cpu_heavy_function, items))
```

**Important:** Functions passed to `ProcessPoolExecutor` must be picklable — use named top-level functions, not lambdas or closures.

---

## Queue-Based Patterns

### asyncio.Queue (Producer-Consumer)

```python
async def producer(queue: asyncio.Queue[str], items: list[str]) -> None:
    for item in items:
        await queue.put(item)
    await queue.put(None)  # sentinel

async def consumer(queue: asyncio.Queue[str | None]) -> None:
    while True:
        item = await queue.get()
        if item is None:
            break
        await process(item)
        queue.task_done()
```

---

## Graceful Shutdown

### asyncio

```python
async def main() -> None:
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_event.set)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(run_server(shutdown_event))
        tg.create_task(run_worker(shutdown_event))

    logger.info("shutdown_complete")
```

### Threading

```python
def main() -> None:
    shutdown_event = threading.Event()

    def handle_signal(signum: int, frame) -> None:
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    workers = [threading.Thread(target=worker, args=(shutdown_event,)) for _ in range(4)]
    for w in workers:
        w.start()

    shutdown_event.wait()
    for w in workers:
        w.join(timeout=30.0)
```

---

## Cancellation Patterns

```python
async def cancellable_operation() -> str:
    try:
        result = await long_running_fetch()
        return result
    except asyncio.CancelledError:
        await cleanup()  # clean up resources
        raise  # ALWAYS re-raise CancelledError
```

---

## Common Pitfalls

| Anti-Pattern | Fix |
|--------------|-----|
| Blocking call in async function | Use async library or `run_in_executor` |
| Threading for CPU-bound work | Use `ProcessPoolExecutor` |
| Missing `await` on coroutine | Always `await` coroutines |
| Swallowing `CancelledError` | Clean up then re-raise |
| No timeout on async operations | Use `asyncio.wait_for` with timeout |
| Shared mutable state without lock | Protect with `Lock` or `RLock` |
| `asyncio.run()` inside running loop | Use `await` directly |
| Untracked `create_task` | Store task references, use `TaskGroup` |
| Acquiring locks in inconsistent order | Sort by object identity |
| Creating executor per function call | Reuse executor instances |
| Passing lambda to `ProcessPoolExecutor` | Use named top-level functions (pickling) |
| Fire-and-forget tasks | Use `TaskGroup` for lifecycle management |

### Deadlock Prevention

```python
# BAD — acquiring locks in different order (deadlock risk)
def transfer(from_acct, to_acct, amount):
    with from_acct.lock:
        with to_acct.lock:  # Thread B might lock these in opposite order
            from_acct.balance -= amount
            to_acct.balance += amount

# GOOD — consistent lock ordering
def transfer(from_acct, to_acct, amount):
    first, second = sorted([from_acct, to_acct], key=lambda a: id(a))
    with first.lock:
        with second.lock:
            from_acct.balance -= amount
            to_acct.balance += amount
```
