---
name: iterative-retrieval
description: >
  Progressive context refinement pattern for subagents and research tasks.
  Solves the "don't know what I need" problem through DISPATCH/EVALUATE/REFINE/LOOP.
  Use when spawning Explore agents, when agents need to find relevant code, or when
  initial searches return too much noise or too little signal.
  Triggers on: subagent context, explore, find relevant, search codebase, iterative,
  retrieval, refine search, context quality.
---

# Iterative Retrieval

Progressive context refinement for subagents and research tasks.

---

## Problem

Subagents are spawned with limited context. Standard approaches fail:

| Approach | Problem |
|----------|---------|
| Send everything | Exceeds context limits, dilutes signal |
| Send nothing | Agent lacks critical information |
| Guess upfront | Often wrong — you don't know what you need until you start looking |

## Solution: 4-Phase Loop

```
DISPATCH → EVALUATE → REFINE → LOOP (max 3 cycles)
```

Each cycle narrows the search. By cycle 2-3, the agent has high-relevance context with minimal noise.

---

## Phase 1: DISPATCH

Broad initial query to gather candidates.

```
Search patterns: ['src/**/*.go', 'internal/**/*.go']
Keywords: ['authentication', 'middleware', 'token']
Excludes: ['*_test.go', 'vendor/', 'mock_*']
```

**Rules:**
- Cast a wide net — it's cheaper to filter than to miss
- Use 2-3 keyword families (synonyms, related terms)
- Exclude known noise (tests, vendored code, mocks)
- Limit to ~20 candidate files (manageable for evaluation)

## Phase 2: EVALUATE

Score each candidate file for relevance (0.0–1.0):

| Score | Meaning | Action |
|-------|---------|--------|
| 0.8–1.0 | Directly implements target functionality | **Keep** — read in full |
| 0.5–0.7 | Contains related patterns, types, interfaces | **Keep** — skim for relevant sections |
| 0.2–0.4 | Tangentially related | **Drop** — note any useful terms found |
| 0.0–0.1 | Not relevant | **Drop** — exclude in next cycle |

For each file, record:
- **Relevance score** with 1-line reasoning
- **Gaps identified** — "this file imports X but X wasn't in our search"
- **New terms discovered** — domain vocabulary found in the code

## Phase 3: REFINE

Update search criteria based on evaluation:

- **Add** new patterns discovered in high-relevance files
- **Add** domain terms found in the codebase (not your initial guess)
- **Exclude** confirmed irrelevant paths and directories
- **Target** specific gaps identified in Phase 2

```
# Cycle 1: Started with "authentication"
# Found: auth.go imports "internal/session" and "pkg/jwt"

# Cycle 2: Refined search
New patterns: ['internal/session/**', 'pkg/jwt/**']
New keywords: ['refresh_token', 'claims', 'bearer']
New excludes: ['internal/legacy/', 'pkg/deprecated/']
```

## Phase 4: LOOP

Check exit conditions:

| Condition | Met? | Action |
|-----------|------|--------|
| 3+ high-relevance files (score ≥ 0.7) | Yes → **EXIT** | Sufficient context |
| No critical gaps remaining | Yes → **EXIT** | Search is complete |
| Max 3 cycles reached | Yes → **EXIT** | Diminishing returns |
| Otherwise | No → **REFINE** | Continue to next cycle |

---

## Example: Bug Fix Context

```
Task: "Fix token expiry not being checked in refresh endpoint"

Cycle 1: DISPATCH
  Patterns: ['**/*.go']
  Keywords: ['token', 'refresh', 'expiry']
  Results:  auth.go (0.9), tokens.go (0.8), user.go (0.3), config.go (0.2)

Cycle 2: REFINE
  Gaps: auth.go imports session_manager.go, jwt_utils.go
  New keywords: ['session', 'jwt', 'claims', 'bearer']
  Drop: user.go, config.go
  Results: session_manager.go (0.95), jwt_utils.go (0.85)

EXIT: 4 files with score ≥ 0.8, no gaps remaining
Final context: auth.go, tokens.go, session_manager.go, jwt_utils.go
```

---

## When to Use

### Use Iterative Retrieval For:

- **Explore agents** — when the Task tool spawns an `Explore` subagent, teach it to refine
- **Bug investigation** — don't know which files are involved yet
- **Feature implementation** — need to understand existing patterns before writing code
- **Cross-cutting concerns** — feature touches multiple modules

### Don't Use For:

- **Known file paths** — if you already know which files to read, just read them
- **Simple searches** — a single Grep or Glob call suffices
- **Small codebases** — <50 files, just read them all

---

## Integration with Agent Pipeline

When spawning agents via the Task tool, include retrieval guidance in the prompt:

```
Task(
  subagent_type: "Explore",
  prompt: "Find all files related to user authentication.
           Use iterative retrieval:
           1. Start with broad search for 'auth', 'login', 'session'
           2. Evaluate relevance of each file (0-1 score)
           3. Refine based on imports and references found
           4. Return only files scoring ≥ 0.7 with brief description of each"
)
```

For implementation agents, pre-gather context using iterative retrieval, then pass the final file list:

```
# Step 1: Gather context (Explore agent)
relevant_files = Task(Explore, "Find files related to...")

# Step 2: Implement (SE agent) — receives focused context
Task(SE, "Implement X. Key files: {relevant_files}")
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Instead |
|--------------|---------|---------|
| Skipping EVALUATE phase | Keep irrelevant files, dilute context | Always score before proceeding |
| More than 3 cycles | Diminishing returns, wasted tokens | Exit at 3, work with what you have |
| Searching without excludes | Test files and mocks pollute results | Always exclude `*_test.*`, `mock_*`, `vendor/` |
| Broad keywords only | "code", "function", "handler" match everything | Use domain-specific terms from the codebase |
| Sending all candidates to agent | Context overload | Only send files scoring ≥ 0.7 |
