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

Design tokens are stored in JSON following the W3C Design Tokens specification. This is the **contract format** between Designer and Frontend Engineer agents.

### Basic Structure

```json
{
  "colour": {
    "$type": "color",
    "primary": {
      "$value": "#1a73e8",
      "$description": "Primary brand colour"
    }
  },
  "spacing": {
    "$type": "dimension",
    "md": { "$value": "16px" }
  }
}
```

### Token Types

W3C Design Token `$type` values: `color`, `dimension`, `fontFamily`, `fontWeight`, `duration`, `cubicBezier`, `number`, `shadow`, `border`, `gradient`, `typography`.

### Composite Types

Shadow, typography, and border tokens use object `$value`:

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

## Component Specification Format

Each component spec in `design.md` follows this structure:

```markdown
## ComponentName

**Purpose**: One-line description.

### Props
| Prop | Type | Default | Required | Description |

### Variants
| Variant | Use Case | Visual |

### States
| State | Trigger | Visual Change |

### Interactions
| Action | Behaviour |

### Accessibility
| Requirement | Implementation |
```

---

## Figma MCP Integration

See `mcp-figma` skill for the full tool reference and usage patterns.

### Reading Designs

When a Figma URL is available:
- `mcp__figma__get_metadata(fileKey, nodeId)` -- structural overview (node IDs, types, positions, sizes)
- `mcp__figma__get_design_context(fileKey, nodeId)` -- detailed context for specific nodes (primary read tool)
- `mcp__figma__get_variable_defs(fileKey, nodeId)` -- extract design tokens/variables with resolved values
- `mcp__figma__get_screenshot(fileKey, nodeId)` -- visual capture for reference

> **Tip**: Use `get_metadata` first for large files to identify key nodes, then `get_design_context` on specific nodes.

### Creating Visual Documentation (FigJam)

- `mcp__figma__generate_diagram(name, mermaidSyntax)` -- create user flow diagrams, component state machines, sequence diagrams in FigJam
- Supported types: `flowchart`, `stateDiagram-v2`, `sequenceDiagram`, `gantt`
- **MUST** present returned URLs to user as markdown links

### Workflow with Figma

1. Ask user for Figma URL (designer agent handles this in Step 1)
2. Read existing designs via `get_metadata` --> `get_design_context`
3. Extract tokens via `get_variable_defs` --> use as baseline for `design_system.tokens.json`
4. Create user flow diagrams in FigJam via `generate_diagram`
5. Create component state diagrams in FigJam via `generate_diagram`
6. Set up Code Connect mappings for existing components
7. Note discrepancies between Figma and spec (report to user)

### Without Figma

If Figma MCP is not available, work from:
- User descriptions and requirements
- Existing CSS/theme files in the codebase
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

## Handoff Format -- What a Frontend Engineer Needs

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

## Components
### [Component Name]
(Full component spec -- props, variants, states, interactions, accessibility)

## Interactions
### [Interaction Name]
- Trigger, behaviour, feedback

## Accessibility
- Keyboard navigation map
- Screen reader announcements
- Focus management plan
- Colour contrast verification

## Open Questions
1. [ ] Items needing user input
```
