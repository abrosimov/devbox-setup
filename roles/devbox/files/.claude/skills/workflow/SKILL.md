---
name: workflow
description: >
  Agent pipeline, workflow commands, and development modes for the Claude Code agent system.
  Covers slash commands, agent roles, language discussion policy, and key conventions.
  Triggers on: workflow, pipeline, agent, command, /implement, /test, /review, /plan,
  /full-cycle, /domain-analysis, next step, which agent.
---

# Workflow Reference

This document describes the agent pipeline and workflow commands for projects using the Claude Code agent system.

## Opt-In Model

The agent workflow is **opt-in per project** via `.claude/workflow.json`. Agents, commands, and skills are deployed globally to `~/.claude/` and always available, but **enforcement** (mandatory agent usage, auto-commit, auto-downgrade) is controlled per-project.

### Workflow Config

Per-project `.claude/workflow.json`:

```json
{
  "agent_pipeline": true,
  "auto_commit": true,
  "complexity_escalation": true
}
```

| Flag | `true` | `false` | Default |
|------|--------|---------|---------|
| `agent_pipeline` | Code changes MUST go through agents | Direct Edit/Write allowed | `true` |
| `auto_commit` | Commands auto-commit after each phase | User commits manually | `true` |
| `complexity_escalation` | Auto-downgrade SE agents to Sonnet for simple tasks | Always use agent's default model (opus) | `true` |

### Project Initialization

When Claude detects a code project without `.claude/workflow.json`, it asks the user whether to enable the workflow. See `CLAUDE.md` for the detection logic.

Use `/init-workflow` to explicitly set up the workflow config:

```bash
/init-workflow full    # all flags true
/init-workflow light   # agent_pipeline: true, auto_commit: false, complexity_escalation: false
/init-workflow         # interactive — choose preset or custom
```

### Without workflow.json

- All commands (`/implement`, `/test`, `/review`, `/full-cycle`) still work — they use agents regardless
- Direct code edits via Edit/Write are allowed (no enforcement)
- Commands default all flags to `true` for backward compatibility

## Directory Structure

```
.claude/
├── CLAUDE.md              # User Authority Protocol (global rules)
├── settings.json          # Claude Code permissions and settings
├── hooks.json             # Pre/post tool-use hooks (hard enforcement)
├── agents/                # Specialized agent definitions
│   ├── software_engineer_*.md
│   ├── unit_tests_writer_*.md
│   ├── integration_tests_writer_*.md
│   ├── code_reviewer_*.md
│   ├── implementation_planner_*.md
│   ├── api_designer.md
│   ├── database_designer.md
│   ├── designer.md
│   ├── domain_expert.md
│   ├── domain_modeller.md
│   ├── observability_engineer.md
│   ├── technical_product_manager.md
│   ├── agent_builder.md
│   ├── skill_builder.md
│   ├── meta_reviewer.md
│   ├── content_reviewer.md
│   ├── freshness_auditor.md
│   └── consistency_checker.md
├── commands/              # Workflow slash commands
│   ├── domain-analysis.md
│   ├── plan.md
│   ├── api-design.md
│   ├── design.md
│   ├── schema.md
│   ├── implement.md
│   ├── test.md
│   ├── review.md
│   ├── full-cycle.md
│   ├── init-workflow.md
│   ├── build-agent.md
│   ├── build-skill.md
│   ├── validate-config.md
│   ├── audit.md
│   ├── checkpoint.md
│   ├── verify.md
│   └── learn.md
├── skills/                # Reusable knowledge modules
└── docs/                  # Historical reference documentation
```

## Workflow Commands

| Command | Description | When to Use |
|---------|-------------|-------------|
| `/domain-analysis` | Validate requirements, challenge assumptions | After spec, before planning |
| `/plan` | Create implementation plan from spec | Before implementation (complex tasks) |
| `/api-design` | Design API contracts (REST/OpenAPI or Protobuf/gRPC) | After planning, before backend implementation |
| `/schema` | Design database schema with migrations | After planning, before/alongside backend implementation |
| `/design` | Create UI/UX design spec and design tokens | After spec/domain analysis, before frontend implementation |
| `/implement` | Run SE agent for current task | Start implementation |
| `/test` | Run test writer agent | After implementation |
| `/review` | Run code reviewer agent | After tests |
| `/full-cycle` | Run complete pipeline with 4 milestone gates | Standard development |
| `/init-workflow` | Initialise agent workflow for current project | First time in a project |
| `/build-agent` | Create/validate/refine agents (2-gate pipeline with meta-review) | When adding/modifying agents |
| `/build-skill` | Create/validate/audit/refine skills (2-gate pipeline with meta-review) | When adding/modifying skills |
| `/audit` | Run library-wide freshness and/or consistency audit | After adding agents/skills, periodic maintenance |
| `/validate-config` | Check cross-references, skill existence, frontmatter integrity | After config changes |
| `/checkpoint` | Save or restore context across sessions/compaction | At logical boundaries, after milestones |
| `/verify` | Run pre-PR quality gate (build, typecheck, lint, test, debug scan) | Before `/review` or PR creation |
| `/learn` | Extract a reusable pattern from current session | After solving non-trivial problems |

Each command:
- Auto-detects project stack (Go/Python/Frontend/Fullstack)
- Pauses for user confirmation between steps
- Suggests next step after completion
- For fullstack projects, routes to appropriate agent(s) based on work streams

## Pipeline Modes

| Mode | Trigger | Approval Model |
|------|---------|---------------|
| **Per-step** | Individual commands (`/implement`, `/test`, `/review`) | Approve after each agent |
| **Gated** | `/full-cycle` | 4 milestone gates, autonomous between |
| **Manual** | Call agents directly by name | Maximum control |

### Gated Mode — 4 Milestone Gates

| Gate | After | User Decides |
|------|-------|-------------|
| G1 | TPM + Domain Expert + Domain Modeller | "Is this the right problem and domain model?" |
| G2 | Designer options | "Which design direction?" (skipped for backend) |
| G3 | Design + API + Plan all ready | "Ready to implement?" |
| G4 | Code Review complete | "Ship it?" |

## Agent Pipeline

<pipeline>

### Step 1: Requirements
- **technical_product_manager** — Transforms ideas into product specifications
  Produces: `spec.md`, `spec_output.json`

### Step 2: Domain Validation
- **domain_expert** — Challenges assumptions, validates requirements, discovers events/commands
  Depends on: Step 1
  Produces: `domain_analysis.md`, `domain_output.json`

### Step 2b: Domain Modelling
- **domain_modeller** — Formalises domain analysis into DDD model with bounded contexts, aggregates, events, and system design bridge
  Depends on: Step 2
  Produces: `domain_model.md`, `domain_model.json`
  Skipped when: Simple domain (Cynefin = Clear, <5 entities) or user says 'skip model'

### Step 3: Planning + Design (parallel for UI features)
- **implementation_planner_*** — Creates detailed implementation plans with work streams
  Depends on: Step 2
  Produces: `plan.md`, `plan_output.json` (includes `work_streams` and `parallelism_groups`)
- **designer** — Creates UI/UX design specs, design tokens, component specifications
  Depends on: Step 2 (runs parallel with planner for UI features)
  Produces: `design.md`, `design_output.json`
  Skipped when: feature_type = backend

### Step 4: Contracts (driven by work streams)
- **database_designer** — Designs database schemas with migrations (PostgreSQL, MySQL, MongoDB, CockroachDB)
  Depends on: Step 3
  Produces: `schema_design.md`, migrations
  Skipped when: plan has no schema work stream
- **api_designer** — Designs API contracts (REST/OpenAPI or Protobuf/gRPC)
  Depends on: Step 3 (and Step 4a if schema changes exist)
  Produces: `api_design.md`, `api_design_output.json`

### Step 5: Implementation (DAG-driven, stream-independent execution)

**Execution model**: Phase 4 uses a DAG (Directed Acyclic Graph) where each task node executes as soon as its dependencies resolve. Streams don't wait for each other.

- **Backend SE**: Depends on Gate 3 approval only
  Produces: source code, `se_backend_output.json`, `backend_completion.json`
- **Frontend SE**: Depends on Gate 3 approval + API contract
  Produces: source code, `se_frontend_output.json`, `frontend_completion.json`
  (Can run in parallel with backend — depends on API contract, NOT backend implementation)
- **Observability**: Depends on Gate 3 approval
  Produces: dashboards, alerts (can run in parallel with SE agents)
- **Test Writers**: Depend on their stream's SE completion (NOT all streams)
  Backend tests start as soon as backend SE finishes, even if frontend SE is still running
- **Code Reviewer**: Depends on ALL streams completing tests
  If blocking issues found → return to affected stream(s) with feedback

**Schema-driven verification**: Each stream writes `{stream}_completion.json` (schema: `schemas/stream_completion.schema.json`). The orchestrator validates via `bin/validate-pipeline-output --full` before advancing the DAG. Exit codes drive targeted retry prompts.

### Step 6: Testing
- **unit_tests_writer_*** — Writes unit tests with bug-hunting mindset (per language/stack)
  Depends on: Step 5
- **integration_tests_writer_*** — Writes integration tests with real dependencies
  Depends on: Step 5

### Step 7: Review
- **code_reviewer_*** — Validates implementation against requirements (per language/stack)
  Depends on: Step 6
  If blocking issues found → return to Step 5 with feedback

</pipeline>

<transitions>
- After Step 2 completes → Step 2b (Domain Modeller) runs if domain is complex
- After Step 2b completes (or is skipped) → **Gate 1** (user approval: "right problem + right model?")
- Steps 3a (Planner) and 3b (Designer) run in parallel for UI/fullstack features
- Planner produces work streams that drive Steps 4-5 execution order and DAG construction
- Step 4 (contracts): Schema designer (if needed) runs before API designer; both autonomous
- Step 5 (implementation): **DAG-based execution** — each stream (SE → test) runs independently. A stream's test writer starts immediately when its SE finishes, without waiting for other streams. Cross-stream tasks (review) start when all their specific dependencies resolve.
- After Step 5 completes (all streams validated by `bin/validate-pipeline-output`) → Review → **Gate 4** (user approval: "ship it?")
- Validation is deterministic (exit codes), not probabilistic (LLM self-assessment)
</transitions>

**Infrastructure agents** (outside the development pipeline):
- **agent_builder** — Creates, validates, and refines agent definitions
- **skill_builder** — Creates, validates, and refines skill modules
- **meta_reviewer** — Adversarial reviewer that challenges builder output against grounded Anthropic docs
- **content_reviewer** — Content substance reviewer that verifies code examples, versions, security, and redundancy
- **freshness_auditor** — Library-wide scanner for outdated versions, deprecated APIs, and best practice drift
- **consistency_checker** — Library-wide scanner for terminology conflicts, broken handoffs, and coverage gaps

### Meta-Pipeline (Infrastructure)

`/build-agent` and `/build-skill` use a 3-gate pipeline for create/refine modes:

```
Builder → GATE 1 (user review) → Meta-Reviewer → GATE 2 (user approve) → Content Reviewer → GATE 3 (user approve)
```

- Gate 1: Builder produces artifact + self-validation + XML artifact block
- Gate 2: Meta-reviewer adversarially challenges against grounded Anthropic docs (structural + discoverability)
- Gate 3: Content reviewer audits substance (code examples, versions, security, redundancy)
- User can `skip-review` at Gate 1 to bypass both meta-review and content review
- User can `skip-content` at Gate 2 to bypass content review only
- Validate/audit modes are single-pass (no meta-review or content review needed)

Grounding references (cached Anthropic docs) are read at the start of every builder operation:
- `skills/agent-builder/references/anthropic-agent-authoring.md`
- `skills/agent-builder/references/anthropic-prompt-engineering.md`
- `skills/skill-builder/references/anthropic-skill-authoring.md`

### Audit Pipeline

`/audit` runs library-wide checks across all agents and skills:

```
/audit           → [Freshness Auditor ‖ Consistency Checker] → merged report
/audit freshness → Freshness Auditor only
/audit consistency → Consistency Checker only
/audit fix       → [Freshness Auditor ‖ Consistency Checker] → route findings to builders
```

- Freshness Auditor (Sonnet): external staleness — versions, deprecated APIs, best practice drift
- Consistency Checker (Sonnet): internal coherence — terminology, handoffs, coverage gaps, duplication
- Fix mode: batches findings per artifact, routes to agent-builder or skill-builder for remediation
- User approves each builder fix before proceeding to the next artifact

## Code Writing & Language Discussion Policy

**Core Principle:** Specialized agents are the authoritative source for their languages.

### When to Use Language-Specific Agents

| Situation | Examples | Agent |
|-----------|----------|-------|
| **Writing code** | Any code changes, even small fixes | `software-engineer-{lang}` |
| **Design discussions** | "When to use pointers vs values?" | `software-engineer-{lang}` |
| **Idiom questions** | "What's the Go way to do X?" | `software-engineer-{lang}` |
| **Architecture decisions** | "Where should this logic live?" | `software-engineer-{lang}` |
| **Pattern selection** | "Which pattern fits?" | `software-engineer-{lang}` |
| **Best practices** | "Should I use X or Y?" | `software-engineer-{lang}` |

### Quick Reference

| Task | Agent | Command |
|------|-------|---------|
| **Any Go topic** | `software-engineer-go` | `/implement` |
| **Any Python topic** | `software-engineer-python` | `/implement` |
| **Any Frontend topic** (React, TypeScript, Next.js) | `software-engineer-frontend` | `/implement` |
| **Fullstack feature** | Backend SE + Frontend SE (sequential or parallel) | `/implement` |
| Go tests | `unit-test-writer-go` | `/test` |
| Python tests | `unit-test-writer-python` | `/test` |
| Frontend tests | `unit-test-writer-frontend` | `/test` |

### Exceptions (Answer Directly)

- General programming concepts (not language-specific)
- Claude Code usage (features, settings)
- Clarifying user requirements
- Trivial typo fixes in comments/strings
- Configuration files (YAML, JSON, TOML)

## Git Workflow

### Branching Model — Island Branches

```
main/master/develop            (default branch — agents never touch)
  ├── PROJ-123_backend         (feature branch — worktree A)
  ├── PROJ-123_frontend        (feature branch — worktree B)
  └── PROJ-456_dashboard       (feature branch — worktree C)
```

Each feature branch is independent. No local merge — integration happens via PR/CI.

**Default branch**: auto-detected by `.claude/bin/git-default-branch`. Override per-repo: `git config --local claude.defaultBranch develop`.

### Branch Lifecycle

1. Command creates feature branch from default branch (or uses current)
2. SE agent implements on feature branch (agent never touches git)
3. Command auto-commits after each agent phase via `git-safe-commit` (when `auto_commit: true` in `workflow.json`)
4. After review, user pushes and creates PR
5. Merge happens in GitHub/GitLab (not locally)

### Multi-Branch Per Ticket

One Jira ticket can span multiple branches/worktrees:

| Pattern | Example | Base Branch |
|---------|---------|-------------|
| **Independent** | backend + frontend (parallel worktrees) | Default branch |
| **Chained** | db → backend → api → frontend | Previous branch via `--from` |
| **Mixed** | backend from default, frontend from backend | Varies |

### Git Safety Scripts

| Script | Purpose | Called By |
|--------|---------|----------|
| `.claude/bin/git-default-branch` | Detect project's default branch | Commands, `claude-wt` |
| `.claude/bin/git-safe-commit` | Commit with branch protection + secret detection | Commands |
| `.claude/bin/git-safe-merge` | ff-only merge with dependency check (opt-in integration branch) | User (manual) |

### Separation of Concerns

| Actor | Git Operations |
|-------|---------------|
| **Commands** | Branch creation, stage, commit |
| **SE Agents** | None (code only) |
| **Review Agents** | Read-only (diff, log) |
| **User** | Push, PR creation, merge (via GitHub) |

### Commit Convention

```
<type>(<JIRA_ISSUE>): <description>
```

Types: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`

## Worktree Parallelism

For working on multiple tasks simultaneously, use git worktrees via `claude-wt`:

```bash
claude-wt new PROJ-123_backend                       # branch from default branch
claude-wt new PROJ-123_frontend --from PROJ-123_backend  # chain from another branch
claude-wt list --ticket PROJ-123                     # see all worktrees for a ticket
claude-wt status                                     # show all with PR status
claude-wt rm PROJ-123_backend                        # remove after merge
claude-wt clean                                      # prune all merged worktrees
```

Directory layout: `../<project>-wt/<branch-name>/`

Each worktree gets its own Claude Code session. `claude-wt` automatically:
- Copies `settings.local.json` to the worktree
- Symlinks downstream memory for shared knowledge
- Creates the branch from the default branch (or specified base via `--from`)

### Parallel Workflow Example

```
Terminal 1:                          Terminal 2:
claude-wt new PROJ-123_backend       claude-wt new PROJ-123_frontend
claude --cwd ../project-wt/...       claude --cwd ../project-wt/...
> /implement backend API              > /implement frontend dashboard
> /test                               > /test
> /review → 'pr'                      > /review → 'pr'
claude-wt rm PROJ-123_backend         claude-wt rm PROJ-123_frontend
```

## Configuration

See `config` skill for configurable paths.

Documentation is organized by Jira issue and branch:
`{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/`

- `spec.md` - Product specification
- `domain_analysis.md` - Domain analysis
- `domain_model.md` - DDD domain model (bounded contexts, aggregates, invariants)
- `domain_model.json` - Structured domain model (see `ddd-modeling` skill)
- `plan.md` - Implementation plan
- `api_design.md` - API design rationale and decisions
- `api_spec.yaml` - OpenAPI specification (REST mode)
- `schema_design.md` - Database schema design rationale
- `migrations/` - Database migration files
- `design.md` - UI/UX design specification
- `design_system.tokens.json` - W3C Design Tokens
- `work_log_backend.md` - Backend SE work log
- `work_log_frontend.md` - Frontend SE work log
- `research.md` - Research findings
- `decisions.md` - Decision log

## Task Identification

Branch naming convention: `JIRAPRJ-123_name_of_the_branch`

- `JIRA_ISSUE`: `git branch --show-current | cut -d'_' -f1`
- `BRANCH_NAME`: `git branch --show-current | cut -d'_' -f2-`

## Model Selection Precedence

When invoking agents via commands, the model is determined by this precedence (highest wins):

| Priority | Source | Example |
|----------|--------|---------|
| 1 (highest) | User explicit argument | `/implement sonnet`, `/implement opus` |
| 2 | Downgrade check at command level | All criteria below thresholds → sonnet (requires `complexity_escalation: true` in `workflow.json`) |
| 3 | Agent frontmatter default | `model: opus` (SE, reviewers, planners) or `model: sonnet` (test writers, etc.) |

**CRITICAL — `model` must be passed explicitly:**
- The Task tool **inherits the parent conversation's model** when no `model` parameter is given
- Agent frontmatter `model` field defines the agent's **intended** model but does NOT override inheritance
- Therefore, every command MUST pass `model` explicitly in the Task invocation
- Without explicit `model`, an agent with `model: opus` in frontmatter will run on the parent's model

**How it works:**
- Commands pass the `model` parameter to the `Task` tool — this is the **only reliable** way to set the agent's model
- If user specified model → use that (Priority 1)
- If downgrade check triggers → use sonnet (Priority 2, `/implement` only)
- Otherwise → use the agent's frontmatter `model` value (Priority 3) — but you must still pass it explicitly

**Reference — agent frontmatter models:**

| Model | Agents |
|-------|--------|
| `opus` | technical-product-manager, domain-expert, domain-modeller, designer, database-designer, api-designer, architect, agent-builder, skill-builder, meta-reviewer, content-reviewer, **all software-engineer-\***, **all implementation-planner-\***, **all code-reviewer-\*** |
| `sonnet` | unit-test-writer-*, observability-engineer, build-resolver-go, refactor-cleaner, doc-updater, tdd-guide, database-reviewer, freshness-auditor, consistency-checker |

**Agents with downgrade awareness** (opus default, may downgrade to sonnet for simple tasks):
- `software-engineer-go` / `software-engineer-python` / `software-engineer-frontend` — via `/implement` command auto-downgrade check

**Agents always on opus** (no downgrade):
- `code-reviewer-*` — via `/review` command (always opus)
- `implementation-planner-*` — via `/plan` command (always opus)

**Agents with escalation awareness** (sonnet default, escalate to opus via complexity check):
- `unit-test-writer-*` — via `/test` command

## Key Conventions

### Common Principles

- **No new dependencies** - Use stdlib and existing project dependencies
- **Follow existing patterns** - Consistency over "better" patterns
- **Comments explain WHY, not WHAT**
- **Backward compatibility** - Never break existing consumers

### Python Standards

- Type hints everywhere with `ruff format` formatting
- Pydantic for validation, dataclasses for simple data
- HTTP clients: Always use timeouts and retry logic
- Exceptions: Specific types, context preserved with `raise from`

### Go Standards

- Follow Effective Go and Go Code Review Comments
- Format with `goimports -local <module-name>` (NEVER `go fmt`)
- Errors: Wrap with context using `fmt.Errorf("...: %w", err)`
- Use `zerolog` for logging (injected, never global)
- Nil safety: Validate at constructor boundaries
- Use testify suites with `s.Require()` assertions

### Frontend Standards (TypeScript + React + Next.js)

- TypeScript strict mode — no `any`, no `as` assertions
- Server Components by default — `'use client'` only for interactivity
- Named exports always (except Next.js page/layout conventions)
- Function declarations for components (not arrow functions)
- Semantic HTML — `<button>`, `<nav>`, `<main>`, never `<div onClick>`
- Accessibility: WCAG 2.1 AA, `aria-label` on icon buttons, `alt` on images
- Format with Prettier, lint with ESLint
- State: URL params > Server Components > React Query > useState > Context
- No `useEffect` for derived state or data fetching
- Feature-based project organisation, kebab-case directories
