---
note_id: "20261103150407"
created: 2026-11-03
modified: 2026-11-12
language: en
type: design
subtype: skill
note_role: artifact
artifact_kind: skill
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Skill: rust-fuzzing", "rust-fuzzing"]
tags: [fuzzing, design/component, design/skill, lang/rust, h3, h4, h5]
addresses: ["[[H5-harness-conventions]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]"]
realises: ["[[language-facts-rust]]", "[[oracle-ladder]]", "[[fuzzing-vs-pbt-boundary]]"]
tested_by: ["[[eval-family-E-conventions]]", "[[eval-family-B-oracle]]"]
decided_by: ["[[FTW-D-002-six-skills]]", "[[FTW-D-008-pbt-out-of-scope]]"]
opens: ["[[FTW-OQ-005-cargo-fuzz-on-stable]]"]
target_path: "roles/devbox/files/dot_ai/skills/rust-fuzzing/"
related: ["[[reference-documents]]"]
---
# Skill `rust-fuzzing`

This design contract is implemented by
`roles/devbox/files/dot_ai/skills/rust-fuzzing/SKILL.md`.
See [[authoring-validation]] for verified behaviour and remaining qualification.
Functional descriptions support ordinary discovery; advanced invocation conditions and routing remain deferred. Use [[agent-procedure]] and
[[skill-fuzzing-campaign]] for scope, effort and research continuation. These operations supply the
language-specific harness, observations and replay assets for a scoped reconnaissance pass or
question-led experiment.

## Reusable Rust operations

| Operation | Inputs and preconditions | Action | Result and next use | Failure or stop |
|---|---|---|---|---|
| Qualify the fuzz build | repository toolchain/workspace, target, build profile and charter | check cargo-fuzz compatibility, build the target, execute replay and independently verify the oracle and required instrumentation | build/replay observations and profile/instrumentation settings used to qualify the planned execution | a successful build does not establish oracle correctness; unavailable toolchain → environment gap |
| Construct the harness | byte or structured input contract, bounded sizes/sequences and independent examples | use a supported fuzz target and bounded decoder; distinguish expected invalid input from a failure | deterministic harness plus useful replayable seeds and documented rejection policy | unsupported decoder behaviour or hidden assertion loss returns a harness gap; no PBT bridge |
| Retain and assess artefacts | corpus and failure paths, original reproducer and repository conventions | preserve useful inputs for replay; reproduce and attempt structure-aware reduction within the justified experiment and its limits | same-symptom reproducer or explicitly unconfirmed original, retained useful corpus | a reducer's successful exit does not prove global minimality; never discard the original on a changed symptom |

## Evidence and language variation

Use [[language-facts-rust]] as research evidence and verify the actual toolchain and build profile
before authoring. `Arbitrary` can decode fuzz inputs; bounded `Vec<Op>` sequences require contract
and size limits. Debug assertions, overflow checks and sanitisers have distinct visibility; record
which are active instead of inferring them from a profile name. Use [[oracle-ladder]] for supported
semantic checks. [[FTW-OQ-005-cargo-fuzz-on-stable]] remains a compatibility question, not permission
to install a different toolchain. External service integration and alternative fuzz backends require
a demonstrated need; they are not required additions to this skill. PBT and mutation analysis are
excluded, including historical bridge and roadmap examples.

Return build, replay and instrumentation observations with the target/toolchain/input versions to
[[skill-fuzzing-campaign]] for interpretation and effort accounting. After interruption, recover the
unfinished build, replay or reduction and its established results; recheck changed dependencies,
then perform the supported next operation. A command limit does not answer the research question.
Report product bugs; correct authored harness defects within scope. Retain useful inputs for replay
under [[corpus-lifecycle]] without an automatic Git commit or publication.

## Planned content validation

[[eval-family-E-conventions]] and [[eval-family-B-oracle]] require a new applicable target whose
bounded decoder, instrumented execution and retained seed replay have independent expected
observations. A defeating case changes a profile or decoder assumption: missing assertion checks
or newly rejected bytes must invalidate the dependent qualification instead of proving no bug.
Resume an interrupted reduction from its last verified candidate; retain the original when a
smaller candidate changes the symptom. Advanced invocation tests remain deferred; Rust runtime qualification is unperformed.
[[repository-placement]] records authored packaging and [[authoring-validation]] records actual checks.
