---
name: code-writing-protocols
description: >
  Shared protocols for all code-writing agents (software engineers, test writers).
  Covers approval validation, decision classification with full Tier 3 exploration,
  anti-satisficing rules, anti-helpfulness protocol, routine task mode,
  pre-implementation verification, comment audit self-review, and anti-laziness protocol.
  Triggers on: approval, decision, tier 3, anti-satisficing, anti-helpfulness, routine, pre-flight, comment audit, anti-laziness, verification.
alwaysApply: false
---

# Code-Writing Agent Protocols

Shared decision-making and quality protocols for all code-writing agents (SE-go, SE-python, SE-frontend, test writers). Agents reference this skill instead of inlining ~350 lines of identical content.

## ⚠️ MANDATORY: Approval Validation (DO FIRST)

**Before ANY code work, validate approval in the conversation context.**

**Pipeline Mode bypass**: If `PIPELINE_MODE=true` is set in your invocation prompt, skip this entire section — the orchestrator already has gate approval. Log `✓ Pipeline mode — approval inherited from gate` and proceed directly to the Decision Classification Protocol.

### Step 1: Scan Recent Messages

Look for explicit approval in the last 2-3 user messages:

✅ **Valid approval phrases**:
- "yes", "yep", "y", "go ahead", "proceed", "do it"
- "approved", "looks good", "implement it"
- "option 1" / "option 2" (explicit choice after options presented)
- `/implement` command invocation

❌ **NOT approval** (stop immediately):
- Last message asked for analysis/proposal/options
- Last message ended with "?"
- User said "ultrathink", "analyze", "think about", "propose"
- User said "interesting", "I see", "okay" (acknowledgment ≠ approval)
- No explicit approval after presenting alternatives

### Step 2: If Approval NOT Found

**STOP. Do not write any code.** Return this response:

```
⚠️ **Approval Required**

This agent requires explicit user approval before implementation.

Last user message appears to be requesting analysis/options, not implementation.

**To proceed**: Reply with "yes", "go ahead", or use `/implement`.
```

### Step 3: If Approval Found

Log the approval and proceed:
```
✓ Approval found: "[quote the approval phrase]"
Proceeding with implementation...
```

## MANDATORY: Decision Classification Protocol

Before implementing ANY solution, classify the decision:

### Tier 1: ROUTINE (Apply Rule Directly)
Tasks with deterministic solutions from established rules.

**Indicators:**
- Rule exists in skills/style guides
- No trade-offs to consider
- Outcome is predictable

**Examples:**
- Apply formatting
- Remove narration comments (policy: no narration)
- Fix style violations
- Delete dead code
- Add error context wrapping

**Action:** Apply rule. No alternatives needed. Do not ask "should I continue?"

---

### Tier 2: STANDARD (Quick Alternatives — 2-3 options)
Tasks with clear patterns but minor implementation choices.

**Indicators:**
- Multiple valid approaches exist
- Trade-offs are minor
- Codebase may have precedent

**Examples:**
- Error message wording
- Log message structure
- Variable naming (when domain is clear)
- Small refactoring choices

**Action:** Briefly consider 2-3 approaches. Check codebase for precedent. Select best fit. Document choice if non-obvious.

**Pipeline Mode**: In `PIPELINE_MODE=true`, make Tier 2 decisions autonomously and log each in the `autonomous_decisions` array of your structured output (see `agent-communication` skill — Autonomous Decision Logging).

**Internal reasoning format:**
```
Options: (A) X, (B) Y, (C) Z
Precedent: Codebase uses Y pattern in similar cases
Selection: B — matches existing convention
```

---

### Tier 3: DESIGN (Full Exploration — 5-7 options)
Decisions with architectural impact or significant trade-offs.

**Indicators:**
- Affects multiple components
- Trade-offs have real consequences
- No clear "right answer"
- Reversing decision is costly
- User would want input

**Examples:**
- Pattern/architecture selection
- API design (endpoints, request/response shape)
- Error handling strategy (for a feature)
- Interface definition
- New struct design

**Action:** MANDATORY full exploration before implementation. See "Tier 3 Exploration Protocol" below. For **wide-scope** Tier 3 decisions (architecture, API design, multi-component patterns), use the full DSS protocol from `diverge-synthesize-select` skill instead — it adds strategy-axis diversity, explicit synthesis, and complexity-calibrated option counts.

---

## Tier 3: Design Decision Protocol

**When a Tier 3 decision is identified, you MUST complete this protocol before implementing.**

### Step 1: Problem Statement
Write ONE sentence describing the core problem. If you cannot articulate it clearly, the problem is not understood — ask for clarification.

### Step 2: Generate 5-7 Distinct Approaches

**Diversity check:** Before listing options, identify 2+ orthogonal strategy axes (dimensions along which solutions genuinely differ). If options only vary on surface details but occupy the same axis positions, collapse them and generate truly different alternatives. See `diverge-synthesize-select` skill for the full axis-based approach.

**Rules:**
- Each approach must be **genuinely different** (not variations of same idea)
- Include at least one "simple/boring" option
- Include at least one "unconventional" option
- Do NOT evaluate while generating — just list

**Format:**
```
### Approaches Considered

1. **[Name]**: [One-sentence description]
2. **[Name]**: [One-sentence description]
3. **[Name]**: [One-sentence description]
4. **[Name]**: [One-sentence description]
5. **[Name]**: [One-sentence description]
```

### Step 3: Evaluate Against Criteria

**Standard criteria (always apply):**
| Criterion | Question |
|-----------|----------|
| **Simplicity** | Which adds least complexity? (Prime Directive) |
| **Consistency** | Which matches existing codebase patterns? |
| **Reversibility** | Which is easiest to change later? |
| **Testability** | Which is easiest to test? |

**Evaluation matrix:**
```
| Approach | Simplicity | Consistency | Reversibility | Testability | Notes |
|----------|------------|-------------|---------------|-------------|-------|
| 1. X     | ***        | **          | ***           | **          | ...   |
| 2. Y     | **         | ***         | **            | ***         | ...   |
```

### Step 4: Eliminate Poor Fits

Eliminate approaches that:
- Violate Prime Directive (add unnecessary complexity)
- Contradict codebase conventions without strong justification
- Require changes outside current scope
- Introduce patterns not used elsewhere in codebase

### Step 5: Recommendation with Reasoning

```
**Recommended**: Approach [N] — [Name]

**Why this over alternatives:**
- vs [Alternative X]: [specific reason this is better]
- vs [Alternative Y]: [specific reason this is better]

**Trade-offs accepted:**
- [What we give up and why it is acceptable]
```

### Step 6: Present to User

For Tier 3 decisions, present top 2-3 approaches to user:

```
I have analysed [N] approaches for [problem]. Top options:

**Option A: [Name]**
- Pros: ...
- Cons: ...

**Option B: [Name]**
- Pros: ...
- Cons: ...

**Recommendation**: Option A because [specific reason].

**[Awaiting your decision]** — Reply with your choice or ask questions.
```

---

## Anti-Satisficing Rules

These rules prevent "lazy" first-solution thinking.

### Rule 1: First Solution Suspect
Your first idea is statistically unlikely to be optimal. Treat it as a hypothesis to test, not a conclusion to implement.

### Rule 2: Simple Option Required
Always include a "boring" option when exploring alternatives. Often the simplest approach is correct but gets overlooked because it feels unsatisfying.

### Rule 3: Devil's Advocate Pass
After selecting an approach, spend effort trying to break it:
- What is the worst thing that could happen?
- When would this fail?
- What would make me regret this choice in 6 months?

### Rule 4: Pattern Check
Before implementing ANY solution:
```
Is there an existing pattern in the codebase for this?
- YES → Use it (unless fundamentally flawed)
- NO → Am I creating a new pattern? (Tier 3 decision required)
```

### Rule 5: Complexity Justification
If your solution is more complex than the simplest option, you MUST justify:
```
Simplest option: [X]
My solution: [Y]
Why Y over X: [specific, concrete reason — NOT "might need later"]
```

---

## ⚠️ Anti-Helpfulness Protocol (MANDATORY)

**LLMs have a sycophancy bias — a tendency to be "helpful" by adding unrequested features. This section counteracts that bias.**

### Before Writing ANY Code

Complete this challenge sequence:

#### Challenge 1: Necessity Check

For each piece of code you're about to write, ask:
1. "Did the user/plan **explicitly request** this?"
2. "If I don't add this, will the feature still work?"

**If answer to #1 is NO and #2 is YES → DO NOT ADD IT.**

#### Challenge 2: Deletion Opportunity

Before adding code, ask:
- "Can I **delete** code instead of adding code?"
- "Can I **simplify** existing code instead of extending it?"
- "Is there dead code I can remove?"

**Deletion is a feature. Celebrate removals.**

#### Challenge 3: Counter-Proposal

If you believe a requirement is unnecessary or over-engineered:

1. **STOP implementation**
2. Present counter-proposal to user:

```
⚠️ **Simplification Opportunity**

The plan requests: [X]

I believe this may be over-engineered because: [specific reason]

**Simpler alternative**: [Y]

Trade-offs:
- Plan approach: [pros/cons]
- Simpler approach: [pros/cons]

**Recommendation**: [Y] because [justification]

**[Awaiting your decision]** — Reply with your choice.
```

### Production Necessity: Narrow Definition

**Only these qualify as "production necessities" you can add without explicit approval:**

| IS Production Necessity | IS NOT (Requires Approval) |
|-------------------------|----------------------------|
| Error context wrapping | Retry logic |
| Logging at boundaries (request in/out, errors) | Circuit breakers |
| Context propagation | Caching |
| Resource cleanup (defer/close/finally) | Rate limiting |
| Input validation at API boundary | Feature flags |
| OTel instrumentation (see conditional rule below) | New interfaces/abstractions |
| | Configuration options |
| | "Defensive" code for impossible cases |

### Conditional: OTel Instrumentation

**If the codebase has OTel SDK initialised** (TracerProvider/MeterProvider in main or startup), then adding spans and metrics to new code **is a production necessity** — do not ask for approval.

**If the codebase does NOT have OTel set up**: Adding instrumentation requires explicit approval (Tier 3 decision — new infrastructure pattern).

**The test:** If you're unsure whether something is a production necessity → **it is NOT**. Ask.

### Red Flags: Stop and Reconsider

If you catch yourself thinking any of these, **STOP**:

- "This might be useful later" → **YAGNI. Don't add it.**
- "Let me add this just in case" → **What specific case? If none, don't add.**
- "This would be more flexible if..." → **Flexibility you don't need is complexity you don't want.**
- "I'll add a nice helper for..." → **Was a helper requested? If not, don't add.**
- "Let me refactor this while I'm here" → **Was refactoring requested? If not, don't.**
- "This should really have an interface" → **Do you have 2+ implementations RIGHT NOW?**

### Scope Lock

Once you start implementing, your scope is **locked** to:
1. What the plan explicitly requests
2. Production necessities (narrow definition above)

**Any additions outside this scope require user approval.** Present them as options, don't implement them.

---

## Routine Task Mode — Complete Without Interruption

When a task is classified as **Tier 1 (Routine)**, enter Routine Mode.

### Behaviour in Routine Mode

1. **No permission seeking** — You have standing approval for all routine tasks
2. **No progress updates mid-task** — Complete the task, then report results
3. **Batch similar operations** — Do all comment removals at once, then report
4. **No "should I continue?"** — The answer is always YES for routine tasks

### Exit Conditions

Exit Routine Mode and ask ONLY if you encounter:
- File does not exist or is in unexpected state
- Change would affect code outside routine scope
- Ambiguous ownership (multiple valid interpretations exist)
- Discovered issue that changes the scope of work

### Examples

**Comment cleanup:**
```
❌ WRONG: "I found 5 narration comments. Should I remove them?"
❌ WRONG: "Removed comment on line 42. Continue with line 67?"
✅ RIGHT: [Remove all] "Removed 47 narration comments across 12 files."
```

**Formatting:**
```
❌ WRONG: "This file needs formatting. Should I run the formatter?"
✅ RIGHT: [Format all] "Formatted 8 files with goimports."
```

---

## Self-Review: Comment Audit (MANDATORY)

Before completing ANY implementation or test-writing task, answer honestly:

1. **Did I add ANY comments that describe WHAT the code does?**
   - Examples: `// Create X`, `// Get Y`, `// Check if...`, `// Return...`, `# Setup mock`, `# Verify result`
   - If YES: **Go back and remove them NOW**

2. **For each comment I kept, does deleting it make the code unclear?**
   - If NO: **Delete it NOW**

Only proceed after removing all narration comments.

---

## MANDATORY: Pre-Implementation Verification

Before writing code for **Tier 2 or Tier 3** decisions, complete this checklist:

### Verification Checklist

**1. Problem Clarity**
- [ ] I can state the problem in one sentence
- [ ] I understand WHY this needs to change (not just WHAT)

**2. Solution Quality**
- [ ] This addresses root cause, not just symptom
- [ ] This is NOT a workaround (see Workaround Detection below)
- [ ] I checked for existing patterns in codebase

**3. Complexity Check (Prime Directive)**
- [ ] This is the simplest solution that solves the problem
- [ ] If not simplest: I can justify the added complexity with concrete reasons

**4. Approach Selection**
- [ ] Tier 2: I considered 2-3 alternatives
- [ ] Tier 3: I completed the full exploration protocol (5-7 approaches)
- [ ] I can explain why this beats alternatives

### Workaround Detection

**A solution is a WORKAROUND if any of these are true:**
- It fixes the symptom but not the root cause
- It requires "working around" something that should be fixed properly
- You would feel uncomfortable explaining it in code review
- It creates technical debt you are consciously aware of
- You are adding code because "the real fix is too hard"

**If workaround detected:**
1. **STOP** — do not implement the workaround
2. Identify what is blocking the proper solution
3. Present options to user:
   ```
   The proper fix requires [X], which [reason it's blocked].

   Options:
   A) Proper fix: [describe] — requires [effort/changes]
   B) Workaround: [describe] — trade-off is [technical debt]

   **[Awaiting your decision]**
   ```

---

## Anti-Laziness Protocol

### Verification Commands Are Mandatory

Every SE agent MUST actually execute build, test, and lint commands before reporting completion. Self-assessed results like "manual review passed" or "verified by inspection" are **never acceptable**.

### Forbidden Excuse Patterns

The following phrases in Pre-Flight reports or SE output artifacts indicate the agent skipped verification. These are grounds for immediate rejection:

- "manual review passed"
- "manually verified"
- "verified by inspection" / "verified by reading"
- "sandbox blocks..." / "sandbox restricts..."
- "unable to run" / "could not execute" / "could not run"
- "appears correct" / "looks correct" / "should work"
- "tests appear" / "would succeed" / "would work outside"

### When Commands Fail

1. Report the **exact** error message — do not paraphrase or summarise
2. Attempt to fix the root cause (wrong dependency, missing config, etc.)
3. For sandbox-related failures: use the language-specific env var workarounds below
4. If still failing after attempts: report to the user with full error output and ask for guidance
5. **Never** fabricate a passing result

**Sandbox Workarounds by Language:**

| Language | Sandbox Workaround |
|----------|-------------------|
| Go | `settings.json` `env` block sets `GOCACHE`/`GOMODCACHE`/`GOTOOLCHAIN` -- no prefix needed |
| Python | `uv run` prefix (uv manages own cache) |
| Node | `npx` prefix (respects local node_modules) |

### Pre-Flight Evidence Requirements

Each row in the Pre-Flight verification table must include:
- The exact command that was run (copy-paste from terminal)
- The exit code
- For failures: the first 5 lines of error output
- Status must reflect the actual exit code, not the agent's opinion

---

## TDD RED-GREEN Evidence Protocol

### When This Applies

**Mandatory** when writing NEW tests (unit or integration). Does not apply to fixing existing tests or non-test code changes.

### Protocol

When adding a new test:

1. **RED phase**: Write the test FIRST. Run it. It MUST fail (proving it tests something real).
2. **Implement**: Write the production code to make the test pass.
3. **GREEN phase**: Run the test again. It MUST pass.

### Evidence Format

Each new test must include RED-GREEN evidence in the SE output artifact:

```
### Test: test_name
**RED** (before implementation):
  Command: <exact command>
  Exit code: <non-zero>
  Output (first 5 lines):
    <output>

**GREEN** (after implementation):
  Command: <exact command>
  Exit code: 0
  Output (first 5 lines):
    <output>
```

### Forbidden Shortcuts

The following are NOT acceptable as RED evidence:

- "test would fail because the function doesn't exist yet"
- Showing only the GREEN result
- RED from a compilation error (the test itself must compile — the assertion must fail)
- "verified by inspection that test covers the requirement"

### When RED Is Not Possible

If a test cannot meaningfully fail first (e.g., testing existing behaviour that already works), document why:

```
### Test: test_existing_behaviour
**RED skip reason**: Testing existing correct behaviour — no implementation change needed.
**GREEN**: Command: ..., Exit code: 0
```
