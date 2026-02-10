---
name: skill-builder
description: >
  Reference templates, frontmatter schema, progressive disclosure patterns, and validation
  checklists for building skill modules in the Claude Code agent system.
  Triggers on: skill builder, create skill, new skill, skill template, skill structure,
  skill validation, skill frontmatter, knowledge module.
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
  When to use it — specific scenarios that trigger activation.
  Triggers on: keyword1, keyword2, keyword3.
---
```

### Field Rules

| Field | Format | Required | Notes |
|-------|--------|----------|-------|
| `name` | kebab-case | Yes | Must match directory name |
| `description` | Multi-line prose | Yes | Primary discovery mechanism — invest heavily here |
| `alwaysApply` | `true` | Rare | Skill always loaded. Only for foundational skills (currently: `philosophy`) |
| `allowed-tools` | Comma-separated | Rare | Restricts which tools the skill references |

---

## Structure Templates

### Minimal (most skills)

```
skill-name/
  SKILL.md              # Everything in one file (<500 lines)
```

Best for: Focused domains with moderate content. Examples: `go-errors`, `python-style`, `security-patterns`.

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

### Good Descriptions (specific, actionable)

```yaml
# Pattern: [Domain] [Specifics]. [When to use]. Triggers on: [keywords].
description: >
  Go error handling patterns including sentinel errors, custom error types,
  error wrapping with fmt.Errorf, and error classification at boundaries.
  Use when discussing error handling, error types, or error propagation in Go.
  Triggers on: error handling, sentinel errors, custom error types, error wrapping,
  stack traces, error classification.
```

```yaml
description: >
  REST API and OpenAPI 3.1 design knowledge. Covers resource naming, HTTP method
  semantics, error formats (RFC 9457), pagination, filtering, versioning,
  authentication, and Spectral linting.
  Triggers on: REST, OpenAPI, API design, endpoint, HTTP method, pagination, versioning.
```

### Bad Descriptions (avoid)

```yaml
# Too vague — Claude can't distinguish from other skills
description: Helps with errors.

# Wrong voice — should be third person
description: I can help you handle errors in your Go code.

# Missing triggers — Claude won't know when to activate
description: Go error handling patterns and best practices.

# Too broad — overlaps with multiple other skills
description: Everything about Go programming.
```

### Description Checklist

- [ ] Third-person voice ("Covers..." not "I help..." or "You should...")
- [ ] Specific domain (not generic)
- [ ] Includes both WHAT and WHEN
- [ ] `Triggers on:` keyword list present
- [ ] Keywords match how users naturally describe the domain
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
| `{language}-{domain}` | `go-errors`, `python-patterns`, `frontend-architecture` | Language-specific knowledge |
| `{domain}` | `security-patterns`, `observability`, `config` | Language-agnostic knowledge |
| `{domain}-{subdomain}` | `api-design-rest`, `api-design-proto` | Domains with distinct sub-types |
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
> For error handling patterns, see `go-errors` skill.

# In SKILL.md — BAD (duplication)
## Error Handling
[Copy of content that also exists in go-errors]
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
✅ See `go-errors` skill for error handling patterns.
❌ See `skills/go-errors/SKILL.md` for error handling patterns.
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
| Missing `Triggers on:` | Claude relies on fuzzy matching instead of keywords | Add explicit keyword list |
| Duplicated content | Token waste + risk of contradicting versions | Keep content in ONE skill, reference from others |
| SKILL.md too long | Wastes tokens for common use cases | Move detailed sub-topics to `references/` |
| Name doesn't match directory | Validation warnings, discovery confusion | Align name field with directory name |
| American English | Inconsistent with system standard | Use British English throughout |
| No TOC for long files | Claude can't see full scope when previewing | Add table of contents for files >100 lines |
| Generic examples | Don't demonstrate the skill's specific patterns | Use domain-specific examples that show the "right way" |
