---
name: frontend-anti-patterns
description: >
  Common frontend anti-patterns and decision trees for avoiding them. Use when reviewing
  component design, state management, or detecting over-engineering in React/TypeScript code.
  Triggers on: useEffect abuse, prop drilling, useMemo, useCallback, any type, barrel file,
  default export, giant component, premature abstraction, over-engineering.
---

# Frontend Anti-Patterns Reference

Quick reference for detecting and avoiding common React/TypeScript anti-patterns.

---

## Quick Decision Trees

### Should I Add State?

```
Do I need to store this value?
│
├─ Can it be derived from existing state/props?
│  └─ YES → Derive it during render. DO NOT store it. ❌
│
├─ Does it belong in the URL (filters, search, pagination)?
│  └─ YES → Use URL search params (nuqs / useSearchParams) ✅
│
├─ Is it server data (fetched from API)?
│  └─ YES → Use React Query / Server Component. NOT useState. ✅
│
├─ Is it form state?
│  └─ YES → Use react-hook-form. NOT manual useState per field. ✅
│
└─ Is it local UI state (open/close, selected tab)?
   └─ YES → useState in the lowest component that needs it ✅
```

### Should I Use `useEffect`?

```
What am I trying to do?
│
├─ Synchronise with external system (DOM, WebSocket, timer)?
│  └─ YES → useEffect is correct ✅
│
├─ Fetch data?
│  └─ Use React Query or Server Component, NOT useEffect ❌
│
├─ Transform data for rendering?
│  └─ Do it during render (derive, don't sync) ❌
│
├─ Handle a user event?
│  └─ Do it in the event handler ❌
│
├─ Reset state when props change?
│  └─ Use key prop to remount, NOT useEffect ❌
│
└─ Notify parent component?
   └─ Call callback in event handler, NOT useEffect ❌
```

### Should I Use `useMemo` / `useCallback`?

```
Is there a measured performance problem?
│
├─ NO → Don't memoize. Premature optimisation. ❌
│
└─ YES → What kind of problem?
   │
   ├─ Expensive computation (>1ms)?
   │  └─ useMemo ✅
   │
   ├─ Child component re-renders with React.memo?
   │  └─ useCallback for callback props ✅
   │
   ├─ Reference equality for dependency arrays?
   │  └─ useMemo for objects/arrays passed as deps ✅
   │
   └─ "Just in case" / "for performance"?
      └─ Don't memoize. Profile first. ❌
```

---

## Anti-Patterns Catalogue

### 1. `useEffect` for Derived State

**Problem**: Synchronising state that can be computed from other state.

```typescript
// ❌ WRONG — useEffect to sync derived state
const [items, setItems] = useState<Item[]>([])
const [filteredItems, setFilteredItems] = useState<Item[]>([])
const [searchQuery, setSearchQuery] = useState('')

useEffect(() => {
  setFilteredItems(items.filter(item => item.name.includes(searchQuery)))
}, [items, searchQuery])
// Bug: renders twice — once with stale filteredItems, once with updated

// ✅ RIGHT — derive during render
const [items, setItems] = useState<Item[]>([])
const [searchQuery, setSearchQuery] = useState('')
const filteredItems = items.filter(item => item.name.includes(searchQuery))
// Always in sync, single render
```

---

### 2. `useEffect` for Data Fetching

**Problem**: Manual fetch + setState + loading + error handling in useEffect.

```typescript
// ❌ WRONG — manual data fetching
const [users, setUsers] = useState<User[]>([])
const [loading, setLoading] = useState(true)
const [error, setError] = useState<Error | null>(null)

useEffect(() => {
  let cancelled = false
  fetch('/api/users')
    .then(r => r.json())
    .then(data => { if (!cancelled) setUsers(data) })
    .catch(err => { if (!cancelled) setError(err) })
    .finally(() => { if (!cancelled) setLoading(false) })
  return () => { cancelled = true }
}, [])

// ✅ RIGHT — React Query handles caching, deduplication, revalidation
const { data: users, isLoading, error } = useQuery({
  queryKey: ['users'],
  queryFn: () => fetch('/api/users').then(r => r.json()),
})

// ✅ ALSO RIGHT — Server Component (no client JS at all)
async function UsersPage() {
  const users = await getUsers()
  return <UserList users={users} />
}
```

---

### 3. `any` Type Escape Hatch

**Problem**: Using `any` to silence TypeScript errors instead of fixing the type.

```typescript
// ❌ WRONG
function handleResponse(data: any) {
  return data.users.map((u: any) => u.name)
}

// ✅ RIGHT — proper types
interface ApiResponse {
  users: User[]
}

function handleResponse(data: ApiResponse): string[] {
  return data.users.map(u => u.name)
}

// ✅ When type is genuinely unknown (API boundary)
function parseResponse(raw: unknown): ApiResponse {
  const parsed = apiResponseSchema.parse(raw)  // Zod validates at runtime
  return parsed
}
```

**When `unknown` is acceptable:**
- External API responses before validation
- `JSON.parse` results
- Error objects in catch blocks

**When `any` is NEVER acceptable:**
- Component props
- Function parameters/returns
- State types
- Internal utility functions

---

### 4. Prop Drilling

**Problem**: Passing props through intermediate components that don't use them.

```typescript
// ❌ WRONG — Layout and Sidebar don't use `user`, just pass it through
<App user={user}>
  <Layout user={user}>
    <Sidebar user={user}>
      <Avatar user={user} />
```

**Fix — choose based on situation:**

| Depth | Fix |
|-------|-----|
| 2 levels | Acceptable. Don't over-abstract. |
| 3 levels | Composition pattern (pass components, not data) |
| 4+ levels | React Context or Zustand |

```typescript
// ✅ FIX — composition (pass the component, not the data)
function App() {
  const user = useUser()
  return (
    <Layout sidebar={<Sidebar avatar={<Avatar user={user} />} />}>
      <MainContent />
    </Layout>
  )
}
```

---

### 5. Giant Components

**Problem**: Components exceeding 200 lines with mixed concerns.

**Symptoms:**
- Multiple `useState` + `useEffect` blocks
- Complex conditional rendering (nested ternaries)
- Inline event handlers with business logic
- Multiple responsibilities in one file

**Fix:**

| Extract | Into |
|---------|------|
| Data fetching + state logic | Custom hook |
| Repeated UI patterns | Sub-component |
| Business logic (validation, transformation) | Utility function |
| Complex conditional blocks | Separate component |

---

### 6. Barrel Files (index.ts Re-exports)

**Problem**: `index.ts` files that re-export everything from a directory.

```typescript
// ❌ WRONG — barrel file
// components/index.ts
export { Button } from './button'
export { Input } from './input'
export { Card } from './card'
// ... 50 more exports

// Importing ONE component loads ALL of them
import { Button } from '@/components'
```

**Why it's wrong:**
- Hurts tree-shaking and bundle size
- Circular dependency risk
- Slower IDE auto-import resolution
- Harder to find where things are defined

```typescript
// ✅ RIGHT — direct imports
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
```

---

### 7. Premature `useMemo` / `useCallback`

**Problem**: Wrapping everything in memoisation "for performance".

```typescript
// ❌ WRONG — premature memoisation
const userName = useMemo(() => `${user.first} ${user.last}`, [user])
const handleClick = useCallback(() => setOpen(true), [])
const items = useMemo(() => [1, 2, 3], [])

// ✅ RIGHT — just compute it
const userName = `${user.first} ${user.last}`
const handleClick = () => setOpen(true)
const items = [1, 2, 3]
```

**When memoisation IS justified:**
- ✅ Expensive computation (measured >1ms): `useMemo(() => heavySort(data), [data])`
- ✅ Reference stability for `React.memo` child: `useCallback(fn, [deps])`
- ✅ Object/array in dependency array of another hook
- ❌ String concatenation, simple filtering, basic arithmetic
- ❌ "Just in case" without measuring

---

### 8. Default Exports

**Problem**: Default exports make refactoring harder and auto-imports unreliable.

```typescript
// ❌ WRONG — can be imported as any name
export default function UserCard() { ... }

// In consumer:
import RandomName from './user-card'  // No error, confusing

// ✅ RIGHT — named export, consistent naming
export function UserCard() { ... }

// In consumer:
import { UserCard } from './user-card'  // Must use correct name
```

**Exception**: Next.js page and layout files require default exports — this is a framework convention.

---

### 9. Premature Component Abstraction

**Problem**: Creating reusable components before you have 2+ use cases.

```typescript
// ❌ WRONG — "reusable" component used exactly once
function GenericDataTable<T>({ data, columns, onSort, onFilter, ... }: Props<T>) {
  // 300 lines of generic table logic
}

// Only used here:
<GenericDataTable data={users} columns={userColumns} />

// ✅ RIGHT — specific component for the use case
function UserTable({ users }: { users: User[] }) {
  // Simple, focused, 50 lines
}
```

**Rule**: Build specific first. Extract generic when you have the 3rd use case.

---

## Red Flags — STOP and Review

Before creating any of these, verify you're not falling into a trap:

- [ ] `useEffect` with setState inside → Can this be derived during render?
- [ ] `useEffect` with fetch inside → Should this use React Query or Server Component?
- [ ] `useMemo` / `useCallback` → Is there a measured performance problem?
- [ ] `any` type → What is the actual type?
- [ ] `index.ts` barrel file → Use direct imports instead
- [ ] `export default` → Use named export (unless Next.js page/layout)
- [ ] Component >200 lines → Extract hooks, sub-components, utilities
- [ ] Context for frequently-changing data → Use Zustand or lift state
- [ ] New abstraction → Do you have 3+ use cases?
