---
name: frontend-accessibility
description: >
  Frontend accessibility patterns and WCAG 2.1 AA compliance. Use when discussing ARIA,
  keyboard navigation, semantic HTML, screen readers, focus management, or colour contrast.
  Triggers on: accessibility, a11y, WCAG, ARIA, keyboard, screen reader, focus, semantic HTML,
  tab order, skip link, live region.
---

# Frontend Accessibility Reference

Accessibility patterns for WCAG 2.1 AA compliance in React applications.

---

## Core Principle

**Accessibility is not a feature — it's a quality requirement.** Every component must be usable by:
- Keyboard-only users
- Screen reader users
- Users with low vision (colour contrast, zoom)
- Users with motor impairments (target sizes)

---

## Semantic HTML First

### Use the Right Element

| Need | Use | NOT |
|------|-----|-----|
| Navigation | `<nav>` | `<div className="nav">` |
| Button | `<button>` | `<div onClick>` or `<a onClick>` |
| Link (navigation) | `<a href>` | `<button>` or `<span onClick>` |
| Heading | `<h1>`-`<h6>` | `<div className="heading">` |
| List | `<ul>/<ol>` + `<li>` | `<div>` + `<div>` |
| Form field label | `<label htmlFor>` | `<span>` near input |
| Table | `<table>` + `<thead>/<tbody>` | `<div>` grid |
| Main content | `<main>` | `<div id="main">` |
| Section | `<section>` with heading | `<div>` |
| Page header | `<header>` | `<div className="header">` |
| Page footer | `<footer>` | `<div className="footer">` |

**Rule**: If a native HTML element does what you need, use it. ARIA is a last resort.

---

## ARIA Patterns

### When to Use ARIA

```
Is there a native HTML element that does this?
│
├─ YES → Use the native element. No ARIA needed.
│
└─ NO → Use ARIA attributes to communicate semantics.
```

### Common ARIA Patterns

#### Modal / Dialog

```typescript
function Modal({ isOpen, onClose, title, children }: ModalProps) {
  const titleId = useId()

  if (!isOpen) return null

  return createPortal(
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />

      {/* Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative z-10"
      >
        <h2 id={titleId}>{title}</h2>
        {children}
        <button onClick={onClose} aria-label="Close">
          <XIcon />
        </button>
      </div>
    </div>,
    document.body
  )
}
```

#### Tabs

```typescript
function Tabs({ tabs }: TabsProps) {
  const [activeIndex, setActiveIndex] = useState(0)

  return (
    <div>
      <div role="tablist" aria-label="Settings">
        {tabs.map((tab, i) => (
          <button
            key={tab.id}
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={i === activeIndex}
            aria-controls={`panel-${tab.id}`}
            tabIndex={i === activeIndex ? 0 : -1}
            onClick={() => setActiveIndex(i)}
            onKeyDown={(e) => handleTabKeyDown(e, i)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {tabs.map((tab, i) => (
        <div
          key={tab.id}
          role="tabpanel"
          id={`panel-${tab.id}`}
          aria-labelledby={`tab-${tab.id}`}
          hidden={i !== activeIndex}
          tabIndex={0}
        >
          {tab.content}
        </div>
      ))}
    </div>
  )
}
```

#### Expandable / Accordion

```typescript
function Accordion({ title, children }: AccordionProps) {
  const [isOpen, setIsOpen] = useState(false)
  const contentId = useId()

  return (
    <div>
      <button
        aria-expanded={isOpen}
        aria-controls={contentId}
        onClick={() => setIsOpen(!isOpen)}
      >
        {title}
        <ChevronIcon className={isOpen ? 'rotate-180' : ''} />
      </button>
      <div id={contentId} hidden={!isOpen}>
        {children}
      </div>
    </div>
  )
}
```

---

## Keyboard Navigation

### Required Keyboard Support

| Key | Action |
|-----|--------|
| **Tab** | Move focus to next interactive element |
| **Shift+Tab** | Move focus to previous interactive element |
| **Enter/Space** | Activate button, link, or control |
| **Escape** | Close modal, dropdown, tooltip |
| **Arrow keys** | Navigate within composite widgets (tabs, menus, listbox) |
| **Home/End** | First/last item in list or menu |

### Focus Management

```typescript
// Focus trap for modals
import { FocusTrap } from 'focus-trap-react'

function Modal({ children }: { children: React.ReactNode }) {
  return (
    <FocusTrap>
      <div role="dialog" aria-modal="true">
        {children}
      </div>
    </FocusTrap>
  )
}
```

### Focus on Route Change

```typescript
// app/layout.tsx — announce route changes
'use client'

import { usePathname } from 'next/navigation'
import { useEffect, useRef } from 'react'

function RouteAnnouncer() {
  const pathname = usePathname()
  const ref = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    ref.current?.focus()
  }, [pathname])

  return <h1 ref={ref} tabIndex={-1} className="sr-only" />
}
```

### Skip Link

```typescript
// First focusable element on the page
function SkipLink() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4"
    >
      Skip to main content
    </a>
  )
}

// Target
<main id="main-content" tabIndex={-1}>
  {/* page content */}
</main>
```

---

## Colour Contrast

### Minimum Ratios (WCAG AA)

| Element | Minimum Ratio |
|---------|--------------|
| Normal text (< 18px / < 14px bold) | 4.5:1 |
| Large text (>= 18px / >= 14px bold) | 3:1 |
| UI components (borders, icons) | 3:1 |
| Focus indicators | 3:1 against adjacent colours |

### Rules

- **Never use colour alone** to convey information (add icons, text, patterns)
- **Focus indicators** must be visible on all backgrounds
- **Disabled elements** are exempt from contrast requirements but should still be perceivable
- **Test with browser DevTools** — Chrome Accessibility panel shows contrast ratios

---

## Live Regions

For dynamic content that updates without user action:

```typescript
// Toast notification
function Toast({ message }: { message: string }) {
  return (
    <div role="status" aria-live="polite">
      {message}
    </div>
  )
}

// Error notification (urgent)
function ErrorAlert({ message }: { message: string }) {
  return (
    <div role="alert" aria-live="assertive">
      {message}
    </div>
  )
}

// Loading state
function LoadingIndicator() {
  return (
    <div role="status" aria-live="polite">
      <span className="sr-only">Loading...</span>
      <Spinner />
    </div>
  )
}
```

| Attribute | When |
|-----------|------|
| `aria-live="polite"` | Non-urgent updates (toast, status change) |
| `aria-live="assertive"` | Urgent (errors, alerts) |
| `role="status"` | Shorthand for `aria-live="polite"` |
| `role="alert"` | Shorthand for `aria-live="assertive"` |

---

## Images and Icons

```typescript
// Informative image — needs alt text
<img src="/user-avatar.jpg" alt="Alice Johnson's profile photo" />

// Decorative image — hide from screen readers
<img src="/decorative-wave.svg" alt="" />

// Icon button — needs accessible label
<button aria-label="Delete user">
  <TrashIcon aria-hidden="true" />
</button>

// Icon with visible label — icon is decorative
<button>
  <PlusIcon aria-hidden="true" />
  <span>Add user</span>
</button>
```

---

## Forms

### Labels

```typescript
// ✅ GOOD — explicit label association
<label htmlFor="email">Email address</label>
<input id="email" type="email" />

// ✅ GOOD — wrapping label
<label>
  Email address
  <input type="email" />
</label>

// ❌ BAD — no label
<input type="email" placeholder="Email" />
// Placeholder is NOT a label — disappears when typing
```

### Error Messages

```typescript
<label htmlFor="email">Email</label>
<input
  id="email"
  type="email"
  aria-invalid={!!error}
  aria-describedby={error ? 'email-error' : undefined}
/>
{error && (
  <p id="email-error" role="alert" className="text-destructive">
    {error}
  </p>
)}
```

### Required Fields

```typescript
<label htmlFor="name">
  Name <span aria-hidden="true">*</span>
</label>
<input id="name" required aria-required="true" />
```

---

## Screen Reader Utilities

```css
/* Visually hidden but available to screen readers */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

/* Tailwind: class="sr-only" (built-in) */
```

```typescript
// Announce state changes to screen readers
<span className="sr-only" role="status">
  {selectedCount} items selected
</span>
```

---

## Quick Reference: Common Violations

| Violation | Fix |
|-----------|-----|
| `<div onClick>` | Use `<button>` |
| `<a>` without `href` | Use `<button>` if no navigation |
| Image without `alt` | Add descriptive alt or `alt=""` for decorative |
| Form input without label | Add `<label htmlFor>` |
| Icon button without label | Add `aria-label` |
| Colour-only information | Add icon, text, or pattern |
| No focus indicator | Ensure `:focus-visible` styles |
| No skip link | Add "Skip to main content" |
| Modal without focus trap | Add `FocusTrap` or manual implementation |
| Dynamic content without live region | Add `role="status"` or `role="alert"` |
| Auto-playing media | Add pause/stop controls |
| Timeout without warning | Warn user and allow extension |
