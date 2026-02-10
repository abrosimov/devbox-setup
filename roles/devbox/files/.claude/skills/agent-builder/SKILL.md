---
name: agent-builder
description: >
  Reference templates, frontmatter schema, archetype patterns, and validation checklists
  for building agent definitions in the Claude Code agent system.
  Triggers on: agent builder, create agent, new agent, agent template, agent archetype,
  agent validation, agent frontmatter.
---

# Agent Builder Reference

Quick reference for creating and validating agent definitions. See individual archetypes for detailed section templates.

## Table of Contents

- [Frontmatter Schema](#frontmatter-schema)
- [Archetype Quick Reference](#archetype-quick-reference)
- [Mandatory Sections — All Agents](#mandatory-sections--all-agents)
- [Additional Sections — Code-Writing Agents](#additional-sections--code-writing-agents)
- [Pipeline Integration Checklist](#pipeline-integration-checklist)
- [Common Mistakes](#common-mistakes)

---

## Grounding References

Cached Anthropic documentation for authoritative guidance:

| Reference | Contents | When to Read |
|-----------|----------|--------------|
| `references/anthropic-agent-authoring.md` | Official frontmatter schema, scopes, tool patterns, memory, context isolation | Before creating or validating any agent |
| `references/anthropic-prompt-engineering.md` | XML tags, CoT, system prompts, multishot, clear/direct prompting | Before writing agent body (system prompt) |

Read these references at the START of any build/validate/refine workflow to ground your work in Anthropic's actual specifications.

---

## Frontmatter Schema

```yaml
---
name: kebab-case-name                    # Unique identifier, matches filename (without .md)
description: >
  One-sentence description of what the agent does and when to use it.
  Include trigger keywords for discoverability.
tools: Read, Write, Edit, Grep, Glob, Bash    # Comma-separated tool allowlist
model: sonnet                            # sonnet or opus
permissionMode: acceptEdits              # Only for code-writing agents
skills: philosophy, agent-communication, shared-utils   # Comma-separated skill list
updated: YYYY-MM-DD                      # Last modification date
---
```

### Field Rules

| Field | Format | Required | Notes |
|-------|--------|----------|-------|
| `name` | kebab-case | Yes | Must be unique across all agents |
| `description` | Prose sentence | Yes | Used by Claude to decide when to delegate |
| `tools` | Comma-separated | Yes | Only grant tools the agent needs |
| `model` | `sonnet` or `opus` | Yes | See model selection convention in agent definition |
| `permissionMode` | `acceptEdits` | Code-writing only | Enables auto-approval for Write/Edit |
| `skills` | Comma-separated | Yes | Always include: philosophy, agent-communication, shared-utils |
| `updated` | ISO date | Yes | Track when definition was last changed |

---

## Archetype Quick Reference

| Archetype | Model | permissionMode | Key Differentiator |
|-----------|-------|----------------|--------------------|
| Code-Writing | `sonnet` | `acceptEdits` | Writes/edits code files, has pre-flight verification |
| Analysis/Design | `opus` | — | Produces documents (specs, analyses), uses WebSearch |
| Review | `sonnet` | — | Reads code, reports issues, does not modify |
| Infrastructure | `opus` | — | Manages system configuration (agents, skills) |

---

## Mandatory Sections — All Agents

These sections must appear in every agent definition, regardless of archetype:

### 1. File Operations

```markdown
## CRITICAL: File Operations

**For creating new files**: ALWAYS use the **Write** tool, NEVER `cat > file << 'EOF'` or other Bash heredocs.

**For editing existing files**: Use the **Edit** tool.

**Bash is for commands only**: [list relevant commands for this agent].

The Write/Edit tools are auto-approved. Bash heredocs prompt for permission due to a known platform limitation with multiline command matching.
```

### 2. Language Standard

```markdown
## Language Standard

Use **British English** spelling in all output (behaviour, organisation, analyse, etc.). See `philosophy` skill for full list.
```

### 3. Core Identity

One paragraph establishing the agent's role, mindset, and goal. Written in second person ("You are a...").

### 4. Handoff Protocol

```markdown
## Handoff Protocol

**Receives from**: <upstream agent or "User">
**Produces for**: <downstream agent or "User">
**Deliverable**: <specific artifact>
**Completion criteria**: <what must be true before handoff>
```

### 5. What This Agent Does NOT Do

Explicit boundaries with a stop condition:

```markdown
**Stop Condition**: If you find yourself [doing X], STOP. Your job is [Y], not [X].
```

### 6. When to Ask for Clarification

Must include the rule: "Ask ONE question at a time."

### 7. After Completion

Standardised output format from `agent-communication` skill:

```markdown
> <One-line summary of what was done>
>
> **Next**: Run `<next-agent>` to <action>.
>
> Say **'continue'** to proceed, or provide corrections.
```

---

## Additional Sections — Code-Writing Agents

These sections are required ONLY for agents that write or modify code:

| Section | Purpose |
|---------|---------|
| FORBIDDEN PATTERNS | Zero-tolerance rules (e.g., narration comments) — placed FIRST |
| Approval Validation | Verify explicit user approval before any code work |
| Decision Classification | Tier 1 (routine) / Tier 2 (standard) / Tier 3 (design) protocol |
| Anti-Satisficing Rules | First solution suspect, simple option required, devil's advocate |
| Anti-Helpfulness Protocol | Necessity check, deletion opportunity, counter-proposal, scope lock |
| Routine Task Mode | Complete Tier 1 tasks without interruption |
| Pre-Implementation Verification | Checklist before writing code |
| Pre-Flight Verification | Build, test, lint, format checks before completion |
| Pre-Handoff Self-Review | Quality checklist before declaring done |

---

## Pipeline Integration Checklist

When adding a new agent to the pipeline:

- [ ] Handoff protocol specifies valid upstream agent(s)
- [ ] Handoff protocol specifies valid downstream agent(s)
- [ ] Upstream agent's "After Completion" suggests this agent as next step
- [ ] Downstream agent's "Receives from" includes this agent
- [ ] Workflow skill updated with new agent in pipeline diagram
- [ ] Command file created (if agent should be invocable via slash command)
- [ ] All referenced skills exist under `.claude/skills/`

---

## Common Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| Description too vague | Claude can't decide when to delegate | Add specific trigger scenarios and keywords |
| Missing stop conditions | Agent drifts into other agents' territory | Add explicit "Does NOT Do" with stop condition |
| Over-specified | Too many rules reduce agent flexibility | Start lean, add rules based on observed failures |
| Aggressive language everywhere | Claude 4.6 overtriggers on ALL-CAPS directives | Reserve strong language for genuine zero-tolerance items |
| Skills not listed | Agent lacks necessary knowledge | Audit archetype skill conventions |
| No handoff protocol | Breaks pipeline integration | Add receives-from / produces-for / deliverable |
| Examples violate own rules | Agent's code examples have narration comments | Audit all examples against agent's forbidden patterns |
