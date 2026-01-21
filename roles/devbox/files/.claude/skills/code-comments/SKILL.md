---
name: code-comments
description: >
  Rules for code comments and documentation. Covers narration comments (forbidden),
  acceptable WHY comments, docstring policies. Triggers on: comment, docstring,
  documentation, narration, self-documenting.
---

# Code Comments Policy

**Default stance: NO comments.** Code should be self-documenting through clear names, types, and structure.

## Zero Tolerance: Narration Comments

❌ **NEVER write comments that describe what code does.**

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

### Rejected vs Accepted Examples

**Python:**
```python
# ❌ REJECTED — narration comments
def process_order(self, order: Order) -> None:
    # Validate the order
    self.__validator.validate(order)

    # Save to database
    self.__repo.save(order)

    # Send notification
    self.__notifier.notify(order.user_id, "Order processed")

# ✅ ACCEPTED — no comments needed, code is clear
def process_order(self, order: Order) -> None:
    self.__validator.validate(order)
    self.__repo.save(order)
    self.__notifier.notify(order.user_id, "Order processed")
```

**Go:**
```go
// ❌ REJECTED — narration comments
func (s *OrderService) Process(ctx context.Context, order Order) error {
    // Validate the order
    if err := s.validator.Validate(order); err != nil {
        return err
    }

    // Save to database
    if err := s.repo.Save(ctx, order); err != nil {
        return err
    }

    return nil
}

// ✅ ACCEPTED — no comments needed, code is clear
func (s *OrderService) Process(ctx context.Context, order Order) error {
    if err := s.validator.Validate(order); err != nil {
        return err
    }

    if err := s.repo.Save(ctx, order); err != nil {
        return err
    }

    return nil
}
```

## Acceptable Comments

Comments are justified ONLY when explaining something **non-obvious** that cannot be captured in names/types.

### WHY Explanations

```python
# ✅ Business constraint
self.__repo.save(order)  # Must save before notification — order ID required

# ✅ External system quirk
response = client.get(url, timeout=(5, 30))  # API rate limit: 10 req/sec max

# ✅ Non-obvious dependency
import prometheus  # Import before Flask routes — must initialize first
```

```go
// ✅ Concurrency constraint
s.mu.Lock()  // Lock before read — map is not thread-safe

// ✅ Protocol requirement
conn.SetDeadline(time.Now().Add(timeout))  // TCP keepalive requires periodic activity

// ✅ Historical context / workaround
// Legacy API returns single quotes instead of double — parse manually
data := strings.ReplaceAll(raw, "'", "\"")
```

### Forbidden Section Markers

❌ **NEVER use section dividers or markers:**

```python
# ❌ FORBIDDEN
# --- Configuration ---
# === Tests ===
# Class-level attributes
# Instance attributes (set in __new__)
```

```go
// ❌ FORBIDDEN
// --- Configuration ---
// === Tests ===
// Private methods
// Public API
```

## Docstring Policy

### Python Docstrings

**Default: NO docstrings.** Names, types, and structure ARE the documentation.

**Forbidden:**
```python
# ❌ Describes what name already says
class UserRepository:
    """Repository for managing users in the database."""

# ❌ Describes what method does
def process_order(self, order: Order) -> ProcessedOrder:
    """Process an order by validating and calculating totals."""

# ❌ Describes exception purpose
class ReadOnlyRepositoryError(Exception):
    """Raised when attempting write operations on a read-only repository."""
```

**Rare exceptions (require justification):**

| Exception | Example |
|-----------|---------|
| Import/init order | "Import before route definitions — Prometheus must initialise first" |
| Non-obvious side effects | "Starts background health-check thread on first call" |
| Thread safety | "Not thread-safe. Create one instance per request." |
| Complex protocol | "Must call `begin()` before `execute()`, then `commit()` or `rollback()`" |
| External library public API | Users rely on `help()`, can't easily read source |

**Correct pattern — contract only, no implementation details:**
```python
# ✅ Contract-only for library public API
def commit(self) -> None:
    """Commit the transaction. Raises TransactionDoomed if doomed."""
```

### Go Doc Comments

Follow standard Go doc comment conventions — but still avoid narration.

**Forbidden:**
```go
// ❌ Describes what name says
// Process processes the order.
func (s *Service) Process(order Order) error {

// ❌ Implementation details
// Process validates the order, saves it, and sends notification.
func (s *Service) Process(order Order) error {
```

**Acceptable:**
```go
// ✅ Non-obvious behaviour
// Process is idempotent — calling twice with same order ID has no effect.
func (s *Service) Process(order Order) error {

// ✅ Important constraint
// Close must be called exactly once. Calling twice panics.
func (c *Connection) Close() error {
```

## Test Comments

**Tests need FEWER comments than production code.** Test names ARE documentation.

**Forbidden in tests:**
```python
# ❌ FORBIDDEN
# Create mock repository
# Setup test data
# Execute the function
# Verify result
```

```go
// ❌ FORBIDDEN
// Create mock repository
// Setup test data
// Execute the function
// Verify result
```

**Only acceptable test comment — explains non-obvious assertion:**
```python
assert result == expected  # API returns sorted by created_at
```

```go
assert.Equal(t, expected, result)  // API returns sorted by created_at
```

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
