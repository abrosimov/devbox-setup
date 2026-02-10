---
name: config
description: >
  Configurable paths, task context variables, and project directory structure for agents
  and commands. Single source of truth for PLANS_DIR, JIRA_ISSUE, BRANCH_NAME, PROJECT_DIR.
  Triggers on: config, paths, PLANS_DIR, PROJECT_DIR, project directory, plan location,
  branch name, Jira issue, task context.
---

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
│   │   ├── decisions.md     # Decision log (TPM)
│   │   ├── domain_analysis.md  # Domain analysis
│   │   ├── api_design.md     # API design rationale and decisions
│   │   ├── api_spec.yaml     # OpenAPI specification (when REST)
│   │   ├── design.md         # UI/UX design specification
│   │   ├── design_system.tokens.json  # W3C Design Tokens
│   │   ├── schema_design.md  # Database schema design rationale
│   │   ├── migrations/       # Database migration files
│   │   ├── work_summary.md  # Agent work summary (quick overview)
│   │   ├── work_log.md      # Agent work log (detailed reasoning)
│   │   ├── spec_output.json  # TPM structured output
│   │   ├── domain_output.json  # Domain Expert structured output
│   │   ├── plan_output.json  # Planner structured output
│   │   ├── design_output.json  # Designer structured output
│   │   ├── api_design_output.json  # API Designer structured output
│   │   ├── pipeline_state.json  # Pipeline progress tracking
│   │   ├── decisions.json    # Pipeline decision log
│   │   └── memory/
│   │       └── upstream.jsonl # Knowledge graph — domain knowledge, decisions (VCS)
│   └── add_user_auth_v2/    # Branch: PROJ-123_add_user_auth_v2
│       └── ...
├── PROJ-456/
│   └── refactor_api/
│       └── ...
```

### File Paths

| File | Created By | Path |
|------|-----------|------|
| Implementation plan | Impl Planner | `{PROJECT_DIR}/plan.md` |
| Product specification | TPM | `{PROJECT_DIR}/spec.md` |
| Research findings | TPM | `{PROJECT_DIR}/research.md` |
| Decision log | TPM | `{PROJECT_DIR}/decisions.md` |
| Domain analysis | Domain Expert | `{PROJECT_DIR}/domain_analysis.md` |
| API design rationale | API Designer | `{PROJECT_DIR}/api_design.md` |
| OpenAPI specification | API Designer | `{PROJECT_DIR}/api_spec.yaml` |
| UI/UX design specification | Designer | `{PROJECT_DIR}/design.md` |
| W3C Design Tokens | Designer | `{PROJECT_DIR}/design_system.tokens.json` |
| Schema design rationale | SE | `{PROJECT_DIR}/schema_design.md` |
| Database migrations | SE | `{PROJECT_DIR}/migrations/` |
| Work summary | SE | `{PROJECT_DIR}/work_summary.md` |
| Work log | SE | `{PROJECT_DIR}/work_log.md` |
| TPM structured output | TPM | `{PROJECT_DIR}/spec_output.json` |
| Domain structured output | Domain Expert | `{PROJECT_DIR}/domain_output.json` |
| Planner structured output | Impl Planner | `{PROJECT_DIR}/plan_output.json` |
| Designer structured output | Designer | `{PROJECT_DIR}/design_output.json` |
| API Designer structured output | API Designer | `{PROJECT_DIR}/api_design_output.json` |
| Pipeline state | Commands | `{PROJECT_DIR}/pipeline_state.json` |
| Pipeline decisions | Commands | `{PROJECT_DIR}/decisions.json` |
| Memory (upstream) | TPM, Domain, Planners | `{PROJECT_DIR}/memory/upstream.jsonl` |
| Memory (downstream) | Code Reviewers | `.claude/memory/downstream.jsonl` (project root, gitignored) |

Where `PROJECT_DIR` = `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}`

### Examples

| Branch Name | Jira Issue | Branch Name | Project Directory |
|-------------|------------|-------------|-------------------|
| `PROJ-123_add_user_auth` | `PROJ-123` | `add_user_auth` | `docs/implementation_plans/PROJ-123/add_user_auth/` |
| `PROJ-123_add_user_auth_v2` | `PROJ-123` | `add_user_auth_v2` | `docs/implementation_plans/PROJ-123/add_user_auth_v2/` |
| `FEAT-42_refactor_api` | `FEAT-42` | `refactor_api` | `docs/implementation_plans/FEAT-42/refactor_api/` |

## Customizing Paths

To override defaults for your project, update the `PLANS_DIR` value in the table above. All agents and commands will read from this file.
