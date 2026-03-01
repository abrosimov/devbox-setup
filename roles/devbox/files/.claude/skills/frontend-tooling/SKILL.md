---
name: frontend-tooling
description: >
  Frontend project tooling with Next.js, Vite, pnpm, ESLint, Prettier, and TypeScript config.
  Use when discussing project setup, build tools, package management, linting, formatting,
  or development tools. Triggers on: Next.js, Vite, pnpm, npm, ESLint, Prettier, TypeScript
  config, tsconfig, Storybook, build, lint, format.
---

# Frontend Tooling Reference

## Detect Project Tooling

Before running commands, detect the project setup from lock files and config files:

| Lock File | Package Manager | Run Command |
|-----------|-----------------|-------------|
| `pnpm-lock.yaml` | pnpm | `pnpm run` |
| `package-lock.json` | npm | `npm run` |
| `yarn.lock` | yarn | `yarn` |
| `bun.lockb` | bun | `bun run` |

| Config File | Framework |
|-------------|-----------|
| `next.config.*` | Next.js |
| `vite.config.*` | Vite |

| Config File | Test Runner |
|-------------|-------------|
| `vitest.config.*` | Vitest |
| `jest.config.*` | Jest |

**Rule**: Use whatever the project already uses. Never mix lock files.

## Pre-Flight Verification

Run these checks before declaring work complete:

```bash
npx tsc --noEmit && npx eslint . && npx prettier --check . && npm test && npm run build
```
