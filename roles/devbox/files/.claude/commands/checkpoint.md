---
description: Save or restore session context across exits, compaction, and new sessions
---

You are managing context survival checkpoints. This command has subcommands.

## Parse Arguments

- `/checkpoint` or `/checkpoint save` → **save** (default)
- `/checkpoint save {label}` → save with explicit label
- `/checkpoint resume` → resume from latest checkpoint
- `/checkpoint list` → list available checkpoints

## Subcommand: save (default)

Create a named snapshot of current session state.

### Steps

#### 1. Determine Label

If user provided a label, use it (kebab-case, e.g. `auth-middleware`).

If no label provided, generate one from the current task context (2-3 words, kebab-case).

#### 2. Gather State

Collect the following information:

```bash
# Git state
BRANCH=$(git branch --show-current)
GIT_SHA=$(git rev-parse --short HEAD)
git status --short
git diff --stat HEAD~3..HEAD 2>/dev/null || git diff --stat HEAD
```

Read the current task list if any tasks exist (use TaskList tool).

Check for pipeline state:
```bash
CONTEXT_JSON=$(~/.claude/bin/resolve-context)
RC=$?
```

**If exit 0** — parse JSON fields: `JIRA_ISSUE`, `BRANCH_NAME`, `BRANCH`, `PROJECT_DIR`
**If exit 2** — branch doesn't match `PROJ-123_description` convention. Ask user (AskUserQuestion):
  "Branch '{branch}' doesn't match PROJ-123_description convention. Enter JIRA issue key or 'none':"
  - Valid key → `JIRA_ISSUE={key}`, `PROJECT_DIR=docs/implementation_plans/{key}/{branch_name}/`
  - "none" → `PROJECT_DIR=docs/implementation_plans/_adhoc/{sanitised_branch}/`

```bash
cat ${PROJECT_DIR}/pipeline_state.json 2>/dev/null || echo '{}'
```

**Progress spine**: Include `bin/progress view --format summary` output in checkpoint data:
```bash
~/.claude/bin/progress view --project-dir "$PROJECT_DIR" --format summary 2>/dev/null || echo "No progress spine found"
```

#### 3. Synthesise Checkpoint

Using ALL gathered information, write a checkpoint file. The file captures everything needed to resume work.

Determine the auto-memory directory — this is the project-specific memory path that Claude Code auto-loads:

```bash
# The auto-memory dir is at ~/.claude/projects/{hash}/memory/
# Find it by looking for the MEMORY.md that's loaded into this session
ls ~/.claude/projects/*/memory/MEMORY.md 2>/dev/null
```

Use the auto-memory directory path from MEMORY.md (visible in your system prompt). Create the checkpoints subdirectory if needed:

```bash
mkdir -p {AUTO_MEMORY_DIR}/checkpoints
```

Write the checkpoint file using the Write tool to `{AUTO_MEMORY_DIR}/checkpoints/{YYYY-MM-DD-HHmm}-{label}.md`:

```markdown
# Checkpoint: {label}
Created: {ISO 8601 timestamp}
Git SHA: {sha}
Branch: {branch}

## Task
{What is being worked on — 1-3 sentences}

## Decisions Made
{Numbered list of key decisions with brief rationale}

## Progress
{Checklist — [x] done items, [ ] remaining items}

## Key Files
{List of files created or modified, with brief annotations}

## Approach & Rationale
{2-4 sentences on the chosen approach and why}

## Blockers / Open Questions
{Any unresolved issues or pending decisions — or "None"}

## Next Steps
{Numbered list of what to do next, in priority order}

## Context for Resumption
If resuming from this checkpoint, read these files first:
{List of 3-5 most important files with brief description of what each contains}
```

#### 4. Update MEMORY.md Working State

Read the current MEMORY.md from the auto-memory directory. Update (or create) the `## Working State` section at the TOP of the file, preserving all other sections.

The Working State section must be **15 lines or fewer**:

```markdown
## Working State
- **Branch**: {branch}
- **Task**: {1-line description}
- **Phase**: {research|planning|implementation|testing|review}
- **Progress**: {brief status, e.g. "3/5 endpoints done, tests passing"}
- **Approach**: {1-line approach summary}
- **Blockers**: {any blockers or "None"}
- **Next**: {immediate next action}
- **Checkpoint**: {label} ({date}, SHA: {sha})
```

**IMPORTANT**: Keep all existing sections in MEMORY.md (like "Stable Notes", "Python Tooling Preferences", etc.) intact. Only replace the `## Working State` section.

#### 5. Optionally Store in Memory MCP

If memory-upstream MCP is available, create a checkpoint entity:

```
create_entities([{
  name: "checkpoint:{label}",
  entityType: "checkpoint",
  observations: [
    "Created: {timestamp}",
    "Branch: {branch}, SHA: {sha}",
    "Task: {task description}",
    "Phase: {phase}",
    "Next: {next steps summary}"
  ]
}])
```

Skip silently if MCP is unavailable.

#### 6. Confirm

```markdown
> Checkpoint **{label}** saved.
> - File: `checkpoints/{filename}`
> - MEMORY.md working state updated.
>
> To resume later: `/checkpoint resume`
```

---

## Subcommand: resume

Reconstruct context from the tiered memory system.

### Steps

#### 1. Read MEMORY.md

The auto-memory MEMORY.md is already in your system prompt. Check for a `## Working State` section.

#### 2. Find Latest Checkpoint

```bash
ls -t {AUTO_MEMORY_DIR}/checkpoints/*.md 2>/dev/null | head -5
```

Read the most recent checkpoint file.

#### 3. Check Git State

```bash
git branch --show-current
git status --short
git log --oneline -5
```

#### 4. Query Memory MCP (if available)

```
search_nodes("checkpoint:")
search_nodes("session:")
search_nodes("blocker:")
```

#### 5. Check Pipeline State

```bash
CONTEXT_JSON=$(~/.claude/bin/resolve-context)
RC=$?
```

**If exit 0** — parse JSON fields: `JIRA_ISSUE`, `BRANCH_NAME`, `BRANCH`, `PROJECT_DIR`
**If exit 2** — branch doesn't match `PROJ-123_description` convention. Ask user (AskUserQuestion):
  "Branch '{branch}' doesn't match PROJ-123_description convention. Enter JIRA issue key or 'none':"
  - Valid key → `JIRA_ISSUE={key}`, `PROJECT_DIR=docs/implementation_plans/{key}/{branch_name}/`
  - "none" → `PROJECT_DIR=docs/implementation_plans/_adhoc/{sanitised_branch}/`

```bash
cat ${PROJECT_DIR}/pipeline_state.json 2>/dev/null
```

**Progress-aware resume**: When restoring, check for progress spine:
```bash
if [ -d "$PROJECT_DIR/progress" ]; then
  echo "=== Progress Spine ==="
  ~/.claude/bin/progress view --project-dir "$PROJECT_DIR" --format tree 2>/dev/null || true
fi
```
This provides richer state reconstruction than pipeline_state.json alone, showing per-milestone and per-agent status.

#### 6. Present Summary

Synthesise all gathered information into a resumption briefing:

```markdown
## Session Resumed

**Last checkpoint**: {label} ({date})

**Task**: {description}
**Branch**: {branch} (SHA: {sha} → current: {current_sha})
**Phase**: {phase}

### What's Done
{from checkpoint progress — completed items}

### What's Remaining
{from checkpoint progress — uncompleted items}

### Blockers
{any blockers from checkpoint or memory}

### Commits Since Checkpoint
{git log between checkpoint SHA and HEAD, if any}

### Suggested Next Action
{The most logical next step based on all context}
```

---

## Subcommand: list

Show available checkpoints.

### Steps

```bash
ls -lt {AUTO_MEMORY_DIR}/checkpoints/*.md 2>/dev/null
```

Present as a table:

```markdown
| # | Date | Label | Branch |
|---|------|-------|--------|
| 1 | 2026-02-13 14:30 | auth-middleware | PROJ-123_add-auth |
| 2 | 2026-02-12 16:45 | db-schema | PROJ-123_add-auth |
```

If no checkpoints exist:

> No checkpoints found. Run `/checkpoint` to create one.
