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
| `DEFAULT_BRANCH` | auto-detected | Project's default branch (main/master/develop) |
| `INTEGRATION_BRANCH` | *(none — opt-in)* | Optional local integration branch for pre-PR testing |

## Workflow Config (Per-Project)

The agent workflow is opt-in per project. Config file: `.claude/workflow.json` in the project root.

```json
{
  "agent_pipeline": true,
  "auto_commit": true,
  "complexity_escalation": true
}
```

| Flag | Default | Description |
|------|---------|-------------|
| `agent_pipeline` | `true` | When `true`, code changes MUST go through agents. When `false`, direct edits allowed |
| `auto_commit` | `true` | When `true`, commands auto-commit via `git-safe-commit`. When `false`, user commits manually |
| `complexity_escalation` | `true` | When `true`, `/implement` auto-downgrades SE agents to Sonnet for simple tasks. When `false`, always use agent default model (opus) |

**Commands read this file at Step 0** and adjust behavior accordingly. If the file is missing, commands default all flags to `true` (backward compatible).

Create with `/init-workflow` or manually.

The default branch is detected automatically by `.claude/bin/git-default-branch`:
```bash
DEFAULT_BRANCH=$(.claude/bin/git-default-branch)
```

Detection priority: `claude.defaultBranch` git config > remote HEAD > `init.defaultBranch` > `"main"`.

To override per-repo: `git config --local claude.defaultBranch develop`

**Optional integration branch** (opt-in for local merge testing):
```bash
git config --local claude.integrationBranch build/stable
```
When set, commands offer local merge as an additional option alongside push+PR.

## Task Context

**IMPORTANT**: Commands compute context ONCE and pass to agents. Agents should NOT re-compute.

### Context Variables

- **`BRANCH`** — `git branch --show-current` — e.g. `PROJ-123_add_user_auth`
- **`JIRA_ISSUE`** — first segment before `_` — e.g. `PROJ-123`
- **`BRANCH_NAME`** — remaining segments after first `_` — e.g. `add_user_auth`
- **`DEFAULT_BRANCH`** — `.claude/bin/git-default-branch` — e.g. `main`
- **`PROJECT_DIR`** — `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}` — e.g. `docs/implementation_plans/PROJ-123/add_user_auth`

### For Commands (Orchestrators)

Compute once at the start:
```bash
CONTEXT_JSON=$(~/.claude/bin/resolve-context)  # exit 0=valid, exit 2=non-convention branch
# Parse: JIRA_ISSUE, BRANCH_NAME, BRANCH, PROJECT_DIR
DEFAULT_BRANCH=$(.claude/bin/git-default-branch)
```

When invoking agents via Task tool, include in prompt:
```
Context: BRANCH={value}, JIRA_ISSUE={value}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}, PROJECT_DIR={PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}
```

### For Agents

Use context provided by orchestrator. If invoked directly (no context), compute once:
```bash
CONTEXT_JSON=$(~/.claude/bin/resolve-context)  # exit 0=valid, exit 2=non-convention branch
# Parse: JIRA_ISSUE, BRANCH_NAME, BRANCH, PROJECT_DIR
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
│   │   ├── analysis.md      # FPF thinking artifact (structured reasoning)
│   │   ├── domain_analysis.md  # Domain analysis
│   │   ├── domain_model.md    # DDD domain model (bounded contexts, aggregates)
│   │   ├── api_design.md     # API design rationale and decisions
│   │   ├── api_spec.yaml     # OpenAPI specification (when REST)
│   │   ├── design.md         # UI/UX design specification
│   │   ├── design_system.tokens.json  # W3C Design Tokens
│   │   ├── schema_design.md  # Database schema design rationale
│   │   ├── migrations/       # Database migration files
│   │   ├── work_log_backend.md   # Backend SE work log (detailed reasoning)
│   │   ├── work_log_frontend.md  # Frontend SE work log (detailed reasoning)
│   │   ├── spec_output.json  # TPM structured output
│   │   ├── domain_output.json  # Domain Expert structured output
│   │   ├── domain_model.json  # Domain Modeller structured output
│   │   ├── plan_output.json  # Planner structured output
│   │   ├── design_output.json  # Designer structured output
│   │   ├── api_design_output.json  # API Designer structured output
│   │   ├── se_backend_output.json  # Backend SE structured output
│   │   ├── se_frontend_output.json # Frontend SE structured output
│   │   ├── pipeline_state.json  # Pipeline progress tracking
│   │   ├── decisions.json    # Pipeline decision log
│   │   ├── progress/              # Progress spine tracking
│   │   │   ├── plan.json          # Milestone DAG (TPM creates, Planner refines)
│   │   │   └── *.json             # Per-agent status files
│   │   └── memory/
│   │       └── upstream.jsonl # Knowledge graph — domain knowledge, decisions (VCS)
│   └── add_user_auth_v2/    # Branch: PROJ-123_add_user_auth_v2
│       └── ...
├── PROJ-456/
│   └── refactor_api/
│       └── ...
├── _adhoc/
│   └── branch-name/           # Non-convention branches (resolve-context exit 2)
│       └── ...
```

### File Paths

| File | Created By | Path |
|------|-----------|------|
| Implementation plan | Impl Planner | `{PROJECT_DIR}/plan.md` |
| Product specification | TPM | `{PROJECT_DIR}/spec.md` |
| Research findings | TPM | `{PROJECT_DIR}/research.md` |
| Decision log | TPM | `{PROJECT_DIR}/decisions.md` |
| FPF analysis | /think command | `{PROJECT_DIR}/analysis.md` |
| Domain analysis | Domain Expert | `{PROJECT_DIR}/domain_analysis.md` |
| Domain model | Domain Modeller | `{PROJECT_DIR}/domain_model.md` |
| API design rationale | API Designer | `{PROJECT_DIR}/api_design.md` |
| OpenAPI specification | API Designer | `{PROJECT_DIR}/api_spec.yaml` |
| UI/UX design specification | Designer | `{PROJECT_DIR}/design.md` |
| W3C Design Tokens | Designer | `{PROJECT_DIR}/design_system.tokens.json` |
| Schema design rationale | Database Designer | `{PROJECT_DIR}/schema_design.md` |
| Database migrations | Database Designer | `{PROJECT_DIR}/migrations/` |
| Backend work log | SE (backend) | `{PROJECT_DIR}/work_log_backend.md` |
| Frontend work log | SE (frontend) | `{PROJECT_DIR}/work_log_frontend.md` |
| Backend SE structured output | SE (backend) | `{PROJECT_DIR}/se_backend_output.json` |
| Frontend SE structured output | SE (frontend) | `{PROJECT_DIR}/se_frontend_output.json` |
| TPM structured output | TPM | `{PROJECT_DIR}/spec_output.json` |
| Domain structured output | Domain Expert | `{PROJECT_DIR}/domain_output.json` |
| Domain model structured output | Domain Modeller | `{PROJECT_DIR}/domain_model.json` |
| Planner structured output | Impl Planner | `{PROJECT_DIR}/plan_output.json` |
| Designer structured output | Designer | `{PROJECT_DIR}/design_output.json` |
| API Designer structured output | API Designer | `{PROJECT_DIR}/api_design_output.json` |
| Pipeline state | Commands | `{PROJECT_DIR}/pipeline_state.json` |
| Pipeline decisions | Commands | `{PROJECT_DIR}/decisions.json` |
| Progress plan | TPM, Impl Planner | `{PROJECT_DIR}/progress/plan.json` |
| Agent progress | Each pipeline agent | `{PROJECT_DIR}/progress/{agent}.json` |
| Memory (upstream) | TPM, Domain, Planners | `{PROJECT_DIR}/memory/upstream.jsonl` |
| Memory (downstream) | Code Reviewers | `.claude/memory/downstream.jsonl` (project root, gitignored) |

Where `PROJECT_DIR` = `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}`

When `resolve-context` exits 2 (non-convention branch), commands fall back to `_adhoc/{sanitised_branch}/` under the plans directory. The sanitised branch name replaces `/` with `-` (e.g. `feature/login` becomes `feature-login`).

### Examples

| Branch Name | Jira Issue | Branch Name | Project Directory |
|-------------|------------|-------------|-------------------|
| `PROJ-123_add_user_auth` | `PROJ-123` | `add_user_auth` | `docs/implementation_plans/PROJ-123/add_user_auth/` |
| `PROJ-123_add_user_auth_v2` | `PROJ-123` | `add_user_auth_v2` | `docs/implementation_plans/PROJ-123/add_user_auth_v2/` |
| `FEAT-42_refactor_api` | `FEAT-42` | `refactor_api` | `docs/implementation_plans/FEAT-42/refactor_api/` |

### Cross-Cutting Documentation

Artifacts not tied to specific tickets live at project root level:

```
docs/
├── prd.md                      # Main PRD (current, top-level)
├── decisions/                  # Project-wide ADRs
│   ├── 001-auth-strategy.md
│   └── 002-database-choice.md
├── design/                     # Cross-cutting architecture docs
│   └── caching-architecture.md
├── domain/                     # Foundational domain models
│   └── bounded-contexts.md
│
└── implementation_plans/       # Ticket-scoped (see above)
    └── ...
```

| File | Created By | Path |
|------|-----------|------|
| Main PRD | TPM | `docs/prd.md` |
| Project-wide ADR | /think, Architect | `docs/decisions/NNN-<topic>.md` |
| Architecture doc | /think, Architect | `docs/design/<topic>.md` |
| Core domain model | Domain Modeller | `docs/domain/<context>.md` |
| FPF analysis (cross-cutting) | /think command | `docs/decisions/NNN-<topic>.md` or `docs/design/<topic>.md` |

**Routing rule**: If thinking relates to a specific Jira ticket → `{PROJECT_DIR}/analysis.md`. If cross-cutting → `docs/decisions/` or `docs/design/`.

## Customizing Paths

To override defaults for your project, update the `PLANS_DIR` value in the table above. All agents and commands will read from this file.

## Settings Hierarchy

Claude Code merges settings from multiple scopes. **More specific scopes override broader ones.**

| Priority | File | Scope | Tracked? |
|----------|------|-------|----------|
| 1 (highest) | `.claude/settings.local.json` | Per-project, per-developer | gitignored |
| 2 | `.claude/settings.json` | Per-project, shared | committed |
| 3 (lowest) | `~/.claude/settings.json` | Global baseline | Ansible-deployed |

**Merge rules:**
- `defaultMode`: overridden by more specific scope
- `allow` / `deny` arrays: **additive** (concatenated across all scopes)
- Evaluation order: deny (checked first) > allow (checked last)

### Global `~/.claude/settings.json`

Deployed by Ansible. Contains:
- **deny**: Security floor (destructive ops, secrets, force push, publishing) — projects can't weaken these
- **allow**: All language tooling (Go, Python, Frontend, Docker, Observability), git safe ops, system utils

### Project `.claude/settings.json`

Optional. Use when a project needs additional permissions beyond the global baseline, or wants to restrict certain operations. Created automatically by `/init-workflow` if requested.

### `settings.local.json` — Personal Overrides

For per-developer customization. Common use cases:

| Use Case | What to Add |
|----------|-------------|
| **Push without prompting** | `"allow": ["Bash(git push *)"]` |
| **Database CLIs** | `"allow": ["Bash(psql *)", "Bash(mongosh *)", "Bash(redis-cli *)"]` |
| **API testing** | `"allow": ["Bash(curl *)", "Bash(http *)"]` |
| **Ansible (devbox project)** | `"allow": ["Bash(ansible *)", "Bash(ansible-playbook *)", "Bash(ansible-lint *)", "Bash(ansible-galaxy *)"]` |
| **Stricter mode** | `"defaultMode": "plan"` |

Example `.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(git push *)",
      "Bash(psql *)"
    ]
  }
}
```

**Note:** `settings.local.json` is gitignored and preserved across Ansible deploys. Each developer maintains their own.
