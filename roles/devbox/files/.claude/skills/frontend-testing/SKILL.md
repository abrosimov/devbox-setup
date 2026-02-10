---
name: frontend-testing
description: >
  Frontend testing patterns with React Testing Library, Vitest, user-event, and MSW.
  Triggers on: test, testing, React Testing Library, Vitest, Jest, user-event, MSW,
  mock, fixture, assertion, component test, hook test, integration test.
---

# Frontend Testing Reference

Testing patterns for TypeScript + React projects using React Testing Library, Vitest, and MSW.

---

## Testing Philosophy

### Test Behaviour, Not Implementation

```typescript
// ❌ BAD — testing implementation details
test('sets isOpen state to true', () => {
  const { result } = renderHook(() => useDisclosure())
  act(() => result.current.open())
  expect(result.current.isOpen).toBe(true)  // Testing internal state
})

// ✅ GOOD — testing behaviour visible to user
test('opens modal when button is clicked', async () => {
  render(<UserSettings />)
  await userEvent.click(screen.getByRole('button', { name: /settings/i }))
  expect(screen.getByRole('dialog')).toBeInTheDocument()
})
```

### The Testing Trophy

| Layer | Ratio | Tools |
|-------|-------|-------|
| **Static analysis** | Always on | TypeScript, ESLint |
| **Unit tests** | Many | Vitest, pure functions |
| **Integration tests** | Most value | React Testing Library + MSW |
| **E2E tests** | Few, critical paths | Playwright |

**Focus on integration tests** — they test components with their hooks, context, and API interactions together.

---

## Query Priority

Use queries that reflect how users find elements:

| Priority | Query | When |
|----------|-------|------|
| 1 | `getByRole` | Always preferred — accessible to everyone |
| 2 | `getByLabelText` | Form fields |
| 3 | `getByPlaceholderText` | When no label exists (fix the markup!) |
| 4 | `getByText` | Non-interactive content |
| 5 | `getByDisplayValue` | Filled form fields |
| 6 | `getByAltText` | Images |
| 7 | `getByTitle` | Rare, last resort |
| 8 | `getByTestId` | **Only when no semantic query works** |

```typescript
// ✅ GOOD — queries by accessible role
screen.getByRole('button', { name: /submit/i })
screen.getByRole('textbox', { name: /email/i })
screen.getByRole('heading', { level: 2 })
screen.getByRole('dialog')
screen.getByRole('alert')

// ❌ BAD — queries by implementation detail
screen.getByTestId('submit-button')
screen.getByClassName('btn-primary')
container.querySelector('.submit-btn')
```

---

## Component Testing

### Basic Component Test

```typescript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UserCard } from './user-card'

const mockUser = {
  id: '1',
  name: 'Alice Johnson',
  email: 'alice@example.com',
  role: 'admin' as const,
}

describe('UserCard', () => {
  it('displays user name and email', () => {
    render(<UserCard user={mockUser} onSelect={vi.fn()} />)

    expect(screen.getByText('Alice Johnson')).toBeInTheDocument()
    expect(screen.getByText('alice@example.com')).toBeInTheDocument()
  })

  it('calls onSelect with user id when clicked', async () => {
    const onSelect = vi.fn()
    render(<UserCard user={mockUser} onSelect={onSelect} />)

    await userEvent.click(screen.getByRole('button'))

    expect(onSelect).toHaveBeenCalledWith('1')
    expect(onSelect).toHaveBeenCalledTimes(1)
  })

  it('shows admin badge for admin users', () => {
    render(<UserCard user={mockUser} onSelect={vi.fn()} />)
    expect(screen.getByText('Admin')).toBeInTheDocument()
  })

  it('does not show admin badge for regular users', () => {
    render(
      <UserCard user={{ ...mockUser, role: 'user' }} onSelect={vi.fn()} />
    )
    expect(screen.queryByText('Admin')).not.toBeInTheDocument()
  })
})
```

### Form Testing

```typescript
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CreateUserForm } from './create-user-form'

describe('CreateUserForm', () => {
  it('shows validation errors for empty required fields', async () => {
    render(<CreateUserForm onSubmit={vi.fn()} />)

    await userEvent.click(screen.getByRole('button', { name: /create/i }))

    expect(await screen.findByText(/name must be at least/i)).toBeInTheDocument()
    expect(await screen.findByText(/valid email/i)).toBeInTheDocument()
  })

  it('submits valid data', async () => {
    const onSubmit = vi.fn()
    render(<CreateUserForm onSubmit={onSubmit} />)

    await userEvent.type(screen.getByLabelText(/name/i), 'Alice Johnson')
    await userEvent.type(screen.getByLabelText(/email/i), 'alice@example.com')
    await userEvent.click(screen.getByRole('button', { name: /create/i }))

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        name: 'Alice Johnson',
        email: 'alice@example.com',
      })
    })
  })

  it('disables submit button while submitting', async () => {
    const onSubmit = vi.fn(() => new Promise(() => {}))  // Never resolves
    render(<CreateUserForm onSubmit={onSubmit} />)

    await userEvent.type(screen.getByLabelText(/name/i), 'Alice')
    await userEvent.type(screen.getByLabelText(/email/i), 'a@b.com')
    await userEvent.click(screen.getByRole('button', { name: /create/i }))

    expect(screen.getByRole('button', { name: /creating/i })).toBeDisabled()
  })
})
```

---

## API Mocking with MSW

### Setup

```typescript
// test/mocks/handlers.ts
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/users', () => {
    return HttpResponse.json([
      { id: '1', name: 'Alice', email: 'alice@example.com' },
      { id: '2', name: 'Bob', email: 'bob@example.com' },
    ])
  }),

  http.post('/api/users', async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json(
      { id: '3', ...body },
      { status: 201 },
    )
  }),

  http.get('/api/users/:id', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      name: 'Alice',
      email: 'alice@example.com',
    })
  }),
]
```

```typescript
// test/mocks/server.ts
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

export const server = setupServer(...handlers)
```

```typescript
// test/setup.ts
import { server } from './mocks/server'

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

### Per-Test Overrides

```typescript
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'

it('shows error when API fails', async () => {
  server.use(
    http.get('/api/users', () => {
      return HttpResponse.json(
        { message: 'Internal Server Error' },
        { status: 500 },
      )
    }),
  )

  render(<UserList />)

  expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i)
})
```

---

## Custom Hook Testing

```typescript
import { renderHook, act } from '@testing-library/react'
import { useCounter } from './use-counter'

describe('useCounter', () => {
  it('starts at initial value', () => {
    const { result } = renderHook(() => useCounter(10))
    expect(result.current.count).toBe(10)
  })

  it('increments', () => {
    const { result } = renderHook(() => useCounter(0))
    act(() => result.current.increment())
    expect(result.current.count).toBe(1)
  })

  it('resets to initial value', () => {
    const { result } = renderHook(() => useCounter(5))
    act(() => result.current.increment())
    act(() => result.current.reset())
    expect(result.current.count).toBe(5)
  })
})
```

---

## Accessibility Testing

```typescript
import { render } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'

expect.extend(toHaveNoViolations)

it('has no accessibility violations', async () => {
  const { container } = render(<UserCard user={mockUser} onSelect={vi.fn()} />)
  const results = await axe(container)
  expect(results).toHaveNoViolations()
})
```

### What to Test for Accessibility

| Check | How |
|-------|-----|
| Screen reader labels | `getByRole('button', { name: ... })` |
| Error announcements | `getByRole('alert')` after error |
| Form labels | `getByLabelText(...)` |
| Focus management | `expect(element).toHaveFocus()` |
| Keyboard navigation | `await userEvent.tab()` + focus checks |
| ARIA attributes | `expect(element).toHaveAttribute('aria-expanded', 'true')` |

---

## Test File Organisation

```
features/users/
├── components/
│   ├── user-card.tsx
│   ├── user-card.test.tsx       ← Co-located with component
│   ├── user-list.tsx
│   └── user-list.test.tsx
├── hooks/
│   ├── use-users.ts
│   └── use-users.test.ts
└── lib/
    ├── user-utils.ts
    └── user-utils.test.ts
```

### Naming

| File | Test File |
|------|-----------|
| `user-card.tsx` | `user-card.test.tsx` |
| `use-auth.ts` | `use-auth.test.ts` |
| `format-date.ts` | `format-date.test.ts` |

---

## Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| Testing internal state/props | Test visible behaviour |
| `getByTestId` for everything | Use accessible queries (role, label, text) |
| Snapshot tests as primary tests | Write explicit assertions |
| Mocking everything | Use MSW for API, real context for state |
| Testing library internals | Test YOUR component's behaviour |
| No `await` on user events | Always `await userEvent.click(...)` |
| `fireEvent` instead of `userEvent` | `userEvent` simulates real user interaction |
