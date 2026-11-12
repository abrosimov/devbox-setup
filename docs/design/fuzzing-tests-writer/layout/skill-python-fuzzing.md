---
note_id: "20261103150406"
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
aliases: ["Skill: python-fuzzing", "python-fuzzing"]
tags: [fuzzing, design/component, design/skill, lang/python, h3, h4, h5]
addresses: ["[[H5-harness-conventions]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]"]
realises: ["[[language-facts-python]]", "[[oracle-ladder]]", "[[fuzzing-vs-pbt-boundary]]"]
tested_by: ["[[eval-family-E-conventions]]", "[[eval-family-B-oracle]]"]
decided_by: ["[[FTW-D-002-six-skills]]", "[[FTW-D-008-pbt-out-of-scope]]"]
target_path: "roles/devbox/files/dot_ai/skills/python-fuzzing/"
related: ["[[reference-documents]]", "[[pbt-agent-prompts]]", "[[FTW-OQ-006-hypofuzz-licence]]"]
---
# Skill `python-fuzzing`

This design contract is implemented by
`roles/devbox/files/dot_ai/skills/python-fuzzing/SKILL.md`.
See [[authoring-validation]] for verified behaviour and remaining qualification.
Functional descriptions support ordinary discovery; advanced invocation conditions and routing remain deferred. Use [[agent-procedure]] and
[[skill-fuzzing-campaign]] for scope, effort and research continuation. These operations supply the
language-specific harness, observations and replay assets for a scoped reconnaissance pass or
question-led experiment.

## Reusable Python operations

| Operation | Inputs and preconditions | Action | Result and next use | Failure or stop |
|---|---|---|---|---|
| Qualify Atheris execution | repository Python environment, Atheris compatibility, target and charter | verify actual instrumented target execution and independent oracle expectations; distinguish pure-Python code from native extensions | environment, instrumentation and replay evidence used to qualify the planned execution | import success alone proves neither execution nor instrumentation; unavailable dependencies → environment gap |
| Construct the harness | input contract, bounded byte/structured decoder and expected exceptions | build deterministic target handling with an explicit expected-rejection policy | runnable harness, useful valid-structure/coverage seeds and documented limits | broad exception swallowing is a harness defect; no PBT or hybrid backend |
| Retain and assess artefacts | original input, observed exception or native failure and contract | reproduce and classify within the justified experiment and its limits; reduce only while preserving the same symptom | replayable corpus/regression input and supported classification | expected `ValueError` or a command timeout is not automatically a product bug; uncertain cases retain original evidence |

## Evidence and language variation

Use [[language-facts-python]] as research evidence, verifying actual Atheris/runtime compatibility
and engine-limit semantics before authoring. `FuzzedDataProvider` or a bounded explicit decoder can
supply structured choices. Native sanitiser instrumentation and its build/runtime dependencies must
be checked when native code is in scope; pure-Python execution does not by itself establish native
coverage. Apply [[oracle-ladder]] using independently expected behaviour.
[[pbt-agent-prompts]] and [[FTW-OQ-006-hypofuzz-licence]] remain historical links and impose no
current work. Hypothesis, HypoFuzz and bridges that create or execute PBT are excluded, as is
mutation analysis; none is a backend, evaluation obligation or optional roadmap item.

Return build, replay and instrumentation observations with the target/toolchain/input versions to
[[skill-fuzzing-campaign]] for interpretation and effort accounting. After interruption, recover the
unfinished build, replay or reduction and its established results; recheck changed dependencies,
then perform the supported next operation. A command limit does not answer the research question.
Report product bugs; correct authored harness defects within scope. Retain useful inputs for replay
under [[corpus-lifecycle]] without an automatic Git commit or publication.

## Planned content validation

[[eval-family-E-conventions]] and [[eval-family-B-oracle]] require a new applicable parser whose
instrumented execution and retained seed replay have independently expected observations. A
defeating case raises an expected rejection and a separate unexpected exception: the first must
not become a product bug and the second must not disappear in a broad exception handler. An
import-only success cannot qualify instrumentation. Repeat a saved replay in a fresh session using
the recorded environment and expected result. Advanced invocation tests remain deferred; Python runtime qualification is unperformed.
[[repository-placement]] records authored packaging and [[authoring-validation]] records actual checks.
