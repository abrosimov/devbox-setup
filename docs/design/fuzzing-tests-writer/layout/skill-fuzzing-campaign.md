---
note_id: "20261103150403"
created: 2026-11-03
modified: 2026-11-12
language: en
type: design
subtype: component
note_role: artifact
artifact_kind: skill
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Skill: fuzzing-campaign", "fuzzing-campaign"]
tags: [fuzzing, design/component, design/skill, h2, h5, h6]
addresses: ["[[H2-no-stopping-rule]]", "[[H5-harness-conventions]]", "[[H6-crash-counting-reports]]"]
realises: ["[[stopping-algorithm]]", "[[corpus-lifecycle]]", "[[reporting-and-claim-hygiene]]"]
tested_by: ["[[eval-family-D-stopping]]", "[[eval-family-F-reporting]]", "[[eval-family-G-triage]]"]
decided_by: ["[[FTW-D-003-thresholds-as-flags]]", "[[FTW-D-002-six-skills]]"]
target_path: "roles/devbox/files/dot_ai/skills/fuzzing-campaign/"
related: ["[[reference-documents]]"]
---
# Skill `fuzzing-campaign`

This design contract is implemented by
`roles/devbox/files/dot_ai/skills/fuzzing-campaign/SKILL.md`.
See [[authoring-validation]] for verified behaviour and remaining qualification.
Research can span sessions and paused intervals. Inputs and preconditions describe the method;
functional descriptions support ordinary discovery; advanced invocation conditions, routing,
command choice and trigger evaluations remain deferred.
Lifecycle transitions after invocation do not select when an agent should be called.

## Reusable operations

| Operation | Inputs and preconditions | Action | Result and next use | Failure or stop |
|---|---|---|---|---|
| Recover research | research identity, subject snapshot and saved checkpoint | recover the question, method of the unfinished operation, established results, pending work and accumulated effort; inspect conditions needed now | perform the next supported operation, change direction with reasons, or return the precise missing prerequisite | loading a checkpoint is not completion; uncertain prior effects need inspection before repetition |
| Explore new material | authorised target, new corpus or feasible variation, available observations and effort limits | inspect or vary a bounded sample, compare resulting behaviour and retain unexpected useful differences | observations that support a new question, an adequate answer, another justified pass or closure | no exact hypothesis or pre-proven utility is required; novelty alone does not justify repeated exploration |
| Plan a question-led experiment | receiving use, established unresolved distinction and existing evidence | specify competing observations, consequences for the receiving use, least sufficient method, limits and completion/failure evidence | one scoped experiment for the applicable language and input-construction operations | no worthwhile attainable contribution → close with limitations; an observable prerequisite may justify pause |
| Interpret observations | raw output, engine/version, interval and instrumentation evidence | record supported meanings and compatible explanations using C.16.IR via [[fpf-framing]] | qualified observations and implications for the current question | quiet counters do not establish saturation, safety or a need to run again |
| Preserve useful corpus | coverage/structured seeds and regression artefacts with provenance | follow [[corpus-lifecycle]], retain inputs and verify replacements under the experiment's limits | replay paths, demonstrated value and unverified items | retain the original when equivalent value is unproved; retention is not a Git commit |
| Assess a failure | original artefact, symptom, contract and justified triage question | reproduce, bucket and reduce while preserving the same symptom | supported finding or preserved unconfirmed input | incomplete/unstable reproduction stays explicit; report product bugs, correct only authored harness defects |
| Decide and checkpoint | observations, current conclusion, available continuations and accumulated effort | relate the result to the current question; choose continued work, a new in-scope question, pause or closure under [[stopping-algorithm]] | selected operation with its reason and usable inputs, or durable closure/pause and report | a choice is not performed work; an invalid or inconclusive experiment does not automatically trigger another |
| Resume or reopen | checkpoint plus observed resume condition, or material evidence affecting a closed conclusion | verify relevant assumptions, retain past dispositions and requalify affected claims; then execute the supported unfinished operation | actual continuation or a linked research revision whose result is used by the next operation | new session/commit/dataset label alone cannot justify repetition or erase effort |

## New directions and completed questions

A closed question remains closed when a new corpus raises a different question. Link the new work
to the material and earlier evidence it uses; do not reopen unrelated conclusions or rename an
exhausted attempt to hide its history. Reconnaissance may finish with a useful distinction, an
adequate answer or no worthwhile continuation. A promising intermediate input can justify a
bounded further examination while its eventual value remains unknown. Preserve useful inputs for
replay even when their generating question closes. [[input-shape-triage]] and [[corpus-lifecycle]]
supply the construction and reuse operations; no frontier service or fixed branching quota is needed.

## Evidence and language variation

[[agent-procedure]] defines research states `ACTIVE`, `PAUSED`, `CLOSED` and closure reasons
`ANSWERED`, `INCONCLUSIVE`, `NO_JUSTIFIED_NEXT_STEP`, `CANCELLED`. Experiment status and finding
classification are separate. No finding does not establish absence of bugs; an exhausted local
run limit does not answer the research question. No fixed reproduction count substitutes for
independent evidence of the same symptom.

The language skills supply corpus formats, instrumentation and engine-output semantics. Every
attempt, including preparation, replay and triage, remains in the research effort record across
sessions. Limits are declared for the current experiment; the earlier mandatory research-wide
wall-clock deadline and finishing reserve are withdrawn. Continuation within existing authority
requires no repeated approval. A real authority or user-only information gap can justify pause.

[[automation-scripts]] specifies checkpoint/evidence support, realised by the authored record
reference and ordinary repository tools; no checkpoint service is required or implemented.
[[reference-documents]] supplies qualified source material. PBT and mutation analysis remain
excluded from operations, evaluations and roadmap.

## Planned content validation

[[eval-family-D-stopping]], [[eval-family-F-reporting]] and [[eval-family-G-triage]] check closure,
pause/resumption, targeted reopening, classification and preservation using independent evidence.
Include a new corpus that supports reconnaissance and a separate in-scope question; an interrupted
reduction resumed from its verified candidate; and a useful non-crashing seed replayed later.
Defeating cases include a renamed old corpus offered as new evidence, a changed oracle invalidating
the reduction predicate, and an incomplete reproducer whose next attempt has no useful purpose.
The expected result must distinguish actual continuation, targeted reconsideration and preserved
uncertainty. No live or trigger run is performed in this methodology pass.
