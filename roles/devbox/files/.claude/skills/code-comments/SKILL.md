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

NEVER write comments that describe what code does. Forbidden: `# Get user from database`, `// Create new connection`, `# Check if valid`, `// Initialize the service`.

### The Deletion Test

**Before writing ANY comment, ask:** "If I delete this, would a competent developer misuse this code?"

- **NO** --> Don't write the comment
- **YES** --> Write ONLY the non-obvious part

## Acceptable Comments

Comments are justified ONLY when explaining something **non-obvious**: WHY something is done, import/init ordering constraints, non-obvious side effects, thread safety caveats, complex protocols.

```python
self.__repo.save(order)  # Must save before notification -- order ID required
```

**NEVER** use section dividers or markers: `# --- Configuration ---`, `// === Tests ===`, `// Private methods`.

## Docstring Policy

**Default: NO docstrings.** Names, types, and structure ARE the documentation.

Rare exceptions requiring justification: import/init ordering, non-obvious side effects, thread safety, complex protocols, external library public APIs where users rely on `help()`.

Go doc comments: follow standard conventions but still avoid narration.

## Self-Review Checklist

Before completing any code task:

1. **Did I add ANY comments that describe WHAT the code does?** If YES --> Remove them NOW
2. **For each comment I kept, does deleting it make the code unclear?** If NO --> Delete it NOW
3. **Are there any section markers or dividers?** If YES --> Remove them NOW

Only proceed after removing all narration comments.
