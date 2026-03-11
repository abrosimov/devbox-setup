---
name: frontend-testing
description: >
  Frontend testing patterns with React Testing Library, Vitest, user-event, and MSW.
  Use when writing or reviewing frontend tests, mocking API calls, testing React
  components or hooks, or setting up test infrastructure for TypeScript/React projects.
  Also use when deciding between unit tests and e2e tests, or when choosing query
  strategies (getByRole vs getByTestId).
---

# Frontend Testing Reference

Test behaviour visible to users, not implementation details. Prefer integration tests (component + hooks + context + API mocking via MSW) over isolated unit tests.

Co-locate test files next to source: `user-card.tsx` / `user-card.test.tsx`.

---

## Unit / Integration Tests (React Testing Library + Vitest)

### Query Priority

1. **`getByRole`** — buttons, links, headings, form elements with accessible names
2. **`getByLabelText`** — form inputs associated with labels
3. **`getByPlaceholder`** — inputs without visible labels
4. **`getByText`** — non-interactive text content
5. **`getByTestId`** — structural containers, or when accessible queries are ambiguous

### When `getByTestId` Is the Right Choice

The rule "prefer accessible queries" applies to **single-instance elements**. In contexts with repeated elements, `getByTestId` on the **container** is often better:

```tsx
// Component: each row has a generic "Edit" button
<div data-testid={`user-row-${user.id}`}>
  <span>{user.name}</span>
  <button aria-label={`Edit ${user.name}`}>Edit</button>
</div>

// Test: scope to the container, then use accessible query within
const row = screen.getByTestId(`user-row-${userId}`);
const editButton = within(row).getByRole("button", { name: /edit/i });
```

### `within()` for Scoped Queries

Always scope queries when testing components that render lists or repeated sections:

```typescript
import { within } from "@testing-library/react";

// BAD: page-level query in list context
screen.getByRole("button", { name: "Delete" }); // throws if multiple

// GOOD: scope to the specific item
const card = screen.getByTestId("item-card-42");
within(card).getByRole("button", { name: "Delete" });
```

### User Events

Always use `@testing-library/user-event` over `fireEvent`:

```typescript
import userEvent from "@testing-library/user-event";
const user = userEvent.setup();

await user.click(button);
await user.type(input, "text");
await user.keyboard("{Enter}");
```

### API Mocking (MSW)

```typescript
import { http, HttpResponse } from "msw";
import { server } from "../mocks/server";

test("shows user list", async () => {
  server.use(
    http.get("/api/users", () =>
      HttpResponse.json([{ id: 1, name: "Alice" }])
    )
  );
  render(<UserList />);
  await screen.findByText("Alice");
});
```

---

## E2E Tests (Playwright)

For Playwright `.spec.ts` file patterns, see the `playwright-e2e` skill. Key differences from RTL:

| Concern | RTL (unit/integration) | Playwright (e2e) |
|---------|----------------------|-----------------|
| Scoping | `within(container)` | `locator.filter()` / `locator.getByRole()` |
| Navigation | Not applicable | Must `waitForURL` after SPA navigation |
| Strict mode | Throws on multiple matches | Throws on multiple matches |
| Fix for lists | `within()` + `getByTestId` container | Row `.filter({ hasText })` or scoped locator |
| Async | `findBy*` / `waitFor()` | Auto-wait built in; use `expect().toBeVisible()` |
