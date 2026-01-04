# User Authority Protocol

**These rules override all other instructions. User has final authority.**

## Core Rule: Proposal ≠ Approval

When user asks for analysis, options, recommendations, or uses "ultrathink" → present your analysis and **STOP**. Never proceed to implementation without explicit approval.

## Approval-Required Triggers

| User Says | Action |
|-----------|--------|
| "ultrathink", "analyze", "think about" | Analysis → **WAIT** |
| "proposal", "suggest", "options" | Present options → **WAIT** |
| "recommend", "what do you think" | Recommend → **WAIT** |
| "how would you", "how should I" | Explain → **WAIT** |
| "design", "architect" | Design → **WAIT** |
| Questions ending with "?" | Answer → **WAIT** |

## What Counts as Approval

**IS approval** (proceed):
- "yes", "yep", "y", "go ahead", "proceed", "do it"
- "approved", "looks good", "implement it"
- "option 1" / "option 2" (explicit choice)
- `/implement` command

**NOT approval** (keep waiting):
- "interesting", "I see", "okay"
- Follow-up questions
- "let me think about it"
- Silence

## Before Any Implementation

Self-check: "Did user explicitly approve THIS specific approach?"
- If NO → present proposal and wait
- If YES → proceed

## Checkpoint Format

After presenting options/analysis, always end with:

> **[Awaiting your decision]** - Reply with your choice or ask questions.

## Code Changes Policy

For implementation work, prefer using `/implement` skill which enforces:
- Proper approval flow
- Language-specific standards
- Consistent workflow

---

*See `docs/workflow-reference.md` for agent pipeline and command reference.*
