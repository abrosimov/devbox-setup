# Claude Code Configuration

This file contains configurable paths and settings for agents and commands.

## Paths

| Variable | Default | Description |
|----------|---------|-------------|
| `PLANS_DIR` | `docs/implementation_plans` | Base directory for all project documentation |

## Task Context

**IMPORTANT**: Commands compute context ONCE and pass to agents. Agents should NOT re-compute.

### Context Variables

| Variable | Derivation | Example |
|----------|------------|---------|
| `BRANCH` | `` `git branch --show-current` `` | `PROJ-123_add_user_auth` |
| `JIRA_ISSUE` | `` `echo "$BRANCH" \| cut -d'_' -f1` `` | `PROJ-123` |
| `BRANCH_NAME` | `` `echo "$BRANCH" \| cut -d'_' -f2-` `` | `add_user_auth` |
| `PROJECT_DIR` | `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}` | `docs/implementation_plans/PROJ-123/add_user_auth` |

### For Commands (Orchestrators)

Compute once at the start:
```bash
BRANCH=`git branch --show-current`
JIRA_ISSUE=`echo "$BRANCH" | cut -d'_' -f1`
BRANCH_NAME=`echo "$BRANCH" | cut -d'_' -f2-`
```

When invoking agents via Task tool, include in prompt:
```
Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, PROJECT_DIR={PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}
```

### For Agents

Use context provided by orchestrator. If invoked directly (no context), compute once:
```bash
BRANCH=`git branch --show-current`
JIRA_ISSUE=`echo "$BRANCH" | cut -d'_' -f1`
BRANCH_NAME=`echo "$BRANCH" | cut -d'_' -f2-`
```

---

## Project Directory Structure

All project documentation is organized by Jira issue and branch name:

```
{PLANS_DIR}/
├── PROJ-123/
│   ├── add_user_auth/       # Branch: PROJ-123_add_user_auth
│   │   ├── plan.md          # Implementation plan
│   │   ├── spec.md          # Product specification
│   │   ├── research.md      # Research findings
│   │   ├── decisions.md     # Decision log
│   │   ├── domain_analysis.md  # Domain analysis
│   │   ├── work_summary.md  # Agent work summary (quick overview)
│   │   └── work_log.md      # Agent work log (detailed reasoning)
│   └── add_user_auth_v2/    # Branch: PROJ-123_add_user_auth_v2
│       └── ...
├── PROJ-456/
│   └── refactor_api/
│       └── ...
```

### File Paths

| File | Path |
|------|------|
| Implementation plan | `{PROJECT_DIR}/plan.md` |
| Product specification | `{PROJECT_DIR}/spec.md` |
| Research findings | `{PROJECT_DIR}/research.md` |
| Decision log | `{PROJECT_DIR}/decisions.md` |
| Domain analysis | `{PROJECT_DIR}/domain_analysis.md` |
| Work summary | `{PROJECT_DIR}/work_summary.md` |
| Work log | `{PROJECT_DIR}/work_log.md` |

Where `PROJECT_DIR` = `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}`

### Examples

| Branch Name | Jira Issue | Branch Name | Project Directory |
|-------------|------------|-------------|-------------------|
| `PROJ-123_add_user_auth` | `PROJ-123` | `add_user_auth` | `docs/implementation_plans/PROJ-123/add_user_auth/` |
| `PROJ-123_add_user_auth_v2` | `PROJ-123` | `add_user_auth_v2` | `docs/implementation_plans/PROJ-123/add_user_auth_v2/` |
| `FEAT-42_refactor_api` | `FEAT-42` | `refactor_api` | `docs/implementation_plans/FEAT-42/refactor_api/` |

## Customizing Paths

To override defaults for your project, update the `PLANS_DIR` value in the table above. All agents and commands will read from this file.
