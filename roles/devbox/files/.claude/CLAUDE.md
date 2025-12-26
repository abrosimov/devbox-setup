# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code configuration directory containing specialized agent prompts for software development workflows. The agents define language-specific coding standards, testing practices, and code review processes for Python and Go projects.

## Directory Structure

```
.claude/
├── settings.json          # Claude Code permissions and settings
├── config.md              # Configurable paths (single source of truth)
├── agents/                # Specialized agent definitions
│   ├── software_engineer_*.md
│   ├── unit_tests_writer_*.md
│   ├── code_reviewer_*.md
│   ├── implementation_planner_*.md
│   ├── domain_expert.md
│   └── technical_product_manager.md
├── commands/              # Workflow slash commands
│   ├── domain-analysis.md # /domain-analysis - validate requirements
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
| `/domain-analysis` | Validate requirements, challenge assumptions | After spec, before planning |
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

1. **technical_product_manager** - Transforms ideas into product specifications (writes to `{PLANS_DIR}/{JIRA_ISSUE}/spec.md`, `research.md`, `decisions.md`)
2. **domain_expert** - Challenges assumptions, validates requirements against reality, creates domain models (writes to `{PLANS_DIR}/{JIRA_ISSUE}/domain_analysis.md`)
3. **implementation_planner_*** - Creates detailed implementation plans from validated specs (writes to `{PLANS_DIR}/{JIRA_ISSUE}/plan.md`)
4. **software_engineer_*** - Writes production code following language-specific standards (reads plan if exists)
5. **unit_tests_writer_*** - Writes tests with a bug-hunting mindset
6. **code_reviewer_*** - Validates implementation against requirements, provides structured feedback

## Code Writing & Language Discussion Policy

**Core Principle:** Specialized agents are the authoritative source for their languages.

### When to Use Language-Specific Agents

Use the appropriate software engineer agent for ANY language-specific topic:

| Situation | Examples | Agent |
|-----------|----------|-------|
| **Writing code** | Any code changes, even small fixes | `software-engineer-{lang}` |
| **Design discussions** | "When to use pointers vs values?", "How should I structure this?" | `software-engineer-{lang}` |
| **Idiom questions** | "What's the Go way to do X?", "Is this Pythonic?" | `software-engineer-{lang}` |
| **Architecture decisions** | "Where should this logic live?", "How to organize packages?" | `software-engineer-{lang}` |
| **Pattern selection** | "Which pattern fits?", "How to implement X idiomatically?" | `software-engineer-{lang}` |
| **Best practices** | "Should I use X or Y?", "What's the preferred approach?" | `software-engineer-{lang}` |

### Quick Reference

| Task | Agent | Command |
|------|-------|---------|
| **Any Go topic** (code, design, idioms) | `software-engineer-go` | `/implement` or direct call |
| **Any Python topic** (code, design, idioms) | `software-engineer-python` | `/implement` or direct call |
| Go tests | `unit-test-writer-go` | `/test` |
| Python tests | `unit-test-writer-python` | `/test` |

**Even for "quick questions"** — agents enforce standards and provide authoritative answers grounded in official style guides (Effective Go, PEP 8, etc.).

### Exceptions

Answer directly (don't use agent) ONLY for:
- **General programming concepts** (not language-specific)
- **Claude Code usage** (features, settings, configuration)
- **Clarifying user requirements** (understanding what they want)
- **Trivial typo fixes** in comments/strings
- **Configuration files** (YAML, JSON, TOML — not code)

### Why This Policy Matters

| Without Policy | With Policy |
|----------------|-------------|
| Inconsistent advice | Authoritative, style-guide-backed answers |
| General knowledge | Language-specific expertise |
| Potential suboptimal patterns | Enforced best practices |
| Ad-hoc responses | Systematic, comprehensive guidance |

## Configuration

See **[config.md](config.md)** for configurable paths (single source of truth).

All project documentation is organized by Jira issue under `{PLANS_DIR}/{JIRA_ISSUE}/`:
- `spec.md` - Product specification
- `domain_analysis.md` - Domain analysis (validated assumptions, constraints, domain model)
- `plan.md` - Implementation plan
- `research.md` - Research findings
- `decisions.md` - Decision log

## Key Conventions

### Task Identification
All planners and reviewers expect branch naming convention: `JIRAPRJ-123_name_of_the_branch`
- Jira issue extracted from branch: `git branch --show-current | cut -d'_' -f1`
- Project directory: `{PLANS_DIR}/{JIRA_ISSUE}/`

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
