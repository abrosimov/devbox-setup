---
name: frontend-patterns
description: >
  Common frontend patterns and idioms. Use when discussing custom hooks, composition,
  compound components, render patterns, optimistic updates, error boundaries, Suspense,
  or React patterns. Triggers on: custom hook, composition, compound component, render prop,
  optimistic update, error boundary, Suspense, portal, forwardRef, HOC.
---

# Frontend Patterns Reference

Common patterns and idioms for TypeScript + React projects.

---

## Custom Hooks

### Extracting Logic

Extract reusable logic into custom hooks when:
- Logic is used in 2+ components
- Component is getting too complex (>100 lines of logic)
- Logic is testable independently

```typescript
// ✅ GOOD — extracted hook, testable with renderHook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])

  return debouncedValue
}

// Usage
function SearchInput() {
  const [query, setQuery] = useState('')
  const debouncedQuery = useDebounce(query, 300)
  // fetch with debouncedQuery
}
```

### Hook Naming

| Pattern | Convention | Example |
|---------|-----------|---------|
| State + logic | `use[Feature]` | `useAuth`, `useCart` |
| Data fetching | `use[Resource]` | `useUsers`, `useOrder` |
| Boolean toggle | `use[Thing]` returning `[value, toggle]` | `useDisclosure` |
| Side effect | `use[Action]` | `useClickOutside`, `useKeyPress` |

### Hook Rules

1. **Always prefix with `use`** — React enforces this
2. **Return tuples for simple state** — `const [value, setValue] = useToggle()`
3. **Return objects for complex state** — `const { data, error, isLoading } = useUsers()`
4. **No conditional hooks** — Hooks must be called in the same order every render

---

## Composition Pattern

### Children as Components (Preferred over Prop Drilling)

```typescript
// ❌ BAD — prop drilling through intermediate components
function Page() {
  const user = useUser()
  return <Layout user={user} />
}
function Layout({ user }: { user: User }) {
  return <Sidebar user={user} />  // Layout doesn't use user, just passes it
}
function Sidebar({ user }: { user: User }) {
  return <Avatar user={user} />
}

// ✅ GOOD — composition, pass components as children
function Page() {
  const user = useUser()
  return (
    <Layout sidebar={<Sidebar avatar={<Avatar user={user} />} />}>
      <MainContent />
    </Layout>
  )
}
```

### Slot Pattern

```typescript
interface CardProps {
  header?: React.ReactNode
  children: React.ReactNode
  footer?: React.ReactNode
}

function Card({ header, children, footer }: CardProps) {
  return (
    <div className="rounded-lg border">
      {header && <div className="border-b p-4">{header}</div>}
      <div className="p-4">{children}</div>
      {footer && <div className="border-t p-4">{footer}</div>}
    </div>
  )
}

// Usage — caller controls content without Card knowing details
<Card
  header={<h2>Title</h2>}
  footer={<Button>Save</Button>}
>
  <p>Content here</p>
</Card>
```

---

## Compound Components

For components with shared implicit state (tabs, accordions, menus):

```typescript
// Usage — clean API, shared state hidden inside
<Tabs defaultValue="profile">
  <TabsList>
    <TabsTrigger value="profile">Profile</TabsTrigger>
    <TabsTrigger value="settings">Settings</TabsTrigger>
  </TabsList>
  <TabsContent value="profile">Profile content</TabsContent>
  <TabsContent value="settings">Settings content</TabsContent>
</Tabs>
```

### When to Use

| Situation | Use Compound? |
|-----------|--------------|
| Components share implicit state (active tab, open item) | ✅ Yes |
| Parent-child relationship is semantic (Tabs → Tab) | ✅ Yes |
| Simple component with clear props | ❌ No — use regular props |
| One-off component | ❌ No — over-engineering |

---

## Error Boundaries

### Route-Level (Next.js Convention)

```typescript
// app/users/error.tsx
'use client'

export default function UsersError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div role="alert">
      <h2>Something went wrong</h2>
      <p>{error.message}</p>
      <button onClick={reset}>Try again</button>
    </div>
  )
}
```

### Component-Level (React ErrorBoundary)

```typescript
import { ErrorBoundary } from 'react-error-boundary'

function UserDashboard() {
  return (
    <ErrorBoundary
      fallback={<p>Failed to load widget</p>}
      onError={(error) => reportError(error)}
    >
      <ExpensiveWidget />
    </ErrorBoundary>
  )
}
```

### Placement Strategy

| Level | When |
|-------|------|
| Root (`app/error.tsx`) | Catch-all for unexpected errors |
| Route (`app/users/error.tsx`) | Feature-specific error recovery |
| Component | Isolate risky widgets (third-party, experimental) |

---

## Suspense & Loading

### Route-Level Loading (Next.js)

```typescript
// app/users/loading.tsx
export default function UsersLoading() {
  return <UserListSkeleton />
}
```

### Component-Level Suspense

```typescript
import { Suspense } from 'react'

function Dashboard() {
  return (
    <div>
      <h1>Dashboard</h1>
      <Suspense fallback={<ChartSkeleton />}>
        <AsyncChart />
      </Suspense>
      <Suspense fallback={<TableSkeleton />}>
        <AsyncTable />
      </Suspense>
    </div>
  )
}
```

### Rules

- **One Suspense per independent data source** — Don't wrap everything in one
- **Skeleton over spinner** — Skeletons reduce perceived loading time
- **Avoid layout shift** — Skeleton should match final layout dimensions

---

## Optimistic Updates

For mutations where the result is predictable:

```typescript
const updateTodo = useMutation({
  mutationFn: (todo: Todo) => api.patch(`/todos/${todo.id}`, todo),
  onMutate: async (newTodo) => {
    await queryClient.cancelQueries({ queryKey: ['todos'] })
    const previous = queryClient.getQueryData(['todos'])
    queryClient.setQueryData(['todos'], (old: Todo[]) =>
      old.map(t => t.id === newTodo.id ? newTodo : t)
    )
    return { previous }
  },
  onError: (_err, _newTodo, context) => {
    queryClient.setQueryData(['todos'], context?.previous)
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: ['todos'] })
  },
})
```

### When to Use

| Situation | Optimistic? |
|-----------|------------|
| Toggle (like, bookmark, checkbox) | ✅ Yes — predictable result |
| List reorder (drag and drop) | ✅ Yes — user expects instant feedback |
| Form submission creating new record | ❌ No — server assigns ID |
| Payment/transaction | ❌ No — must confirm success |

---

## Controlled vs Uncontrolled

### Decision Tree

```
Does parent need to read/write this value?
│
├─ YES → Controlled (value + onChange props)
│
└─ NO → Does parent need the value on submit only?
   │
   ├─ YES → Uncontrolled with ref or FormData
   │
   └─ NO → Uncontrolled (internal state)
```

```typescript
// Controlled — parent manages state
<Input value={name} onChange={setName} />

// Uncontrolled — component manages own state, parent reads on submit
<form onSubmit={(e) => {
  const formData = new FormData(e.currentTarget)
  handleSubmit(formData)
}}>
  <input name="email" defaultValue="user@example.com" />
</form>
```

---

## forwardRef Pattern

When a component needs to expose its DOM node to parents:

```typescript
import { forwardRef } from 'react'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  function Input({ label, error, ...props }, ref) {
    return (
      <div>
        <label>{label}</label>
        <input ref={ref} aria-invalid={!!error} {...props} />
        {error && <p role="alert">{error}</p>}
      </div>
    )
  }
)
```

### When to Use

| Situation | forwardRef? |
|-----------|------------|
| Primitive UI components (Input, Button) | ✅ Yes — parent may need focus/scroll |
| Form components | ✅ Yes — react-hook-form needs refs |
| Feature components (UserCard, Dashboard) | ❌ No — no reason to expose DOM |

---

## Portal Pattern

For rendering outside the component hierarchy (modals, tooltips, toasts):

```typescript
import { createPortal } from 'react-dom'

function Modal({ children, isOpen }: { children: React.ReactNode; isOpen: boolean }) {
  if (!isOpen) return null

  return createPortal(
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-50">
      <div className="fixed inset-0 bg-black/50" />
      <div className="relative z-10">{children}</div>
    </div>,
    document.body
  )
}
```

---

## Pattern Selection Quick Reference

| Need | Pattern |
|------|---------|
| Reusable logic across components | Custom hook |
| Avoid prop drilling | Composition (children/slots) |
| Shared implicit state (tabs, menus) | Compound components |
| Graceful error recovery | Error boundaries |
| Loading states | Suspense + skeleton |
| Instant UI feedback on mutation | Optimistic updates |
| Expose DOM node to parent | forwardRef |
| Render outside component tree | Portal |
| Conditional rendering with data | Controlled component |
| Form values on submit only | Uncontrolled + FormData |
