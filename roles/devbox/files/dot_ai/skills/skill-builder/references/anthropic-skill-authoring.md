# Anthropic Skill Authoring Reference

Cached reference from official Anthropic documentation (March 2026).
Sources: https://code.claude.com/docs/en/skills, https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices

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

## Frontmatter Schema — All Official Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | No | Display name. If omitted, uses directory name. Lowercase letters, numbers, hyphens only. Max 64 chars. Cannot contain "anthropic" or "claude". Cannot contain XML tags |
| `description` | Recommended | What the skill does and when to use it. Max 1024 chars. Cannot contain XML tags. Claude uses this to decide when to apply the skill |
| `argument-hint` | No | Hint shown during autocomplete for expected arguments. Example: `[issue-number]` or `[filename] [format]` |
| `disable-model-invocation` | No | `true` prevents Claude from auto-loading. For manual workflows. Default: `false` |
| `user-invocable` | No | `false` hides from `/` menu. For background knowledge. Default: `true` |
| `allowed-tools` | No | Tools Claude can use without asking permission when this skill is active |
| `model` | No | Model to use when this skill is active |
| `context` | No | Set to `fork` to run in a forked subagent context |
| `agent` | No | Which subagent type to use when `context: fork` |
| `hooks` | No | Hooks scoped to this skill's lifecycle |

## Invocation Control Matrix

| Frontmatter | User can invoke | Claude can invoke | Loading |
|-------------|----------------|-------------------|---------|
| (default) | Yes | Yes | Description always in context; full skill on invocation |
| `disable-model-invocation: true` | Yes | No | Description NOT in context; full loads when user invokes |
| `user-invocable: false` | No | Yes | Description always in context; full loads when invoked |

Setting `disable-model-invocation: true` reduces context cost to zero — the skill is hidden from Claude entirely until manually invoked.

## String Substitutions

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments passed when invoking the skill |
| `$ARGUMENTS[N]` | Specific argument by 0-based index |
| `$N` | Shorthand for `$ARGUMENTS[N]` |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `${CLAUDE_SKILL_DIR}` | Directory containing the skill's SKILL.md file |

## Dynamic Context Injection

**Syntax**: `` !`command` ``

The command executes BEFORE skill content is sent to Claude. Output replaces the placeholder. This is preprocessing — Claude only sees the final result.

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
| Description | `name` + `description` in frontmatter (~100 tokens per skill) | Always (at startup) |
| Core detail | SKILL.md body | When skill is activated |
| Granular | Supporting files (`references/`, `scripts/`, `examples/`) | When Claude needs specific detail |

### Description is the Discovery Mechanism

Claude reads ALL skill descriptions at startup. This is the PRIMARY trigger for whether a skill gets loaded. Invest heavily in description quality.

### Context Budget

Skill descriptions share a character budget that scales at 2% of the context window, with a fallback of 16,000 characters. If you have many skills, some may be excluded. Override with `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable.

### Supporting Files Are Lazy-Loaded

Reference them from SKILL.md so Claude knows they exist. Claude loads them only when needed. Keep references one level deep — avoid deeply nested file references.

## Writing Effective Descriptions

### Undertriggering

Claude tends to "undertrigger" skills — not using them when they'd be useful. To combat this, make descriptions assertive ("pushy" in Anthropic's own words).

### Description Best Practices

1. **Write in third person**: "Processes Excel files" not "I can help you process" or "You can use this to process"
2. **Include both WHAT and WHEN**: State what the skill does and when Claude should use it
3. **Be assertive with triggers**: Include broad trigger conditions. Use "Also use when..." and "even for seemingly simple tasks"
4. **Include keywords users would naturally say**: Not just technical terms but natural language variations
5. **Justify activation**: Explain why Claude should use this skill ("as this skill enforces project conventions")

### Effective Description Examples

```yaml
# PDF Processing
description: >
  Extract text and tables from PDF files, fill forms, merge documents.
  Use when working with PDF files or when the user mentions PDFs, forms,
  or document extraction.

# Excel Analysis
description: >
  Analyse Excel spreadsheets, create pivot tables, generate charts.
  Use when analysing Excel files, spreadsheets, tabular data, or .xlsx files.

# Git Commit Helper
description: >
  Generate descriptive commit messages by analysing git diffs. Use when the
  user asks for help writing commit messages or reviewing staged changes.
```

### Bad Description Examples

```yaml
# Too vague
description: Helps with documents

# Too passive — won't trigger for simple tasks
description: Advanced PDF processing for complex multi-page documents

# Wrong voice
description: I can help you process Excel files
```

### Iterating on Descriptions

- If the skill triggers when it shouldn't — narrow the description
- If it doesn't trigger when it should — broaden the description
- Claude only consults skills for tasks it can't easily handle on its own — simple one-step queries may not trigger even with a matching description

## Troubleshooting

### Skill Not Triggering

1. Check the description includes keywords users would naturally say
2. Verify the skill appears when asking "What skills are available?"
3. Try rephrasing the request to match the description more closely
4. Invoke it directly with `/skill-name` if user-invocable
5. Make the description more assertive ("Also use when...", "even for...")

### Skill Triggers Too Often

1. Make the description more specific
2. Add `disable-model-invocation: true` for manual-only invocation

### Claude Doesn't See All Skills

Context budget exceeded. Run `/context` to check for warnings about excluded skills. Set `SLASH_COMMAND_TOOL_CHAR_BUDGET` to override.

## Validation Checklist (from Anthropic guidance)

- [ ] `name` is lowercase, hyphenated, max 64 characters, no reserved words
- [ ] `description` clearly states WHAT and WHEN (not just what)
- [ ] `description` is assertive enough to combat undertriggering
- [ ] `description` is under 1024 characters
- [ ] `description` uses third-person voice ("Covers..." not "I help...")
- [ ] Keywords match how users naturally describe the domain
- [ ] SKILL.md is the complete instruction set (Claude receives nothing else unless it reads supporting files)
- [ ] Supporting files are referenced from SKILL.md
- [ ] SKILL.md under 500 lines (move detail to references/)
- [ ] References are one level deep from SKILL.md
- [ ] No duplicated content across skills
- [ ] Files >100 lines have a table of contents at the top
