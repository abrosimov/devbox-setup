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

### Git Commits

Never add `Co-Authored-By` trailers to commit messages.

---

## Code Projects Only

### Go Formatting Policy

When formatting Go code, **ALWAYS** use `goimports -local <module-name>`, **NEVER** use `go fmt` or `gofmt`. Extract `<module-name>` from the first line of `go.mod`.

### Agent Workflow (Opt-In Per Project)

The agent workflow is controlled by a per-project `.claude/workflow.json` file.

**Detection:** When a user asks you to write or modify code (`.go`, `.py`, `.ts`, `.tsx` files) and no `.claude/workflow.json` exists in the project root, ask:

> This project doesn't have the agent workflow configured. Would you like to enable it?
>
> **A) Full workflow** — agents required for code changes, auto-commit after each phase
> **B) Lightweight** — agents required for code changes, you commit manually
> **C) Skip** — work without the agent pipeline this session

- **A** → run `/init-workflow full`
- **B** → run `/init-workflow light`
- **C** → proceed normally; do not ask again this session

**Only ask once per session.** If the user chose C, remember it for the rest of the conversation.

**When `workflow.json` exists with `"agent_pipeline": true`:**

All code changes MUST go through agents. For ANY modification to `.go`, `.py`, `.ts`, `.tsx` files:
1. Use `/implement` command to spawn the appropriate software-engineer agent
2. NEVER use Edit/Write tools directly on code files

Agents enforce:
- Proper approval flow
- Language-specific standards (Effective Go, PEP8, type hints)
- Production necessities (error handling, logging, timeouts)
- Consistent patterns from the codebase

**When `workflow.json` is absent or `"agent_pipeline": false`:**

Agents are available via `/implement`, `/test`, `/review` but not mandatory. Direct code edits are allowed.

### Cross-Cutting Rules (Always Active)

These are enforced by `alwaysApply: true` skills. Brief reminders:

- **Immutability**: Prefer data transformation pipelines over mutation — return new instances, don't modify in place (see `philosophy` skill)
- **Comments**: Only WHY/WARNING/TODO — never narrate what code does (see `code-comments` skill)
- **Security at boundaries**: Validate all external input; never trust user data internally (see `security-patterns` skill)
- **Model selection**: Opus for SE/reviewers/planners (use `/implement sonnet` for cost-sensitive tasks), Sonnet for test writers/utility agents, Haiku for search/grep
- **Agent delegation**: Use specialised agents for code changes when workflow is enabled (see `workflow` skill)

---

## Editing Agents & Skills (Context Optimization)

When working inside `roles/devbox/files/.claude/` (editing agent/skill/command definitions):

- **Surgical reads only**: Read only the target file being edited. Do NOT read referenced skills or other agents "for context" unless the user explicitly asks.
- **Delegate edits to subagents**: For multi-file changes, use the Task tool to spawn subagents. Each gets its own context window — file reads don't accumulate in the main conversation.
- **Prefer Grep over Read**: When checking cross-references or looking for patterns across files, use Grep to find specific lines instead of reading entire files.
- **One file per edit cycle**: Finish editing one file before moving to the next. Avoid loading multiple large files simultaneously.
- **Disable unused MCPs**: Run `/mcp` at session start to disable playwright, figma, storybook when editing config files (~15-20K tokens saved).

---

*See `workflow` skill for agent pipeline and command reference.*
