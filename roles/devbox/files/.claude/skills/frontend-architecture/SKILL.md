---
name: frontend-architecture
description: >
  Frontend architecture patterns and design rules. Use when discussing component architecture,
  project structure, Server vs Client components, state management, data fetching, or
  module boundaries. Triggers on: component architecture, project structure, state management,
  Server Component, Client Component, data fetching, React Query, context, layout.
---

# Frontend Architecture Reference

Architectural design rules for TypeScript + React + Next.js projects.

---

## Project Structure — Feature-Based Organisation

Organise code by what it does, not by architectural layer:

```
src/
├── app/                      # Next.js App Router (pages, layouts, routes)
│   ├── layout.tsx
│   ├── page.tsx
│   ├── users/
│   │   ├── page.tsx
│   │   ├── [id]/
│   │   │   └── page.tsx
│   │   ├── loading.tsx
│   │   └── error.tsx
│   └── api/                  # API routes (if needed)
│       └── users/
│           └── route.ts
├── components/               # Shared/reusable components
│   ├── ui/                   # Primitive UI components (Button, Input, Card)
│   └── layout/               # Layout components (Header, Sidebar, Footer)
├── features/                 # Feature modules (self-contained)
│   ├── auth/
│   │   ├── components/       # Feature-specific components
│   │   ├── hooks/            # Feature-specific hooks
│   │   ├── lib/              # Feature-specific utilities
│   │   └── types.ts          # Feature-specific types
│   └── users/
│       ├── components/
│       ├── hooks/
│       ├── lib/
│       └── types.ts
├── hooks/                    # Shared custom hooks
├── lib/                      # Shared utilities, API clients
│   ├── utils.ts
│   ├── api.ts
│   └── validations.ts
├── types/                    # Shared type definitions
│   └── index.ts
└── styles/                   # Global styles (if needed)
    └── globals.css
```

### Rules

| Rule | Rationale |
|------|-----------|
| Feature folders are self-contained | High cohesion, low coupling |
| Shared components in `components/` | Reused across 2+ features |
| No circular imports between features | Features are independent modules |
| Co-locate related files | Types, hooks, utils next to components that use them |
| Flat over nested | Avoid deep nesting (max 3 levels inside a feature) |

### Adapt to Existing Codebase

**DO NOT impose this structure.** Follow what the codebase already uses:

| If codebase uses... | Follow it |
|---------------------|-----------|
| `src/components/` flat structure | Keep it flat |
| `pages/` directory (Pages Router) | Use Pages Router conventions |
| Feature folders with different naming | Match existing naming |
| CSS Modules | Use CSS Modules |
| Styled Components | Use Styled Components |

---

## Server Components vs Client Components

### The Default: Server Components

Everything is a Server Component unless it needs client-side interactivity.

```
Needs hooks (useState, useEffect)?  → Client Component
Needs event handlers (onClick)?     → Client Component
Needs browser APIs (window, etc.)?  → Client Component
None of the above?                  → Server Component ✅
```

### Decision Tree

```
Does this component need interactivity?
│
├─ NO → Server Component (default)
│  ├─ Can fetch data directly
│  ├─ Can access backend/DB
│  ├─ Can use async/await
│  └─ Zero client-side JS
│
└─ YES → Where does interactivity live?
   │
   ├─ Entire component is interactive → 'use client' on this file
   │
   └─ Only part is interactive → Split:
      ├─ Server Component (parent, fetches data)
      └─ Client Component (child, handles interaction)
```

### The Boundary Pattern

Push `'use client'` as far down the tree as possible:

```typescript
// ✅ GOOD — Server Component fetches, Client Component interacts
// app/users/page.tsx (Server Component)
async function UsersPage() {
  const users = await getUsers()
  return <UserList users={users} />
}

// features/users/components/user-list.tsx
'use client'
export function UserList({ users }: { users: User[] }) {
  const [selected, setSelected] = useState<string | null>(null)
  return (/* interactive list */)
}
```

```typescript
// ❌ BAD — entire page is Client Component just for one interaction
'use client'
export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  useEffect(() => { fetchUsers().then(setUsers) }, [])
  return (/* ... */)
}
```

---

## State Management

### Decision Tree

```
Where does this state live?
│
├─ URL (search, filters, pagination)?
│  └─ Use URL search params (nuqs or useSearchParams) ✅
│
├─ Server data (fetched from API)?
│  └─ Use React Query / TanStack Query ✅
│     (or Next.js Server Components for initial load)
│
├─ Form state?
│  └─ Use react-hook-form + Zod ✅
│
├─ Local UI state (open/closed, selected)?
│  └─ useState in the component ✅
│
├─ Shared between siblings (2-3 components)?
│  └─ Lift state to common parent ✅
│
├─ Shared across many components (theme, auth)?
│  └─ React Context ✅
│
└─ Complex cross-feature state?
   └─ Zustand (lightweight) or Redux Toolkit ✅
      (This is rare — most apps don't need it)
```

### Rules

| Rule | Why |
|------|-----|
| URL is the best state manager | Shareable, bookmarkable, SSR-compatible |
| Server state ≠ client state | Don't duplicate server data in client state |
| Derive, don't store | If it can be computed from other state, compute it |
| Scope as narrowly as possible | State in the lowest component that needs it |
| Context for low-frequency updates | Theme, auth, locale — NOT frequently changing data |

### Anti-Patterns

```typescript
// ❌ BAD — duplicating server state in client state
const [users, setUsers] = useState<User[]>([])
useEffect(() => {
  fetch('/api/users').then(r => r.json()).then(setUsers)
}, [])

// ✅ GOOD — let React Query manage server state
const { data: users } = useQuery({
  queryKey: ['users'],
  queryFn: () => fetch('/api/users').then(r => r.json()),
})

// ❌ BAD — storing derived state
const [items, setItems] = useState(initialItems)
const [filteredItems, setFilteredItems] = useState(initialItems)
// Must keep filteredItems in sync with items — bug-prone

// ✅ GOOD — derive during render
const [items, setItems] = useState(initialItems)
const [filter, setFilter] = useState('')
const filteredItems = items.filter(item => item.name.includes(filter))
```

---

## Data Fetching Patterns

### Server Components (Preferred for Initial Load)

```typescript
// app/users/page.tsx — fetches at request time on server
async function UsersPage() {
  const users = await db.user.findMany()
  return <UserList users={users} />
}
```

### React Query (Client-Side Mutations & Revalidation)

```typescript
// hooks/use-users.ts
export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => api.get<User[]>('/users'),
  })
}

export function useCreateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateUserInput) => api.post<User>('/users', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}
```

### Server Actions (Next.js Form Mutations)

```typescript
// app/users/actions.ts
'use server'

export async function createUser(formData: FormData) {
  const parsed = createUserSchema.safeParse({
    name: formData.get('name'),
    email: formData.get('email'),
  })
  if (!parsed.success) {
    return { error: parsed.error.flatten() }
  }
  await db.user.create({ data: parsed.data })
  revalidatePath('/users')
}
```

---

## Component Design Principles

### Smart vs Presentational

| Type | Responsibility | Example |
|------|---------------|---------|
| **Smart** (container) | Data fetching, state, business logic | `UserListPage`, `CheckoutFlow` |
| **Presentational** (UI) | Render props, emit events | `UserCard`, `Button`, `DataTable` |

Smart components use hooks and manage state. Presentational components are pure functions of their props.

### Component Size Limit

**Target: under 200 lines per file.** If a component exceeds this:

1. Extract sub-components into the same feature folder
2. Extract hooks for complex logic
3. Extract utility functions

### Props Design

| Principle | Application |
|-----------|-------------|
| Minimal props | Only what the component needs |
| Specific types | `variant: 'primary' \| 'secondary'` over `variant: string` |
| Children over render props | Unless you need to pass data back |
| Callback naming | `onAction` pattern: `onClick`, `onSubmit`, `onSelect` |
| Boolean defaults to false | `disabled` not `enabled`, `loading` not `loaded` |

---

## Quick Reference: Architecture Violations

| Violation | Fix |
|-----------|-----|
| `'use client'` on page that only fetches data | Remove directive, use Server Component |
| `useEffect` for data fetching | Use React Query or Server Component |
| `useState` for URL state (filters, search) | Use URL search params |
| `useState` + `useEffect` to sync derived state | Derive during render |
| Context for frequently-changing data | Use Zustand or lift state |
| Feature importing from another feature's internals | Extract to shared module |
| Deep prop drilling (>3 levels) | Composition pattern or Context |
| Giant component (>200 lines) | Extract sub-components and hooks |
| Barrel files (`index.ts` re-exporting everything) | Direct imports |
| `any` type to "fix" TypeScript error | Find the correct type |
