# Decision Log

## Metadata
| Field | Value |
|-------|-------|
| Created | 2025-12-05 |
| Purpose | Track all decisions made during agent system analysis and improvements |
| Related | agent_analysis_plan.md |

---

## 2025-12-05 — Initial Analysis Setup

### Context
User requested deep analysis of the agent system with the goal of identifying improvements for simplicity, robustness, and reliability.

### Current State
- 10 agent definitions across 5 roles (TPM, Planner, SE, Tests, Reviewer)
- Language-specific variants for Python and Go
- Specialized Python-Monolith planner for Flask-OpenAPI3 architecture

### Workflow Assumption
```
TPM (optional) → Implementation Planner (optional) → Software Engineer → Unit Tests Writer → Code Reviewer
                                                                                                    ↓
                                                                              Feedback loop → User → SE/Tests
```

### Decisions Made

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Create structured analysis plan | Complex analysis requires systematic approach; prevents missing important aspects |
| 2 | Track decisions in dedicated file | Future reference for why certain choices were made; helps with onboarding |
| 3 | Execute plan step-by-step with user | User can course-correct; prevents wasted effort on wrong direction |

### Open Questions
- ~~What is the primary pain point with current agents?~~ **Answered**: Manual agent invocation friction
- ~~Are all 5 roles necessary or can some be combined?~~ **Answered**: TPM/Planner optional for complex only
- What's the typical failure mode in practice?

---

## 2025-12-05 — User Context Clarification

### Context
User provided key context about their workflow and pain points before starting Phase 1.

### Key Insights

| Aspect | User Response | Implication |
|--------|---------------|-------------|
| Pain point | Tired of manually mentioning agents for each task | Need automation or simplified invocation |
| Experience | New to agent-based software engineering | Validate approach is sound, not just optimize |
| TPM/Planner usage | Only for complex issues/projects | These are optional; core flow is SE → Tests → Reviewer |
| Small/medium tasks | Uses chat mode directly | Agents may be overkill for simple tasks |
| Language priority | Both Python and Go equally | Must maintain parity between language variants |

### Workflow Refinement
```
Complex tasks:    TPM → Planner → SE → Tests → Reviewer
Medium tasks:     SE → Tests → Reviewer
Simple tasks:     Chat mode (no specialized agents)
```

### Questions This Raises
1. Can we auto-detect complexity and suggest appropriate workflow?
2. Should SE/Tests/Reviewer be a single "implement and verify" agent for medium tasks?
3. Is the 3-agent chain (SE → Tests → Reviewer) the right granularity?

---

## 2025-12-05 — Python Agent Length Clarification

### Context
During Phase 1 analysis, noted that Go agents are 2-3x longer than Python equivalents.

### User Clarification
> Python agents are smaller because they're still in progress and some of the features I want from Go are unavailable currently in our Python development cycle.

### Implications
| Original Assessment | Revised Understanding |
|--------------------|-----------------------|
| Length disparity is a problem | Length disparity is intentional |
| Python may be missing content | Python will be expanded over time |
| Need to "balance" agents | Go is the reference; Python catches up |

### Decision
**Go agents are the "gold standard"** - Python agents will evolve to match as their development cycle matures. No action needed to "fix" disparity.

### Action Items
- [ ] When proposing improvements, apply to Go first
- [ ] Python improvements should not add features unavailable in their cycle

---

## 2025-12-05 — Human-in-the-Loop Requirement

### Context
During Phase 3 research, orchestration/automation was proposed. User raised concern:
> "I also want to be able to take control on actions and correct them at any time."

### Options Considered

| Option | Description | Control Level | Friction |
|--------|-------------|---------------|----------|
| A: Fully Manual | User calls each agent explicitly | Full | High (current) |
| **B: Guided Manual** | Agent suggests next step, user confirms | Full | Medium |
| **C: Pausable Pipeline** | Auto-runs, pauses between agents | At checkpoints | Low |
| **D: Interruptible** | Auto-runs, user can interrupt anytime | Anytime | Lowest |
| E: Fully Autonomous | Runs to completion | None | None |

### User Input
> "Options B, C and D are fine. B was an addition to suggested ones"

### Decision
**All three (B, C, D) are acceptable** - they can coexist:

| Workflow Type | Best Option | Trigger |
|--------------|-------------|---------|
| Learning/exploring | B (Guided) | Default for new patterns |
| Standard development | C (Pausable) | `/implement-feature` command |
| Trusted batch work | D (Interruptible) | `/full-cycle --auto` flag |

### Implementation Approach
1. **Foundation**: Add "suggested next step" to all agents (enables B)
2. **Slash commands**: Create workflow triggers (enables C)
3. **Auto flag**: Optional `--auto` to reduce pauses (enables D)

User always retains ability to:
- Correct before next step
- Interrupt at any point
- Skip steps
- Stop entirely

---

## 2025-12-05 — Phase 5 Final Decisions

### Context
Completed deep analysis (Phases 1-4) and designed improvement proposals.

### Architecture Decision
**Keep existing architecture, enhance communication**

| Option | Decision | Rationale |
|--------|----------|-----------|
| Rewrite agents | ❌ Rejected | Working well individually |
| Merge agents | ❌ Rejected | Specialization is valuable |
| Add orchestration layer | ❌ Rejected | Over-engineering |
| **Enhance handoffs** | ✅ Chosen | Minimal change, maximum impact |

### Implementation Strategy

**Additive changes only** - don't restructure, add targeted sections:

| Change | Type | Impact |
|--------|------|--------|
| SE reads plan | Add section | Fixes critical context loss |
| After Completion | Add to all | Enables guided workflow |
| Structured feedback | Add to Reviewer | Enables feedback loop |
| Escalation guidance | Add to all | Prevents wrong assumptions |
| Slash commands | New files | Reduces invocation friction |

### What We're NOT Doing

| Item | Reason |
|------|--------|
| Extracting shared content | Adds complexity, duplication is manageable |
| Auto-chaining agents | User wants control |
| Simplifying Reviewer | Works well, defer to later |
| Composite agents | Loses specialization benefits |

### Implementation Order

1. **Phase 5A (Foundation)**: SE reads plan, After Completion, Feedback format, Escalation
2. **Phase 5B (Workflow)**: Slash commands
3. **Phase 5C (Polish)**: SE summary for Tests, Reviewer simplification (deferred)

### Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Commands to invoke workflow | 3-5 | 1 |
| Context preserved | ~20% | ~80% |
| User decisions per transition | 2-3 | 1 |

---

<!-- Template for future entries:

## YYYY-MM-DD — <Topic>

### Context
<What was being discussed>

### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| A | ... | ... |
| B | ... | ... |

### Decision
**Chosen**: <Option X>
**Rationale**: <Why this option>
**Trade-offs accepted**: <What we're giving up>

### Action Items
- [ ] <Task 1>
- [ ] <Task 2>

-->
