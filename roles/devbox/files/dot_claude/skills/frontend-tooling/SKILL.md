---
name: frontend-tooling
description: >
  Frontend project tooling with Next.js, Vite, pnpm, ESLint, Prettier, and TypeScript config.
  Use when discussing project setup, build tools, package management, linting, formatting,
  or development tools. Also use when working with tsconfig, Storybook configuration, or
  build pipelines.
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

Substitute `<pm>` with the package manager detected above (`pnpm`, `npm`, `yarn`, or `bun`) and its runner (`pnpm dlx`, `npx`, `yarn dlx`, `bunx`):

```bash
<runner> tsc --noEmit && <runner> eslint . && <runner> prettier --check . && <pm> test && <pm> run build
```

Concrete forms:

| Package manager | Preflight command |
|-----------------|-------------------|
| pnpm | `pnpm dlx tsc --noEmit && pnpm dlx eslint . && pnpm dlx prettier --check . && pnpm test && pnpm run build` |
| npm | `npx tsc --noEmit && npx eslint . && npx prettier --check . && npm test && npm run build` |
| yarn | `yarn dlx tsc --noEmit && yarn dlx eslint . && yarn dlx prettier --check . && yarn test && yarn build` |
| bun | `bunx tsc --noEmit && bunx eslint . && bunx prettier --check . && bun test && bun run build` |
