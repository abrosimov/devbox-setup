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

---

## Test File Structure

Standard structure for a test file — imports, test data, grouped describes:

```typescript
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { ComponentUnderTest } from './component-under-test'

const mockUser = {
  id: '1',
  name: 'Alice Johnson',
  email: 'alice@example.com',
  role: 'admin' as const,
}

describe('ComponentUnderTest', () => {
  it('displays user information', () => {
    // ...
  })

  it('handles user interaction', async () => {
    // ...
  })

  describe('when API fails', () => {
    it('shows error message', async () => {
      // ...
    })

    it('allows retry', async () => {
      // ...
    })
  })
})
```

Group by behaviour, not by method. Use nested `describe` for distinct behavioural groups.

---

## userEvent Setup Pattern

Always create `userEvent.setup()` per test — it ensures proper event sequencing:

```typescript
it('submits the form', async () => {
  const user = userEvent.setup()
  render(<CreateUserForm onSubmit={vi.fn()} />)

  await user.type(screen.getByLabelText(/name/i), 'Alice')
  await user.click(screen.getByRole('button', { name: /submit/i }))
})
```

Always `await` userEvent calls — they are async.

---

## Async State Testing

Test all async states: loading, success, error, empty, and retry.

```typescript
describe('UserList', () => {
  it('shows loading state initially', () => {
    render(<UserList />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('displays users after loading', async () => {
    render(<UserList />)

    expect(await screen.findByText('Alice Johnson')).toBeInTheDocument()
    expect(screen.getByText('Bob Smith')).toBeInTheDocument()
  })

  it('shows error message when API fails', async () => {
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

  it('shows empty state when no users exist', async () => {
    server.use(
      http.get('/api/users', () => {
        return HttpResponse.json([])
      }),
    )

    render(<UserList />)

    expect(await screen.findByText(/no users found/i)).toBeInTheDocument()
  })

  it('allows retry after error', async () => {
    const user = userEvent.setup()
    let callCount = 0
    server.use(
      http.get('/api/users', () => {
        callCount++
        if (callCount === 1) {
          return HttpResponse.json({ message: 'Error' }, { status: 500 })
        }
        return HttpResponse.json([mockUser])
      }),
    )

    render(<UserList />)

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /try again/i }))

    expect(await screen.findByText('Alice Johnson')).toBeInTheDocument()
  })
})
```

---

## Advanced Form Patterns

### Clearing Field-Level Errors on Correction

```typescript
it('clears field-level error when user corrects input', async () => {
  const user = userEvent.setup()
  render(<CreateUserForm onSubmit={vi.fn()} />)

  await user.click(screen.getByRole('button', { name: /create/i }))
  expect(await screen.findByText(/name must be at least/i)).toBeInTheDocument()

  await user.type(screen.getByLabelText(/name/i), 'Alice')

  await waitFor(() => {
    expect(screen.queryByText(/name must be at least/i)).not.toBeInTheDocument()
  })
})
```

---

## MSW Best Practices

**Default handlers** go in a shared setup file. **Per-test overrides** go in the test itself.

```typescript
// Shared handlers — test/mocks/handlers.ts
export const handlers = [
  http.get('/api/users', () => {
    return HttpResponse.json([
      { id: '1', name: 'Alice Johnson', email: 'alice@example.com' },
      { id: '2', name: 'Bob Smith', email: 'bob@example.com' },
    ])
  }),
]

// Per-test override — inside the test file
it('handles network error', async () => {
  server.use(
    http.get('/api/users', () => {
      return HttpResponse.error()
    }),
  )

  render(<UserList />)
  expect(await screen.findByRole('alert')).toBeInTheDocument()
})
```

**Important:** `onUnhandledRequest: 'error'` catches unmocked API calls — a test that silently hits the real network is a bug.

---

## Hook Testing with Providers

When hooks need providers (QueryClient, Router), wrap in a custom renderer:

```typescript
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    )
  }
}

describe('useUsers', () => {
  it('returns user list', async () => {
    const { result } = renderHook(() => useUsers(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.data).toHaveLength(2)
    })
  })
})
```

---

## Advanced Accessibility Testing

### Keyboard Navigation and Screen Reader Announcements

```typescript
describe('UserCard accessibility', () => {
  it('is keyboard navigable', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    render(<UserCard user={mockUser} onSelect={onSelect} />)

    await user.tab()
    expect(screen.getByRole('button')).toHaveFocus()

    await user.keyboard('{Enter}')
    expect(onSelect).toHaveBeenCalledWith('1')
  })

  it('announces errors to screen readers', async () => {
    const user = userEvent.setup()
    render(<CreateUserForm onSubmit={vi.fn()} />)

    await user.click(screen.getByRole('button', { name: /create/i }))

    const alerts = await screen.findAllByRole('alert')
    expect(alerts.length).toBeGreaterThan(0)
  })
})
```

### Accessibility Edge Cases

| Scenario | What to Test |
|----------|-------------|
| Focus management | Focus moves to correct element after action |
| Live regions | Dynamic content is announced |
| Form errors | Errors associated with fields via `aria-describedby` |
| Modal focus trap | Tab cycles within modal |
| Skip navigation | Skip link targets correct content |
| Keyboard shortcuts | All functionality reachable via keyboard |

---

## Error Boundary Testing

```typescript
describe('UserProfile error boundary', () => {
  it('shows fallback UI when child component throws', () => {
    const ThrowingComponent = () => {
      throw new Error('Test error')
    }

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <ErrorBoundary fallback={<div role="alert">Something went wrong</div>}>
        <ThrowingComponent />
      </ErrorBoundary>
    )

    expect(screen.getByRole('alert')).toHaveTextContent(/something went wrong/i)

    consoleSpy.mockRestore()
  })
})
```

---

## Custom Render with Providers

For components requiring providers (QueryClient, Router, Theme, Auth), create a reusable custom render:

```typescript
// test/utils.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, type RenderOptions } from '@testing-library/react'

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

function AllProviders({ children }: { children: React.ReactNode }) {
  const queryClient = createTestQueryClient()
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

function renderWithProviders(
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) {
  return render(ui, { wrapper: AllProviders, ...options })
}

export { renderWithProviders as render }
```

Import from `@/test/utils` instead of `@testing-library/react` when testing components that need providers.

---

## Bug-Hunting Scenarios

For EVERY component, systematically consider these categories.

### Input Boundaries

| Category | Test Cases |
|----------|-----------|
| Empty | `""`, `undefined`, `null`, `[]`, no items |
| Single | One element, one character, one item |
| Boundary | Max length (if defined), exactly at limit |
| Overflow | Very long strings, very large lists, deep nesting |

### Component-Specific Edge Cases

| Area | Edge Cases |
|------|-----------|
| **Text** | Empty, whitespace only, very long (overflow), special chars, HTML entities, RTL text |
| **Lists** | Empty, single item, many items (100+), items with missing optional fields |
| **Forms** | Empty submit, partial fill, paste into fields, autocomplete, autofill |
| **Buttons** | Double click, click while disabled, click during loading |
| **Images** | Missing src, broken URL, slow load, very large |
| **Dates** | Today, past, future, timezone edge, midnight, DST |
| **Numbers** | 0, negative, very large, decimal, NaN |
| **Auth** | Logged in, logged out, expired session, insufficient permissions |

### Security Testing (if code handles user input, URLs, or sensitive data)

| Pattern | What to Test |
|---------|-------------|
| XSS via `dangerouslySetInnerHTML` | Pass `<script>alert('xss')</script>` in data, verify DOMPurify sanitises it |
| URL injection | Pass `javascript:alert(1)` as URL, verify rejection before navigation |
| `eval()` / `new Function()` | Verify never called with user input |
| localStorage tokens | Verify auth tokens NOT stored in localStorage (httpOnly cookies instead) |
| Exposed secrets | Verify no API keys or secrets in rendered output |
| Open redirect | Pass `https://evil.com` as redirect URL, verify validated against allowlist |
| postMessage | Verify `event.origin` checked before processing messages |
| CSRF tokens | Verify API calls include CSRF token where required |
| Console.log | Verify no sensitive data in console output (check with `vi.spyOn(console, 'log')`) |

**Examples:**
```typescript
it('sanitises HTML content before rendering', () => {
  render(<RichContent html='<img onerror="alert(1)" src="x">' />)
  const img = document.querySelector('img[onerror]')
  expect(img).not.toBeInTheDocument()
})

it('rejects javascript: URLs', async () => {
  const user = userEvent.setup()
  render(<LinkInput onSubmit={vi.fn()} />)
  await user.type(screen.getByLabelText(/url/i), 'javascript:alert(1)')
  await user.click(screen.getByRole('button', { name: /save/i }))
  expect(await screen.findByRole('alert')).toHaveTextContent(/invalid url/i)
})
```

### Async Edge Cases

| Scenario | What to Test |
|----------|-------------|
| Race conditions | Component unmounts before response arrives |
| Stale data | Data changes while component is mounted |
| Rapid interaction | Multiple clicks before first response |
| Network failure | Timeout, connection refused, DNS failure |
| Partial data | API returns some fields as null/undefined |
| Empty response | `[]` or `{}` from API |

---

## What NOT to Test

### Type System Guarantees — Skip These

| Skip Testing | Why |
|--------------|-----|
| TypeScript type correctness | Compiler's job |
| Props type validation | TypeScript checks this at build time |
| React rendering mechanics | React's job, not yours |
| Third-party library internals | Not your code |

### Forbidden Test Patterns

```typescript
// FORBIDDEN — tests React, not your code
it('renders without crashing', () => {
  render(<UserCard user={mockUser} />)
})

// FORBIDDEN — tests prop passing, not behaviour
it('receives correct props', () => {
  render(<UserCard user={mockUser} />)
})

// FORBIDDEN — snapshot as sole test
it('matches snapshot', () => {
  const { container } = render(<UserCard user={mockUser} />)
  expect(container).toMatchSnapshot()
})

// FORBIDDEN — testing internal state
it('sets isLoading to true', () => {
  const { result } = renderHook(() => useUsers())
  expect(result.current.isLoading).toBe(true)
})
```

### Test Public Behaviour Only

Test through rendered output. Do not test:
- Internal state variables
- Private helper functions
- Implementation of event handlers (test the outcome instead)
- CSS class names (test visible behaviour)
- Component instance methods (test via user interaction)

---

## Test Data Realism

Use realistic data when code **validates or displays** that data. Mock data is acceptable for IDs and internal references.

| Data Type | When to Use Realistic Data |
|-----------|---------------------------|
| Names, emails | When displayed to user or validated |
| Dates | When formatted or compared |
| URLs | When validated or navigated to |
| Form input | When validation logic runs |
| API responses | When shape affects rendering |
| IDs | Mock is usually fine |

```typescript
// GOOD — realistic data for display/validation
const mockUser = {
  id: '1',
  name: 'Alice Johnson',
  email: 'alice@example.com',
  createdAt: '2024-01-15T10:30:00Z',
}

// BAD — meaningless data that hides bugs
const mockUser = {
  id: 'x',
  name: 'test',
  email: 'test',
  createdAt: 'date',
}
```

**Rule**: If tests pass with mock data but fail with real data, the tests were wrong.
