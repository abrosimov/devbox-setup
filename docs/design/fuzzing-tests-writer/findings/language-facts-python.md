---
note_id: "20261103150302"
created: 2026-11-03
modified: 2026-11-11
language: en
type: design
subtype: finding
note_role: artifact
artifact_kind: finding
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Language facts — Python"]
tags: [fuzzing, design/finding, lang/python, h5, h3, h4]
addresses: ["[[H5-harness-conventions]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]"]
grounded_in: ["[[08-lang-python|R8]]"]
realised_by: ["[[skill-python-fuzzing]]"]
tested_by: ["[[eval-family-E-conventions]]"]
opens: ["[[FTW-OQ-006-hypofuzz-licence]]"]
related: ["[[language-facts-go]]", "[[language-facts-rust]]", "[[fuzzing-vs-pbt-boundary]]", "[[pbt-agent-prompts]]"]
---
# Language facts — Python

[[08-lang-python|R8]] is a historical snapshot of Python fuzzing tools as of 2026-11-03. This pass
uses its Atheris findings as candidates for an adapter; it does not certify current interpreter,
platform, sanitizer or package compatibility. Verify those against the installed versions and
current primary documentation when authoring the Python skill.

## Operations to specify at authoring

| Operation | Python-specific contract | Required evidence |
|---|---|---|
| Discover and load | Follow repository packaging and the selected Atheris entry-point convention | Actual target load and callable invocation; import success alone does not validate a harness |
| Instrument | Instrument the intended Python code and, when applicable, native dependencies | Evidence that known product behaviour is observed; a quiet counter alone does not diagnose missing instrumentation |
| Replay | Execute stored bytes through the same callable, with the fuzz loop separated from ordinary replay where needed | Known valid, expected-invalid and regression cases with observed exits |
| Search | Use supported Atheris/libFuzzer limits for the admitted experiment | Actual supported flags, process timing and raw logs |
| Decode structure | Use a justified fuzzing-side byte decoder or bounded repair | Deterministic mapping, bounds and raw bytes retained |
| Classify failures | Catch specific expected domain exceptions; inspect unexpected diagnostics | Independent reproduction and contract/environment checks before declaring a product bug |
| Preserve and reduce | Retain useful corpus entries and original failures; reduce the same symptom within budget | Durable paths and a verified ordinary replay command |

Native-extension sanitizer builds require a separate compatibility check for the actual compiler,
interpreter and extension. Do not copy historical preload flags, leak settings or platform tables
without verification. Retain partial evidence and useful inputs after interruptions; save callable,
instrumentation and environment context for replay in another session. Process termination and
research closure have different meanings under [[stopping-algorithm]].

## Verification sources and boundaries

Use the primary [Atheris documentation and source](https://github.com/google/atheris) and
[libFuzzer documentation](https://llvm.org/docs/LibFuzzer.html), recording the versions and the
specific operations checked. Follow the existing repository's corpus/test layout rather than
assuming every `corpus/` directory is replayed by pytest.

Hypothesis strategies and tests, HypoFuzz, `fuzz_one_input` bridges and PBT-based API testing are
excluded by [[fuzzing-vs-pbt-boundary]], including pre-existing suites. The historical
[[FTW-OQ-006-hypofuzz-licence]] is therefore not a blocker for this Python adapter. This note
specifies evidence needed at authoring; it does not claim that an Atheris campaign has run.
