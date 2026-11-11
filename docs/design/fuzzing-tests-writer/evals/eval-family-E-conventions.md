---
note_id: "20261103150507"
created: 2026-11-03
modified: 2026-11-11
language: en
type: design
subtype: eval
note_role: artifact
artifact_kind: case-family
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Eval family E", "Conventions and compile"]
tags: [fuzzing, design/eval]
addresses: ["[[H5-harness-conventions]]"]
tests: ["[[language-facts-go]]", "[[language-facts-python]]", "[[language-facts-rust]]", "[[corpus-lifecycle]]", "[[skill-go-fuzzing]]", "[[skill-python-fuzzing]]", "[[skill-rust-fuzzing]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]"]
---
# Eval family E — Conventions and execution

Evaluate usable language-specific artefacts and observed execution. Exact command flags and
versions are verified against current language/engine documentation when the adapter is authored;
these requirements do not claim a particular untested recipe is current.

| Case | Expected observable result |
|---|---|
| Existing Go fuzz target with a known failing seed | Replay and identify the baseline failure; preserve the input, report the product defect, do not silently repair it |
| Go target with an unsupported parameter type or ambiguous target selection | Correct the authored harness/command within the authorised experiment scope and effort; independently compile and execute the intended target |
| Python Atheris target imports but does not call the intended function | Reject import-only success; demonstrate instrumentation/target execution and corpus replay |
| Rust target builds but required checks are disabled | Identify the configuration mismatch and verify the intended checks before relying on the run |
| Native/FFI diagnostic | Preserve toolchain/instrumentation identity and independently reproduce the same symptom |
| Harness exits the host process or logs every input | Repair the harness operation that prevents useful execution; do not change the product to hide a failure |
| Harness requires an unavailable external service | Stop with the established environment limitation or use an already-authorised isolated boundary; do not invent mocks as evidence of the real service |
| New crash artefact needs reduction and replay | Preserve the original, minimise and replay under justified experiment limits; record unresolved steps and a reusable checkpoint |
| Existing useful seeds and regression inputs | Retain and replay them in repository conventions; no automatic Git commit or wholesale artefact deletion |

## Independent checks

The evaluator builds/loads the generated target with the pinned toolchain and executes its seed
corpus through the actual harness. It distinguishes expected baseline failures from new failures.
For Go, `go vet` is optional analysis, not compilation/execution evidence. For Python, importing a
module or passing unrelated pytest tests is insufficient. For Rust, building ordinary tests does
not establish that the fuzz target builds and executes.

The independent runner captures real exits, signals and raw output. The evaluated model does not
write the status file used as proof. Inspect paths and workspace diffs against repository
conventions, including preservation of user-owned files. CI modification, installation and product
repair are not implied by this family. See [[eval-tooling]] and the language fact notes.
