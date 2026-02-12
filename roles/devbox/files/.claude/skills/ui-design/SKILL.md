---
name: ui-design
description: >
  UI/UX design knowledge for component specification, design tokens (W3C format), responsive layout,
  accessibility, and integration with Figma MCP and Storybook MCP.
  Triggers on: UI design, UX, design tokens, component spec, layout, accessibility, WCAG, Figma,
  Storybook, design system, responsive, breakpoint.
---

# UI/UX Design Knowledge

Reference knowledge for Designer (UI/UX) agent when creating design specifications and design systems.

---

## W3C Design Tokens Format (v2025.10)

Design tokens are stored in JSON following the W3C Design Tokens specification.

### Basic Structure

```json
{
  "colour": {
    "$type": "color",
    "primary": {
      "$value": "#1a73e8",
      "$description": "Primary brand colour"
    },
    "primary-hover": {
      "$value": "#1557b0"
    },
    "surface": {
      "$value": "#ffffff"
    },
    "on-surface": {
      "$value": "#1f1f1f"
    }
  },
  "spacing": {
    "$type": "dimension",
    "xs": { "$value": "4px" },
    "sm": { "$value": "8px" },
    "md": { "$value": "16px" },
    "lg": { "$value": "24px" },
    "xl": { "$value": "32px" },
    "2xl": { "$value": "48px" }
  }
}
```

### Token Types

W3C Design Token `$type` values and their `$value` formats:

- **Colour** — type: `color`, value: Hex/RGB/HSL — `"#1a73e8"`
- **Dimension** — type: `dimension`, value: Number + unit — `"16px"`, `"1.5rem"`
- **Font family** — type: `fontFamily`, value: String or array — `["Inter", "sans-serif"]`
- **Font weight** — type: `fontWeight`, value: Number or name — `400`, `"bold"`
- **Duration** — type: `duration`, value: Number + unit — `"200ms"`
- **Cubic bezier** — type: `cubicBezier`, value: Array of 4 numbers — `[0.4, 0, 0.2, 1]`
- **Number** — type: `number`, value: Plain number — `1.5`
- **Shadow** — type: `shadow`, value: Object — see below
| Border | `border` | Object | See below |
| Gradient | `gradient` | Array | See below |
| Typography | `typography` | Object | See below |

### Composite Types

```json
{
  "shadow": {
    "$type": "shadow",
    "elevation-1": {
      "$value": {
        "color": "#00000026",
        "offsetX": "0px",
        "offsetY": "1px",
        "blur": "3px",
        "spread": "0px"
      }
    }
  },
  "typography": {
    "$type": "typography",
    "heading-1": {
      "$value": {
        "fontFamily": "{font.family.heading}",
        "fontSize": "2rem",
        "fontWeight": 700,
        "lineHeight": 1.2,
        "letterSpacing": "-0.02em"
      }
    }
  },
  "border": {
    "$type": "border",
    "default": {
      "$value": {
        "color": "{colour.border}",
        "width": "1px",
        "style": "solid"
      }
    }
  }
}
```

### Token References (Aliases)

Use `{}` syntax to reference other tokens:

```json
{
  "colour": {
    "brand": { "$value": "#1a73e8" },
    "interactive": { "$value": "{colour.brand}" }
  },
  "component": {
    "button": {
      "background": { "$value": "{colour.interactive}" }
    }
  }
}
```

---

## Design Token Categories

### Required Categories

| Category | Description | Examples |
|----------|-------------|---------|
| **Colour** | All colour values (brand, semantic, surface) | Primary, secondary, error, warning, success |
| **Spacing** | Consistent spacing scale | 4px base with multipliers: 4, 8, 12, 16, 24, 32, 48 |
| **Typography** | Font families, sizes, weights, line heights | Heading 1-6, body, caption, overline |
| **Shadows** | Elevation/depth tokens | Elevation 0-5 |
| **Border radius** | Corner rounding values | None, sm, md, lg, full |
| **Breakpoints** | Responsive breakpoints | sm: 640px, md: 768px, lg: 1024px, xl: 1280px |
| **Z-index** | Stacking order | Dropdown: 1000, modal: 1100, tooltip: 1200 |

### Optional Categories

| Category | When Needed |
|----------|------------|
| **Duration/Easing** | Animated interfaces |
| **Opacity** | Overlay-heavy designs |
| **Border** | Complex border patterns |
| **Gradient** | Gradient-heavy designs |

### Semantic Colour Pattern

```json
{
  "colour": {
    "brand": {
      "primary": { "$value": "#1a73e8" },
      "secondary": { "$value": "#5f6368" }
    },
    "semantic": {
      "error": { "$value": "#d93025" },
      "warning": { "$value": "#f9ab00" },
      "success": { "$value": "#1e8e3e" },
      "info": { "$value": "#1a73e8" }
    },
    "surface": {
      "default": { "$value": "#ffffff" },
      "elevated": { "$value": "#f8f9fa" },
      "overlay": { "$value": "#00000080" }
    },
    "text": {
      "primary": { "$value": "#1f1f1f" },
      "secondary": { "$value": "#5f6368" },
      "disabled": { "$value": "#9aa0a6" },
      "inverse": { "$value": "#ffffff" }
    }
  }
}
```

---

## Component Specification Format

### Structure

Each component specification follows this format:

```markdown
## ComponentName

**Purpose**: One-line description of what this component does.

### Props

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| variant | "primary" \| "secondary" \| "ghost" | "primary" | No | Visual style variant |
| size | "sm" \| "md" \| "lg" | "md" | No | Component size |
| disabled | boolean | false | No | Disables interaction |

### Variants

| Variant | Use Case | Visual |
|---------|----------|--------|
| Primary | Main CTA, form submit | Filled background, high contrast |
| Secondary | Secondary actions | Outlined, medium contrast |
| Ghost | Tertiary, inline actions | Text only, low contrast |

### States

| State | Trigger | Visual Change |
|-------|---------|---------------|
| Default | Initial | Base styling |
| Hover | Mouse enter | Background darken 10% |
| Active | Mouse down | Background darken 20% |
| Focus | Tab/keyboard | 2px outline offset 2px |
| Disabled | disabled=true | 40% opacity, no pointer events |
| Loading | loading=true | Spinner replaces content |

### Interactions

| Action | Behaviour |
|--------|-----------|
| Click | Fires onClick, shows ripple effect |
| Keyboard Enter/Space | Same as click |
| Tab | Moves focus to/from component |

### Accessibility

| Requirement | Implementation |
|-------------|---------------|
| Role | `button` (native) or `role="button"` |
| Label | Content text or `aria-label` |
| Disabled | `aria-disabled="true"` + prevent click |
| Loading | `aria-busy="true"` + live region |
```

---

## Responsive Design

### Breakpoint Definitions

| Name | Min Width | Target |
|------|-----------|--------|
| `xs` | 0px | Mobile portrait |
| `sm` | 640px | Mobile landscape |
| `md` | 768px | Tablet |
| `lg` | 1024px | Desktop |
| `xl` | 1280px | Large desktop |
| `2xl` | 1536px | Ultra-wide |

### Mobile-First Approach

Design for `xs` first, then enhance:

```
Base styles (mobile) → sm: adjustments → md: adjustments → lg: adjustments
```

### Responsive Patterns

| Pattern | Description | When to Use |
|---------|-------------|-------------|
| **Stack → Horizontal** | Vertical on mobile, horizontal on desktop | Navigation, card grids |
| **Sidebar collapse** | Sidebar → drawer on mobile | Dashboard layouts |
| **Column drop** | Multi-column → single column | Content pages |
| **Font scale** | Smaller type on mobile | All text |
| **Touch targets** | 44x44px minimum on mobile | Buttons, links |

---

## Layout Patterns

### Common Layouts

| Layout | Structure | Use For |
|--------|-----------|---------|
| **Holy Grail** | Header, sidebar, main, sidebar, footer | Portals, dashboards |
| **Sidebar + Content** | Fixed sidebar, scrollable content | Admin panels, docs |
| **Top Nav + Content** | Fixed header, scrollable content | Marketing, blogs |
| **Dashboard Grid** | Header, sidebar, grid of cards | Analytics, monitoring |
| **Split View** | Two panels side by side | Email clients, editors |

### Grid System

```markdown
### Grid

- Columns: 12
- Gutter: {spacing.md} (16px)
- Margin: {spacing.lg} (24px) on mobile, {spacing.2xl} (48px) on desktop
- Max content width: 1280px (centred)
```

---

## Accessibility — WCAG 2.1 AA Minimum

### Colour Contrast

| Element | Minimum Ratio |
|---------|--------------|
| Normal text (< 18px) | 4.5:1 |
| Large text (>= 18px bold, >= 24px normal) | 3:1 |
| UI components and graphics | 3:1 |
| Focus indicators | 3:1 against adjacent colours |

### Keyboard Navigation

| Requirement | How |
|-------------|-----|
| All interactive elements focusable | Native HTML or `tabindex="0"` |
| Visible focus indicator | 2px outline, offset 2px |
| Logical tab order | DOM order matches visual order |
| Skip links | "Skip to main content" as first focusable |
| Escape closes | Modals, dropdowns, tooltips |
| Arrow keys | Within composite widgets (tabs, menus) |

### ARIA Landmarks

| Landmark | Element | Purpose |
|----------|---------|---------|
| `banner` | `<header>` | Site header |
| `navigation` | `<nav>` | Primary navigation |
| `main` | `<main>` | Main content (one per page) |
| `complementary` | `<aside>` | Supporting content |
| `contentinfo` | `<footer>` | Site footer |
| `search` | `<search>` or `role="search"` | Search functionality |

### Focus Management

| Scenario | Focus Behaviour |
|----------|----------------|
| Modal opens | Focus moves to first focusable element in modal |
| Modal closes | Focus returns to trigger element |
| Tab change | Focus moves to tab panel content |
| Toast/snackbar | Announced via `aria-live="polite"` |
| Route change | Focus moves to main content or page heading |
| Form error | Focus moves to first error |

### Common ARIA Patterns

| Widget | Key ARIA |
|--------|----------|
| Modal | `role="dialog"`, `aria-modal="true"`, `aria-labelledby` |
| Tabs | `role="tablist"`, `role="tab"`, `role="tabpanel"`, `aria-selected` |
| Dropdown menu | `role="menu"`, `role="menuitem"`, `aria-expanded` |
| Accordion | `aria-expanded`, `aria-controls` |
| Alert | `role="alert"` or `aria-live="assertive"` |
| Tooltip | `role="tooltip"`, `aria-describedby` |

---

## Figma MCP Integration

See `mcp-figma` skill for the full tool reference and usage patterns.

### Reading Designs

When a Figma URL is available:
- `mcp__figma__get_metadata(fileKey, nodeId)` — structural overview (node IDs, types, positions, sizes)
- `mcp__figma__get_design_context(fileKey, nodeId)` — detailed context for specific nodes (primary read tool)
- `mcp__figma__get_variable_defs(fileKey, nodeId)` — extract design tokens/variables with resolved values
- `mcp__figma__get_screenshot(fileKey, nodeId)` — visual capture for reference

> **Tip**: Use `get_metadata` first for large files to identify key nodes, then `get_design_context` on specific nodes.

### Creating Visual Documentation (FigJam)

- `mcp__figma__generate_diagram(name, mermaidSyntax)` — create user flow diagrams, component state machines, sequence diagrams in FigJam
- Supported types: `flowchart`, `stateDiagram-v2`, `sequenceDiagram`, `gantt`
- **MUST** present returned URLs to user as markdown links

### Workflow with Figma

1. Ask user for Figma URL (designer agent handles this in Step 1)
2. Read existing designs via `get_metadata` → `get_design_context`
3. Extract tokens via `get_variable_defs` → use as baseline for `design_system.tokens.json`
4. Create user flow diagrams in FigJam via `generate_diagram`
5. Create component state diagrams in FigJam via `generate_diagram`
6. Set up Code Connect mappings for existing components
7. Note discrepancies between Figma and spec (report to user)

### Without Figma

If Figma MCP is not available, work from:
- User descriptions and requirements
- Existing CSS/theme files in the codebase
- Industry-standard patterns (Material, etc.)
- Describe user flows in text within `design.md` instead of FigJam diagrams

---

## Storybook MCP Integration

When Storybook MCP server is available, use it to:

### Understanding Existing Components

- **List components**: Discover what already exists in the component library
- **Read props**: Understand existing component APIs
- **Read stories**: See usage examples and variants
- **Identify gaps**: What needs to be created vs what can be reused

### Workflow with Storybook

1. Check if Storybook MCP is available
2. If available: inventory existing components
3. Map existing components to design requirements
4. Identify reusable components, components needing modification, new components needed
5. Write specs that extend existing patterns (don't reinvent)

### Without Storybook

If Storybook MCP is not available:
- Search codebase for component files (`*.tsx`, `*.vue`, `*.svelte`)
- Read existing component props/types
- Follow existing patterns discovered in code

---

## Style Dictionary — Token Transformation

Design tokens in W3C format can be transformed to platform-specific formats using Style Dictionary:

### Common Transformations

- **CSS Custom Properties** — `--colour-primary: #1a73e8;`
- **Tailwind 4 `@theme`** — integrated via CSS custom properties
- **SCSS Variables** — `$colour-primary: #1a73e8;`
- **iOS (Swift)** — `UIColor` extensions
- **Android (Kotlin)** — colour resource XML
- **JSON (flat)** — flat key-value pairs

### Tailwind 4 Integration

Tailwind 4 reads design tokens directly from CSS custom properties via `@theme`:

```css
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

The Designer agent produces W3C tokens; the Frontend Engineer transforms them to the target platform.

---

## Handoff Format — What a Frontend Engineer Needs

The Designer agent produces these deliverables for the Frontend Engineer:

| File | Contents |
|------|----------|
| `design_system.tokens.json` | W3C Design Tokens (colours, spacing, typography, shadows, etc.) |
| `design.md` | Layout specs, component specs, interaction patterns, accessibility notes |

### `design.md` Structure

```markdown
# Design Specification

**Task**: JIRA-123
**Created**: YYYY-MM-DD

## Design Tokens

Token file: `design_system.tokens.json`
Summary of key decisions (colour palette rationale, spacing scale, typography choices).

## Layout

### Page: [Page Name]
- Structure (grid, sidebar, etc.)
- Responsive behaviour at each breakpoint
- Content areas and their purpose

## Components

### [Component Name]
(Full component spec — props, variants, states, interactions, accessibility)

## Interactions

### [Interaction Name]
- Trigger, behaviour, feedback
- Animation timing and easing

## Accessibility

- Keyboard navigation map
- Screen reader announcements
- Focus management plan
- Colour contrast verification

## Open Questions

1. [ ] Items needing user input
```
