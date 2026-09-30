---
name: agent-base-protocol
description: >
  Shared foundational protocol for all agents. Covers file operations, language standard,
  and clarification rules. Referenced by all agent definitions to avoid duplication.
alwaysApply: false
problem: "Every agent would otherwise re-inline the same file-ops, language, and clarification rules, drifting apart over time."
related: [project-preferences, shared-utils, writing-for-the-reader, response-templates]
---

# Agent Base Protocol

Foundational rules shared by all agents. Agents reference this skill instead of inlining these sections. The User Authority Protocol (the shared core deployed as each engine's global instructions) is the source for questions, decisions, reporting, and language; this skill only adds what agents need on top of it.

## File Operations

Create new files with the **Write** tool and edit existing ones with the **Edit** tool; keep Bash for commands (build tools, test runners, linters, formatters).

The reason: Write/Edit are auto-approved in `acceptEdits` mode, while Bash heredocs (`cat > file << 'EOF'`) trigger a permission prompt because of a platform limitation with multi-line command matching.

## Language Standard

The core's language invariant applies: match the user's language in conversation, and write every persisted artefact in British English. The `project-preferences` skill holds the word list. If the Cyrillic guard hook warns about a written file, correct it on the next edit.

## When to Ask for Clarification

Follow core §1: look for the answer yourself first, and ask only about what the evidence cannot answer and what would change the result. When the user describes a problem rather than requesting a change, the deliverable is an assessment, then stop — a menu of "how should I fix this?" questions is already a fix step.

### Decide yourself (routine — Tier 1)

These have deterministic answers; apply the rule and proceed:
- Removing a comment that violates the comment policy
- Formatting a file
- Adding error context
- Continuing routine work

### Decide and state it in one line (standard — Tier 2)

Naming when the domain is clear, structure when approaches are close, scope when one reading is clearly more defensible. Pick a defensible default and mention it in one line of the report, so the user can overturn it cheaply.

### Show candidates (decision — Tier 3)

When the core §2 threshold holds — the choice is irreversible, touches several files or components, crosses the named scope, the user asked for options, or two or three unknowns could change the outcome substantially — present 3–7 candidates as the decision card (template T2 in the `response-templates` skill). Typical cases: pattern or architecture selection, API design choices, interface definitions, new abstraction boundaries.

### How to ask

Put each question in the message with its context: what you are working on, what the reader will actually see or get under each option, and your recommendation with its reason. The `writing-for-the-reader` skill has the question template and the canonical bad example. Ask every live question of a turn together, so the user answers once rather than turn by turn.

A question tool (such as `AskUserQuestion`) only collects the pick; it cannot carry the context, so the context stays in the message text. A subagent cannot reach the user at all — it returns its questions or decision card to the orchestrator, which presents them.
