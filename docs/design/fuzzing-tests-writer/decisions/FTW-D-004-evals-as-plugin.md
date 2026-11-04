---
note_id: "202611031506004"
created: 2026-11-03
language: en
type: meta
subtype: decision
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-D-004"]
tags: [fuzzing, design/decision]
status: accepted
supersedes: []
superseded_by: []
related: ["[[eval-tooling]]", "[[eval-plan]]", "[[eval-fixtures]]"]
---
# FTW-D-004: Behavioural evals run through claude plugin eval on a plugin directory; skill triggering keeps the repository's existing machinery

## Decision

Package the agent and the six skills as `tests/fuzzing_agent_evals/plugin/` and write cases with scaffolded fixture workspaces and deterministic graders; keep `trigger_evals.json` / `evals.json` with `make eval-skills` for descriptions; add a headless driver only for the `unit_tests_writer` baseline arm.

## Context

`claude plugin eval` evaluates a plugin, not a loose `~/.claude/agents/*.md`; it supplies the without-plugin baseline, a CI threshold and a JSON report (R10). The repository already wires Anthropic's skill-creator scripts.

## Alternatives considered

(a) Only the skill-creator scripts — no fixture workspaces, no deterministic file graders, no delegation check. (b) A bespoke harness over `claude -p` for everything — duplicates what the plugin-eval tool provides and has no baseline arm.

## Consequences

Fixtures must vendor dependencies (sandbox network limits); CI needs Claude Code ≥ 2.1.269 and bubblewrap/socat on Linux ([[FTW-OQ-009-plugin-eval-prerequisites]]); hold-out is by tag.

## Reopen when

the plugin-eval tool documents a direct agent-file target or a train/test split, or the cost ceiling makes three runs per case unaffordable.
