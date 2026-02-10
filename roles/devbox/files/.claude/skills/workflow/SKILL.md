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
│   ├── observability_engineer.md
│   ├── technical_product_manager.md
│   ├── agent_builder.md
│   └── skill_builder.md
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
│   ├── build-agent.md
│   ├── build-skill.md
│   └── validate-config.md
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
| `/build-agent` | Create, validate, or refine agent definitions | When adding/modifying agents |
| `/build-skill` | Create, validate, audit, or refine skill modules | When adding/modifying skills |
| `/validate-config` | Check cross-references, skill existence, frontmatter integrity | After config changes |

Each command:
- Auto-detects project language (Go/Python/Frontend)
- Pauses for user confirmation between steps
- Suggests next step after completion

## Pipeline Modes

| Mode | Trigger | Approval Model |
|------|---------|---------------|
| **Per-step** | Individual commands (`/implement`, `/test`, `/review`) | Approve after each agent |
| **Gated** | `/full-cycle` | 4 milestone gates, autonomous between |
| **Manual** | Call agents directly by name | Maximum control |

### Gated Mode — 4 Milestone Gates

| Gate | After | User Decides |
|------|-------|-------------|
| G1 | TPM + Domain Expert | "Is this the right problem?" |
| G2 | Designer options | "Which design direction?" (skipped for backend) |
| G3 | Design + API + Plan all ready | "Ready to implement?" |
| G4 | Code Review complete | "Ship it?" |

## Agent Pipeline

<pipeline>

### Step 1: Requirements
- **technical_product_manager** — Transforms ideas into product specifications
  Produces: `spec.md`, `spec_output.json`

### Step 2: Domain Validation
- **domain_expert** — Challenges assumptions, validates requirements
  Depends on: Step 1
  Produces: `domain_analysis.md`, `domain_output.json`

### Step 3: Planning + Design (parallel for UI features)
- **implementation_planner_*** — Creates detailed implementation plans
  Depends on: Step 2
  Produces: `plan.md`, `plan_output.json`
- **designer** — Creates UI/UX design specs, design tokens, component specifications
  Depends on: Step 2 (runs parallel with planner for UI features)
  Produces: `design.md`, `design_output.json`
  Skipped when: feature_type = backend

### Step 4: Contracts
- **api_designer** — Designs API contracts (REST/OpenAPI or Protobuf/gRPC)
  Depends on: Step 3
  Produces: `api_design.md`, `api_design_output.json`
- **database_designer** — Designs database schemas with migrations (PostgreSQL, MySQL, MongoDB, CockroachDB)
  Depends on: Step 3
  Produces: `schema_design.md`, migrations

### Step 5: Implementation
- **software_engineer_*** — Writes production code (Go, Python, or Frontend)
  Depends on: Step 4

### Step 6: Testing
- **unit_tests_writer_*** — Writes unit tests with bug-hunting mindset
  Depends on: Step 5
- **integration_tests_writer_*** — Writes integration tests with real dependencies
  Depends on: Step 5

### Step 7: Review
- **code_reviewer_*** — Validates implementation against requirements
  Depends on: Step 6
  If blocking issues found → return to Step 5 with feedback

### Independent
- **observability_engineer** — Designs dashboards, alerts, and recording rules (can run any time after Step 3)

</pipeline>

<transitions>
- After Step 2 completes → **Gate 1** (user approval: "right problem?")
- Steps 3a (Planner) and 3b (Designer) run in parallel for UI/fullstack features
- After Step 3 completes (Designer presents options) → **Gate 2** (user picks design direction; skipped for backend)
- After Step 4 completes → **Gate 3** (user approval: "ready to implement?")
- Steps 5 → 6 → 7 run autonomously with fix loop
- After Step 7 completes (no blocking issues) → **Gate 4** (user approval: "ship it?")
</transitions>

**Infrastructure agents** (outside the development pipeline):
- **agent_builder** — Creates, validates, and refines agent definitions
- **skill_builder** — Creates, validates, and refines skill modules

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
| Go tests | `unit-test-writer-go` | `/test` |
| Python tests | `unit-test-writer-python` | `/test` |

### Exceptions (Answer Directly)

- General programming concepts (not language-specific)
- Claude Code usage (features, settings)
- Clarifying user requirements
- Trivial typo fixes in comments/strings
- Configuration files (YAML, JSON, TOML)

## Configuration

See `config` skill for configurable paths.

Documentation is organized by Jira issue and branch:
`{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/`

- `spec.md` - Product specification
- `domain_analysis.md` - Domain analysis
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
| 1 (highest) | User explicit argument | `/implement opus` |
| 2 | Complexity check at command level | Plan >200 lines → opus |
| 3 | Agent frontmatter default | `model: sonnet` |

**How it works:**
- Commands (`/implement`, `/test`, `/review`) pass the `model` parameter to the `Task` tool
- The `Task` tool's `model` parameter **overrides** the agent frontmatter `model` field
- If no model is specified by command or user, the agent frontmatter default applies
- Agents invoked directly (not via commands) always use their frontmatter model

**Agents with complexity awareness:**
- `software-engineer-go` / `software-engineer-python` / `software-engineer-frontend` — via `/implement` command
- `observability-engineer` — self-assessed complexity check

## Key Conventions

### Common Principles

- **No new dependencies** - Use stdlib and existing project dependencies
- **Follow existing patterns** - Consistency over "better" patterns
- **Comments explain WHY, not WHAT**
- **Backward compatibility** - Never break existing consumers

### Python Standards

- Type hints everywhere with `black` formatting
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
