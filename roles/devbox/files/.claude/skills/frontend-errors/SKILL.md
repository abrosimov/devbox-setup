---
name: frontend-errors
description: >
  Frontend error handling patterns and best practices. Use when discussing error boundaries,
  async error handling, form validation, API error handling, or user-facing error messages.
  Triggers on: error boundary, error handling, form validation, Zod, API error, try catch,
  error page, error.tsx, toast, notification.
---

# Frontend Error Handling Reference

Error handling patterns for TypeScript + React + Next.js projects.

---

## Error Categories

| Category | Source | Handling |
|----------|--------|----------|
| **Render errors** | Component throws during render | Error boundary |
| **Async errors** | API calls, data fetching | React Query error state / try-catch |
| **Validation errors** | User input | Zod + form library |
| **Route errors** | Page load failures, 404 | Next.js error.tsx / not-found.tsx |
| **Network errors** | Connection lost, timeout | Global error handler + retry |

---

## Error Boundaries

### Hierarchy

```
app/
├── error.tsx              ← Root catch-all (last resort)
├── global-error.tsx       ← Catches root layout errors
├── not-found.tsx          ← 404 page
├── users/
│   ├── error.tsx          ← Catches user feature errors
│   ├── not-found.tsx      ← User not found
│   └── [id]/
│       └── error.tsx      ← Catches individual user page errors
```

### Route-Level Error Boundary

```typescript
// app/users/error.tsx
'use client'

import { useEffect } from 'react'

export default function UsersError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log to error reporting service
    reportError(error)
  }, [error])

  return (
    <div role="alert" className="p-8 text-center">
      <h2 className="text-lg font-semibold">Failed to load users</h2>
      <p className="mt-2 text-muted-foreground">{error.message}</p>
      <button
        onClick={reset}
        className="mt-4 rounded-md bg-primary px-4 py-2 text-white"
      >
        Try again
      </button>
    </div>
  )
}
```

### Global Error Boundary

```typescript
// app/global-error.tsx — catches root layout errors
'use client'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html>
      <body>
        <div role="alert">
          <h2>Something went wrong</h2>
          <button onClick={reset}>Try again</button>
        </div>
      </body>
    </html>
  )
}
```

### Component-Level Error Boundary

For isolating risky widgets without breaking the whole page:

```typescript
import { ErrorBoundary } from 'react-error-boundary'

function Dashboard() {
  return (
    <div className="grid grid-cols-3 gap-4">
      <ErrorBoundary fallback={<WidgetError />}>
        <RevenueChart />
      </ErrorBoundary>
      <ErrorBoundary fallback={<WidgetError />}>
        <UserStats />
      </ErrorBoundary>
      <ErrorBoundary fallback={<WidgetError />}>
        <ActivityFeed />
      </ErrorBoundary>
    </div>
  )
}

function WidgetError() {
  return (
    <div role="alert" className="rounded-lg border border-destructive p-4">
      <p>Failed to load widget</p>
    </div>
  )
}
```

---

## Form Validation with Zod

### Schema Definition

```typescript
import { z } from 'zod'

export const createUserSchema = z.object({
  name: z
    .string()
    .min(2, 'Name must be at least 2 characters')
    .max(100, 'Name must be under 100 characters'),
  email: z
    .string()
    .email('Please enter a valid email address'),
  role: z.enum(['admin', 'user', 'guest'], {
    errorMap: () => ({ message: 'Please select a role' }),
  }),
  age: z
    .number({ invalid_type_error: 'Age must be a number' })
    .int('Age must be a whole number')
    .min(18, 'Must be at least 18')
    .optional(),
})

export type CreateUserInput = z.infer<typeof createUserSchema>
```

### Client-Side with react-hook-form

```typescript
'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { createUserSchema, type CreateUserInput } from './schema'

export function CreateUserForm() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateUserInput>({
    resolver: zodResolver(createUserSchema),
  })

  async function onSubmit(data: CreateUserInput) {
    const result = await createUser(data)
    if (result.error) {
      // Handle server-side errors
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      <div>
        <label htmlFor="name">Name</label>
        <input id="name" {...register('name')} aria-invalid={!!errors.name} />
        {errors.name && (
          <p role="alert" className="text-destructive">{errors.name.message}</p>
        )}
      </div>
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Creating...' : 'Create User'}
      </button>
    </form>
  )
}
```

### Server-Side with Server Actions

```typescript
// app/users/actions.ts
'use server'

import { createUserSchema } from './schema'

export async function createUser(formData: FormData) {
  const parsed = createUserSchema.safeParse({
    name: formData.get('name'),
    email: formData.get('email'),
    role: formData.get('role'),
  })

  if (!parsed.success) {
    return {
      success: false as const,
      errors: parsed.error.flatten().fieldErrors,
    }
  }

  try {
    await db.user.create({ data: parsed.data })
    revalidatePath('/users')
    return { success: true as const }
  } catch (error) {
    return {
      success: false as const,
      errors: { _form: ['Failed to create user. Please try again.'] },
    }
  }
}
```

---

## API Error Handling

### Typed API Client

```typescript
// lib/api.ts
class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(
      body.message ?? `Request failed: ${response.statusText}`,
      response.status,
      body.code,
    )
  }

  return response.json()
}
```

### React Query Error Handling

```typescript
function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => apiFetch<User[]>('/users'),
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status < 500) return false
      return failureCount < 3
    },
  })
}

// In component
function UserList() {
  const { data: users, error, isLoading } = useUsers()

  if (isLoading) return <UserListSkeleton />
  if (error) return <ErrorDisplay error={error} />

  return (/* render users */)
}
```

### Error Display Component

```typescript
interface ErrorDisplayProps {
  error: Error
  retry?: () => void
}

export function ErrorDisplay({ error, retry }: ErrorDisplayProps) {
  const message = error instanceof ApiError
    ? getApiErrorMessage(error)
    : 'An unexpected error occurred'

  return (
    <div role="alert" className="rounded-lg border border-destructive p-4">
      <p>{message}</p>
      {retry && (
        <button onClick={retry} className="mt-2">
          Try again
        </button>
      )}
    </div>
  )
}

function getApiErrorMessage(error: ApiError): string {
  switch (error.status) {
    case 400: return 'Invalid request. Please check your input.'
    case 401: return 'Please sign in to continue.'
    case 403: return 'You do not have permission to do this.'
    case 404: return 'The requested resource was not found.'
    case 429: return 'Too many requests. Please wait a moment.'
    default: return 'Something went wrong. Please try again.'
  }
}
```

---

## Error Message Principles

| Principle | Application |
|-----------|-------------|
| **User-friendly** | Never show stack traces, status codes, or technical details to users |
| **Actionable** | Tell the user what they can do: "Try again", "Sign in", "Check your input" |
| **Honest** | Don't blame the user for server errors ("Something went wrong" not "Invalid request") |
| **Specific** | "Email is already in use" not "Validation failed" |
| **Accessible** | Use `role="alert"` for errors, `aria-invalid` for form fields |

---

## Not Found (404) Handling

```typescript
// app/not-found.tsx — global 404
export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold">404</h1>
        <p className="mt-2">Page not found</p>
        <a href="/" className="mt-4 inline-block text-primary">
          Go home
        </a>
      </div>
    </div>
  )
}

// app/users/[id]/page.tsx — trigger 404 for missing resources
import { notFound } from 'next/navigation'

async function UserPage({ params }: { params: { id: string } }) {
  const user = await getUser(params.id)
  if (!user) notFound()
  return <UserProfile user={user} />
}
```

---

## Quick Reference

| Error Type | Handler |
|-----------|---------|
| Component render crash | `error.tsx` (route) or `ErrorBoundary` (component) |
| Root layout crash | `global-error.tsx` |
| Resource not found | `not-found.tsx` + `notFound()` |
| Form validation | Zod schema + react-hook-form |
| Server Action failure | Return error object, display in form |
| API call failure | React Query error state + retry |
| Network failure | Global error handler + offline detection |
| Async in event handler | try-catch, show toast/notification |
