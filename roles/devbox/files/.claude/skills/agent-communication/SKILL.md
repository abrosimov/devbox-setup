---
name: agent-communication
description: >
  Shared patterns for agent handoffs, escalation rules, completion formats, and user interaction.
  Use when agents need to communicate with each other or with users.
  Triggers on: handoff, escalation, completion, next step, continue, approval.
---

# Agent Communication Patterns

Standardised patterns for agent-to-agent handoffs, user communication, and escalation.

## Handoff Protocol

Every agent must define its position in the pipeline:

```markdown
**Receives from**: <upstream agent or "User">
**Produces for**: <downstream agent or "User">
**Deliverable**: <specific artifact — file, report, code>
**Completion criteria**: <what must be true before handoff>
```

### Common Pipelines

| Pipeline | Flow |
|----------|------|
| Full cycle | TPM → Domain Expert → Planner → SE → Test Writer → Reviewer |
| Full with design | TPM → Domain Expert → Planner → API Designer → Designer → SE → Test Writer → Reviewer |
| API design only | User → API Designer → SE |
| UI design only | User → Designer → FE (future) |
| Quick fix | User → SE → Test Writer → Reviewer |
| Test only | User → Test Writer → Reviewer |
| Review only | User → Reviewer |

## Completion Output Format

When an agent completes its work, use this format:

```markdown
> <One-line summary of what was done>
>
> **Next**: Run `<next-agent>` to <action>.
>
> Say **'continue'** to proceed, or provide corrections.
```

### Examples

**Software Engineer:**
```markdown
> Implementation complete. Created/modified X files.
>
> **Next**: Run `/test` to write tests.
>
> Say **'continue'** to proceed, or provide corrections.
```

**Test Writer:**
```markdown
> Tests complete. X test cases covering Y scenarios.
>
> **Next**: Run `/review` to review implementation and tests.
>
> Say **'continue'** to proceed, or provide corrections.
```

**API Designer:**
```markdown
> API design complete. 4 resources, 12 endpoints defined.
>
> **Next**: Run `/implement` to begin backend implementation, or `/design` for UI/UX design.
>
> Say **'continue'** to proceed, or provide corrections.
```

**Designer (UI/UX):**
```markdown
> Design specification complete. 8 components specified, 42 tokens defined.
>
> **Next**: Frontend Engineer (when available) to implement from this spec.
>
> Say **'continue'** to proceed, or provide corrections.
```

**Code Reviewer (issues found):**
```markdown
> Review complete. Found X blocking, Y important, Z optional issues.
>
> **Next**: Address blocking issues with `/implement`, then re-run `/review`.
>
> Say **'fix'** to have SE address issues, or provide specific instructions.
```

**Code Reviewer (approved):**
```markdown
> Review complete. No blocking issues found.
>
> **Next**: Ready to commit and create PR.
>
> Say **'commit'** to proceed, or provide corrections.
```

## Escalation Rules

### Model Escalation (Sonnet → Opus)

Use complexity metrics to determine when Opus is needed:

```markdown
**If ANY threshold is exceeded**, stop and tell the user:

> ⚠️ **Complex task detected.** This has [specific metrics].
>
> For thorough coverage, re-run with Opus:
> ```
> /<command> opus
> ```
> Or say **'continue'** to proceed with Sonnet (faster, may miss edge cases).
```

### User Escalation

Stop and ask the user when:

1. **Ambiguous requirements** — Multiple valid interpretations
2. **Trade-off decisions** — Significant impact either way
3. **Scope questions** — Unclear what's in/out of scope
4. **Blocking issues** — Cannot proceed without input

### How to Ask Questions

**CRITICAL: Ask ONE question at a time.** Never overwhelm with multiple questions.

**Format:**
```markdown
[Context]: Working on [X], encountered [situation].

Options:
A) [Option] — [trade-off]
B) [Option] — [trade-off]

Recommendation: [A/B] because [reason].

**[Awaiting your decision]**
```

**Example:**
```markdown
The `process_order` function can handle empty orders two ways:

A) Reject with ValidationError — Explicit, prevents downstream issues
B) Return empty result — Permissive, lets caller decide

Recommendation: A because empty orders indicate upstream bugs.

**[Awaiting your decision]**
```

## Approval Validation

Before implementation, agents must verify explicit approval exists.

### Valid Approval Phrases

- "yes", "yep", "y", "go ahead", "proceed", "do it"
- "approved", "looks good", "implement it"
- "option 1" / "option 2" (explicit choice)
- `/implement` command

### NOT Approval (Keep Waiting)

- "interesting", "I see", "okay" (acknowledgment)
- Follow-up questions
- "let me think about it"
- Silence

### Approval Check Format

```markdown
✓ Approval found: "[quote the approval phrase]"
Proceeding with implementation...
```

Or if not found:

```markdown
⚠️ **Approval Required**

This agent requires explicit user approval before implementation.

**To proceed**: Reply with "yes", "go ahead", or use `/implement`.
```

## Decision Classification

Classify decisions before acting:

| Tier | Type | Action |
|------|------|--------|
| 1 | Routine | Apply rule directly, no approval needed |
| 2 | Standard | Quick consideration, check precedent, proceed |
| 3 | Design | Full exploration (5-7 options), present to user |

### Tier 1 Examples (Just Do It)
- Apply formatting
- Fix style violations
- Remove narration comments
- Add missing type hints

### Tier 2 Examples (Quick Decision)
- Error message wording
- Variable naming (when domain clear)
- Small refactoring choices

### Tier 3 Examples (Present Options)
- Pattern/architecture selection
- API design choices
- New abstraction boundaries

## Stop Conditions

Every agent has boundaries. When you catch yourself crossing them, STOP.

**Common stop conditions:**
- Writing code when job is review → STOP, report issues only
- Modifying production code when job is testing → STOP, test as-is
- Adding features not in plan → STOP, ask about scope
- Implementing without approval → STOP, request approval

## Feedback Format

When reporting issues back to another agent or user:

```markdown
### 🔴 Must Fix (Blocking)
- [ ] `file.py:42` — **Issue**: <description>
  **Fix**: <conceptual fix, not code>

### 🟡 Should Fix (Important)
- [ ] `file.py:87` — **Issue**: <description>
  **Fix**: <conceptual fix>

### 🟢 Consider (Optional)
- [ ] `file.py:120` — **Suggestion**: <improvement idea>

### Summary
Review: X blocking | Y important | Z suggestions
Action: [Fix blocking and re-review] or [Ready to proceed]
```
