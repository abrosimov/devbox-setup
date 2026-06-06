---
name: skill-builder
description: >
  Reference templates, frontmatter schema, progressive disclosure patterns, and validation
  checklists for building skill modules in the Claude Code agent system. Use when creating
  a new skill, validating skill structure, or improving skill descriptions. Also use when
  working with SKILL.md files, skill frontmatter, or knowledge modules.
---

# Skill Builder Reference

Quick reference for creating and validating skill modules. Covers structure, description patterns, and quality standards.

## Table of Contents

- [Frontmatter Schema](#frontmatter-schema)
- [Structure Templates](#structure-templates)
- [Description Patterns](#description-patterns)
- [Progressive Disclosure Guide](#progressive-disclosure-guide)
- [Naming Conventions](#naming-conventions)
- [Cross-Reference Rules](#cross-reference-rules)
- [Common Mistakes](#common-mistakes)

---

## Grounding References

Cached Anthropic documentation for authoritative guidance:

| Reference | Contents | When to Read |
|-----------|----------|--------------|
| `references/anthropic-skill-authoring.md` | Official SKILL.md format, frontmatter schema, invocation control, dynamic context injection, progressive disclosure | Before creating or validating any skill |

Read this reference at the START of any build/validate/refine workflow to ground your work in Anthropic's actual specifications.

---

## Frontmatter Schema

```yaml
---
name: skill-name
description: >
  What this skill covers — one or two sentences describing the domain.
  Use when [specific scenarios]. Also use when [broader triggers] — even
  for seemingly simple tasks, as this skill enforces [value proposition].
---
```

### Field Rules (Official Frontmatter)

| Field | Format | Required | Notes |
|-------|--------|----------|-------|
| `name` | kebab-case | Yes | Max 64 chars. Must not contain "anthropic" or "claude". Must match directory name |
| `description` | Multi-line prose | Yes | Max 1024 chars. Primary discovery mechanism — invest heavily here |
| `argument-hint` | String | No | Hint shown during autocomplete, e.g. `[issue-number]` |
| `disable-model-invocation` | `true` | No | Prevents Claude from auto-loading. For manual-only workflows |
| `user-invocable` | `false` | No | Hides from `/` menu. For background knowledge only |
| `allowed-tools` | Comma-separated | No | Tools Claude can use without permission when skill is active |
| `model` | String | No | Model override when skill is active |
| `context` | `fork` | No | Run in a forked subagent context |
| `agent` | String | No | Subagent type when `context: fork` is set |
| `hooks` | Object | No | Hooks scoped to this skill's lifecycle |

### Custom Extensions (Project-Specific)

These fields are NOT processed by Claude Code — they are used by our eval/validation framework only:

| Field | Format | Notes |
|-------|--------|-------|
| `alwaysApply` | `true` | Used by our system to mark always-loaded skills. Not an official field |
| `triggers` | List | Used by `validate-skill-evals` for trigger evaluation. Not an official field |
| `version` | Number | Used by our validation scripts. Not an official field |

---

## Structure Templates

### Minimal (most skills)

```
skill-name/
  SKILL.md              # Everything in one file (<500 lines)
```

Best for: Focused domains with moderate content. Examples: `go-engineer`, `python-tooling`, `config`.

### With References (large domains)

```
skill-name/
  SKILL.md              # Core patterns, quick reference (<500 lines)
  references/
    topic-a.md          # Deep dive loaded only when needed
    topic-b.md          # Deep dive loaded only when needed
```

Best for: Domains with detailed sub-topics. Keep SKILL.md as the "80% case" reference; put deep dives in references.

### With Scripts (automation)

```
skill-name/
  SKILL.md              # Instructions and context
  scripts/
    action.sh           # Deterministic, repeatable operations
```

Best for: Skills that involve executable operations (validation, setup, extraction).

---

## Description Patterns

Claude tends to "undertrigger" skills — not using them when they'd be useful. To combat this, make descriptions assertive and include broad trigger conditions.

### Good Descriptions (specific, assertive)

```yaml
# Pattern: [What it does]. Use when [specific]. Also use when [broader] — [value justification].
description: >
  Go error handling patterns including sentinel errors, custom error types,
  error wrapping with fmt.Errorf, and error classification at boundaries.
  Use when implementing or reviewing error handling in Go. Also use when the
  user mentions error types, error propagation, or stack traces — even for
  simple error checks, as this skill enforces project error-handling conventions.
```

```yaml
description: >
  Extract text and tables from PDF files, fill forms, merge documents.
  Use when working with PDF files or when the user mentions PDFs, forms,
  or document extraction.
```

```yaml
description: >
  REST API and OpenAPI 3.1 design knowledge. Covers resource naming, HTTP method
  semantics, error formats (RFC 9457), pagination, filtering, versioning,
  authentication, and Spectral linting. Use when designing API endpoints, reviewing
  API contracts, or when the user mentions REST, OpenAPI, pagination, or versioning.
```

### Bad Descriptions (avoid)

```yaml
# Too vague — Claude can't distinguish from other skills
description: Helps with errors.

# Wrong voice — should be third person
description: I can help you handle errors in your Go code.

# Missing "when to use" — Claude won't know when to activate
description: Go error handling patterns and best practices.

# Too broad — overlaps with multiple other skills
description: Everything about Go programming.

# Not assertive enough — Claude will skip it for simple tasks
description: Go error handling patterns. Use for complex error scenarios.
```

### Description Checklist

- [ ] Third-person voice ("Covers..." not "I help..." or "You should...")
- [ ] Specific domain (not generic)
- [ ] Includes both WHAT and WHEN ("Use when...")
- [ ] Assertive — includes broader triggers ("Also use when...")
- [ ] Justifies activation ("as this skill enforces..." or "to ensure...")
- [ ] Keywords match how users naturally describe the domain
- [ ] Under 1024 characters
- [ ] Distinguishable from related skills' descriptions

---

## Progressive Disclosure Guide

### What Goes in SKILL.md (Core)

Content Claude needs **most of the time** when this skill is activated:

- Core patterns and conventions
- Quick-reference tables
- Decision trees ("When to use X vs Y")
- Common mistakes to avoid
- Brief examples (3-5 lines each)

### What Goes in references/ (Granular)

Content Claude needs **only for specific sub-scenarios**:

- Detailed API reference
- Comprehensive example collections
- Migration guides
- Historical context ("why we chose X over Y")
- Full specification excerpts

### The 80/20 Rule

SKILL.md should cover 80% of use cases. The remaining 20% goes in references. If SKILL.md tries to cover 100%, it wastes tokens for the 80% case.

---

## Naming Conventions

| Pattern | Examples | When to Use |
|---------|----------|-------------|
| `{language}-{domain}` | `go-engineer`, `go-testing`, `frontend-engineer` | Language-specific knowledge |
| `{domain}` | `structured-output`, `agent-communication`, `config` | Language-agnostic knowledge |
| `{domain}-{subdomain}` | `go-review-checklist`, `agent-base-protocol` | Domains with distinct sub-types |
| `{action}-{target}` (gerund) | `agent-builder`, `skill-builder` | Action-oriented skills |

### Avoid These Names

- `helper`, `utils`, `tools` — too generic, not discoverable
- `misc`, `other`, `general` — not a domain, just a dumping ground
- `new-*`, `old-*`, `v2-*` — version in content, not in name

---

## Cross-Reference Rules

### Rule 1: Information Lives in ONE Place

If content exists in Skill A, Skill B should reference it, not duplicate it.

```markdown
# In SKILL.md — GOOD (reference)
> For testing patterns, see `go-testing` skill.

# In SKILL.md — BAD (duplication)
## Testing Patterns
[Copy of content that also exists in go-testing]
```

### Rule 2: References Are One Level Deep

SKILL.md can reference files in its own `references/` directory. Those reference files should NOT reference further sub-files.

```
SKILL.md → references/topic.md     ✅ One level
SKILL.md → references/topic.md → references/sub-topic.md   ❌ Too deep
```

### Rule 3: Cross-Skill References Use Skill Names

When referencing another skill, use its `name` field, not its directory path:

```markdown
✅ See `go-testing` skill for testing patterns.
❌ See `skills/go-testing/SKILL.md` for testing patterns.
```

---

## Evaluation Scenarios Template

Before writing a skill, define test scenarios:

```markdown
## Evaluation Scenarios

### Scenario 1: [Common use case]
- **Agent**: [Which agent would use this]
- **Query**: "[What triggers this skill]"
- **Expected**: [What the skill should enable]

### Scenario 2: [Edge case]
- **Agent**: [Which agent]
- **Query**: "[Tricky scenario]"
- **Expected**: [Correct handling]

### Scenario 3: [Out-of-scope test]
- **Agent**: [Which agent]
- **Query**: "[Adjacent but out of scope]"
- **Expected**: [Skill does NOT activate or defers to correct skill]
```

---

## Common Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| Vague description | Skill activates at wrong times or not at all | Rewrite with specific domain, triggers, and when-to-use |
| No "Use when..." clause | Claude can't determine when to activate | Add assertive trigger conditions with keywords |
| Duplicated content | Token waste + risk of contradicting versions | Keep content in ONE skill, reference from others |
| SKILL.md too long | Wastes tokens for common use cases | Move detailed sub-topics to `references/` |
| Name doesn't match directory | Validation warnings, discovery confusion | Align name field with directory name |
| American English | Inconsistent with system standard | Use British English throughout |
| No TOC for long files | Claude can't see full scope when previewing | Add table of contents for files >100 lines |
| Generic examples | Don't demonstrate the skill's specific patterns | Use domain-specific examples that show the "right way" |
