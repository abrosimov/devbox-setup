---
name: frontend-style
description: >
  Frontend style guide for naming, file organisation, TypeScript conventions, and imports.
  Use when discussing naming conventions, file structure, formatting rules, import organisation,
  or code style. Triggers on: naming, format, style, convention, file name, import, TypeScript
  config, PascalCase, camelCase, kebab-case.
---

# Frontend Style Reference

Naming, file organisation, and code style for TypeScript + React projects.

---

## Naming Conventions

### Files and Directories

| Entity | Convention | Example |
|--------|-----------|---------|
| Directories | kebab-case | `user-profile/`, `auth-wizard/` |
| Component files | kebab-case | `user-card.tsx`, `search-input.tsx` |
| Hook files | kebab-case with `use-` prefix | `use-auth.ts`, `use-debounce.ts` |
| Utility files | kebab-case | `format-date.ts`, `api-client.ts` |
| Type files | kebab-case | `types.ts`, `user-types.ts` |
| Test files | Same name + `.test` | `user-card.test.tsx` |
| Constants files | kebab-case | `constants.ts`, `routes.ts` |

### Code Identifiers

| Entity | Convention | Example |
|--------|-----------|---------|
| Components | PascalCase | `UserCard`, `SearchInput` |
| Hooks | camelCase with `use` prefix | `useAuth`, `useDebounce` |
| Functions | camelCase | `formatDate`, `validateEmail` |
| Variables | camelCase | `userName`, `isLoading` |
| Constants | SCREAMING_SNAKE_CASE | `MAX_RETRIES`, `API_BASE_URL` |
| Types/Interfaces | PascalCase | `User`, `CreateUserInput` |
| Enums (if used) | PascalCase + PascalCase members | `Status.Active` |
| Props interfaces | PascalCase + `Props` suffix | `UserCardProps` |

### Boolean Variables

Use auxiliary verbs for clarity:

```typescript
// ✅ GOOD — clear boolean intent
const isLoading = true
const hasError = false
const canSubmit = true
const shouldRefetch = false
const isVisible = true

// ❌ BAD — ambiguous
const loading = true
const error = false
const submit = true
```

### Event Handlers

| Pattern | Naming |
|---------|--------|
| Prop callback | `on[Event]`: `onClick`, `onSubmit`, `onSelect` |
| Internal handler | `handle[Event]`: `handleClick`, `handleSubmit` |

```typescript
interface Props {
  onSelect: (id: string) => void  // prop: on-prefix
}

function UserList({ onSelect }: Props) {
  const handleClick = (id: string) => {  // handler: handle-prefix
    onSelect(id)
  }
}
```

---

## TypeScript Conventions

### Interfaces vs Types

| Use | When |
|-----|------|
| `interface` | Object shapes, component props, extendable contracts |
| `type` | Unions, intersections, mapped types, utility types |

```typescript
// ✅ interface for props (extendable)
interface ButtonProps {
  variant: 'primary' | 'secondary'
  children: React.ReactNode
}

// ✅ type for unions
type Status = 'idle' | 'loading' | 'success' | 'error'

// ✅ type for utility/mapped types
type Partial<T> = { [P in keyof T]?: T[P] }
```

### Strict TypeScript Rules

- **No `any`** — use `unknown` + runtime validation
- **No `as` assertions** — narrow with type guards instead
- **No `!` non-null assertion** — handle null/undefined explicitly
- **No `// @ts-ignore`** — fix the type error
- **No `// @ts-expect-error`** — only in tests as last resort
- **No enums** — use `as const` objects or union types

```typescript
// ❌ BAD — enum
enum Status {
  Active = 'active',
  Inactive = 'inactive',
}

// ✅ GOOD — const object + type
const STATUS = {
  Active: 'active',
  Inactive: 'inactive',
} as const

type Status = (typeof STATUS)[keyof typeof STATUS]
```

### Function Declarations

```typescript
// ✅ PREFER — function declaration for components and named functions
function UserCard({ user }: UserCardProps) { ... }
function formatDate(date: Date): string { ... }

// ✅ OK — arrow for callbacks and inline functions
const handleClick = () => { ... }
users.filter((u) => u.active)

// ❌ AVOID — arrow for top-level components
const UserCard = ({ user }: UserCardProps) => { ... }
```

**Why function declarations:**
- Hoisted (can be defined after usage in same file)
- Better stack traces (named in error messages)
- Consistent with React conventions

### Component Props

```typescript
// ✅ GOOD — explicit interface, destructured props
interface UserCardProps {
  user: User
  onSelect: (id: string) => void
  variant?: 'compact' | 'full'
}

function UserCard({ user, onSelect, variant = 'full' }: UserCardProps) {
  // ...
}

// ❌ BAD — inline type, React.FC
const UserCard: React.FC<{ user: any; onClick: Function }> = (props) => {
  // ...
}
```

**Avoid `React.FC` because:**
- Implicit `children` typing (removed in React 18 but still confusing)
- Prevents generic components
- Arrow function expression vs declaration

---

## Import Organisation

### Order (top to bottom)

1. **React/framework imports** — `react`, `next/*`
2. **External packages** — `@tanstack/react-query`, `zod`
3. **Internal absolute imports** — `@/components/*`, `@/lib/*`
4. **Relative imports** — `./sub-component`, `../utils`
5. **Type-only imports** — `import type { User } from ...`
6. **CSS/style imports** — `import './styles.css'`

Separate each group with a blank line.

```typescript
import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'

import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

import { UserAvatar } from './user-avatar'

import type { User } from '@/types'

import './user-card.css'
```

### Path Aliases

Use `@/` for absolute imports from `src/`:

```typescript
// ✅ GOOD — absolute with alias
import { Button } from '@/components/ui/button'

// ❌ BAD — relative reaching up multiple levels
import { Button } from '../../../components/ui/button'
```

---

## File Structure Within a Component File

```typescript
// 1. Imports (grouped as above)

// 2. Types/interfaces
interface UserCardProps { ... }

// 3. Constants (if any)
const MAX_NAME_LENGTH = 50

// 4. Component (named export)
export function UserCard({ user }: UserCardProps) {
  // a. Hooks (all at top)
  const router = useRouter()
  const [isOpen, setIsOpen] = useState(false)

  // b. Derived state
  const displayName = user.name.slice(0, MAX_NAME_LENGTH)

  // c. Event handlers
  const handleClick = () => { ... }

  // d. Early returns (loading, error, empty)
  if (!user) return null

  // e. JSX return
  return (/* ... */)
}

// 5. Sub-components (if small and only used here)
function UserCardSkeleton() {
  return (/* ... */)
}
```

---

## CSS / Styling Conventions

### Tailwind CSS (Preferred)

```typescript
// ✅ GOOD — Tailwind utility classes
function Button({ children, variant }: ButtonProps) {
  return (
    <button className={cn(
      'rounded-md px-4 py-2 font-medium transition-colours',
      variant === 'primary' && 'bg-blue-600 text-white hover:bg-blue-700',
      variant === 'secondary' && 'border border-grey-300 hover:bg-grey-50',
    )}>
      {children}
    </button>
  )
}
```

### `cn` Utility (clsx + tailwind-merge)

```typescript
// lib/utils.ts
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

### Conditional Classes

```typescript
// ✅ GOOD — cn utility with conditional classes
<div className={cn(
  'base-class',
  isActive && 'active-class',
  variant === 'primary' ? 'primary-styles' : 'secondary-styles',
)} />

// ❌ BAD — template literal concatenation
<div className={`base-class ${isActive ? 'active' : ''} ${variant}`} />
```

---

## Exports

| Rule | Rationale |
|------|-----------|
| Named exports always | Consistent naming, better refactoring |
| One component per file | Clear ownership, easier to find |
| Co-locate types with components | Types travel with their component |
| No barrel files (`index.ts`) | Direct imports are clearer and tree-shake better |

**Exception**: Next.js pages, layouts, loading, error files require `export default`.

---

## Comments

Follow the `code-comments` skill rules:

| Comment Type | When |
|-------------|------|
| **WHY comments** | Non-obvious business rules, workarounds |
| **WARNING comments** | Gotchas, "don't change this because..." |
| **TODO comments** | Temporary, must reference ticket |
| **NEVER** | Narration: `// render the list`, `// handle click` |

```typescript
// ❌ FORBIDDEN
// Map users to cards
const cards = users.map(u => <UserCard key={u.id} user={u} />)

// ✅ ACCEPTABLE
// API returns timestamps in UTC; convert to local for display
const displayTime = utcToLocal(event.startTime)
```
