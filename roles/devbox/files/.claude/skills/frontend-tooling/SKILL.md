---
name: frontend-tooling
description: >
  Frontend project tooling with Next.js, Vite, pnpm, ESLint, Prettier, and TypeScript config.
  Use when discussing project setup, build tools, package management, linting, formatting,
  or development tools. Triggers on: Next.js, Vite, pnpm, npm, ESLint, Prettier, TypeScript
  config, tsconfig, Storybook, build, lint, format.
---

# Frontend Tooling Reference

Build tools, linting, formatting, and project configuration for frontend projects.

---

## Package Managers

### pnpm (Preferred)

```bash
# Install dependencies
pnpm install

# Add dependency
pnpm add react-hook-form

# Add dev dependency
pnpm add -D @testing-library/react

# Run script
pnpm run build
pnpm test

# Update dependencies
pnpm update --interactive
```

### Detect and Adapt

| Lock File | Manager | Run Command |
|-----------|---------|-------------|
| `pnpm-lock.yaml` | pnpm | `pnpm run` |
| `package-lock.json` | npm | `npm run` |
| `yarn.lock` | yarn | `yarn` |
| `bun.lockb` | bun | `bun run` |

**Rule**: Use whatever the project already uses. Never mix lock files.

---

## Next.js

### Project Structure

```
next.config.ts         # Next.js configuration
tsconfig.json          # TypeScript configuration
tailwind.config.ts     # Tailwind configuration
postcss.config.mjs     # PostCSS (required by Tailwind)
app/                   # App Router
├── layout.tsx         # Root layout
├── page.tsx           # Home page
├── globals.css        # Global styles
├── error.tsx          # Global error boundary
├── not-found.tsx      # 404 page
└── loading.tsx        # Global loading UI
```

### Key Commands

```bash
# Development
pnpm dev                # Start dev server (with Turbopack)

# Build
pnpm build              # Production build
pnpm start              # Start production server

# Lint
pnpm lint               # Run ESLint (Next.js built-in)
```

### Configuration

```typescript
// next.config.ts
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Strict mode catches common bugs
  reactStrictMode: true,

  // Image optimisation domains
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'example.com' },
    ],
  },
}

export default nextConfig
```

---

## Vite (For Non-Next.js Projects)

### Key Commands

```bash
# Development
pnpm dev                # Start dev server

# Build
pnpm build              # Production build
pnpm preview            # Preview production build

# Type check (Vite doesn't type-check)
pnpm tsc --noEmit
```

### Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

---

## TypeScript Configuration

### Strict tsconfig.json

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "exactOptionalPropertyTypes": true,
    "target": "ES2022",
    "lib": ["DOM", "DOM.Iterable", "ES2022"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "paths": {
      "@/*": ["./src/*"]
    },
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "isolatedModules": true,
    "noEmit": true
  },
  "include": ["src", "app"],
  "exclude": ["node_modules"]
}
```

### Key Strict Options

| Option | What It Does |
|--------|-------------|
| `strict` | Enables all strict checks (noImplicitAny, strictNullChecks, etc.) |
| `noUncheckedIndexedAccess` | Array/object index access returns `T \| undefined` |
| `noImplicitOverride` | Requires `override` keyword in class inheritance |
| `exactOptionalPropertyTypes` | Distinguishes `undefined` from missing property |

---

## ESLint

### Configuration (Flat Config)

```typescript
// eslint.config.mjs
import { dirname } from 'path'
import { fileURLToPath } from 'url'
import { FlatCompat } from '@eslint/eslintrc'

const __dirname = dirname(fileURLToPath(import.meta.url))
const compat = new FlatCompat({ baseDirectory: __dirname })

export default [
  ...compat.extends('next/core-web-vitals', 'next/typescript'),
  {
    rules: {
      // Enforce named exports
      'import/no-default-export': 'error',
      // Allow default in Next.js pages
      'import/no-default-export': ['error', {
        // Override per-file in Next.js
      }],
    },
  },
]
```

### Key Rules

| Rule | Enforcement |
|------|------------|
| `@typescript-eslint/no-explicit-any` | Error — no `any` types |
| `@typescript-eslint/no-unused-vars` | Error — no dead code |
| `react-hooks/rules-of-hooks` | Error — hooks called correctly |
| `react-hooks/exhaustive-deps` | Warn — dependency arrays complete |
| `import/no-default-export` | Error — named exports only |

### Commands

```bash
# Lint
npx eslint .

# Lint and fix
npx eslint --fix .

# Lint specific files
npx eslint src/components/
```

---

## Prettier

### Configuration

```json
// .prettierrc
{
  "semi": false,
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2,
  "plugins": ["prettier-plugin-tailwindcss"]
}
```

### Commands

```bash
# Check formatting
npx prettier --check .

# Fix formatting
npx prettier --write .
```

### Integration with ESLint

Use `eslint-config-prettier` to disable ESLint rules that conflict with Prettier:

```bash
pnpm add -D eslint-config-prettier
```

---

## Tailwind CSS

### Configuration (v4)

Tailwind 4 uses CSS-based configuration:

```css
/* app/globals.css */
@import 'tailwindcss';

@theme {
  --color-primary: #1a73e8;
  --color-primary-hover: #1557b0;
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --radius-sm: 4px;
  --radius-md: 8px;
}
```

### Configuration (v3)

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './features/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colours: {
        primary: 'hsl(var(--primary))',
        secondary: 'hsl(var(--secondary))',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}

export default config
```

---

## Storybook

### When to Use

| Situation | Storybook? |
|-----------|-----------|
| Building a component library | ✅ Yes |
| Designing components in isolation | ✅ Yes |
| Visual regression testing | ✅ Yes |
| Small project, few components | ❌ Overkill |
| Server Components only | ❌ Storybook is client-side |

### Story Format

```typescript
// components/ui/button.stories.tsx
import type { Meta, StoryObj } from '@storybook/react'
import { Button } from './button'

const meta = {
  title: 'UI/Button',
  component: Button,
  tags: ['autodocs'],
} satisfies Meta<typeof Button>

export default meta
type Story = StoryObj<typeof meta>

export const Primary: Story = {
  args: {
    variant: 'primary',
    children: 'Click me',
  },
}

export const Secondary: Story = {
  args: {
    variant: 'secondary',
    children: 'Click me',
  },
}

export const Disabled: Story = {
  args: {
    variant: 'primary',
    children: 'Click me',
    disabled: true,
  },
}
```

---

## Pre-Flight Verification Commands

| Check | Command | What It Catches |
|-------|---------|-----------------|
| TypeScript | `npx tsc --noEmit` | Type errors |
| ESLint | `npx eslint .` | Code quality, React rules |
| Prettier | `npx prettier --check .` | Formatting |
| Tests | `npx vitest run` or `npm test` | Regressions |
| Build | `npm run build` | SSR errors, import issues |

### Running All Checks

```bash
# Sequential — stops on first failure
npx tsc --noEmit && npx eslint . && npx prettier --check . && npm test && npm run build
```

---

## Detect Project Tooling

Before running commands, detect the project setup:

```bash
# Detect package manager
ls pnpm-lock.yaml package-lock.json yarn.lock bun.lockb 2>/dev/null

# Detect framework
ls next.config.* vite.config.* 2>/dev/null

# Detect test runner
ls vitest.config.* jest.config.* 2>/dev/null
```

| Found | Framework | Test Runner |
|-------|-----------|-------------|
| `next.config.*` | Next.js | Vitest or Jest |
| `vite.config.*` | Vite | Vitest |
| `jest.config.*` | Any | Jest |
| `vitest.config.*` | Any | Vitest |
