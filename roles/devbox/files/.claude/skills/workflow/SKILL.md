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
│   ├── code_reviewer_*.md
│   ├── implementation_planner_*.md
│   ├── api_designer.md
│   ├── designer.md
│   ├── domain_expert.md
│   └── technical_product_manager.md
├── commands/              # Workflow slash commands
│   ├── domain-analysis.md
│   ├── plan.md
│   ├── api-design.md
│   ├── design.md
│   ├── implement.md
│   ├── test.md
│   ├── review.md
│   └── full-cycle.md
├── skills/                # Reusable knowledge modules
└── docs/                  # Historical reference documentation
```

## Workflow Commands

| Command | Description | When to Use |
|---------|-------------|-------------|
| `/domain-analysis` | Validate requirements, challenge assumptions | After spec, before planning |
| `/plan` | Create implementation plan from spec | Before implementation (complex tasks) |
| `/api-design` | Design API contracts (REST/OpenAPI or Protobuf/gRPC) | After planning, before backend implementation |
| `/design` | Create UI/UX design spec and design tokens | After planning, before frontend implementation |
| `/implement` | Run SE agent for current task | Start implementation |
| `/test` | Run test writer agent | After implementation |
| `/review` | Run code reviewer agent | After tests |
| `/full-cycle` | Run complete pipeline with pauses | Standard development |

Each command:
- Auto-detects project language (Go/Python)
- Pauses for user confirmation between steps
- Suggests next step after completion

## Workflow Modes

| Mode | How | Control Level |
|------|-----|---------------|
| **Guided** | Agent suggests next step, you confirm | Full control |
| **Pausable** | `/full-cycle` runs pipeline, pauses between agents | At checkpoints |
| **Manual** | Call agents directly by name | Maximum control |

## Agent Pipeline

```
technical_product_manager → domain_expert → implementation_planner
                                                    ↓
                                    ┌───────────────┼───────────────┐
                                    ↓               ↓               ↓
                              api_designer    designer (UI/UX)      │
                                    ↓               ↓               │
                                    └───────┬───────┘               │
                                            ↓                       ↓
                            code_reviewer ← unit_tests_writer ← software_engineer
```

1. **technical_product_manager** - Transforms ideas into product specifications
2. **domain_expert** - Challenges assumptions, validates requirements
3. **implementation_planner_*** - Creates detailed implementation plans
4. **api_designer** - Designs API contracts (REST/OpenAPI or Protobuf/gRPC)
5. **designer** - Creates UI/UX design specs, design tokens, component specifications
6. **software_engineer_*** - Writes production code
7. **unit_tests_writer_*** - Writes tests with bug-hunting mindset
8. **code_reviewer_*** - Validates implementation against requirements

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
- `design.md` - UI/UX design specification
- `design_system.tokens.json` - W3C Design Tokens
- `research.md` - Research findings
- `decisions.md` - Decision log

## Task Identification

Branch naming convention: `JIRAPRJ-123_name_of_the_branch`

- `JIRA_ISSUE`: `git branch --show-current | cut -d'_' -f1`
- `BRANCH_NAME`: `git branch --show-current | cut -d'_' -f2-`

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
