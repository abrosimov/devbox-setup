---
note_id: "20261103150404"
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
aliases: ["Skill: structured-input-generation", "structured-input-generation"]
tags: [fuzzing, design/component, design/skill, h3, h5]
addresses: ["[[H3-random-seeds-for-structured-input]]", "[[H5-harness-conventions]]"]
realises: ["[[input-shape-triage]]", "[[corpus-lifecycle]]"]
tested_by: ["[[eval-family-C-structure]]"]
decided_by: ["[[FTW-D-002-six-skills]]"]
target_path: "roles/devbox/files/dot_ai/skills/structured-input-generation/"
related: ["[[reference-documents]]"]
---
# Skill `structured-input-generation`

This design contract is implemented by
`roles/devbox/files/dot_ai/skills/structured-input-generation/SKILL.md`.
See [[authoring-validation]] for verified behaviour and remaining qualification.
Functional descriptions support ordinary discovery; advanced invocation conditions and routing remain deferred. Use [[agent-procedure]] and
[[skill-fuzzing-campaign]] for the research question, scope, effort and continuation. Construction
can serve reconnaissance of unfamiliar inputs before a precise hypothesis is available.

## Reusable operations

| Operation | Inputs and preconditions | Action | Result and next use | Failure or stop |
|---|---|---|---|---|
| Characterise input structure | input contract, available examples, observations and size limits | inspect/replay a bounded sample under [[input-shape-triage]]; distinguish bytes, syntax, repaired fields and operation sequences | observed distinctions and a construction plan or a newly formed question for [[skill-fuzzing-campaign]] | missing format meaning is recorded; poor reachability alone does not prescribe a technique escalation |
| Construct and examine inputs | scoped plan, legitimate seed source and applicable validity conditions | construct bounded seeds, grammar expansions or repaired inputs while retaining a byte path; examine acceptance and reached behaviour | raw inputs, construction provenance and observations for language-specific replay and campaign interpretation | distinguish expected structure from observed acceptance; uncertain benefit can motivate a bounded trial, not an assertion of success |
| Decode structured choices | byte input and bounded decoder/operation contract | map bytes to supported values or sequences without silently changing the target's contract | deterministic decoding and versioned raw input that the language harness can replay | unsupported or excessive input follows the explicit rejection policy, not swallowed exceptions |
| Reduce a structured failure | original reproducer, same-symptom observation and structure-aware reductions | attempt bounded reductions, independently replaying candidates; on resumption restore the predicate and last verified candidate | verified same-symptom input for reporting/replay, or original and unfinished operation for continuation | preserve original on changed symptom, uncertain validity, instability or interruption |

## Evidence and language variation

Use [[corpus-lifecycle]] and [[reference-documents]] for preservation and grammar techniques.
Grammar coverage describes exercised productions; it does not establish product correctness or
campaign saturation. A custom mutator must preserve required representation constraints and keep
its unsupported cases visible. Useful seeds remain available for replay rather than being discarded
because they do not reproduce a crash.

Go can use supported typed fuzz arguments or an explicit byte decoder; Python can use Atheris
`FuzzedDataProvider`; Rust can use a fuzzing decoder such as `Arbitrary` with bounded operation
sequences. Each option needs local compatibility and deterministic behaviour checked at authoring.
[[fuzzing-vs-pbt-boundary]] excludes PBT bridges; mutation analysis is also excluded. Ordinary
fuzz-input mutation remains a fuzzing operation. Do not import historical hybrid examples as current requirements.

## Planned content validation

[[eval-family-C-structure]] uses a new supported recursive input whose bounded generation reaches
the intended parser behaviour, with independently specified acceptance evidence. A defeating case
changes a checksum or decoder assumption: syntactic validity alone must not be reported as deeper
reachability. An interrupted reduction must resume from the verified candidate and preserve the
original if a smaller input loses the symptom. No skill-trigger cases or live runs are included now.
