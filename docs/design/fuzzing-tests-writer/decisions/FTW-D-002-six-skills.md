---
note_id: "202611031506002"
created: 2026-11-03
language: en
type: meta
subtype: decision
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-D-002"]
tags: [fuzzing, design/decision]
status: accepted
supersedes: []
superseded_by: []
related: ["[[skill-fuzzing-applicability]]", "[[skill-fuzzing-campaign]]", "[[skill-structured-input-generation]]", "[[skill-go-fuzzing]]", "[[skill-python-fuzzing]]", "[[skill-rust-fuzzing]]", "[[FTW-D-008-pbt-out-of-scope]]"]
---
# FTW-D-002: Six skills: three methodology, three per language; no separate property-based-testing skill

## Decision

Write `fuzzing-applicability`, `fuzzing-campaign`, `structured-input-generation`, `go-fuzzing`, `python-fuzzing`, `rust-fuzzing`. Claim hygiene is the closing section of the campaign skill; grammar material is a reference file of the structure skill. *Amended by [[FTW-D-008-pbt-out-of-scope]]*: property-based testing is not folded into any of these skills; the gate skill carries the fuzzing-versus-PBT boundary table and the hand-off outcome instead.

## Context

The annexes proposed between six and fourteen skills with overlapping names (R1 §5.5, R2 §5.4, R3 §5.4, R7 §5.6, R8 §5.4, R9 §5.6). The property-based libraries are language-specific and the discipline is one page; the existing `go-testing`/`python-testing` skills already own language test idiom.

## Alternatives considered

(a) One monolithic `fuzzing` skill — exceeds the size that triggers reliably and mixes engine facts with method. (b) Twelve fine-grained skills — trigger overlap, more descriptions to tune, more Codex allowlist entries.

## Consequences

Each skill stays ≤ 300 lines with references beside it; the six names go into the Codex shared list; `go-testing` and `python-testing` get a pointer paragraph rather than fuzz content.

## Reopen when

trigger evals show two skills firing together on most queries (merge) or one skill above 300 lines after authoring (split).
