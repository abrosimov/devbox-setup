---
name: editing-claude-config
description: >
  Context-optimisation patterns for editing Claude Code configuration under
  `roles/devbox/files/dot_claude/` (agents, skills, commands, hooks.json,
  settings.json, schemas, bin, templates). Use when reading or editing any
  file under that path, when working inside `~/.claude/` directly, or when
  the conversation involves modifying Claude Code's own agent/skill/command
  definitions. Keeps the main conversation context lean by deferring deep
  reads to subagents and Grep, and disabling unused MCP servers.
alwaysApply: false
problem: "Editing agents or skills naively reads every cross-referenced file, burning 30-50 K main-context tokens before any edit."
related: [agent-builder, skill-builder]
---

# Editing Claude Code Configuration

Rules for working inside `roles/devbox/files/dot_claude/` (Ansible source) or
its deployment target `~/.claude/`. The directory holds agent, skill, command,
hook, schema, and helper-script definitions — many large files cross-reference
each other, and naïve read-everything browsing burns main-context tokens fast.

## Why this skill exists

Editing one agent often touches ~5 related files (the skill it references, a
sibling agent, the command that invokes it). If every related file is `Read`
at full length into the main conversation, 30–50 K tokens burn before any
edit happens. This skill enforces a discipline that keeps the main context
lean — the same edit completes in a fraction of the budget.

## Surgical reads only

Read **only the target file** you are about to edit. Do not pull in referenced
skills, sibling agents, or other definitions "for context" unless the user
explicitly asks for them. If you need a single fact from a referenced file,
prefer `Grep` over `Read` (see below).

## Delegate multi-file edits to subagents

For multi-file changes, spawn subagents via the `Task` tool. Each subagent
gets its own context window — file reads do not accumulate in the main
conversation; only the subagent's summary returns. Pattern: one subagent per
affected file, parallel when the edits are independent.

## Prefer Grep over Read for cross-references

When checking whether a symbol, command name, skill name, or agent reference
exists elsewhere, use `Grep` with a tight pattern. `Grep` returns matched
lines only (typically <100 tokens); `Read` returns the whole file. Reserve
`Read` for files you are about to edit or for understanding a multi-line
construct.

## One file per edit cycle

Finish editing one file before opening the next. Avoid loading multiple large
agent/skill definitions into context simultaneously — even read-only. If the
sequence is "edit A → check B → edit C", do A's edits, drop A from the active
working set, then move on.

## Disable unused MCPs at session start

Run `/mcp` at session start and disable MCP servers irrelevant to config work
— typically `playwright`, `figma`, `storybook`. Each carries ~5–7 K tokens of
tool-schema overhead. Disabling the three above saves ~15–20 K tokens of
main-context budget on every turn.

## Anti-patterns

- Reading every agent referenced in a `## See also` section before starting.
- `cat`-ing entire skill files via Bash to "get the lay of the land".
- Keeping `playwright` / `figma` / `storybook` MCPs enabled when working
  purely on text-only config files.
- Doing multi-file refactors directly in the main conversation rather than
  delegating to subagents.
- Re-`Read`-ing a file you just edited to "verify" — the Edit tool would
  have errored if the change failed, and the harness tracks file state for
  you.
