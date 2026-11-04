---
note_id: "20261104100009"
created: 2026-11-04
language: en
type: meta
subtype: decision
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-D-009"]
tags: [fuzzing, design/decision]
status: accepted
supersedes: []
superseded_by: []
related: ["[[fuzzing-charter]]", "[[agent-procedure]]", "[[eval-family-H-charter]]"]
---
# FTW-D-009: The agent fixes objective, scope and a verifiable result before writing any harness

## Decision

Step 1 of [[agent-procedure]] produces a charter ([[fuzzing-charter]]: entry point, objective with plausible bug classes, oracle and contract, out of scope, verifiable result, budget class and stop rule, success/failure criteria). No harness file is written before it; the report is compared against it item by item.

## Context

User requirement for this iteration; consistent with SYSE.47 §4.1 (recover the required result and the observable evidence of completion before constructing the procedure) and with the sourced preconditions of the stopping and reporting rules ([[H7-no-objective-before-work]]).

## Alternatives considered

(a) Objective implicit in the gate decision — too thin to compare a report against. (b) Objective written after the first exploratory campaign — reproduces H1/H2.

## Consequences

A new eval family H with a `tool_order` grader; the campaign report template gains a leading charter restatement and a closing checklist; [[skill-fuzzing-applicability]] carries the charter template.

## Reopen when

evals show the charter adds turns without changing decisions on any family (then it can be folded into the gate output).
