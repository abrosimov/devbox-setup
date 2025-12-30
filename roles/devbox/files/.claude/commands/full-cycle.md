---
description: Run complete development cycle (implement → test → review)
---

You are orchestrating a complete development cycle with human checkpoints.

## Workflow Overview

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Implement   │────▶│    Test      │────▶│   Review     │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │
       ▼                    ▼                    ▼
   [User OK?]           [User OK?]          [Issues?]
       │                    │                    │
    continue             continue           fix or done
```

## Steps

### Phase 0: Setup

**Compute Task Context (once)**:
```bash
BRANCH=`git branch --show-current`
JIRA_ISSUE=`echo "$BRANCH" | cut -d'_' -f1`
BRANCH_NAME=`echo "$BRANCH" | cut -d'_' -f2-`
```

Store these values — pass to all agents throughout the cycle.

**Detect project language**:
- If `go.mod` exists → **Go project**
- If `pyproject.toml` or `requirements.txt` exists → **Python project**
- If both or unclear → Ask user

### Phase 1: Implementation

1. Run `software-engineer-{lang}` agent with `Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}`
2. Present summary of changes made
3. **PAUSE**: Ask user to confirm or correct

User options:
- `continue` → proceed to Phase 2
- `fix <instruction>` → apply correction, then re-summarize
- `stop` → end workflow

### Phase 2: Testing

1. Run `unit-test-writer-{lang}` agent with `Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}`
2. Present summary of tests created
3. Run tests to verify they pass
4. **PAUSE**: Ask user to confirm or correct

User options:
- `continue` → proceed to Phase 3
- `fix <instruction>` → apply correction, re-run tests
- `skip` → skip to Phase 3
- `stop` → end workflow

### Phase 3: Review

1. Run `code-reviewer-{lang}` agent with `Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}`
2. Present structured feedback with severity levels
3. **PAUSE**: Present options based on results

If blocking issues found:
> Review found X blocking issues. Say **'fix'** to address them.

If no blocking issues:
> Review passed. Say **'commit'** to create commit, or **'done'** to finish.

### Fix Loop

If user says 'fix':
1. Run SE agent with review feedback
2. Re-run tests
3. Re-run review
4. Present updated feedback

## User Commands (Available at Any Checkpoint)

| Command | Action |
|---------|--------|
| `continue` | Proceed to next phase |
| `fix <instruction>` | Apply specific fix before continuing |
| `skip` | Skip current phase, move to next |
| `stop` | End workflow entirely |
| `back` | Return to previous phase |

## Notes

- Each phase pauses for your confirmation
- You can correct or redirect at any checkpoint
- The workflow preserves context between phases
- Use `stop` at any time to exit
