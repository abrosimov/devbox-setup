---
name: playwright-e2e
description: >
  Playwright e2e test authoring patterns — scoped locators, strict mode, SPA navigation,
  test isolation, and the testability contract between components and tests. Use when writing
  Playwright .spec.ts files, fixing flaky e2e tests, debugging strict mode violations,
  or reviewing e2e test code. Also use when a frontend component renders lists or tables
  with repeated interactive elements (buttons, links, menus) that tests must target individually.
---

# Playwright E2E Test Authoring

Patterns for writing robust, non-flaky Playwright tests in TypeScript. This skill covers the **test-authoring side** — how to write `.spec.ts` files that survive real-world conditions.

For comprehensive Playwright reference (POM, fixtures, CI/CD, mocking, debugging, accessibility, mobile, etc.), see the `playwright-best-practices` plugin skill.

---

## The Testability Contract

Component authors and test authors share a contract. Tests can only be as robust as the components they target.

### Component Author Responsibilities (frontend-engineer)

1. **Unique accessible names in lists/tables** — every interactive element in a repeated row must be distinguishable:
   ```tsx
   // BAD: generic label repeated per row
   <Button aria-label="Delete pipeline">

   // GOOD: includes entity identity
   <Button aria-label={`Delete pipeline ${pipeline.name}`}>
   ```

2. **Structural containers with identity** — rows/cards that group related elements should be identifiable:
   ```tsx
   // GOOD: row is scopeable by content or test-id
   <TableRow data-testid={`pipeline-row-${pipeline.id}`}>

   // ALSO GOOD: row identifiable by unique text content
   <TableRow>
     <TableCell><Link>{pipeline.name}</Link></TableCell>
     ...
   </TableRow>
   ```

3. **`data-testid` for structural containers** — use on elements that don't have natural accessible names but need programmatic targeting:
   - Table rows, card containers, panel sections, canvas overlays
   - NOT on buttons, links, inputs (use accessible names for those)

4. **Consistent labeling patterns** — if the list page labels a delete button `"Delete pipeline ${name}"`, the detail page should use the same pattern, not a generic `"Delete pipeline"`.

### Test Author Responsibilities

1. **Always scope to the nearest meaningful container** — never use page-global queries in list/table contexts
2. **Wait for navigation** after every click that changes the URL
3. **Use `{ exact: true }` or unique names** when the default substring match could be ambiguous
4. **Handle pre-existing data** — tests must work regardless of what other tests left behind

---

## Scoped Locators (Critical Pattern)

The #1 cause of strict mode violations: using `page.getByRole()` on a list page where multiple rows have similar buttons.

### In List/Table Context

```typescript
// BAD: page-global query matches all delete buttons
await page.getByRole("button", { name: "Delete pipeline" }).click();

// GOOD: scope to the specific row first
const row = page.getByRole("row").filter({ hasText: pipelineName });
await row.getByRole("button", { name: /delete/i }).click();

// ALSO GOOD: use the unique accessible name directly
await page.getByRole("button", { name: `Delete pipeline ${pipelineName}` }).click();

// ALSO GOOD: scope via data-testid container
const row = page.getByTestId(`pipeline-row-${pipelineId}`);
await row.getByRole("button", { name: /delete/i }).click();
```

### Filter Chaining

```typescript
// Find a specific list item by its content, then act within it
const item = page.getByRole("listitem").filter({ hasText: "My Item" });
await item.getByRole("button", { name: "Edit" }).click();

// Combine filters for precision
const card = page.getByRole("article")
  .filter({ hasText: itemName })
  .filter({ has: page.getByText("Active") });
await card.getByRole("button", { name: "Configure" }).click();
```

### When To Use `{ exact: true }`

```typescript
// REQUIRED: when the name is a substring of other names on the page
await page.getByRole("button", { name: "Delete", exact: true }).click();
// Without exact, "Delete" matches "Delete pipeline", "Delete version", etc.

// NOT NEEDED: when the name is already unique
await page.getByRole("button", { name: `Delete pipeline ${specificName}` }).click();
```

---

## SPA Navigation Waits

In single-page apps, `link.click()` triggers client-side routing. Playwright does NOT automatically wait for SPA navigation to complete.

```typescript
// BAD: click link then immediately query — old page DOM still present
await page.getByRole("link", { name: pipelineName }).click();
await page.getByRole("button", { name: "Delete pipeline" }).click(); // strict mode: finds buttons from BOTH pages

// GOOD: wait for URL change after navigation click
await page.getByRole("link", { name: pipelineName }).click();
await expect(page).toHaveURL(/\/pipelines\//);
await page.getByRole("button", { name: "Delete pipeline" }).click();

// ALSO GOOD: wait for a page-specific element
await page.getByRole("link", { name: pipelineName }).click();
await expect(page.getByRole("heading", { name: pipelineName })).toBeVisible();
```

### After Form Submissions

```typescript
// Wait for success indicator AND URL change
await page.getByRole("button", { name: "Save" }).click();
await expect(page.getByText("Saved successfully")).toBeVisible();
await expect(page).toHaveURL(/\/pipelines\//);
```

---

## Strict Mode Rules

Playwright's strict mode (default) throws when a locator matches multiple elements. This is a feature, not a bug — it catches ambiguous tests.

**When you get a strict mode violation:**
1. Do NOT add `.first()` as a band-aid — it hides the real problem
2. DO scope your locator to a container (row, card, dialog, section)
3. DO use a more specific name or `{ exact: true }`
4. `.first()` / `.nth()` are acceptable ONLY when the order is semantically meaningful (e.g., "first item in a sorted list")

---

## Test Isolation Patterns

### Cleanup

```typescript
// GOOD: each describe block cleans up its own data
test.afterAll(async ({ browser }) => {
  const page = await browser.newPage();
  await deletePipeline(page, pipeName);
  await page.close();
});

// Cleanup helper must be resilient to missing data
async function deletePipeline(page: Page, name: string) {
  await page.goto("/pipelines");
  // Wait for list to load before checking
  await page.locator("table, :text('No pipelines yet')").first().waitFor({ timeout: 10_000 });

  const row = page.getByRole("row").filter({ hasText: name });
  if ((await row.count()) === 0) return; // already gone

  // Scope delete button to the specific row
  await row.getByRole("button", { name: /delete/i }).click();
  await page.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(page.getByText(/deleted/i)).toBeVisible();
}
```

### Unique Test Data

```typescript
// Generate unique names per test run to avoid collisions
const ts = () => Date.now().toString(36);
const pipeName = `E2E Test ${ts()}`;

// For parallel workers, include worker index
test.beforeAll(async ({}, testInfo) => {
  const uniqueName = `E2E Test W${testInfo.workerIndex} ${ts()}`;
});
```

---

## Canvas / Complex UI Testing

For ReactFlow, drag-and-drop, or other canvas-based UIs:

```typescript
// BAD: coordinate-based click hoping to hit empty canvas
await page.mouse.click(rfBounds.x + width - 20, rfBounds.y + height - 20);

// BETTER: use the ReactFlow pane element directly
const pane = page.locator(".react-flow__pane");
await pane.click({ position: { x: 10, y: 10 } });

// BEST: if the component exposes a keyboard shortcut or button
await page.keyboard.press("Escape"); // close panel via keyboard
```

When coordinate clicks are unavoidable:
- Wait for animations/transitions to complete first
- Verify the element at the target coordinates via snapshot
- Add a small delay for canvas re-render: `await page.waitForTimeout(200)`

---

## Anti-Patterns

| Anti-Pattern | Why It Fails | Fix |
|-------------|--------------|-----|
| `page.getByRole("button", { name: "Delete" })` in list context | Strict mode — matches every row's delete button | Scope to row first |
| Click link then immediately query | SPA DOM not updated yet | `await expect(page).toHaveURL(...)` |
| `getByRole("button", { name: "Delete pipeline" })` without exact | Substring matches "Delete pipeline X", "Delete pipeline Y", etc. | Use `{ exact: true }` or full unique name |
| `.first()` to silence strict mode | Hides ambiguity, picks wrong element on DOM changes | Scope to container instead |
| `page.waitForTimeout(3000)` for loading | Slow, still flaky | Wait for specific condition |
| Generic `aria-label="Delete"` on list items | All buttons have same accessible name | Include entity name in label |
| Coordinate clicks on canvas without waits | Hit wrong element during animation | Wait for stability, use keyboard alternatives |
| Shared test data across parallel workers | Collision, flaky cleanup | Unique data per worker/run |
