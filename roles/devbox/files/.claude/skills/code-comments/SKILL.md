---
name: code-comments
alwaysApply: true
description: >
  Rules for code comments and documentation. Covers narration comments (forbidden),
  acceptable WHY comments, docstring policies. Triggers on: comment, docstring,
  documentation, narration, self-documenting.
---

# Code Comments Policy

**Default stance: NO comments.** Code should be self-documenting through clear names, types, and structure.

## Zero Tolerance: Narration Comments

NEVER write comments that describe what code does.

### Forbidden Patterns

| Language | Forbidden Examples |
|----------|-------------------|
| Python | `# Get user from database`, `# Create new connection`, `# Check if valid` |
| Go | `// Get user from database`, `// Create new connection`, `// Check if valid` |
| Both | `# Return the result`, `// Initialize the service`, `# Loop through items` |

### The Deletion Test

**Before writing ANY comment, ask:** "If I delete this, would a competent developer misuse this code?"

- **NO** → Don't write the comment
- **YES** → Write ONLY the non-obvious part

## Acceptable Comments

Comments are justified ONLY when explaining something **non-obvious** that cannot be captured in names/types.

### WHY Explanations

```python
self.__repo.save(order)  # Must save before notification — order ID required
```

### Forbidden Section Markers

NEVER use section dividers or markers:

```
# --- Configuration ---    // === Tests ===    // Private methods
```

## Docstring Policy

### Python Docstrings

**Default: NO docstrings.** Names, types, and structure ARE the documentation.

**Rare exceptions (require justification):**

| Exception | Example |
|-----------|---------|
| Import/init order | "Import before route definitions — Prometheus must initialise first" |
| Non-obvious side effects | "Starts background health-check thread on first call" |
| Thread safety | "Not thread-safe. Create one instance per request." |
| Complex protocol | "Must call `begin()` before `execute()`, then `commit()` or `rollback()`" |
| External library public API | Users rely on `help()`, can't easily read source |

### Go Doc Comments

Follow standard Go doc comment conventions — but still avoid narration.

```go
// ❌ Process processes the order.
func (s *Service) Process(order Order) error {

// ✅ Process is idempotent — calling twice with same order ID has no effect.
func (s *Service) Process(order Order) error {
```

## Test Comments

Tests need fewer comments than production code. Only acceptable: explaining non-obvious assertions.

## Comment Formatting

### Python
- Two spaces before `#`, one space after: `code  # comment`
- Inline comments on same line as code, not above

### Go
- One space after `//`: `// comment`
- Doc comments start with identifier name: `// Process does X`

## Self-Review Checklist

Before completing any code task:

1. **Did I add ANY comments that describe WHAT the code does?**
   - If YES → Remove them NOW

2. **For each comment I kept, does deleting it make the code unclear?**
   - If NO → Delete it NOW

3. **Are there any section markers or dividers?**
   - If YES → Remove them NOW

Only proceed after removing all narration comments.
