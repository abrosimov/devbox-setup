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
| `PROJECT_DIR` | `{PLANS_DIR}/{JIRA_ISSUE}` | `docs/implementation_plans/PROJ-123` |

### For Commands (Orchestrators)

Compute once at the start:
```bash
BRANCH=`git branch --show-current`; JIRA_ISSUE=`echo "$BRANCH" | cut -d'_' -f1`
```

When invoking agents via Task tool, include in prompt:
```
Context: BRANCH={value}, JIRA_ISSUE={value}, PROJECT_DIR={PLANS_DIR}/{JIRA_ISSUE}
```

### For Agents

Use context provided by orchestrator. If invoked directly (no context), compute once:
```bash
JIRA_ISSUE=`git branch --show-current | cut -d'_' -f1`
```

---

## Project Directory Structure

All project documentation is organized by Jira issue:

```
{PLANS_DIR}/
├── PROJ-123/
│   ├── plan.md          # Implementation plan
│   ├── spec.md          # Product specification
│   ├── research.md      # Research findings
│   ├── decisions.md     # Decision log
│   ├── domain_analysis.md  # Domain analysis
│   ├── work_summary.md  # Agent work summary (quick overview)
│   └── work_log.md      # Agent work log (detailed reasoning)
├── PROJ-456/
│   └── ...
```

### File Paths

| File | Path |
|------|------|
| Implementation plan | `{PLANS_DIR}/{JIRA_ISSUE}/plan.md` |
| Product specification | `{PLANS_DIR}/{JIRA_ISSUE}/spec.md` |
| Research findings | `{PLANS_DIR}/{JIRA_ISSUE}/research.md` |
| Decision log | `{PLANS_DIR}/{JIRA_ISSUE}/decisions.md` |
| Domain analysis | `{PLANS_DIR}/{JIRA_ISSUE}/domain_analysis.md` |
| Work summary | `{PLANS_DIR}/{JIRA_ISSUE}/work_summary.md` |
| Work log | `{PLANS_DIR}/{JIRA_ISSUE}/work_log.md` |

### Examples

| Branch Name | Jira Issue | Project Directory |
|-------------|------------|-------------------|
| `PROJ-123_add_user_auth` | `PROJ-123` | `docs/implementation_plans/PROJ-123/` |
| `FEAT-42_refactor_api` | `FEAT-42` | `docs/implementation_plans/FEAT-42/` |

## Customizing Paths

To override defaults for your project, update the `PLANS_DIR` value in the table above. All agents and commands will read from this file.
