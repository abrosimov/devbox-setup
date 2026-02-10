---
name: mcp-playwright
description: >
  Playwright MCP patterns for browser automation, accessibility inspection, and
  smoke testing. Covers navigation, interaction, screenshots, accessibility tree,
  and console monitoring. Triggers on: playwright, browser automation, smoke test,
  accessibility tree, screenshot, e2e, visual verification.
---

# Playwright MCP

Browser automation using the Playwright MCP server.

---

## Available Tools (Key Subset)

| Tool | Purpose |
|------|---------|
| `mcp__playwright__browser_navigate` | Navigate to a URL |
| `mcp__playwright__browser_click` | Click an element (by accessibility ref) |
| `mcp__playwright__browser_type` | Type text into an input field |
| `mcp__playwright__browser_snapshot` | Get current page accessibility tree snapshot |
| `mcp__playwright__browser_screenshot` | Capture a screenshot of the current page |
| `mcp__playwright__browser_console_messages` | Get browser console log messages |
| `mcp__playwright__browser_wait_for` | Wait for text or element to appear |
| `mcp__playwright__browser_tab_list` | List open browser tabs |
| `mcp__playwright__browser_tab_new` | Open a new tab |
| `mcp__playwright__browser_tab_close` | Close a tab |
| `mcp__playwright__browser_select_option` | Select a dropdown option |
| `mcp__playwright__browser_hover` | Hover over an element |

---

## When to Use

**Use for:**
- Smoke testing after frontend implementation (verify page renders, interactions work)
- Inspecting accessibility tree of live pages (verify ARIA roles, labels)
- Checking for console errors after navigation
- Verifying design implementation against design specs
- Capturing current UI state before designing changes

**Do NOT use for:**
- Unit testing (use testing frameworks instead)
- API testing (use HTTP tools instead)
- Performance benchmarking (Playwright adds overhead)
- Generating production test suites (write proper Playwright tests in code)

---

## Usage Patterns

### Pattern 1: Smoke Test After Implementation

Verify the implementation works end-to-end.

**Sequence:**
1. Navigate to the page
2. Take a snapshot (accessibility tree) to verify structure
3. Check console messages for errors
4. Interact with key elements (click buttons, fill forms)
5. Take a screenshot for visual verification

```
1. browser_navigate → http://localhost:3000/feature
2. browser_snapshot → verify expected elements present
3. browser_console_messages → check for errors/warnings
4. browser_click → interact with primary action
5. browser_screenshot → capture result
```

### Pattern 2: Accessibility Audit

Inspect the accessibility tree to verify ARIA compliance.

**Sequence:**
1. Navigate to the page
2. Take a snapshot (returns accessibility tree)
3. Verify: landmark roles present, labels on interactive elements, heading hierarchy
4. Tab through interactive elements (type Tab key)
5. Verify focus indicators and tab order

### Pattern 3: Design Verification

Compare live UI against design specifications.

**Sequence:**
1. Navigate to the page
2. Take a screenshot at each breakpoint (resize viewport)
3. Take a snapshot to verify component structure
4. Compare against design.md specifications

---

## Accessibility Tree vs Screenshots

| Approach | When to Use | Returns |
|----------|-------------|---------|
| `browser_snapshot` | Verify structure, roles, labels | Text-based accessibility tree |
| `browser_screenshot` | Verify visual appearance, layout | Image |

**Prefer snapshots** for structural verification (faster, deterministic).
**Use screenshots** for visual verification (layout, colours, spacing).

---

## Anti-Patterns

| Anti-Pattern | Problem | Instead |
|--------------|---------|---------|
| Screenshots for every check | Slow, token-heavy | Use snapshots; screenshots only for visual checks |
| Testing in production | Risk of side effects | Use local dev server (localhost) |
| Complex multi-page flows | Fragile, slow | Keep smoke tests to 3-5 steps max |
| Generating test files from MCP output | Tests won't be maintainable | Use MCP for exploration; write tests in code |

---

## Graceful Degradation

If `mcp__playwright` is not available (connection error, Docker not running, or not configured):
- **Skip** browser-based checks
- **Proceed** with non-browser verification (run test suite, check build output)
- **Note** in output: "Browser smoke test skipped — Playwright MCP not available"
- **Do not** block on MCP availability
