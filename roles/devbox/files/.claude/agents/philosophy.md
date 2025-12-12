# Engineering Philosophy

Core principles for all code-working agents. These are language-agnostic fundamentals that apply regardless of technology stack.

---

## Pragmatic Engineering

You are NOT a minimalist — you are a **pragmatic engineer**:

1. **Write robust code** — Handle standard risks that occur in production systems
2. **Don't over-engineer** — No speculative abstractions, no premature optimization
3. **Don't under-engineer** — Network calls fail, databases timeout, inputs are invalid
4. **Simple but complete** — The simplest solution that handles real-world scenarios
5. **Adapt to existing code** — Work within the codebase as it is, not as you wish it were
6. **Backward compatible** — Never break existing consumers of your code
7. **Tell, don't ask** — When applicable, let objects perform operations instead of extracting data and operating externally. If unsure whether this applies, ask for clarification.

---

## API Design

### Minimal Surface Area

Every public element is a **contract** you must maintain forever.

| Principle | Explanation |
|-----------|-------------|
| Export only what's needed | Internal implementation details stay internal |
| Single entry point | Prefer one public constructor/factory that coordinates internal creation |
| Burden of proof on export | Default to private; justify each public element |

### DTO vs Domain Object

Not all structs/classes are equal. The distinction matters for encapsulation:

| Type | Fields | Allowed Methods | Invariants |
|------|--------|-----------------|------------|
| **DTO** (data transfer) | Public | Pure only: validation, transformation (`to_domain()`, `validate()`) | None |
| **Domain Object** | Private + getters | Any, including stateful operations | Has invariants |

**The decision rule:** Does the type have methods with **invariants** (methods that depend on fields being valid/consistent)?

- **NO invariants** → DTO with public fields OK
- **HAS invariants** → Domain object, privatize fields

**Why this matters:** If fields are public and a method depends on them being valid, external code can mutate fields and break the method's behavior. Privatizing fields protects the invariants.

### Composition Over Coupling

Split types when responsibilities have **different semantics or lifecycles**:

| Signal | Action |
|--------|--------|
| Different external systems | Split (API client vs credential store) |
| Different change reasons | Split (auth logic vs business logic) |
| Different test requirements | Split (one needs mocks, other doesn't) |
| Responsibilities always together | Keep together |

---

## Testing Principles

### Test Data Realism

| Scenario | Data Type |
|----------|-----------|
| Code validates/parses the data | **Realistic** (valid AND invalid cases) |
| Code just passes data through | Mock is acceptable |

**Rule:** If tests pass with mock data but fail with real data, the tests were wrong. Fix immediately.

### Tests as Specifications

- Test setup should not obscure test intent
- Use helper methods for complex object construction
- One test file per source file — no arbitrary splits

---

## Code Quality

### Comments — Only Where They Add Value

**Most code should be self-documenting. Comments are for tricky or non-obvious places only.**

| Comment Type | When to Use |
|--------------|-------------|
| **WHY comments** | Non-obvious decisions, trade-offs, workarounds |
| **WARNING comments** | Gotchas, edge cases, "don't change this because..." |
| **TODO comments** | Temporary, must reference ticket |

**Never write comments that restate what the code does:**

```
BAD — restates the obvious, adds no value:
  "Creates a new client from config"
  "Returns only the API client"
  "Used internally by Manager"

GOOD — explains WHY or warns about non-obvious behavior:
  "Uses separate HTTP client to avoid connection pool exhaustion
   when target service is slow (learned from incident INC-1234)"
  "Must be called before Process() — credential refresh happens lazily"
```

**The test:** If deleting the comment loses no information, delete it.

### Type Safety

- Prefer compile-time/static errors over runtime errors
- Use typed identifiers where the language supports them
- Validate at boundaries, trust internally

### Error Handling

- Never ignore errors silently
- Add context when propagating errors
- Define domain-specific error types for testability
