# Phase 5: Improvement Proposals

## Metadata
| Field | Value |
|-------|-------|
| Created | 2025-12-05 |
| Status | Complete |
| Purpose | Concrete, implementable improvements based on analysis |
| Approach | Minimal invasive changes that preserve agent specialization |

---

## Design Principles

1. **Additive, Not Rewriting** - Add sections to agents, don't restructure them
2. **Preserve Specialization** - Each agent keeps its single job
3. **Enable Without Forcing** - Workflow guidance is optional, not mandatory
4. **Human-in-the-Loop Default** - Always pause for user confirmation
5. **Go First** - Apply to Go agents first (reference standard)

---

## Implementation Overview

| Phase | Changes | Effort | Impact |
|-------|---------|--------|--------|
| **5A: Foundation** | 3 new sections across agents | 3-4 hrs | Fixes critical gaps |
| **5B: Workflow** | 4 slash commands | 1-2 hrs | Reduces friction |
| **5C: Polish** | SE summary, Reviewer simplification | 2-3 hrs | Optimization |

---

## Phase 5A: Foundation Changes

### Change 1: SE Reads Implementation Plan

**Add to: `software_engineer_go.md`, `software_engineer_python.md`**

**Location**: After "Engineering Philosophy", before "Core Principles"

```markdown
## Before Implementation

### Step 1: Check for Implementation Plan

Before writing any code, check if a plan exists:

1. Get current branch:
   ```bash
   git branch --show-current
   ```

2. Look for plan at `docs/implementation_plans/<branch_name>.md`

### Step 2: If Plan Exists

- Read the plan thoroughly before starting
- Follow the implementation steps in order
- Use the "Codebase Context" section to understand existing patterns
- Reference the "Code Guidance" for each step
- Mark each step complete as you finish it (update the plan file)

### Step 3: If No Plan Exists

Proceed with user's direct requirements:
- Explore codebase to understand patterns
- Ask clarifying questions if requirements are ambiguous
- Document your approach as you go
```

---

### Change 2: After Completion Protocol (All Agents)

**Add to: ALL agent files**

**Location**: At the end, before any existing "Behaviour" section

```markdown
## After Completion

When your task is complete, provide:

### 1. Summary
Brief description of what was accomplished:
- What was created/modified/reviewed
- Key decisions made
- Any deviations from plan (if plan existed)

### 2. Files Changed
List all files created or modified:
```
created: path/to/new_file.go
modified: path/to/existing_file.go
```

### 3. Suggested Next Step
```

**TPM version:**
```markdown
### 3. Suggested Next Step
> Specification complete. Files created:
> - `docs/spec.md`
> - `docs/research.md`
> - `docs/decisions.md`
>
> **Next**: Run `implementation-planner-go` or `implementation-planner-python` to create detailed implementation plan.
>
> Say **'continue'** to proceed, or provide corrections.
```

**Planner version:**
```markdown
### 3. Suggested Next Step
> Implementation plan created at `docs/implementation_plans/<branch>.md`
>
> **Next**: Run `software-engineer-go` or `software-engineer-python` to implement.
>
> Say **'continue'** to proceed, or provide corrections.
```

**SE version:**
```markdown
### 3. Suggested Next Step
> Implementation complete.
>
> **Next**: Run `unit-test-writer-go` or `unit-test-writer-python` to write tests.
>
> Say **'continue'** to proceed, or provide corrections.
```

**Tests version:**
```markdown
### 3. Suggested Next Step
> Tests complete. Run them with:
> - Go: `go test -race ./...`
> - Python: `pytest -v`
>
> **Next**: Run `code-reviewer-go` or `code-reviewer-python` to review all changes.
>
> Say **'continue'** to proceed, or provide corrections.
```

**Reviewer version:**
```markdown
### 3. Suggested Next Step

**If issues found:**
> Review complete. Found X blocking, Y important, Z optional issues.
> See **Feedback for Software Engineer** section below.
>
> **Next**: Address blocking issues, then re-run `code-reviewer-{lang}`.
>
> Say **'fix these'** to have SE address issues, or provide specific instructions.

**If no blocking issues:**
> Review complete. No blocking issues found.
>
> **Next**: Ready to commit and open PR.
>
> Say **'commit'** to proceed, or provide corrections.
```

---

### Change 3: Structured Feedback Format (Reviewers)

**Add to: `code_reviewer_go.md`, `code_reviewer_python.md`**

**Location**: Replace or augment existing "Report" section

```markdown
## Feedback for Software Engineer

After completing review, provide structured feedback that SE can act on:

### 🔴 Must Fix (Blocking)
Issues that MUST be resolved before merge. PR cannot proceed with these.

Format each issue as:
- [ ] `file.go:42` — **Issue**: Error not wrapped with context
  **Fix**: Add `fmt.Errorf("fetching user: %w", err)`

### 🟡 Should Fix (Important)
Issues that SHOULD be resolved. Not blocking but significant.

- [ ] `file.go:87` — **Issue**: Missing test for error path
  **Fix**: Add test case for `ErrNotFound` scenario

### 🟢 Consider (Optional)
Suggestions for improvement. Nice-to-have, not required.

- [ ] `file.go:120` — **Suggestion**: Could simplify with early return

### Summary Line
```
Review: X blocking | Y important | Z suggestions
Action: [Fix blocking and re-review] or [Ready to merge]
```

### Checklist for SE
Copy this checklist when addressing feedback:
```markdown
## Fixes for Review Feedback
- [ ] file.go:42 - Wrap error with context
- [ ] file.go:87 - Add error path test
```
```

---

### Change 4: Escalation Guidance (All Agents)

**Add to: ALL agent files**

**Location**: Before "Behaviour" section

```markdown
## When to Escalate

Stop and ask the user for clarification when:

1. **Ambiguous Requirements**
   - Requirements can be interpreted multiple ways
   - Acceptance criteria conflict with each other
   - Edge cases aren't specified

2. **Significant Trade-offs**
   - Multiple valid approaches exist
   - Performance vs readability trade-off
   - Breaking change might be needed

3. **Uncertainty**
   - Code patterns you don't recognize
   - External dependencies you can't verify
   - Potential security implications

4. **Conflicts**
   - Task conflicts with existing codebase conventions
   - Requirements conflict with implementation plan
   - New information contradicts earlier decisions

**How to Escalate**
State clearly:
1. What you're uncertain about
2. What options you see (if any)
3. What information would help you proceed

Example:
> **Clarification needed**: The requirement says "return user or error" but existing
> codebase pattern returns `(nil, nil)` for not-found. Options:
> 1. Follow requirement (breaking existing pattern)
> 2. Follow existing pattern (may not meet requirement)
>
> Which approach should I take?
```

---

## Phase 5B: Workflow Commands

### Slash Command: `/implement`

**File**: `.claude/commands/implement.md`

```markdown
---
description: Implement current task using software engineer agent
---

You are orchestrating the implementation phase of a development workflow.

## Steps

1. **Detect project language**:
   - If `go.mod` exists → Go project
   - If `pyproject.toml` or `requirements.txt` exists → Python project
   - If unclear → Ask user

2. **Check for implementation plan**:
   - Get branch: `git branch --show-current`
   - Look for: `docs/implementation_plans/<branch>.md`

3. **Run appropriate agent**:
   - Go: Use `software-engineer-go` agent
   - Python: Use `software-engineer-python` agent

4. **After completion**:
   - Summarize changes
   - Suggest running `/test` next
   - Wait for user confirmation
```

### Slash Command: `/test`

**File**: `.claude/commands/test.md`

```markdown
---
description: Write tests for recent changes using unit test writer agent
---

You are orchestrating the testing phase of a development workflow.

## Steps

1. **Detect project language** (same as /implement)

2. **Identify what needs testing**:
   - Check `git diff` for recent changes
   - Look for implementation summary from SE (if present)

3. **Run appropriate agent**:
   - Go: Use `unit-test-writer-go` agent
   - Python: Use `unit-test-writer-python` agent

4. **After completion**:
   - Summarize tests created
   - Run tests to verify they pass
   - Suggest running `/review` next
   - Wait for user confirmation
```

### Slash Command: `/review`

**File**: `.claude/commands/review.md`

```markdown
---
description: Review changes using code reviewer agent
---

You are orchestrating the review phase of a development workflow.

## Steps

1. **Detect project language** (same as /implement)

2. **Gather context**:
   - Get Jira ticket from branch name
   - Check implementation plan if exists
   - Get full diff: `git diff main...HEAD`

3. **Run appropriate agent**:
   - Go: Use `code-reviewer-go` agent
   - Python: Use `code-reviewer-python` agent

4. **After completion**:
   - Present structured feedback (blocking/important/optional)
   - If blocking issues: Suggest running `/implement` to fix
   - If clean: Suggest committing
   - Wait for user decision
```

### Slash Command: `/full-cycle`

**File**: `.claude/commands/full-cycle.md`

```markdown
---
description: Run complete development cycle (implement → test → review)
---

You are orchestrating a complete development cycle with human checkpoints.

## Workflow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Implement   │────▶│    Test      │────▶│   Review     │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │
       ▼                    ▼                    ▼
   [User OK?]           [User OK?]          [Issues?]
       │                    │                    │
       ▼                    ▼                    ▼
   continue/fix         continue/fix        fix→loop / done
```

## Steps

### Phase 1: Implementation
1. Run `/implement` logic
2. Present summary of changes
3. **PAUSE**: Ask user to confirm or correct
4. If user says "continue" → proceed to Phase 2
5. If user provides corrections → apply and re-summarize

### Phase 2: Testing
1. Run `/test` logic
2. Present summary of tests created
3. Run tests, show results
4. **PAUSE**: Ask user to confirm or correct
5. If user says "continue" → proceed to Phase 3
6. If user provides corrections → apply and re-summarize

### Phase 3: Review
1. Run `/review` logic
2. Present structured feedback
3. **PAUSE**: Present options:
   - If blocking issues: "Say 'fix' to address issues, or provide specific instructions"
   - If clean: "Say 'commit' to create commit, or 'done' to finish"

### Loop Handling
If user says "fix":
1. Run SE agent with review feedback as input
2. Re-run tests
3. Re-run review
4. Present updated feedback

## User Commands at Any Checkpoint
- `continue` — Proceed to next phase
- `fix <instruction>` — Apply specific fix before continuing
- `skip` — Skip current phase, move to next
- `stop` — End workflow entirely
- `back` — Return to previous phase
```

---

## Phase 5C: Polish (Later)

### Change 5: SE Implementation Summary (for Tests)

**Add to: `software_engineer_go.md`, `software_engineer_python.md`**

**Location**: Within "After Completion" section

```markdown
### 4. Implementation Summary (for Test Writer)

Provide context to help test writer understand your implementation:

**Changes Made**:
- Brief description of each file's changes

**Edge Cases Considered**:
- What boundary conditions did you handle?
- What error scenarios did you implement?

**Testing Suggestions**:
- Which paths definitely need test coverage?
- Any tricky scenarios the test writer should know about?

Example:
> **Changes**: Added `UserService` with `Get`, `Create`, `Update` methods.
>
> **Edge Cases**:
> - Empty ID returns `ErrInvalidID`
> - Duplicate email returns `ErrDuplicateEmail`
> - Context cancellation checked before DB calls
>
> **Testing Focus**:
> - Error paths in `Create` (validation, duplicate, DB failure)
> - Concurrent `Update` calls (race condition potential)
```

---

### Change 6: Reviewer Simplification (Deferred)

**Status**: Defer to later iteration

**Rationale**:
- Current 11-step process is thorough
- Simplification risks missing checks
- Focus first on handoffs (higher impact)
- Revisit after other changes are validated

**When to revisit**:
- If users report reviewer is too slow
- If steps are consistently skipped
- After 2-4 weeks of using new workflow

---

## Implementation Checklist

### Phase 5A: Foundation (Do First)

| # | File | Change | Status |
|---|------|--------|--------|
| 1 | `software_engineer_go.md` | Add "Before Implementation" | ⬜ |
| 2 | `software_engineer_python.md` | Add "Before Implementation" | ⬜ |
| 3 | `technical_product_manager.md` | Add "After Completion" | ⬜ |
| 4 | `implementation_planner_go.md` | Add "After Completion" | ⬜ |
| 5 | `implementation_planner_python.md` | Add "After Completion" | ⬜ |
| 6 | `implementation_planner_python_monolith.md` | Add "After Completion" | ⬜ |
| 7 | `software_engineer_go.md` | Add "After Completion" | ⬜ |
| 8 | `software_engineer_python.md` | Add "After Completion" | ⬜ |
| 9 | `unit_tests_writer_go.md` | Add "After Completion" | ⬜ |
| 10 | `unit_tests_writer_python.md` | Add "After Completion" | ⬜ |
| 11 | `code_reviewer_go.md` | Add "After Completion" + "Feedback Format" | ⬜ |
| 12 | `code_reviewer_python.md` | Add "After Completion" + "Feedback Format" | ⬜ |
| 13 | ALL agents | Add "When to Escalate" | ⬜ |

### Phase 5B: Workflow (Do Second)

| # | File | Change | Status |
|---|------|--------|--------|
| 14 | `.claude/commands/implement.md` | Create | ⬜ |
| 15 | `.claude/commands/test.md` | Create | ⬜ |
| 16 | `.claude/commands/review.md` | Create | ⬜ |
| 17 | `.claude/commands/full-cycle.md` | Create | ⬜ |

### Phase 5C: Polish (Do Later)

| # | File | Change | Status |
|---|------|--------|--------|
| 18 | `software_engineer_go.md` | Add "Implementation Summary" | ⬜ |
| 19 | `software_engineer_python.md` | Add "Implementation Summary" | ⬜ |
| 20 | `code_reviewer_*.md` | Simplify workflow | ⬜ Deferred |

---

## Expected Outcomes

### Before → After

| Aspect | Before | After |
|--------|--------|-------|
| Invoke agent | Type full agent name | `/implement` or `/full-cycle` |
| Know next step | Remember workflow | Agent suggests |
| Context between agents | Lost | Preserved via summaries |
| Review feedback | Unstructured report | Prioritized checklist |
| Feedback loop | Manual translation | Structured handoff |
| Escalation | Ad-hoc | Defined triggers |

### User Experience Flow

**Before:**
```
User: "Use software-engineer-go to implement user service"
[SE works]
User: "Now use unit-test-writer-go to write tests"
[Tests work]
User: "Now use code-reviewer-go to review"
[Reviewer outputs long report]
User: [manually extracts issues, tells SE what to fix]
```

**After:**
```
User: "/full-cycle"
[SE works, outputs summary]
Claude: "Implementation complete. Changes: X, Y, Z. Continue to testing?"
User: "continue"
[Tests work, outputs summary]
Claude: "Tests complete. 15 tests passing. Continue to review?"
User: "continue"
[Reviewer works, outputs structured feedback]
Claude: "Review: 2 blocking, 3 important. Say 'fix' to address, or give instructions."
User: "fix"
[SE fixes, re-tests, re-reviews]
Claude: "Review: 0 blocking. Ready to commit."
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Agents ignore new sections | Sections are explicit, at key locations |
| Slash commands conflict | Unique names, clear descriptions |
| User loses control | Every step pauses for confirmation |
| Changes break existing behavior | All changes are additive |
| Too much output | Summaries are concise, details available |

---

## Validation Plan

After implementation:

1. **Test each agent individually** - Verify new sections work
2. **Test slash commands** - Verify language detection, agent invocation
3. **Test full cycle** - Run `/full-cycle` on a real task
4. **Test interruption** - Verify user can stop/correct at each step
5. **Test feedback loop** - Verify SE can consume Reviewer output

---

## Summary

**Total Changes**: 17 modifications + 4 new files

**Effort**: ~6-8 hours total

**Impact**:
- Eliminates manual orchestration friction
- Preserves context between agents
- Enables guided workflow with full user control
- Structured feedback enables clean loops

**Architecture**: Unchanged — same agents, same specialization, enhanced communication
