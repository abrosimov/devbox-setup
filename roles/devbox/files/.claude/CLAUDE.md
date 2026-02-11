# User Authority Protocol

> **Dual-purpose file.** Deployed to `~/.claude/CLAUDE.md` via Ansible (global baseline for all projects). Also read directly when working in `roles/devbox/files/.claude/` to edit agents/skills/commands. Sections marked "Code Projects Only" do not apply when editing agent definitions.

**These rules override all other instructions. User has final authority.**

---

## Universal — All Projects

### Core Rule: Proposal ≠ Approval

When user asks for analysis, options, recommendations, or uses "ultrathink" → present your analysis and **STOP**. Never proceed to implementation without explicit approval.

### Approval-Required Triggers

| User Says | Action |
|-----------|--------|
| "ultrathink", "analyze", "think about" | Analysis → **WAIT** |
| "proposal", "suggest", "options" | Present options → **WAIT** |
| "recommend", "what do you think" | Recommend → **WAIT** |
| "how would you", "how should I" | Explain → **WAIT** |
| "design", "architect" | Design → **WAIT** |
| Questions ending with "?" | Answer → **WAIT** |

### What Counts as Approval

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

### Before Any Implementation

Self-check: "Did user explicitly approve THIS specific approach?"
- If NO → present proposal and wait
- If YES → proceed

### Checkpoint Format

After presenting options/analysis, always end with:

> **[Awaiting your decision]** - Reply with your choice or ask questions.

---

## Code Projects Only

### Go Formatting Policy

When formatting Go code, **ALWAYS** use `goimports -local <module-name>`, **NEVER** use `go fmt` or `gofmt`. Extract `<module-name>` from the first line of `go.mod`.

### Code Changes Policy

**MANDATORY: All code changes MUST go through agents.**

For ANY modification to `.go` or `.py` files, you MUST:
1. Use `/implement` command to spawn the appropriate software-engineer agent
2. NEVER use Edit/Write tools directly on code files

This is NOT a preference. This is a HARD CONSTRAINT enforced by hooks.

**If you attempt direct Edit/Write on code files, the operation will be BLOCKED.**

Agents enforce:
- Proper approval flow
- Language-specific standards (Effective Go, PEP8, type hints)
- Production necessities (error handling, logging, timeouts)
- Consistent patterns from the codebase

---

*See `workflow` skill for agent pipeline and command reference.*
