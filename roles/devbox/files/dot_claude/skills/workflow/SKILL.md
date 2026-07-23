---
name: workflow
description: >
  Agent pipeline, workflow commands, and development modes for the Claude Code agent system.
  Covers slash commands, agent roles, language discussion policy, and key conventions.
  Use when determining which agent or command to use, understanding the pipeline flow,
  or looking up workflow conventions like model selection and agent routing.
problem: "Slash-command routing, agent selection, and model policy fragment without a single reference for the pipeline."
related: [config, agent-communication]
---

# Workflow Reference

This document describes the agent pipeline and workflow commands for projects using the Claude Code agent system.

## Agent Pipeline (Always On)

The agent pipeline is enforced globally for every project. Any change to source code (`.go`, `.py`, `.ts`, `.tsx`, ...) MUST go through the appropriate specialist agent via `/techne-*` commands — direct `Edit`/`Write` on code files is not allowed. See `USER_AUTHORITY_PROTOCOL.md` for the authoritative rule.

The user commits manually after each agent run; commands do not auto-commit.

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
│   ├── code_reviewer.md            # polyglot: Go, Python, Frontend
│   ├── implementation_planner.md   # stack-agnostic (Go/Python/frontend)
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
├── commands/              # Workflow slash commands (all techne- prefixed)
│   ├── techne-api-design.md
│   ├── techne-audit.md
│   ├── techne-build-agent.md
│   ├── techne-build-skill.md
│   ├── techne-decision.md
│   ├── techne-design.md
│   ├── techne-devcontainer.md
│   ├── techne-domain-analysis.md
│   ├── techne-focus.md
│   ├── techne-guide.md
│   ├── techne-implement.md
│   ├── techne-learn.md
│   ├── techne-log.md
│   ├── techne-next.md
│   ├── techne-options.md
│   ├── techne-plan.md
│   ├── techne-review.md
│   ├── techne-schema.md
│   ├── techne-test.md
│   ├── techne-think.md
│   ├── techne-validate-config.md
│   └── techne-verify.md
├── skills/                # Reusable knowledge modules
└── docs/                  # Historical reference documentation
```

## Workflow Commands

| Command | Description | When to Use |
|---------|-------------|-------------|
| `/techne-domain-analysis` | Validate requirements, challenge assumptions | After spec, before planning |
| `/techne-plan` | Create implementation plan from spec | Before implementation (complex tasks) |
| `/techne-api-design` | Design API contracts (REST/OpenAPI or Protobuf/gRPC) | After planning, before backend implementation |
| `/techne-schema` | Design database schema with migrations | After planning, before/alongside backend implementation |
| `/techne-design` | Create UI/UX design spec and design tokens | After spec/domain analysis, before frontend implementation |
| `/techne-implement` | Run SE agent for current task | Start implementation |
| `/techne-test` | Run test writer agent | After implementation |
| `/techne-review` | Run code reviewer agent | After tests |
| `/techne-build-agent` | Create/validate/refine agents (2-gate pipeline with meta-review) | When adding/modifying agents |
| `/techne-build-skill` | Create/validate/audit/refine skills (2-gate pipeline with meta-review) | When adding/modifying skills |
| `/techne-audit` | Run library-wide freshness and/or consistency audit | After adding agents/skills, periodic maintenance |
| `/techne-validate-config` | Check cross-references, skill existence, frontmatter integrity | After config changes |
| `/techne-verify` | Run pre-PR quality gate (build, typecheck, lint, test, debug scan) | Before `/techne-review` or PR creation |
| `/techne-options` | Generate diverse solution options via DSS (Diverge-Synthesize-Select) | Before design decisions with wide scope |
| `/techne-learn` | Extract a reusable pattern from current session | After solving non-trivial problems |

Each command:
- Auto-detects project stack (Go/Python/Frontend/Fullstack)
- Pauses for user confirmation between steps
- Suggests next step after completion
- For fullstack projects, routes to appropriate agent(s) based on work streams

## Invocation Modes

| Mode | Trigger | Approval Model |
|------|---------|---------------|
| **Per-step** | Individual commands (`/techne-implement`, `/techne-test`, `/techne-review`) | Approve after each agent |
| **Manual** | Call agents directly by name | Maximum control |

## Agent Roster

Specialist agents available via `/techne-*` commands. Each is invoked one-shot for its specific concern. See `agents/` for full definitions.

| Stage | Agent | Produces |
|-------|-------|----------|
| Requirements | `technical_product_manager` | `spec.md` |
| Domain validation | `domain_expert` | `domain_analysis.md` |
| Domain modelling | `domain_modeller` | `domain_model.md` |
| Planning | `implementation_planner` | `plan.md` |
| UI design | `designer` | `design.md` |
| Database design | `database_designer` | `schema_design.md`, migrations |
| API design | `api_designer` | `api_design.md`, `api_spec.yaml` |
| Implementation | `software_engineer_{go,python,frontend}` | source code, `se_{lang}_output.json` |
| Observability | `observability_engineer` | dashboards, alerts |
| Unit tests | `unit_tests_writer_{go,python,frontend}` | test files |
| Integration tests | `integration_tests_writer_{go,python}` | test files |
| Review | `code_reviewer` | review report (inline) |

Each stage runs independently via its `/techne-*` command. The user drives the flow by choosing which command to run next.

**Infrastructure agents** (outside the development pipeline):
- **agent_builder** — Creates, validates, and refines agent definitions
- **skill_builder** — Creates, validates, and refines skill modules
- **meta_reviewer** — Adversarial reviewer that challenges builder output against grounded Anthropic docs
- **content_reviewer** — Content substance reviewer that verifies code examples, versions, security, and redundancy
- **freshness_auditor** — Library-wide scanner for outdated versions, deprecated APIs, and best practice drift
- **consistency_checker** — Library-wide scanner for terminology conflicts, broken handoffs, and coverage gaps

**Additional agents** (support roles, invoked by commands or other agents as needed):
- **architect** — System and solution architecture design across stacks
- **build_resolver_go** — Diagnoses and fixes Go build/compile failures
- **database_reviewer** — Reviews schema designs and migrations for correctness and safety
- **doc_updater** — Updates documentation to reflect code and config changes
- **refactor_cleaner** — Performs focused refactoring and dead-code cleanup
- **tdd_guide** — Guides test-driven development flow (red-green-refactor)
- **focus_coach** — Frames and paces a task into micro-steps (drives `/techne-focus`)

### Meta-Pipeline (Infrastructure)

`/techne-build-agent` and `/techne-build-skill` use a 3-gate pipeline for create/refine modes:

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

`/techne-audit` runs library-wide checks across all agents and skills:

```
/techne-audit           → [Freshness Auditor ‖ Consistency Checker] → merged report
/techne-audit freshness → Freshness Auditor only
/techne-audit consistency → Consistency Checker only
/techne-audit fix       → [Freshness Auditor ‖ Consistency Checker] → route findings to builders
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
| **Any Go topic** | `software-engineer-go` | `/techne-implement` |
| **Any Python topic** | `software-engineer-python` | `/techne-implement` |
| **Any Frontend topic** (React, TypeScript, Next.js) | `software-engineer-frontend` | `/techne-implement` |
| **Fullstack feature** | Backend SE + Frontend SE (sequential or parallel) | `/techne-implement` |
| Unit tests (any stack) | `unit-test-writer` | `/techne-test` |

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
3. User commits manually after each agent phase (commands do not auto-commit; use `git-safe-commit` for branch-protection + secret detection)
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
| `.claude/bin/git-default-branch` | Detect project's default branch | Commands, `proj wt` |
| `.claude/bin/git_safe_commit.py` | Commit with branch protection + secret detection | Commands |
| `.claude/bin/git_safe_merge.py` | ff-only merge with dependency check (opt-in integration branch) | User (manual) |

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

For working on multiple tasks simultaneously, use git worktrees via `proj wt`:

```bash
proj wt add PROJ-123_backend                          # branch from default branch
proj wt add PROJ-123_frontend --from PROJ-123_backend  # chain from another branch
proj wt ls                                             # list worktrees
proj wt status                                         # show all with PR status
proj wt rm PROJ-123_backend                            # remove after merge
proj wt clean                                          # prune all merged worktrees
```

Directory layout: `$AION_AUTOPOIESEON/<project>/<branch-name>/` (sibling of `base/`)

Operate on a worktree from its own cwd (the Claude session is started there), or use `git -C <path>` / absolute paths. Never prepend `cd <path> &&` to a command — see *Shell discipline* in `CLAUDE.md`.

Each worktree gets its own Claude Code session. `proj wt add` automatically:
- Copies `.claude/settings.local.json` to the worktree
- Symlinks `.claude/memory/` for shared downstream knowledge
- Creates the branch from the default branch (or specified base via `--from`)
- Tracks existing remote branches when available

The `WorktreeCreate` hook in `hooks.json` delegates to `proj wt`, so `claude --worktree <name>` also follows this layout.

### Parallel Workflow Example

```
Terminal 1:                          Terminal 2:
proj wt add PROJ-123_backend        proj wt add PROJ-123_frontend
claude --cwd $AION_AUTOPOIESEON/p/... claude --cwd $AION_AUTOPOIESEON/p/...
> /techne-implement backend API              > /techne-implement frontend dashboard
> /techne-test                               > /techne-test
> /techne-review → 'pr'                      > /techne-review → 'pr'
proj wt rm PROJ-123_backend          proj wt rm PROJ-123_frontend
```

## Configuration

See `config` skill for configurable paths.

Documentation is organized by Jira issue and branch:
`{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/`

- `spec.md` - Product specification
- `domain_analysis.md` - Domain analysis
- `domain_model.md` - DDD domain model (bounded contexts, aggregates, invariants)
- `plan.md` - Implementation plan
- `api_design.md` - API design rationale and decisions
- `api_spec.yaml` - OpenAPI specification (REST mode)
- `schema_design.md` - Database schema design rationale
- `migrations/` - Database migration files
- `design.md` - UI/UX design specification
- `design_system.tokens.json` - W3C Design Tokens
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
| 1 (highest) | User explicit argument | `/techne-implement sonnet`, `/techne-implement opus` |
| 2 | Agent frontmatter default | See table below |

**Default model philosophy**: Opus is the default for SE agents. Use `/techne-implement sonnet` for cost-sensitive tasks where quality trade-off is acceptable (Sonnet 4.6: 79.6% SWE-bench vs Opus 80.8%).

**CRITICAL — `model` must be passed explicitly:**
- The Task tool **inherits the parent conversation's model** when no `model` parameter is given
- Agent frontmatter `model` field defines the agent's **intended** model but does NOT override inheritance
- Therefore, every command MUST pass `model` explicitly in the Task invocation
- Without explicit `model`, an agent with `model: opus` in frontmatter will run on the parent's model

**How it works:**
- Commands pass the `model` parameter to the `Task` tool — this is the **only reliable** way to set the agent's model
- If user specified model → use that (Priority 1)
- Otherwise → use the agent's frontmatter `model` value (Priority 2) — but you must still pass it explicitly

**Reference — agent frontmatter models:**

| Model | Agents |
|-------|--------|
| `opus` | technical-product-manager, domain-expert, domain-modeller, designer, database-designer, api-designer, architect, agent-builder, skill-builder, meta-reviewer, content-reviewer, code-reviewer, **implementation-planner**, **all software-engineer-\*** |
| `sonnet` | unit-test-writer-*, observability-engineer, build-resolver-go, refactor-cleaner, doc-updater, tdd-guide, database-reviewer, freshness-auditor, consistency-checker |
| `haiku` | Search, grep, file discovery tasks (via `model: "haiku"` in Task tool) |

**Effort parameter guidance** (pass via `max_turns` or prompt hint):

| Model | Effort | Use When |
|-------|--------|----------|
| haiku | low | Search, grep, file discovery tasks |
| sonnet | medium | Test writing, utility agents, cost-sensitive SE tasks |
| opus | high | SE implementation, planners, reviewers |

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
