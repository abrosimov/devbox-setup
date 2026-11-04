---
note_id: "20261104100008"
created: 2026-11-04
language: en
type: meta
subtype: decision
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-D-008"]
tags: [fuzzing, design/decision]
status: accepted
supersedes: []
superseded_by: []
related: ["[[fuzzing-vs-pbt-boundary]]", "[[applicability-gate]]", "[[pbt-agent-prompts]]", "[[FTW-D-002-six-skills]]"]
---
# FTW-D-008: Property-based testing is a separate track; this agent does fuzzing only and keeps a strict boundary

## Decision

The fuzzing agent writes fuzz targets, seed corpora, campaign wiring and reports. It does not write property-based tests (Hypothesis, proptest, rapid, including their state machines). Typed APIs with algebraic laws, numeric metamorphic cases and model-based stateful cases leave the gate as `out-of-scope: pbt-track` with the reason recorded in the charter. Hybrid bridges (`rapid.MakeFuzz`, `fuzz_one_input`, bolero) are used only when the PBT artefact already exists and the charter names coverage guidance as the objective ([[fuzzing-vs-pbt-boundary]]).

## Context

The user asked to concentrate on fuzzing now and to keep the two approaches strictly separated because both have their own details; rapid in particular shares mechanisms with `go test -fuzz` (R7 §3.5) and the annexes blur the line in places (R1 §4.2 treats them as 'one continuum').

## Alternatives considered

(a) One agent for both (the first draft's 'property-test first' rows) — mixes two budgets, two regression forms and two shrinking models, and would make the fuzzing agent author strategies it cannot evaluate. (b) Fuzzing agent writes PBT 'when cheaper' — reintroduces the blur the user rejected.

## Consequences

Gate outcomes, the shape table, the per-language skills and eval families A–C are rewritten without PBT deliverables; the PBT prompts are recorded in [[pbt-agent-prompts]] for the other track; [[FTW-D-002-six-skills]] is amended (no PBT catalogue in the gate skill).

## Reopen when

the PBT track exists and an orchestrator wants one entry point that dispatches to either; then the dispatch lives in a command, not in this agent.
