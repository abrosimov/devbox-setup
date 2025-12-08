# Claude Code Configuration

This file contains configurable paths and settings for agents and commands.

## Paths

| Variable | Default | Description |
|----------|---------|-------------|
| `PLANS_DIR` | `docs/implementation_plans` | Base directory for all project documentation |

## Project Directory Structure

All project documentation is organized by Jira issue:

```
{PLANS_DIR}/
├── PROJ-123/
│   ├── plan.md          # Implementation plan
│   ├── spec.md          # Product specification
│   ├── research.md      # Research findings
│   └── decisions.md     # Decision log
├── PROJ-456/
│   ├── plan.md
│   ├── spec.md
│   └── ...
```

### Path Resolution

1. **Extract Jira issue from branch**: `git branch --show-current | cut -d'_' -f1`
2. **Project directory**: `{PLANS_DIR}/{JIRA_ISSUE}/`

### File Paths

| File | Path |
|------|------|
| Implementation plan | `{PLANS_DIR}/{JIRA_ISSUE}/plan.md` |
| Product specification | `{PLANS_DIR}/{JIRA_ISSUE}/spec.md` |
| Research findings | `{PLANS_DIR}/{JIRA_ISSUE}/research.md` |
| Decision log | `{PLANS_DIR}/{JIRA_ISSUE}/decisions.md` |

### Examples

| Branch Name | Jira Issue | Project Directory |
|-------------|------------|-------------------|
| `PROJ-123_add_user_auth` | `PROJ-123` | `docs/implementation_plans/PROJ-123/` |
| `FEAT-42_refactor_api` | `FEAT-42` | `docs/implementation_plans/FEAT-42/` |

## Customizing Paths

To override defaults for your project, update the `PLANS_DIR` value in the table above. All agents and commands will read from this file.
