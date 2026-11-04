---
note_id: "202611031506001"
created: 2026-11-03
modified: 2026-11-04
language: en
type: meta
subtype: decision
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-D-001"]
tags: [fuzzing, design/decision]
status: accepted
supersedes: []
superseded_by: []
related: ["[[applicability-gate]]", "[[agent-procedure]]", "[[eval-family-A-gate]]"]
---
# FTW-D-001: The applicability gate is a skill and the first step of the agent procedure

## Decision

The agent writes no harness before producing a one-line gate decision with the matching row of [[applicability-gate]] quoted. *Amended by [[FTW-D-008-pbt-out-of-scope]]*: the outcomes are `fuzz(method, oracle)` / `out-of-scope: pbt-track` / `out-of-scope: unit-tests` / `do-not-fuzz`. The gate lives in [[skill-fuzzing-applicability]] so other agents (`code_reviewer`, `unit_tests_writer`) can load it too.

## Context

[[H1-no-applicability-gate]] was confirmed as the dominant failure cause; every language annex agrees on the hard-stop rows (R1 §5.1, R7 §5.4, R8 §5.1, R9 §5.3).

## Alternatives considered

(a) Gate as prose inside the agent prompt only — not reusable by the reviewer, not independently eval-able. (b) Gate after a first exploratory campaign — spends budget before deciding, which is exactly the H1 failure.

## Consequences

Family A evals grade the decision line deterministically; `out-of-scope: unit-tests` hands off to `unit_tests_writer` and `out-of-scope: pbt-track` to the PBT agent, with nothing written for either; the prompt stays short because the table is in the skill.

## Reopen when

a gate row is contradicted by a reproducible counter-example in the evals, or a new ecosystem tool changes a hard stop (for example Go gains custom mutators).
