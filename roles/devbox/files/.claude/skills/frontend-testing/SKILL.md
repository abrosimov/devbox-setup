---
name: frontend-testing
description: >
  Frontend testing patterns with React Testing Library, Vitest, user-event, and MSW.
  Use when writing or reviewing frontend tests, mocking API calls, testing React
  components or hooks, or setting up test infrastructure for TypeScript/React projects.
---

# Frontend Testing Reference

Use React Testing Library, Vitest, and MSW. Follow standard testing practices -- test behaviour visible to users, not implementation details.

Prefer integration tests (component + hooks + context + API mocking via MSW) over isolated unit tests. Use accessible queries (`getByRole`, `getByLabelText`) over `getByTestId`.

Co-locate test files next to source: `user-card.tsx` / `user-card.test.tsx`.
