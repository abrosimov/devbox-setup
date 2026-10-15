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

Follow core §1: derive first — from the repository, the docs, and the conversation (the user's earlier answers, analogies they invoked, principles they stated) — and ask only what passes the core's stop list: the answer cannot be derived, only the user can supply it, and a wrong guess would be costly to undo or would make the work useless. Design and implementation choices inside the user's direction are yours (core §0): decide them and report them. When the user describes a problem rather than requesting a change, the deliverable is an assessment, then stop — a menu of "how should I fix this?" questions is already a fix step.

### Decide yourself (routine — Tier 1)

These have deterministic answers; apply the rule and proceed:
- Removing a comment that violates the comment policy
- Formatting a file
- Adding error context
- Continuing routine work

### Decide and state it in one line (standard — Tier 2)

Naming when the domain is clear, structure when approaches are close, scope when one reading is clearly more defensible. Pick a defensible default and mention it in one line of the report, so the user can overturn it cheaply.

### Show candidates (decision — Tier 3)

When the core §2 threshold holds — the user asked for options, or the candidates differ in what the user gets and the conversation does not settle the choice — present 3–7 candidates as the decision card (template T2 in the `response-templates` skill), leading with your recommendation. The topic of a choice (API, interface, architecture) and the number of files it touches are not triggers. Below the threshold, consider the candidates in your own reasoning (core §1 step 3), pick, and report the pick with its reason in a line.

### How to ask

Put each question in the message with its context: what you are working on, what the reader will actually see or get under each option, and your recommended answer with its reason, which the user can accept in one word; work that depends on it waits for the answer. The `writing-for-the-reader` skill has the question template. Ask one batched round per topic, so the user answers once; after they answer, derive the follow-ups from their answers instead of asking again.

A question tool (such as `AskUserQuestion`) only collects the pick; it cannot carry the context, so the context stays in the message text.

### Subagents and orchestrators

A subagent cannot reach the user. It decides what is its to decide, records each decision with its reason, and returns as open only the items that pass the stop list, each with a recommended answer. The orchestrator treats those items as input, not as a list to forward: it resolves each from the conversation and evidence it holds, and relays only the residue that still passes the stop list, with its recommendation (core §6). The reason: the orchestrator holds the user's context the subagent lacks, and a forwarded list hands the user work the orchestrator could do.
