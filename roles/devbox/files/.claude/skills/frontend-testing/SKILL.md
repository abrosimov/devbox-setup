---
name: frontend-testing
description: >
  Frontend testing patterns with React Testing Library, Vitest, user-event, and MSW.
  Triggers on: test, testing, React Testing Library, Vitest, Jest, user-event, MSW,
  mock, fixture, assertion, component test, hook test, integration test.
---

# Frontend Testing Reference

Use React Testing Library, Vitest, and MSW. Follow standard testing practices -- test behaviour visible to users, not implementation details.

Prefer integration tests (component + hooks + context + API mocking via MSW) over isolated unit tests. Use accessible queries (`getByRole`, `getByLabelText`) over `getByTestId`.

Co-locate test files next to source: `user-card.tsx` / `user-card.test.tsx`.
