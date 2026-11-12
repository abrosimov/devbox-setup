---
note_id: "20261103150405"
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
aliases: ["Skill: go-fuzzing", "go-fuzzing"]
tags: [fuzzing, design/component, design/skill, lang/go, h3, h5]
addresses: ["[[H5-harness-conventions]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]"]
realises: ["[[language-facts-go]]", "[[oracle-ladder]]", "[[fuzzing-vs-pbt-boundary]]"]
tested_by: ["[[eval-family-E-conventions]]", "[[eval-family-B-oracle]]"]
decided_by: ["[[FTW-D-007-go-target-version]]", "[[FTW-D-002-six-skills]]", "[[FTW-D-008-pbt-out-of-scope]]"]
opens: ["[[FTW-OQ-003-go-skip-and-minimisation]]", "[[FTW-OQ-004-go-ossfuzz-shim]]"]
target_path: "roles/devbox/files/dot_ai/skills/go-fuzzing/"
related: ["[[reference-documents]]"]
---
# Skill `go-fuzzing`

This design contract is implemented by
`roles/devbox/files/dot_ai/skills/go-fuzzing/SKILL.md`.
See [[authoring-validation]] for verified behaviour and remaining qualification.
Functional descriptions support ordinary discovery; advanced invocation conditions and routing remain deferred. Use [[agent-procedure]] and
[[skill-fuzzing-campaign]] for scope, effort and research continuation. These operations supply the
language-specific harness, observations and replay assets for a scoped reconnaissance pass or
question-led experiment.

## Reusable Go operations

| Operation | Inputs and preconditions | Action | Result and next use | Failure or stop |
|---|---|---|---|---|
| Qualify the target | repository Go toolchain, package, `testing.F` contract and charter | check supported arguments and package conventions; build/test the relevant target, execute seed replay and independently check oracle behaviour | compilation, replay and instrumentation evidence used to qualify the planned execution | `go vet` alone is not compilation or execution evidence; unresolved target/oracle defect → harness gap |
| Construct fuzzing input | supported typed arguments or byte decoder, known seeds and size bounds | build a deterministic harness and retain useful seeds in `f.Add`/`testdata/fuzz` or the repository's equivalent | harness and replayable corpus with provenance | unsupported types, decoder errors or expected rejections remain visible; no PBT bridge |
| Retain and assess artefacts | original failure or useful input, repository conventions and toolchain-compatible encoding | distinguish seed corpus, engine cache and failure artefacts; reproduce and reduce within the justified experiment and its limits | regression reproducer or useful seed retained for replay, original preserved when reduction is uncertain | cache residence alone is not durable repository retention; no automatic commit |

## Evidence and language variation

[[language-facts-go]] is evidence to verify against the repository's actual pinned Go version;
its historical Go 1.27.3 baseline is not an instruction to replace the project's toolchain or proxy.
Use [[oracle-ladder]] for contract-backed checks. Supported platform, argument and artefact behaviour,
race instrumentation and any OSS-Fuzz integration require separate evidence if needed; an ordinary
`testing.F` result does not prove an external shim consumes the same seeds. The open questions
[[FTW-OQ-003-go-skip-and-minimisation]] and [[FTW-OQ-004-go-ossfuzz-shim]] retain their limits.

Return build, replay and instrumentation observations with the target/toolchain/input versions to
[[skill-fuzzing-campaign]] for interpretation and effort accounting. After interruption, recover the
unfinished build, replay or reduction and its established results; recheck changed dependencies,
then perform the supported next operation. A command limit does not answer the research question.
Report product bugs; correct authored harness defects within scope. Retain useful inputs for replay
under [[corpus-lifecycle]] without an automatic Git commit or publication.

## Planned content validation

[[eval-family-E-conventions]] and [[eval-family-B-oracle]] require a new applicable package whose
supported seed encoding is executed and then replayed from the retained corpus in a fresh session.
A defeating case provides a seed incompatible with the target's arguments or a contract example
that disproves the proposed oracle: return the encoding/oracle gap without silently dropping the
input or reporting a product defect. Independent expected observations must establish execution
and rejection meaning; static checks alone are insufficient. Advanced invocation tests remain deferred. See [[repository-placement]] for authored packaging and
[[authoring-validation]] for the scope of actual runtime checks.
