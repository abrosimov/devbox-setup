---
name: mcp-figma
description: >
  Figma MCP patterns for reading design files, extracting tokens, inspecting components,
  and bridging design-to-code workflows. Covers file structure, style extraction, component
  properties, and asset export. Triggers on: Figma, design file, design tokens, Figma MCP,
  Figma styles, Figma components, design system, design-to-code, visual design.
---

# Figma MCP

Reading design files and extracting design information using the Figma MCP server.

---

## Available Tools (Key Subset)

| Tool | Purpose |
|------|---------|
| `mcp__figma__get_file` | Get file structure — pages, frames, hierarchy |
| `mcp__figma__get_file_styles` | Extract colour, text, and effect styles |
| `mcp__figma__get_file_components` | List all components and their properties |
| `mcp__figma__get_component` | Get specific component details — variants, properties |
| `mcp__figma__get_node` | Get a specific node by ID (frame, group, instance) |
| `mcp__figma__get_images` | Export nodes as images (PNG, SVG, PDF) |

---

## When to Use

**Use for:**
- Extracting design tokens from Figma styles (colours, typography, spacing, shadows)
- Inventorying components before writing specifications
- Reading component variants and properties to inform component APIs
- Comparing live implementation against Figma design (design verification)
- Exporting icons and assets for use in the codebase

**Do NOT use for:**
- Writing or modifying Figma files (MCP is read-only)
- Exporting the entire file at once (too large — use specific nodes)
- Replacing the design specification (the spec is the contract, not Figma)
- Pixel-perfect comparison (use Playwright screenshots for visual checks)

---

## Usage Patterns

### Pattern 1: Token Extraction

Extract design tokens from Figma styles and map to W3C format.

**Sequence:**
1. Get file styles to discover colour, text, and effect styles
2. Map colours to W3C `color` tokens
3. Map text styles to W3C `typography` tokens
4. Map effect styles (shadows) to W3C `shadow` tokens
5. Cross-reference with existing `design_system.tokens.json` if present

```
1. get_file_styles → list all colour/text/effect styles
2. For each colour style → map to { "$type": "color", "$value": "#hex" }
3. For each text style → map to { "$type": "typography", "$value": { fontFamily, fontSize, ... } }
4. For each shadow → map to { "$type": "shadow", "$value": { color, offsetX, offsetY, blur, spread } }
5. Write to design_system.tokens.json
```

> See `ui-design` skill for the W3C Design Tokens format specification.

### Pattern 2: Component Inventory

Discover existing components to inform specification or implementation.

**Sequence:**
1. Get file components to list all components
2. For each component, read variants and properties
3. Map to component specification format (props, variants, states)
4. Identify reusable components vs new components needed

```
1. get_file_components → list all components with names and keys
2. get_component(key) → get variants, properties for each
3. Map variant properties → Props table in component spec
4. Note naming conventions and grouping patterns
```

### Pattern 3: Design Verification

Compare implementation against Figma design.

**Sequence:**
1. Get the specific frame/node for the screen being implemented
2. Read dimensions, spacing, and token references
3. Compare against the live implementation (use Playwright for screenshots)
4. Note discrepancies between Figma and implementation

```
1. get_node(nodeId) → get frame dimensions, children, properties
2. Extract spacing, sizing, colour references
3. Compare against code values
4. Report discrepancies to user
```

### Pattern 4: Asset Export

Export icons and images for the codebase.

**Sequence:**
1. Identify the nodes to export (icon components, illustrations)
2. Export as SVG for icons, PNG for raster images
3. Note export settings (scale, format)

```
1. get_file_components → find icon components
2. get_images(nodeIds, format="svg") → export as SVG
3. Save to appropriate directory in codebase
```

---

## Figma ↔ Design Tokens Mapping

| Figma Concept | W3C Token Type | Notes |
|---------------|---------------|-------|
| Colour style | `color` | Map fill colours, not stroke |
| Text style | `typography` | Includes family, size, weight, line height |
| Effect style (shadow) | `shadow` | Map drop shadows, not inner shadows |
| Corner radius | `dimension` | Extract from component frames |
| Spacing (auto-layout) | `dimension` | Extract gap and padding from auto-layout frames |

---

## Anti-Patterns

| Anti-Pattern | Problem | Instead |
|--------------|---------|---------|
| Exporting entire file | Too large, slow, token-heavy | Use specific nodes/components |
| Treating Figma as source of truth for code | Figma changes without spec updates | The design spec (`design.md`) is the contract |
| Writing to Figma | MCP is read-only | Create specs and tokens as files |
| Ignoring Figma naming conventions | Components may use internal naming | Map Figma names to code conventions explicitly |
| Extracting tokens without checking existing | Duplicates or conflicts | Always cross-reference with existing token files |

---

## Graceful Degradation

If `mcp__figma` is not available (not configured, no API token, or connection error):
- **Skip** Figma-based extraction
- **Work from** existing `design.md` specs, `design_system.tokens.json`, CSS/theme files, or user descriptions
- **Note** in output: "Figma MCP not available — working from existing specs and codebase"
- **Do not** block on MCP availability
