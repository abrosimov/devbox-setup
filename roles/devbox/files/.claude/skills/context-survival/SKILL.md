---
name: context-survival
description: >
  Tiered memory architecture for surviving context loss from exits, compaction,
  and new sessions. Covers checkpoints, ambient context (MEMORY.md Working State),
  session-save hooks, strategic compaction, and the resume protocol.
  Triggers on: checkpoint, resume, context loss, compaction, session, working state,
  MEMORY.md, survive, persist, remember across sessions.
---

# Context Survival

Patterns for preserving working context across session exits, context compaction, and new sessions.

---

## Problem

Claude Code context is ephemeral. It is lost when:
- User exits the session (Ctrl+C, `/exit`, crash)
- Context compaction truncates older messages (approaching token limit)
- A new session starts on the same project
- Subagent processes complete and their context is discarded

## Solution: Three-Tier Memory Architecture

```
┌─────────────────────────────────────────────┐
│  TIER 1: HOT — Ambient Context (MEMORY.md)  │
│  Always loaded. Updated by /checkpoint +    │
│  hooks. Survives everything.                │
│  ≤15 lines in "Working State" section.      │
└──────────────────┬──────────────────────────┘
                   │ references
┌──────────────────▼──────────────────────────┐
│  TIER 2: WARM — Checkpoint Files            │
│  User-triggered via /checkpoint. Full state │
│  dumps in checkpoints/ directory. Survives  │
│  everything. Rich, detailed.                │
└──────────────────┬──────────────────────────┘
                   │ fed by
┌──────────────────▼──────────────────────────┐
│  TIER 3: COLD — Memory MCP Knowledge Graph  │
│  Cross-session queryable entities. Upstream  │
│  (per-ticket) + downstream (project-wide).  │
│  Survives everything. Structured, queryable.│
└─────────────────────────────────────────────┘
```

Each tier has different update frequency and retrieval cost:
- **Hot** context survives compaction (re-read from disk on every message)
- **Warm** context survives exits (files persist, loaded on demand)
- **Cold** context survives everything (MCP-backed JSONL, queryable)

---

## Tier 1: Ambient Context (MEMORY.md Working State)

The auto-memory `MEMORY.md` file is **always loaded into the system prompt**. This makes it the most reliable context survival mechanism — it survives compaction, exits, and new sessions automatically.

### Working State Section

The `## Working State` section at the top of MEMORY.md captures current reality:

```markdown
## Working State
- **Branch**: feature/PROJ-123_add-auth
- **Task**: Implement JWT authentication middleware
- **Phase**: implementation
- **Progress**: 3/5 endpoints done, tests passing
- **Approach**: go-jwt/v5, middleware pattern
- **Blockers**: None
- **Next**: Implement refresh token endpoint
- **Checkpoint**: auth-middleware (2026-02-13, SHA: a1b2c3d)
```

### Rules

- **15 lines maximum** — MEMORY.md has a 200-line truncation limit; leave room for stable notes
- **Current reality, not history** — represents what IS, not what WAS
- **Machine-managed** — updated by `/checkpoint` command and session-save hooks
- **Preserve other sections** — never delete "Stable Notes" or other manually curated content

### Update Triggers

| Trigger | Mechanism | Richness |
|---------|-----------|----------|
| `/checkpoint` command | Claude writes it | Full context (task, decisions, approach) |
| PreCompact hook | `session-save` script | Minimal (branch, SHA, modified files) |
| SessionEnd hook | `session-save` script | Minimal (safety net) |

---

## Tier 2: Checkpoint Files

Rich, detailed snapshots created by the `/checkpoint` command.

### Location

```
~/.claude/projects/{hash}/memory/checkpoints/
├── 2026-02-13-1430-auth-middleware.md
├── 2026-02-13-1100-db-schema.md
└── 2026-02-12-1645-project-setup.md
```

### When to Checkpoint

**Good checkpoint moments** (logical boundaries):
- Research → Planning transition (research is bulky, plan is the output)
- Planning → Implementation transition (plan is in file, free up context)
- After a significant implementation milestone (3 endpoints done, core logic complete)
- Before switching focus (feature A → feature B)
- Debugging → next feature transition (debug traces pollute context)

**Bad checkpoint moments:**
- Mid-implementation (lose variable names, file paths, mental model)
- Mid-debugging (lose error context and hypotheses)
- After trivial changes (noise, no value)

### Checkpoint Structure

Each checkpoint file contains:
1. **Metadata** — timestamp, git SHA, branch
2. **Task** — what's being worked on
3. **Decisions** — key choices with rationale
4. **Progress** — checklist of done/remaining
5. **Key Files** — important files with annotations
6. **Approach** — chosen strategy and why
7. **Blockers** — unresolved issues
8. **Next Steps** — prioritised action list
9. **Resumption Context** — which files to read first

---

## Tier 3: Memory MCP Entities

Cross-session queryable knowledge stored in the Memory MCP knowledge graph.

### Session Entities (New)

| Entity Type | Naming | Example |
|-------------|--------|---------|
| `checkpoint` | `checkpoint:{label}` | `checkpoint:auth-middleware` |
| `blocker` | `blocker:{description}` | `blocker:rate-limit-library-choice` |

### Relations

| Relation | Example |
|----------|---------|
| `created-at` | `checkpoint:auth-middleware` → `created-at` → `session:2026-02-13` |
| `blocks` | `blocker:rate-limit-library` → `blocks` → `checkpoint:auth-middleware` |
| `resolved-by` | `blocker:rate-limit-library` → `resolved-by` → `decision:rate-limit:tollbooth` |

### Usage

Checkpoints optionally store entities in Memory MCP for cross-session querying:

```
# At checkpoint time
create_entities([{
  name: "checkpoint:auth-middleware",
  entityType: "checkpoint",
  observations: ["Branch: PROJ-123_add-auth", "Phase: implementation", "3/5 endpoints done"]
}])

# At resume time
search_nodes("checkpoint:")
search_nodes("blocker:")
```

---

## Hooks

### session-save (PreCompact + SessionEnd)

Automatic safety net. Fires on:
- **PreCompact** — saves working state before context is summarised
- **SessionEnd** — saves working state when session terminates

What it captures (shell script, no AI):
- Current branch and SHA
- Modified files (uncommitted changes)
- Timestamp and event type
- A note to run `/checkpoint resume`

What it **cannot** capture (no AI access):
- Task description, decisions, approach
- Progress assessment, next steps

This is why `/checkpoint` (AI-powered) is the primary mechanism.

### suggest-checkpoint (PostToolUse)

Counts "work" tool calls (Edit, Write, Bash, Task) per session. Suggests `/checkpoint` at:
- ~40 calls (first suggestion)
- Every ~25 calls after

Runs async (non-blocking). Only provides `additionalContext` — Claude decides whether to act.

---

## Resume Protocol

When starting a new session or recovering from compaction:

### Automatic (Zero Effort)

MEMORY.md Working State is always visible in the system prompt. If it was updated by a hook or previous checkpoint, Claude immediately sees:
- What branch and task
- What phase and progress
- Where to look next

### Manual (`/checkpoint resume`)

Full reconstruction from all three tiers:

1. Read MEMORY.md Working State (already in prompt)
2. Find and read latest checkpoint file
3. Check git state (branch, status, recent commits)
4. Query Memory MCP for checkpoint/blocker entities
5. Check pipeline state (if using agent workflow)
6. Synthesise and present resumption briefing

---

## Integration with Agent Workflow

### After Agent Completion

When a command (`/implement`, `/test`, `/review`) finishes, consider suggesting a checkpoint:

```markdown
> Implementation complete. Created/modified X files.
>
> **Next**: Run `/test` to write tests.
>
> Tip: Run `/checkpoint` to save progress before continuing.
```

### Pipeline State as Context

The pipeline state file (`pipeline_state.json`) complements checkpoints by tracking which pipeline stages are complete. The resume protocol reads both.

---

## Anti-Patterns

| Anti-Pattern | Problem | Instead |
|--------------|---------|---------|
| Checkpointing every 5 minutes | Noise, no signal | Checkpoint at logical boundaries |
| Relying only on hooks | Hooks capture git state, not task context | Use `/checkpoint` for rich snapshots |
| Putting full file contents in checkpoints | Bloat, stale quickly | Reference file paths, let reader open them |
| Skipping MEMORY.md update | Loses the "hot" tier | Always update Working State in checkpoints |
| Storing session transcripts | Token waste, privacy concerns | Store summaries and decisions, not raw conversation |
