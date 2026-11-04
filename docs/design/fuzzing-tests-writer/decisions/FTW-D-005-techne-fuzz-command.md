---
note_id: "202611031506005"
created: 2026-11-03
language: en
type: meta
subtype: decision
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-D-005"]
tags: [fuzzing, design/decision]
status: accepted
supersedes: []
superseded_by: []
related: ["[[agent-procedure]]", "[[repository-placement]]"]
---
# FTW-D-005: A new /techne-fuzz command routes to the agent rather than an argument on /techne-test

## Decision

Add `roles/devbox/files/dot_ai/commands/techne-fuzz.md`; `/techne-test` is left as the unit-test entry point and hands off to the fuzzing agent only through the gate's recommendation path.

## Context

`/techne-test` carries its own complexity check and model selection for `unit_tests_writer`; the fuzzing agent needs a different pre-flight (existing targets, corpora, budget class) and defaults to Opus for the gate ([[agent-procedure]]).

## Alternatives considered

(a) `/techne-test fuzz` argument — one command with two pre-flights and two model policies. (b) No command; rely on automatic delegation — the delegation grader can check it, but users need an explicit entry point for budgeted campaigns.

## Consequences

The `techne-` prefix rule applies; the command computes context once (`resolve_context.py`) and passes the budget class; the delegation eval checks both routes.

## Reopen when

the two agents merge, or `/techne-test` grows a generic strategy argument.
