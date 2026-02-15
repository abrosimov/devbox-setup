---
name: frontend-reliability
description: >
  Frontend resilience patterns for React/Next.js/TypeScript. Covers optimistic updates with
  rollback, double-submit prevention, idempotency keys from the client, offline-first with
  IndexedDB and service workers, AbortController for request deduplication, and graceful
  degradation in the UI.
  Triggers on: optimistic update, double submit, offline first, service worker, IndexedDB,
  AbortController, request deduplication, stale-while-revalidate, frontend retry,
  frontend reliability, offline, sync queue.
---

# Frontend Reliability

Patterns that keep the UI responsive and data consistent even when the network is unreliable.

---

## Optimistic Updates with Rollback

Update the UI immediately, then reconcile with the server. If the server rejects, roll back.

### TanStack Query -- Full Pattern

```typescript
const updateTodo = useMutation({
  mutationFn: (todo: Todo) => api.updateTodo(todo),

  onMutate: async (newTodo) => {
    // 1. Cancel in-flight queries that would overwrite our optimistic update
    await queryClient.cancelQueries({ queryKey: ["todos", newTodo.id] });

    // 2. Snapshot current state for rollback
    const previousTodo = queryClient.getQueryData<Todo>(["todos", newTodo.id]);

    // 3. Optimistically update cache
    queryClient.setQueryData(["todos", newTodo.id], newTodo);

    // 4. Return snapshot for onError rollback
    return { previousTodo };
  },

  onError: (_err, _newTodo, context) => {
    // 5. Roll back to snapshot
    if (context?.previousTodo) {
      queryClient.setQueryData(["todos", context.previousTodo.id], context.previousTodo);
    }
  },

  onSettled: (_data, _error, variables) => {
    // 6. Always refetch to ensure server truth
    queryClient.invalidateQueries({ queryKey: ["todos", variables.id] });
  },
});
```

### When to Use Optimistic Updates

| Situation | Optimistic? | Why |
|-----------|-------------|-----|
| Toggle like/bookmark | Yes | Low-risk, easy rollback |
| Edit text field | Yes | Feels instant, server rarely rejects |
| Submit payment | **No** | High stakes; show loading state instead |
| Delete item | Maybe | Use with undo toast, not immediate delete |

### Anti-Pattern: Optimistic Without Rollback

```typescript
// BAD -- no rollback path, UI lies to user on failure
onMutate: async (newTodo) => {
  queryClient.setQueryData(["todos", newTodo.id], newTodo);
  // No snapshot saved, no onError handler
},
```

---

## Double-Submit Prevention

Three layers of defence, applied together:

### Layer 1: Disable UI During Submission

```typescript
function SubmitButton({ isPending }: { isPending: boolean }) {
  return (
    <button type="submit" disabled={isPending} aria-busy={isPending}>
      {isPending ? "Processing..." : "Submit"}
    </button>
  );
}
```

### Layer 2: Client-Side Idempotency Key

Generate a key **once per user action**, reuse on retries.

```typescript
function useIdempotentSubmit<TData, TVariables>(
  mutationFn: (variables: TVariables & { idempotencyKey: string }) => Promise<TData>,
) {
  const keyRef = useRef<string | null>(null);

  return useMutation({
    mutationFn: async (variables: TVariables) => {
      // Generate on first attempt, reuse on retry
      if (!keyRef.current) {
        keyRef.current = crypto.randomUUID();
      }
      return mutationFn({ ...variables, idempotencyKey: keyRef.current });
    },
    onSettled: () => {
      keyRef.current = null; // reset for next user action
    },
  });
}

// Usage
const submit = useIdempotentSubmit(async (data) => {
  return fetch("/api/orders", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": data.idempotencyKey,
    },
    body: JSON.stringify(data),
  });
});
```

### Layer 3: AbortController for Deduplication

Cancel the previous in-flight request when a new one starts.

```typescript
function useDedupedFetch() {
  const controllerRef = useRef<AbortController | null>(null);

  return useCallback(async (url: string, options?: RequestInit) => {
    // Abort previous request
    controllerRef.current?.abort();
    controllerRef.current = new AbortController();

    return fetch(url, {
      ...options,
      signal: controllerRef.current.signal,
    });
  }, []);
}
```

---

## Offline-First Patterns

### Architecture

```
User Action
    ↓
[Mutation Queue (IndexedDB)]  ← writes stored locally
    ↓
[Sync Engine]  ← processes queue when online
    ↓
[Server API]
    ↓
[Cache Update]  ← server response updates local cache
```

### IndexedDB Mutation Queue

```typescript
import { openDB, type IDBPDatabase } from "idb";

interface QueuedMutation {
  id: string;
  url: string;
  method: string;
  body: string;
  headers: Record<string, string>;
  createdAt: number;
  retryCount: number;
}

class MutationQueue {
  private db: IDBPDatabase | null = null;

  async init() {
    this.db = await openDB("app-offline", 1, {
      upgrade(db) {
        db.createObjectStore("mutations", { keyPath: "id" });
      },
    });
  }

  async enqueue(mutation: Omit<QueuedMutation, "id" | "createdAt" | "retryCount">) {
    await this.db!.put("mutations", {
      ...mutation,
      id: crypto.randomUUID(),
      createdAt: Date.now(),
      retryCount: 0,
    });
  }

  async processQueue() {
    const mutations = await this.db!.getAll("mutations");
    for (const mutation of mutations.sort((a, b) => a.createdAt - b.createdAt)) {
      try {
        await fetch(mutation.url, {
          method: mutation.method,
          body: mutation.body,
          headers: mutation.headers,
        });
        await this.db!.delete("mutations", mutation.id);
      } catch {
        // Will retry on next sync
        await this.db!.put("mutations", {
          ...mutation,
          retryCount: mutation.retryCount + 1,
        });
        break; // preserve order: don't process later mutations
      }
    }
  }
}
```

### Online/Offline Detection

```typescript
function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
    const onOnline = () => setIsOnline(true);
    const onOffline = () => setIsOnline(false);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  return isOnline;
}
```

### Conflict Resolution Strategies

| Strategy | When to Use | How |
|----------|-------------|-----|
| **Last-write-wins** | Low-conflict data (user preferences) | Timestamp comparison |
| **Server-wins** | Authoritative server state (inventory) | Always accept server version |
| **Client-wins** | User-generated content (drafts) | Always accept client version |
| **Manual merge** | High-value data (documents) | Show conflict UI to user |
| **ETag-based** | Concurrent editing | `If-Match` header, 409 on conflict |

```typescript
// ETag-based conflict detection
async function updateWithETag(id: string, data: unknown, etag: string) {
  const resp = await fetch(`/api/items/${id}`, {
    method: "PUT",
    headers: { "If-Match": etag },
    body: JSON.stringify(data),
  });
  if (resp.status === 409) {
    throw new ConflictError("Item was modified by another user");
  }
  return resp.json();
}
```

---

## Preventing Data Loss

### Unsaved Changes Warning

```typescript
function useUnsavedChanges(hasChanges: boolean) {
  useEffect(() => {
    if (!hasChanges) return;

    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      // Modern browsers show a generic message
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [hasChanges]);
}
```

### Auto-Save to Local Storage

```typescript
function useAutoSave<T>(key: string, data: T, debounceMs = 1000) {
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => {
      localStorage.setItem(key, JSON.stringify(data));
    }, debounceMs);
    return () => clearTimeout(timeoutRef.current);
  }, [key, data, debounceMs]);
}

// Restore on mount
function useRestoreAutoSave<T>(key: string): T | null {
  const [restored] = useState<T | null>(() => {
    const saved = localStorage.getItem(key);
    return saved ? JSON.parse(saved) : null;
  });
  return restored;
}
```

---

## Frontend Graceful Degradation

### Feature Flag Kill Switch

```typescript
function ProductPage({ productId }: { productId: string }) {
  const { data: product } = useQuery({ queryKey: ["product", productId] });
  const { data: flags } = useQuery({ queryKey: ["feature-flags"] });

  return (
    <div>
      <ProductDetails product={product} />

      {/* Disable recommendations when backend is struggling */}
      {flags?.recommendations_enabled && (
        <ErrorBoundary fallback={null}>
          <Suspense fallback={<RecommendationsSkeleton />}>
            <Recommendations productId={productId} />
          </Suspense>
        </ErrorBoundary>
      )}
    </div>
  );
}
```

### Stale-While-Revalidate with Fallback

```typescript
const { data, isError } = useQuery({
  queryKey: ["products", id],
  queryFn: () => api.getProduct(id),
  staleTime: 5 * 60 * 1000,     // 5 min before refetch
  gcTime: 30 * 60 * 1000,       // 30 min before cache eviction
  retry: 2,
  // On error, stale cache data is still returned
  // isError is true but data contains last successful fetch
});

if (isError && !data) {
  return <ErrorMessage />;  // truly no data available
}

// data may be stale but still useful
return <ProductView product={data} isStale={isError} />;
```

---

## Quick Reference

| Problem | Solution | Layer |
|---------|----------|-------|
| Double click → duplicate request | Disable button + idempotency key | UI + API |
| Network error during form submit | Retry with same idempotency key | Network |
| User navigates away with unsaved data | `beforeunload` + auto-save | Browser |
| Server down for maintenance | Stale cache + degraded UI | Cache |
| Concurrent edits by two users | ETag / optimistic locking | API |
| Offline user needs to work | IndexedDB queue + sync on reconnect | Storage |
| Slow API makes UI feel broken | Optimistic update + rollback on error | Cache |

> **See also:** `distributed-transactions` for server-side idempotency key handling, `reliability-patterns` for retry/circuit breaker concepts, `frontend-errors` for error boundary patterns, `frontend-patterns` for TanStack Query patterns.
