# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code configuration directory containing specialized agent prompts for software development workflows. The agents define language-specific coding standards, testing practices, and code review processes for Python and Go projects.

## Directory Structure

```
.claude/
├── settings.json          # Claude Code permissions and settings
├── agents/                # Specialized agent definitions
│   ├── software_engineer_*.md
│   ├── unit_tests_writer_*.md
│   ├── code_reviewer_*.md
│   ├── implementation_planner_*.md
│   └── technical_product_manager.md
├── commands/              # Workflow slash commands
│   ├── plan.md            # /plan - create implementation plan
│   ├── implement.md       # /implement - run SE agent
│   ├── test.md            # /test - run test writer agent
│   ├── review.md          # /review - run code reviewer agent
│   └── full-cycle.md      # /full-cycle - run complete pipeline
└── docs/                  # Analysis and decision documentation
```

## Workflow Commands

Use slash commands to run the development workflow:

| Command | Description | When to Use |
|---------|-------------|-------------|
| `/plan` | Create implementation plan from spec | Before implementation (complex tasks) |
| `/implement` | Run SE agent for current task | Start implementation |
| `/test` | Run test writer agent | After implementation |
| `/review` | Run code reviewer agent | After tests |
| `/full-cycle` | Run complete pipeline with pauses | Standard development |

Each command:
- Auto-detects project language (Go/Python)
- Pauses for user confirmation between steps
- Suggests next step after completion

### Workflow Modes

| Mode | How | Control Level |
|------|-----|---------------|
| **Guided** | Agent suggests next step, you confirm | Full control |
| **Pausable** | `/full-cycle` runs pipeline, pauses between agents | At checkpoints |
| **Manual** | Call agents directly by name | Maximum control |

## Agent Pipeline

Agents follow a typical development pipeline:

1. **technical_product_manager** - Transforms ideas into product specifications (writes to `docs/spec.md`, `docs/research.md`, `docs/decisions.md`)
2. **implementation_planner_*** - Creates detailed implementation plans from specs (writes to `docs/implementation_plans/<branch_name>.md`)
3. **software_engineer_*** - Writes production code following language-specific standards (reads plan if exists)
4. **unit_tests_writer_*** - Writes tests with a bug-hunting mindset
5. **code_reviewer_*** - Validates implementation against requirements, provides structured feedback

## Configuration

### Paths (Single Source of Truth)

| Path | Default | Purpose |
|------|---------|---------|
| `PLANS_DIR` | `docs/implementation_plans` | Implementation plans location |
| `SPEC_FILE` | `docs/spec.md` | Product specification |
| `RESEARCH_FILE` | `docs/research.md` | Research findings |
| `DECISIONS_FILE` | `docs/decisions.md` | Decision log |

All agents should use these configured paths rather than hardcoding.

## Key Conventions

### Task Identification
All planners and reviewers expect branch naming convention: `JIRAPRJ-123_name_of_the_branch`
- Task ID extracted from branch: `git branch --show-current | cut -d'_' -f1`
- Plans stored in: `{PLANS_DIR}/<branch_name>.md`

### Common Principles Across Agents
- **No new dependencies** - Use stdlib and existing project dependencies only
- **Follow existing patterns** - Consistency with codebase over "better" patterns
- **Comments explain WHY, not WHAT**
- **Backward compatibility** - Never break existing consumers; use 3-branch deprecation process

### Python Standards
- Type hints everywhere with `black` formatting
- Use Pydantic for validation, dataclasses for simple data containers
- HTTP clients: Always use timeouts `(connect, read)` and retry logic
- Exceptions: Specific types, context preserved with `raise from`

### Go Standards
- Follow Effective Go and Go Code Review Comments
- Format with `goimports -local <module-name>`
- Errors: Always wrap with context using `fmt.Errorf("...: %w", err)`
- Use `zerolog` for logging (injected, never global)
- Nil safety: Validate at constructor boundaries, trust internally (no nil receiver checks in methods)
- Use testify suites with `s.Require()` assertions

## Editing Agent Prompts

When modifying agent files:
- Preserve YAML frontmatter structure (`name`, `description`, `tools`, `model`)
- Keep code examples consistent with established patterns
- Maintain cross-references between related agents (e.g., planners reference engineer patterns)
