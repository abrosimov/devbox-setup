---
name: agent-base-protocol
description: >
  Shared foundational protocol for all agents. Covers file operations, language standard,
  and clarification rules. Referenced by all agent definitions to avoid duplication.
alwaysApply: false
---

# Agent Base Protocol

Foundational rules shared by all agents. Agents reference this skill instead of inlining these sections.

## CRITICAL: File Operations

**For creating new files**: ALWAYS use the **Write** tool, NEVER `cat > file << 'EOF'` or other Bash heredocs.

**For editing existing files**: Use the **Edit** tool.

**Bash is for commands only**: build tools, test runners, linters, formatters, etc.

The Write/Edit tools are auto-approved by `acceptEdits` mode. Bash heredocs prompt for permission due to a known platform limitation with multiline command matching.

## Language Standard

**Written artifacts** — file contents, code, comments, docstrings, commit messages, PR titles/descriptions, plans, designs, JSON outputs, and persisted memory files — MUST use **British English** spelling (behaviour, organisation, analyse, colour, honour, licence [noun], practise [verb], catalogue, etc.) regardless of the conversation language.

**Conversational responses** — chat replies, AskUserQuestion text, TaskCreate subjects, and any UI-visible output that is not persisted — match the user's language. If the user writes in Russian, respond in Russian; if in English, respond in English.

A non-blocking PostToolUse hook (`bin/post-edit-cyrillic-guard`) warns when Cyrillic characters appear in Edit/Write/MultiEdit/NotebookEdit content outside the allowlist (`testdata/`, `fixtures/`, `memory/`). Self-correct on the next edit when the warning fires.

See `project-preferences` skill for the full word list.

## When to Ask for Clarification

**CRITICAL: Ask ONE question at a time.** Do not overwhelm the user.

### NEVER Ask (Routine Tasks — Tier 1)

These have deterministic answers. Apply the rule and proceed:
- "Should I remove this comment?" — YES, if it violates comment policy
- "Should I format this file?" — YES, always
- "Should I add error context?" — YES, always
- "Should I continue?" during routine work — YES, always

### Ask Only If Genuinely Ambiguous (Tier 2)

- Naming when domain semantics are unclear
- Structure when multiple approaches are equally valid
- Scope when requirements could be read multiple ways

### Always Ask (Tier 3 — Design Decisions)

After completing the exploration protocol, present options:
- Pattern/architecture selection
- API design choices
- Interface definition
- New abstraction boundaries

### How to Ask

**Default to a multiple-choice ask.** The user can pick a letter in 1 second; free-text takes 30. Multiple-choice also externalises your internal candidate distribution, which is the point.

1. **Provide context** — What you are working on, what led to this question
2. **Prefer multiple-choice over free-text** — Produce 2–4 concrete interpretations or approaches (A/B/C/D), each with a one-line trade-off. Free-text "what did you mean?" is permitted only when you cannot enumerate a small candidate set.
3. **State your recommendation** — Which option you would choose and why
4. **Ask the specific question** — What decision you need from them

**Format:**
```
[Context]: Working on [X], encountered [situation].

Options:
A) [Option] — [trade-off]
B) [Option] — [trade-off]

Recommendation: [A/B] because [reason].

**[Awaiting your decision]**
```
