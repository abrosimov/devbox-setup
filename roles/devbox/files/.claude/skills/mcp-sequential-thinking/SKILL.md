---
name: mcp-sequential-thinking
description: >
  Sequential Thinking MCP patterns for structured multi-step reasoning. Covers when
  to use sequential thinking, thought management, branching, and summary generation.
  Triggers on: sequential thinking, structured reasoning, thought chain, problem
  decomposition, multi-step analysis, trade-off analysis.
---

# Sequential Thinking MCP

Structured problem decomposition using the Sequential Thinking MCP server.

---

## Available Tools

| Tool | Purpose |
|------|---------|
| `mcp__sequentialthinking__sequentialthinking` | Process a single thought in a reasoning chain |

### sequentialthinking Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `thought` | string | Yes | The content of the current thinking step |
| `nextThoughtNeeded` | boolean | Yes | Whether another thought step is needed |
| `thoughtNumber` | integer | Yes | Current position in the sequence (1-based) |
| `totalThoughts` | integer | Yes | Estimated total thoughts needed (can be revised) |
| `isRevision` | boolean | No | Whether this revises a previous thought |
| `revisesThought` | integer | No | Which thought number is being reconsidered |
| `branchFromThought` | integer | No | Starting point for an alternative reasoning path |
| `branchId` | string | No | Identifier for this branch of thinking |

---

## When to Use

**Use for:**
- Trade-off analysis with multiple competing options (3+ options)
- Problem decomposition where each step constrains the next
- Assumption validation chains (validate A before reasoning about B)
- Multi-criteria decision making
- Domain classification (Cynefin) with supporting evidence

**Do NOT use for:**
- Simple lookups or factual questions
- Linear tasks with obvious steps
- Code review checklists (already structured)
- Tasks with fewer than 3 reasoning steps

---

## Usage Patterns

### Pattern 1: Trade-Off Analysis

Use when comparing options with multiple dimensions.

**Sequence:**
1. Frame the decision — what are we choosing between?
2. List evaluation criteria (weighted by importance)
3. One thought per option — evaluate against criteria
4. Synthesis — compare options side by side
5. Recommendation with confidence level

**Example thought chain:**
```
Thought 1/5: "We need to choose between cursor-based and offset-based pagination.
Criteria: performance at scale (weight: high), developer ergonomics (medium),
backwards compatibility (low)."

Thought 2/5: "Option A: Cursor-based — O(1) seek time regardless of offset,
stable results during pagination, but opaque cursors are harder to debug..."

Thought 3/5: "Option B: Offset-based — familiar LIMIT/OFFSET, easy to implement,
but O(n) for deep pages and unstable when data changes..."

Thought 4/5: "Comparing: cursor wins on performance (high weight), offset wins
on ergonomics (medium weight). At our expected scale (>1M rows), performance
dominates..."

Thought 5/5: "Recommendation: cursor-based pagination. Confidence: high.
Key trade-off accepted: slightly worse developer ergonomics."
```

### Pattern 2: Assumption Validation Chain

Use when conclusions depend on prior assumptions being true.

**Sequence:**
1. List all assumptions (explicit and implicit)
2. One thought per assumption — evidence for/against
3. Branch if an assumption is invalidated (revise downstream thoughts)
4. Synthesise validated vs invalidated assumptions

### Pattern 3: Problem Decomposition

Use for breaking complex problems into tractable sub-problems.

**Sequence:**
1. State the full problem
2. Identify independent sub-problems
3. One thought per sub-problem — constraints and dependencies
4. Identify the critical path (which sub-problems block others)
5. Propose an ordering

---

## Branching and Revision

### When to Branch

Branch when a thought reveals that an earlier assumption was wrong:

```
Thought 4/6 (branch from thought 2, branchId: "no-cache"):
"If we remove the caching assumption, the performance profile changes
significantly..."
```

### When to Revise

Revise when new information refines (but doesn't invalidate) an earlier thought:

```
Thought 5/6 (revises thought 3):
"After researching further, the API rate limit is 1000/min not 100/min,
which changes the batching strategy..."
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Instead |
|--------------|---------|---------|
| One-thought chains | Overhead without value | Skip sequential thinking entirely |
| Thoughts that repeat previous content | Token waste | Reference prior thoughts, add new insight only |
| Unbounded chains (20+ thoughts) | Context pollution | Limit to 8-10 thoughts max, summarise earlier ones |
| Using for simple decisions | Over-engineering | Just decide; sequential thinking is for genuinely hard trade-offs |

---

## Graceful Degradation

If `mcp__sequentialthinking` is not available (connection error or not configured):
- **Skip** structured reasoning tool calls
- **Proceed** with inline reasoning in your response
- **Do not** block on MCP availability
