# Phase 2: Workflow & Interaction Analysis

## Metadata
| Field | Value |
|-------|-------|
| Created | 2025-12-05 |
| Status | In Progress |
| Purpose | Analyze agent interactions, handoffs, and orchestration friction |

---

## Current State: Manual Orchestration

### How User Currently Invokes Agents

```
User: "Use software-engineer-python to implement X"
      ↓
Claude: Loads agent, executes task
      ↓
User: "Now use unit-test-writer-python to write tests"
      ↓
Claude: Loads agent, executes task
      ↓
User: "Now use code-reviewer-python to review"
      ↓
Claude: Loads agent, executes task
```

**Pain Point**: User must explicitly name each agent and manage transitions.

---

## Handoff Analysis

### 1. TPM → Planner

| Aspect | Current State | Issue |
|--------|---------------|-------|
| Output location | `docs/spec.md`, `docs/research.md`, `docs/decisions.md` | ✓ Well-defined |
| Planner reads | Checks for `docs/spec.md` | ✓ Explicit |
| Completion signal | None | ❌ User must decide when spec is "done" |
| Handoff instruction | None in TPM | ❌ TPM doesn't say "now call Planner" |

**Gap**: TPM finishes but doesn't signal readiness or suggest next step.

### 2. Planner → Software Engineer

| Aspect | Current State | Issue |
|--------|---------------|-------|
| Output location | `docs/implementation_plans/<branch>.md` | ✓ Well-defined |
| SE reads plan | **NOT MENTIONED** | ❌ Critical gap |
| Completion signal | None | ❌ User must decide when plan is approved |
| Handoff instruction | None | ❌ Planner doesn't suggest next step |

**Critical Gap**: SE agent doesn't reference implementation plan at all!

```markdown
# In SE agent - NO mention of:
- Reading implementation plan
- Following plan steps
- Checking off plan items
```

### 3. Software Engineer → Unit Test Writer

| Aspect | Current State | Issue |
|--------|---------------|-------|
| SE output | Code changes (no manifest) | ⚠️ No explicit list of what was created |
| Tests reads | Uses `git diff` to find changes | ✓ Self-discovers |
| Context passed | None explicitly | ⚠️ Tests re-discovers everything |
| Handoff instruction | None | ❌ SE doesn't suggest next step |

**Partial Gap**: Tests can discover via git, but loses SE's intent/context.

### 4. Unit Test Writer → Code Reviewer

| Aspect | Current State | Issue |
|--------|---------------|-------|
| Tests output | Test files created | ✓ Discoverable |
| Reviewer reads | Uses `git diff`, Jira MCP | ✓ Self-discovers |
| Context passed | None | ⚠️ Reviewer re-analyzes everything |
| Handoff instruction | None | ❌ Tests doesn't suggest next step |

**Partial Gap**: Reviewer works independently but duplicates analysis.

### 5. Code Reviewer → Software Engineer (Feedback Loop)

| Aspect | Current State | Issue |
|--------|---------------|-------|
| Reviewer output | Markdown report | ✓ Structured |
| Feedback format | Detailed but unstructured | ⚠️ No machine-readable format |
| SE reads feedback | **NOT MENTIONED** | ❌ SE doesn't know about review feedback |
| Loop mechanism | None defined | ❌ User must manually orchestrate |

**Critical Gap**: No defined feedback loop mechanism.

---

## Information Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER ORCHESTRATION                        │
│  (manually invokes each agent, manages all transitions)          │
└─────────────────────────────────────────────────────────────────┘
        │           │            │            │            │
        ▼           ▼            ▼            ▼            ▼
    ┌───────┐   ┌────────┐   ┌────────┐   ┌───────┐   ┌──────────┐
    │  TPM  │──▶│Planner │──▶│   SE   │──▶│ Tests │──▶│ Reviewer │
    └───────┘   └────────┘   └────────┘   └───────┘   └──────────┘
        │           │            │            │            │
        ▼           ▼            ▼            ▼            ▼
    docs/       docs/imp_    (code        (test        (report
    spec.md     plans/       changes)     files)       only)
                <branch>.md

        ════════════════════════════════════════════════════
        EXPLICIT READS:  ✓           ✗            ~            ~
        (does next agent read previous output?)
```

**Legend**:
- ✓ = Explicitly reads previous output
- ✗ = Does NOT read previous output
- ~ = Self-discovers via git (loses context)

---

## Context Loss Analysis

### What Gets Lost at Each Transition

| Transition | Lost Context |
|------------|--------------|
| TPM → Planner | TPM's reasoning about rejected alternatives |
| Planner → SE | **The entire plan!** SE doesn't read it |
| SE → Tests | SE's understanding of edge cases, why certain approaches were chosen |
| Tests → Reviewer | Test writer's risk assessment, areas of concern |
| Reviewer → SE | Severity of issues, which are blocking vs nice-to-have |

### Redundant Work

| Agent | Redundant Work | Cause |
|-------|----------------|-------|
| Planner | Re-researches codebase | TPM may have already explored |
| SE | Explores codebase from scratch | Doesn't read plan's "Codebase Context" |
| Tests | Analyzes git diff | Could receive summary from SE |
| Reviewer | Full enumeration from scratch | Could receive SE+Tests summary |

---

## Orchestration Friction Analysis

### Current User Burden

1. **Remember agent names**: `software-engineer-python`, `unit-test-writer-python`, etc.
2. **Know the sequence**: Which agent comes after which?
3. **Decide transitions**: When is SE "done"? When to call Tests?
4. **Manage context**: Repeat information that agents should share
5. **Handle failures**: What if Reviewer finds issues? Manually loop back.

### Friction Points Ranked

| Rank | Friction | Frequency | User Quote |
|------|----------|-----------|------------|
| 1 | Naming agents explicitly | Every task | "Tired of mentioning agents each time" |
| 2 | Managing feedback loops | When issues found | (implied) |
| 3 | Deciding when to transition | Every transition | (implicit) |
| 4 | Repeating context | Frequently | (implicit) |

---

## Alternative Workflow Models

### Model A: Current (Explicit Orchestration)
```
User calls each agent by name, manages all transitions
```
- **Pros**: Full control, flexibility
- **Cons**: High friction, user burden, context loss

### Model B: Chained Agents (Auto-Transition)
```
User calls first agent, each agent calls the next automatically
```
- **Pros**: Zero orchestration burden
- **Cons**: Less control, may run unnecessary agents, expensive

### Model C: Conductor Agent (Smart Orchestration)
```
User describes task, conductor decides which agents to invoke
```
- **Pros**: Intelligent routing, context preserved
- **Cons**: Added complexity, conductor can make wrong choices

### Model D: Composite Agents (Merged Roles)
```
Fewer, larger agents that combine related roles
```
- **Pros**: Simpler invocation, preserved context
- **Cons**: Less specialization, larger prompts

### Model E: Slash Commands (Workflow Triggers)
```
User types /implement, /test, /review - or /full-cycle
```
- **Pros**: Easy invocation, memorable, can bundle steps
- **Cons**: Requires command setup, less flexible

---

## Workflow Variants by Task Size

### Current Reality (from user input)

| Task Size | Current Approach | Agents Used |
|-----------|------------------|-------------|
| Simple | Chat mode | None (direct Claude) |
| Medium | Manual agent calls | SE → Tests → Reviewer |
| Complex | Full pipeline | TPM → Planner → SE → Tests → Reviewer |

### Observation
User already naturally segments by complexity. The friction is in **medium tasks** where 3 agents must be manually invoked.

---

## Key Questions

1. **Should SE read the implementation plan?**
   - Currently doesn't. This seems like a critical oversight.

2. **Should agents auto-chain?**
   - User might lose control they want.

3. **Can we reduce 3 agents to 1-2 for medium tasks?**
   - Combine SE + Tests? Or SE + Tests + Review?

4. **Should there be a "workflow mode" vs "agent mode"?**
   - `/implement-feature` runs SE → Tests → Review automatically
   - Individual agents still available for fine control

5. **How to handle the feedback loop?**
   - Reviewer outputs structured feedback
   - User can say "fix these" and SE knows what to fix

---

## Preliminary Recommendations

### Quick Wins (No structural changes)

1. **Add plan reading to SE agents**
   ```markdown
   ## Before Implementation
   1. Check for `docs/implementation_plans/<branch>.md`
   2. If exists, follow the plan steps
   3. Mark steps complete as you go
   ```

2. **Add "next step" suggestions to each agent**
   ```markdown
   ## After Completion
   Suggest: "Implementation complete. To write tests, invoke unit-test-writer-{lang}"
   ```

3. **Add structured feedback format to Reviewer**
   ```markdown
   ## Feedback for SE
   ### Must Fix (Blocking)
   - [ ] file.go:42 - Error not wrapped

   ### Should Fix (Important)
   - [ ] file.go:87 - Missing test coverage

   ### Consider (Optional)
   - [ ] file.go:100 - Could simplify logic
   ```

### Structural Options (Need discussion)

| Option | Change | Benefit | Cost |
|--------|--------|---------|------|
| Slash commands | Add `/implement`, `/test`, `/review`, `/full-cycle` | Easy invocation | Setup effort |
| Composite agent | `implementer` = SE + Tests | Fewer transitions | Larger prompt, less specialization |
| Conductor | Meta-agent routes to specialists | Smart orchestration | Complexity, potential wrong routing |

---

## Summary

### What's Working
- Agents are individually well-designed
- Self-discovery via git works (though lossy)
- User has flexibility and control

### What's Not Working
- SE doesn't read implementation plan (critical gap)
- No handoff suggestions between agents
- User bears full orchestration burden
- Context lost at every transition
- Feedback loop undefined

### Core Problem
**Agents are designed as independent units, not as a workflow.**

Each agent is excellent in isolation but doesn't know:
- What came before it
- What comes after it
- How to pass context forward
