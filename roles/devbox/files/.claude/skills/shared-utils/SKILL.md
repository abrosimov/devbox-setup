---
name: shared-utils
description: >
  Shared utility scripts for all agents. Use when needing Jira context from branch,
  or other cross-cutting utilities. Triggers on: Jira issue, branch name, task context,
  get issue, extract issue.
---

# Shared Utilities

Cross-cutting utility scripts and standards used by multiple agents and skills.

## Agent Preamble (All Agents Must Follow)

### File Operations

**For creating new files**: ALWAYS use the **Write** tool, NEVER `cat > file << 'EOF'` or other Bash heredocs.

**For editing existing files**: Use the **Edit** tool.

**Bash is for commands only**: `git`, build tools, test runners, formatters, etc.

The Write/Edit tools are auto-approved in `acceptEdits` mode. Bash heredocs prompt for permission due to a known platform limitation with multiline command matching.

### Language Standard

Use **British English** spelling in all output:

| American | British |
|----------|---------|
| behavior | behaviour |
| organization | organisation |
| analyze | analyse |
| color | colour |
| center | centre |
| realize | realise |
| optimize | optimise |

### Reference Documents

All agents should consult:

| Document | Contents |
|----------|----------|
| `philosophy.md` | **Prime Directive (reduce complexity)**, pragmatic engineering principles |

## Jira Context

Extract Jira issue from git branch name.

**Convention:** Branch names follow `JIRAPRJ-123_description_of_branch`

### Bash

```bash
# Source to set variables
source skills/shared/scripts/jira_context.sh
echo "Working on: $JIRA_ISSUE / $BRANCH_NAME"

# Or run directly and parse output
./skills/shared/scripts/jira_context.sh
# Output:
# BRANCH=PROJ-123_feature_name
# JIRA_ISSUE=PROJ-123
# BRANCH_NAME=feature_name
```

### Fish

```fish
# Source to set variables
source skills/shared/scripts/jira_context.fish
echo "Working on: $JIRA_ISSUE / $BRANCH_NAME"
```

### Output Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `BRANCH` | Full branch name | `PROJ-123_add_user_auth` |
| `JIRA_ISSUE` | Extracted Jira key | `PROJ-123` |
| `BRANCH_NAME` | Description part (after first `_`) | `add_user_auth` |

### Project Directory

Once you have `JIRA_ISSUE` and `BRANCH_NAME`, find project files at:
```
{PLANS_DIR}/${JIRA_ISSUE}/${BRANCH_NAME}/
```

For example, the implementation plan:
```
{PLANS_DIR}/${JIRA_ISSUE}/${BRANCH_NAME}/plan.md
```

Where `{PLANS_DIR}` is configured in ``config` skill` (typically `docs/implementation_plans`).
