# Anthropic Skill Authoring Reference

Cached reference from official Anthropic documentation (February 2026).
Source: https://code.claude.com/docs/en/skills

## SKILL.md Structure

Two required parts:
1. YAML frontmatter (between `---` markers)
2. Markdown content with instructions

## Directory Structure

```
my-skill/
├── SKILL.md           # Main instructions (required)
├── template.md        # Template for Claude to fill in
├── examples/
│   └── sample.md      # Example output showing expected format
└── scripts/
    └── helper.py      # Script Claude can execute
```

## Frontmatter Schema — All Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | No | Display name. If omitted, uses directory name. Lowercase letters, numbers, hyphens (max 64 chars) |
| `description` | Recommended | What the skill does and when to use it. Claude uses this to decide when to apply |
| `argument-hint` | No | Hint shown during autocomplete for expected arguments. Example: `[issue-number]` |
| `disable-model-invocation` | No | `true` prevents Claude from auto-loading. For manual workflows. Default: `false` |
| `user-invocable` | No | `false` hides from `/` menu. For background knowledge. Default: `true` |
| `allowed-tools` | No | Tools Claude can use without asking permission when this skill is active |
| `model` | No | Model to use when this skill is active |
| `context` | No | Set to `fork` to run in a forked subagent context |
| `agent` | No | Which subagent type to use when `context: fork` |
| `hooks` | No | Hooks scoped to this skill's lifecycle |

### Fields NOT in Our System (verify if needed)

- `argument-hint` — autocomplete hints (we don't currently use)
- `disable-model-invocation` — prevent auto-loading (we rely on description quality)
- `context: fork` — fork to subagent (we use the agent `skills` field instead)
- `agent` — subagent type for forked context
- `hooks` — skill-scoped hooks
- `model` — skill-level model override

## Invocation Control Matrix

| Frontmatter | User can invoke | Claude can invoke | Loading |
|-------------|----------------|-------------------|---------|
| (default) | Yes | Yes | Description always in context; full skill on invocation |
| `disable-model-invocation: true` | Yes | No | Description NOT in context; full loads when user invokes |
| `user-invocable: false` | No | Yes | Description always in context; full loads when invoked |

Our system primarily uses the default mode (both user and Claude can invoke).
Exception: `philosophy` uses `alwaysApply: true` (always fully loaded).

## String Substitutions

- **`$ARGUMENTS`** — all arguments passed when invoking
- **`$ARGUMENTS[N]`** — specific argument by 0-based index
- **`$N`** — shorthand for `$ARGUMENTS[N]`
- **`${CLAUDE_SESSION_ID}`** — current session ID

## Dynamic Context Injection

**Syntax**: `` !`command` ``

The command executes BEFORE skill content is sent to Claude. Output replaces the placeholder.

```yaml
---
name: pr-summary
description: Summarise changes in a pull request
context: fork
agent: Explore
---

## Pull request context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`

## Your task
Summarise this pull request...
```

This enables skills that inject live data (git status, file listings, API responses) at activation time.

## Context Fork Pattern

Skills can run in a forked subagent context (`context: fork`):

| Approach | System prompt | Task | Also loads |
|----------|--------------|------|------------|
| Skill with `context: fork` | From agent type | SKILL.md content | CLAUDE.md |
| Subagent with `skills` | Subagent's markdown body | Claude's delegation message | Preloaded skills + CLAUDE.md |

**Key difference**:
- `context: fork` — you write the task in SKILL.md, pick an agent type to execute
- Subagent `skills` — you define custom subagent, skills are reference material

## Progressive Disclosure (Anthropic's Model)

### Three Tiers

| Tier | What | When Loaded |
|------|------|-------------|
| Description | `name` + `description` in frontmatter | Always (at startup) |
| Core detail | SKILL.md body | When skill is activated |
| Granular | Supporting files (`references/`, `scripts/`, `examples/`) | When Claude needs specific detail |

### Description is the Discovery Mechanism

Claude reads ALL skill descriptions at startup. This is the PRIMARY trigger for whether a skill gets loaded. Invest heavily in description quality.

### Supporting Files Are Lazy-Loaded

Reference them from SKILL.md so Claude knows they exist. Claude loads them only when needed. This saves context window tokens.

## Validation Checklist (from Anthropic guidance)

- [ ] `name` is lowercase, hyphenated, max 64 characters
- [ ] `description` clearly states WHAT and WHEN (not just what)
- [ ] SKILL.md is the complete instruction set (Claude receives nothing else unless it reads supporting files)
- [ ] Supporting files are referenced from SKILL.md
- [ ] SKILL.md under 500 lines (move detail to references/)
- [ ] Description uses third-person voice ("Covers..." not "I help...")
- [ ] Trigger keywords match how users naturally describe the domain
- [ ] No duplicated content across skills
