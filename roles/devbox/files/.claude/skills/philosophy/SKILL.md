---
name: philosophy
alwaysApply: true
description: >
  Engineering philosophy and core principles for all agents. Covers the Prime Directive
  (reduce complexity), pragmatic engineering, API design, interface design, testing principles,
  and code quality standards. Triggers on: complexity, abstraction, over-engineering, YAGNI,
  simplicity, philosophy, prime directive, pragmatic, interface design, DTO, domain object.
---

# Engineering Philosophy

Core principles for all code-working agents. These are language-agnostic fundamentals that apply regardless of technology stack.

---

## The Prime Directive: Reduce Complexity

**The primary goal of software engineering is to reduce complexity, not increase it.**

Every line of code is a liability. Every abstraction adds cognitive load. Every feature creates maintenance burden. The engineer's job is to solve problems with the **minimum viable complexity**.

### Occam's Razor for Code

> "Entities should not be multiplied beyond necessity."

| Principle | Application |
|-----------|-------------|
| **Simplest solution wins** | If two designs solve the problem, choose the one with fewer moving parts |
| **Additions require justification** | Default is NO. Every new file, function, type, parameter must prove its necessity |
| **Deletions are features** | Removing code improves the system. Celebrate deletions. |

### Certainty Over Cleverness

**Predictable code beats clever code.** Debugging clever code costs more than writing boring code.

| Prefer | Over | Why |
|--------|------|-----|
| Explicit | Implicit | Reader sees what happens without hunting |
| Boring | Clever | Clever fails in unexpected ways |
| Obvious | Elegant | Elegant often means "hard to understand" |
| Repetition (2-3x) | Premature abstraction | DRY is not always right; WET can be clearer |

**The test:** Can a tired engineer at 3am understand this code? If not, simplify.

### Cognitive Load Budget

Every codebase has a **cognitive load budget**. Each addition spends from this budget:

| High Cost (avoid) | Low Cost (prefer) |
|-------------------|-------------------|
| New abstraction layers | Direct implementation |
| Custom DSLs | Standard language features |
| Implicit behaviour (magic) | Explicit behaviour |
| Many small files | Fewer, cohesive files |
| Deep inheritance | Flat composition |
| Generic solutions | Specific solutions |

**Rule:** Before adding complexity, ask: "Is this solving a problem we actually have, or one we imagine we might have?"

### Less Is More -- Practical Application

| Situation | Wrong Instinct | Right Action |
|-----------|----------------|--------------|
| "This might need to change" | Add abstraction layer | Write concrete code; refactor IF it changes |
| "This could be reused" | Extract to shared library | Keep inline; extract only on 3rd use |
| "This handles all cases" | Build comprehensive framework | Handle current cases; extend when needed |
| "This is more flexible" | Add configuration options | Hardcode; make configurable only when requested |

### The Reversal Test

Before adding any code, ask: **"If this already existed, would removing it improve the system?"**

- If YES --> Don't add it
- If NO --> Proceed, but keep it minimal

---

## Language Standard: British English

**All agents must use British English spelling in all output** -- documentation, comments, error messages, and communication.

| American (DON'T) | British (DO) |
|------------------|--------------|
| behavior | behaviour |
| color | colour |
| organize | organise |
| analyze | analyse |
| serialize | serialise |
| initialize | initialise |
| optimize | optimise |
| defense | defence |
| center | centre |
| license (noun) | licence |

---

## Error Detection Hierarchy -- Fail Fast

**Catch issues as early as possible in the development/deployment lifecycle.**

Push errors left: compile-time > startup-time > runtime.

| When | How | Example |
|------|-----|---------|
| **Compile-time** (BEST) | Type system, linter | `type UserID string` prevents passing `OrderID` |
| **Startup-time** (GOOD) | Constructor validation, init panic | `NewServer()` returns error if config invalid |
| **Runtime** (ACCEPTABLE) | Return error, caller handles | `Process()` returns error if external API fails |
| **Runtime panic** (NEVER) | Crash | `Must()` in request handler -- FORBIDDEN |

**Why this matters:**
- Compile-time errors caught in IDE, before commit
- Startup errors caught in first test run, before deploy
- Runtime errors require production monitoring to detect
- Runtime panics crash services, affect users

**Design principle:** If we can make an error happen during compile-time, we do it. If we can make it happen during startup-time, we do it. Everyone makes mistakes, so known issues must be caught ASAP.

> See `go-errors` skill for language-specific examples.

---

## Data Transformation -- Prefer Immutability

**Prefer creating new data over mutating existing data.** Think of data processing as a pipeline: each step takes input and produces new output, leaving the original untouched.

| Pattern | Instead Of |
|---------|-----------|
| Return new struct with changes | Modify struct fields in place |
| Map/filter to new collection | Modify collection in place |
| Builder that produces new instance | Setter methods that mutate |
| Pipeline: input --> transform --> new output | input --> mutate --> return same |

**Why:**
- No hidden side effects -- callers keep their original data
- Safe for concurrency -- no shared mutable state
- Easier debugging -- data doesn't change under you
- Enables pipeline composition

**Exception:** Performance-critical hot paths where allocation cost is measured and proven to be a bottleneck. Document with a WHY comment.

---

## Pragmatic Engineering

You are NOT a minimalist -- you are a **pragmatic engineer**:

1. **Write robust code** -- Handle standard risks that occur in production systems
2. **Don't over-engineer** -- No speculative abstractions, no premature optimization
3. **Don't under-engineer** -- Network calls fail, databases timeout, inputs are invalid
4. **Simple but complete** -- The simplest solution that handles real-world scenarios
5. **Adapt to existing code** -- Work within the codebase as it is, not as you wish it were
6. **Backward compatible** -- Never break existing consumers of your code
7. **Tell, don't ask** -- When applicable, let objects perform operations instead of extracting data and operating externally. If unsure whether this applies, ask for clarification.

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

- **NO invariants** --> DTO with public fields OK
- **HAS invariants** --> Domain object, privatize fields

**Why this matters:** If fields are public and a method depends on them being valid, external code can mutate fields and break the method's behaviour. Privatizing fields protects the invariants.

> **Go-specific patterns:** See `go-architecture` skill "Struct Separation" for when to separate structs based on technical concerns (DB types, security, generated APIs).

---

## Interface Design -- When and Where

### Don't Create Interfaces Prematurely

**Go proverb:** "The bigger the interface, the weaker the abstraction."

**Our addition:** "Don't create the interface until you need it."

#### When to Create an Interface:

| Situation | Create Interface? |
|-----------|-------------------|
| Have 2+ implementations | Yes |
| Need to mock for testing | Yes |
| External contract (plugin system) | Yes |
| "Might need multiple implementations later" | No -- YAGNI |
| "Interfaces are best practice" | No -- Cargo cult |

**When you add a second implementation, THEN extract interface.**

> **Go-specific patterns:** See `go-architecture` skill "Interface Design" for consumer-side definition, same-file placement, and small interface principles.

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
- One test file per source file -- no arbitrary splits
