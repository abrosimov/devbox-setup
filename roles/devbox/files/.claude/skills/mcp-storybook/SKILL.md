---
name: mcp-storybook
description: >
  Storybook MCP patterns for discovering existing components, reading stories and props,
  and understanding the component library before implementing or reviewing. Covers component
  inventory, prop discovery, pattern matching, and visual reference.
  Triggers on: Storybook MCP, component library, story, stories, existing components,
  component inventory, component discovery, design system components.
---

# Storybook MCP

Discovering and inspecting existing components using the Storybook MCP server.

---

## Available Tools (Key Subset)

| Tool | Purpose |
|------|---------|
| `mcp__storybook__list_stories` | List all stories in the Storybook instance |
| `mcp__storybook__get_story` | Get a specific story's source, args, and metadata |
| `mcp__storybook__get_component_info` | Get component props, types, and description |
| `mcp__storybook__search_stories` | Search stories by name or tag |
| `mcp__storybook__get_story_screenshot` | Capture a screenshot of a rendered story |

---

## When to Use

**Use for:**
- Inventorying existing components before implementing new features
- Understanding component APIs (props, variants) before consuming or extending them
- Finding similar components to follow existing conventions for new ones
- Visual reference — comparing rendered stories against design specs
- Identifying reusable components vs components that need to be created

**Do NOT use for:**
- Writing stories (write them in code as `*.stories.tsx` files)
- Replacing unit tests (use React Testing Library / Vitest)
- Performance testing (Storybook adds overhead)
- Screenshotting every story (token-heavy — use targeted checks)

---

## Usage Patterns

### Pattern 1: Component Inventory

Understand the existing component library before implementing new features.

**Sequence:**
1. List all stories to see the full component catalogue
2. Group by category/folder to understand organisation
3. Identify components that can be reused for the current task
4. Note naming conventions and prop patterns

```
1. list_stories → get full catalogue with titles and categories
2. Group results by title prefix (e.g., "UI/Button", "Forms/Input")
3. Identify matches: "Do any existing components solve part of this task?"
4. Note patterns: naming, variant approach, composition style
```

### Pattern 2: Prop Discovery

Understand existing component APIs before extending or consuming them.

**Sequence:**
1. Get component info for the target component
2. Read props, types, and default values
3. Check existing stories for usage examples
4. Understand which props are required vs optional

```
1. get_component_info("Button") → props, types, description
2. Review prop types — what variants exist? What's customisable?
3. get_story("UI/Button/Primary") → see usage example with args
4. Use discovered API in your implementation
```

### Pattern 3: Pattern Matching

Find similar components to follow existing conventions.

**Sequence:**
1. Search stories for components similar to what you need to create
2. Read the closest match's story and component info
3. Follow the same patterns (prop naming, variant approach, composition)
4. Ensure new component is consistent with existing library

```
1. search_stories("dialog") → find existing dialog/modal components
2. get_component_info → understand their prop API
3. get_story → see how they handle variants, states
4. Follow same patterns for new component
```

### Pattern 4: Visual Reference

Compare rendered stories against design specifications.

**Sequence:**
1. Find the story for the component being verified
2. Screenshot the story in its default state
3. Compare against design spec or Figma (if Figma MCP available)
4. Check variant stories for consistency

```
1. search_stories("UserCard") → find relevant stories
2. get_story_screenshot("UI/UserCard/Default") → capture visual
3. Compare against design.md specifications
4. Note visual discrepancies
```

---

## Component Discovery Workflow

When starting a new feature, follow this sequence:

```
1. "What components already exist?"
   → list_stories → full catalogue

2. "Can I reuse any of these?"
   → get_component_info for candidates → check props match needs

3. "How are similar components built?"
   → get_story for closest match → read args, decorators, patterns

4. "What conventions should I follow?"
   → Note: naming, prop patterns, variant approach, story structure
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Instead |
|--------------|---------|---------|
| Writing stories via MCP | MCP is read-only discovery tool | Write stories as `*.stories.tsx` files in code |
| Screenshotting every story | Slow, token-heavy | Screenshot only specific stories you need to verify |
| Replacing RTL tests with Storybook | Different purposes | Use Storybook for discovery and visual checks, RTL for behaviour tests |
| Ignoring existing components | Reinventing the wheel | Always inventory before creating new components |
| Assuming Storybook is complete | Not all components may have stories | Cross-reference with codebase (`*.tsx` files) |

---

## Graceful Degradation

If `mcp__storybook` is not available (Storybook not running, MCP not configured, or connection error):
- **Search codebase** for `*.stories.tsx` files to discover components
- **Read component files** directly (`*.tsx`) for props and types
- **Follow existing patterns** discovered in code
- **Note** in output: "Storybook MCP not available — discovering components from codebase"
- **Do not** block on MCP availability
