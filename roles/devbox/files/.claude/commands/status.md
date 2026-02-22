---
description: Show pipeline progress — milestones, gates, and agent status
---

You are showing the user the current pipeline progress for this project.

## Steps

### Step 1: Resolve Context

```bash
CONTEXT_JSON=$(~/.claude/bin/resolve-context)
RC=$?
```

If exit 0: parse `PROJECT_DIR` from the JSON.
If exit 2: use `_adhoc/{sanitised_branch}/` fallback (see `config` skill).

### Step 2: Check for Progress Spine

```bash
if [ -d "$PROJECT_DIR/progress" ]; then
  HAS_PROGRESS=true
else
  HAS_PROGRESS=false
fi
```

### Step 3: Display Progress

**If progress spine exists** (`$HAS_PROGRESS=true`):

Show the tree view:
```bash
~/.claude/bin/progress view --project-dir "$PROJECT_DIR" --format tree
```

This shows:
- Milestone statuses: ✓ completed, ● in_progress, ○ pending, ✗ failed, ⊘ skipped, ! blocked
- Subtask status under each milestone
- Gate progression (G1 [passed] → G2 [pending] → ...)
- Current agent activity ("You are here" indicator)

**If `$1` is `--verbose` or `-v`**:

Also show per-agent details:
```bash
~/.claude/bin/progress view --project-dir "$PROJECT_DIR" --format table
```

And show recent decisions:
```bash
~/.claude/bin/progress view --project-dir "$PROJECT_DIR" --format json 2>/dev/null | jq '.decisions[-3:]' 2>/dev/null || true
```

**If no progress spine exists**:

Check for legacy `pipeline_state.json`:
```bash
if [ -f "$PROJECT_DIR/pipeline_state.json" ]; then
  echo "Legacy pipeline state found. Progress spine not yet initialized."
  echo ""
  echo "To migrate: ~/.claude/bin/progress migrate --project-dir \"$PROJECT_DIR\""
  echo ""
  # Show basic stage status from legacy file
  jq -r '.stages | to_entries[] | "\(.key): \(.value.status)"' "$PROJECT_DIR/pipeline_state.json" 2>/dev/null || true
else
  echo "No pipeline state found for this project."
  echo ""
  echo "Run /full-cycle to start a new pipeline, or /implement for individual tasks."
fi
```

## Arguments

| Argument | Effect |
|----------|--------|
| *(none)* | Tree view of milestones and gates |
| `--verbose` / `-v` | Tree view + per-agent table + recent decisions |
| `--json` | Raw JSON output (for scripting) |

When `--json` is passed:
```bash
~/.claude/bin/progress view --project-dir "$PROJECT_DIR" --format json
```
