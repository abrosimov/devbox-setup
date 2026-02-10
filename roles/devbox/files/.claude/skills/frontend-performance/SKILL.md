---
name: frontend-performance
description: >
  Frontend performance patterns and Core Web Vitals optimisation. Use when discussing
  code splitting, lazy loading, bundle size, memoisation, image optimisation, or rendering
  performance. Triggers on: performance, Core Web Vitals, LCP, CLS, INP, lazy loading,
  code splitting, bundle size, memoisation, image optimisation, Lighthouse.
---

# Frontend Performance Reference

Performance patterns for React + Next.js applications.

---

## Core Web Vitals

| Metric | What It Measures | Good | Needs Improvement | Poor |
|--------|-----------------|------|-------------------|------|
| **LCP** (Largest Contentful Paint) | Loading speed | < 2.5s | 2.5s - 4s | > 4s |
| **INP** (Interaction to Next Paint) | Responsiveness | < 200ms | 200ms - 500ms | > 500ms |
| **CLS** (Cumulative Layout Shift) | Visual stability | < 0.1 | 0.1 - 0.25 | > 0.25 |

---

## Code Splitting

### Route-Based (Automatic in Next.js)

Next.js automatically code-splits by route. Each `page.tsx` is a separate bundle.

### Component-Level (Manual)

```typescript
import dynamic from 'next/dynamic'

// ✅ GOOD — heavy component loaded only when needed
const HeavyChart = dynamic(() => import('@/components/heavy-chart'), {
  loading: () => <ChartSkeleton />,
  ssr: false,  // Skip SSR if component uses browser-only APIs
})

function Dashboard() {
  return (
    <div>
      <StatCards />
      <HeavyChart />  {/* Loaded separately */}
    </div>
  )
}
```

### When to Code-Split

| Situation | Split? |
|-----------|--------|
| Heavy library (chart, editor, map) | ✅ Yes — `dynamic()` |
| Below the fold content | ✅ Yes — lazy load |
| Modal/dialog content | ✅ Yes — loaded on open |
| Small utility component | ❌ No — overhead not worth it |
| Above the fold content | ❌ No — delays LCP |
| Navigation/header | ❌ No — needed immediately |

---

## Image Optimisation

### Next.js Image Component

```typescript
import Image from 'next/image'

// ✅ GOOD — optimised, responsive, lazy-loaded
<Image
  src="/hero.jpg"
  alt="Product showcase"
  width={1200}
  height={600}
  priority  // Only for above-the-fold images (LCP)
  sizes="(max-width: 768px) 100vw, 1200px"
/>

// ❌ BAD — unoptimised native img
<img src="/hero.jpg" alt="Product showcase" />
```

### Rules

| Rule | Why |
|------|-----|
| Use `next/image` always | Auto-optimisation, WebP, lazy loading |
| Set `priority` on LCP image | Preloads, improves LCP |
| Provide `sizes` for responsive | Correct size served per viewport |
| Always set `width` and `height` | Prevents CLS (layout shift) |
| Use `fill` for unknown dimensions | With `object-fit` and parent sizing |

---

## Rendering Performance

### Avoid Unnecessary Re-renders

```typescript
// ❌ BAD — new object/array reference every render
function Parent() {
  return <Child style={{ colour: 'red' }} items={[1, 2, 3]} />
  // style and items are NEW objects each render
}

// ✅ GOOD — stable references
const style = { colour: 'red' }
const items = [1, 2, 3]

function Parent() {
  return <Child style={style} items={items} />
}
```

### When React.memo Helps

```typescript
// ✅ JUSTIFIED — expensive render, receives stable props
const DataGrid = memo(function DataGrid({ data }: { data: Row[] }) {
  // Renders 1000+ rows
  return (/* expensive render */)
})

// ❌ NOT JUSTIFIED — cheap render
const Label = memo(function Label({ text }: { text: string }) {
  return <span>{text}</span>  // Memoisation overhead > render cost
})
```

### Decision: Should I Memoize?

```
Is there a measured performance problem? (React DevTools Profiler)
│
├─ NO → Don't memoize. Stop here. ❌
│
└─ YES → What's causing re-renders?
   │
   ├─ Parent re-renders with same props to child?
   │  └─ React.memo on child + useCallback for callback props ✅
   │
   ├─ Expensive computation during render?
   │  └─ useMemo for the computation ✅
   │
   ├─ Object/array created each render, used in dependency array?
   │  └─ useMemo for stable reference ✅
   │
   └─ Component renders too often from context?
      └─ Split context or use Zustand for fine-grained subscriptions ✅
```

---

## Bundle Size

### Monitoring

```bash
# Next.js — built-in bundle analyser
ANALYZE=true npm run build

# Or install @next/bundle-analyzer
```

### Common Offenders

| Library | Size | Alternative |
|---------|------|-------------|
| `moment` | ~300KB | `date-fns` (tree-shakeable) or `Intl` API |
| `lodash` | ~70KB | `lodash-es` (tree-shakeable) or native JS |
| `chart.js` | ~200KB | Dynamic import, load on demand |
| `react-icons` (full) | ~50KB | Import specific icons: `react-icons/fi` |

### Rules

| Rule | Why |
|------|-----|
| Import specific modules | `import { format } from 'date-fns'` not `import * as dateFns` |
| Dynamic import heavy libraries | Chart, editor, map — load when visible |
| Check bundle impact before adding deps | `npx bundlephobia <package>` |
| Prefer native APIs | `Intl.DateTimeFormat` over date libraries |
| No barrel file imports | Direct imports tree-shake better |

---

## Loading Performance

### Streaming with Suspense

```typescript
// app/dashboard/page.tsx
import { Suspense } from 'react'

export default function DashboardPage() {
  return (
    <div>
      <h1>Dashboard</h1>
      {/* Fast: renders immediately */}
      <WelcomeMessage />

      {/* Slow: streams in when ready */}
      <Suspense fallback={<StatsSkeleton />}>
        <SlowStats />
      </Suspense>

      <Suspense fallback={<ChartSkeleton />}>
        <SlowChart />
      </Suspense>
    </div>
  )
}
```

### Prefetching

```typescript
// Next.js Link — prefetches on hover by default
import Link from 'next/link'

<Link href="/users">Users</Link>  // Prefetched automatically

// Disable for rarely visited pages
<Link href="/admin" prefetch={false}>Admin</Link>
```

---

## Font Optimisation

```typescript
// app/layout.tsx — Next.js automatic font optimisation
import { Inter } from 'next/font/google'

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',  // Prevents invisible text during load
})

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.className}>
      <body>{children}</body>
    </html>
  )
}
```

### Rules

| Rule | Why |
|------|-----|
| Use `next/font` | Self-hosted, no external requests |
| Set `display: 'swap'` | Text visible during font load |
| Subset fonts | Only load characters you need |
| Limit font weights | Each weight is a separate file |

---

## CLS Prevention

| Cause | Fix |
|-------|-----|
| Images without dimensions | Set `width` and `height` on `<Image>` |
| Dynamically injected content | Reserve space with skeleton/placeholder |
| Web fonts causing reflow | `font-display: swap` + `next/font` |
| Ads or embeds without size | Set explicit container dimensions |
| Content above existing content | Insert below or use `position: fixed` |

```typescript
// ✅ GOOD — space reserved, no shift
<div className="h-[300px]">
  <Suspense fallback={<ChartSkeleton className="h-[300px]" />}>
    <Chart />
  </Suspense>
</div>

// ❌ BAD — content pushes page when loaded
<Suspense fallback={null}>
  <Chart />  {/* Unknown height, causes CLS */}
</Suspense>
```

---

## Quick Reference

| Problem | Solution |
|---------|----------|
| Slow initial load | Server Components, code splitting |
| Large bundle | Dynamic imports, tree-shaking, check deps |
| Slow interaction | Reduce re-renders, memo if measured |
| Layout shift (CLS) | Reserve space, set dimensions |
| Slow images | `next/image`, priority on LCP image |
| Font flash | `next/font` with `display: 'swap'` |
| Slow subsequent navigations | Prefetch links, React Query cache |
| Heavy computation in render | `useMemo` (only if measured) |
