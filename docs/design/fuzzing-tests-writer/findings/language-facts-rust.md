---
note_id: "20261103150303"
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
aliases: ["Language facts — Rust"]
tags: [fuzzing, design/finding, lang/rust, h5, h3, h4]
addresses: ["[[H5-harness-conventions]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]"]
grounded_in: ["[[09-lang-rust|R9]]"]
realised_by: ["[[skill-rust-fuzzing]]"]
tested_by: ["[[eval-family-E-conventions]]"]
opens: ["[[FTW-OQ-005-cargo-fuzz-on-stable]]"]
related: ["[[language-facts-go]]", "[[language-facts-python]]"]
---
# Language facts — Rust

[[09-lang-rust|R9]] is a historical snapshot of cargo-fuzz, `libfuzzer-sys`, `arbitrary` and related
tools as of 2026-11-03; the research session did not execute them. Current nightly/stable support,
platform requirements and default flags require primary-source and local verification at
skill authoring. They are not established by this methodology revision.

## Operations to specify at authoring

| Operation | Rust-specific contract | Required evidence |
|---|---|---|
| Discover and build | Use the repository's fuzz manifest and target conventions with the selected toolchain | Actual target discovery and compilation, recording toolchain and instrumentation |
| Replay seeds | Load stored engine bytes through the same target/decoder | Verified corpus replay; a separate ordinary test adapter where the repository requires it |
| Search | Use supported cargo-fuzz/libFuzzer limits for the admitted experiment | Actual commands, raw output, exits and process timing |
| Decode structure | Use a justified `arbitrary`/byte decoder with explicit size and recursion bounds | Input exhaustion/rejection behaviour, decoder version and raw bytes retained |
| Check memory/logic | Use relevant sanitizer, panic/resource and contract checks | Build flags and contract evidence; memory-safe code can still have logic/resource defects |
| Reduce and preserve | Retain originals and useful seeds; bound corpus/failure reduction | Same-symptom reproduction and durable replay paths |

A successful search command does not establish that ordinary `cargo test` replays its corpus.
Verify that handover explicitly. Likewise, record debug assertion, overflow and sanitizer settings
rather than assuming a development or optimised build has the same oracle. Reproduction must
retain the decoder and configuration that make the bytes meaningful.

## Verification sources and boundaries

Use the primary [cargo-fuzz book](https://rust-fuzz.github.io/book/cargo-fuzz.html),
[cargo-fuzz source](https://github.com/rust-fuzz/cargo-fuzz),
[`arbitrary` documentation](https://docs.rs/arbitrary/latest/arbitrary/) and matching tool
versions. [[FTW-OQ-005-cargo-fuzz-on-stable]] and [[FTW-OQ-002-libfuzzer-legend]] identify details
that must be settled for a concrete adapter, not prerequisites for endless methodology research.

The default specification centres on cargo-fuzz and direct fuzzing-side decoding. An existing
alternative harness may be assessed within the authorised task, but does not add an engine
portfolio or separate infrastructure project. PBT suites and bridges are excluded by
[[fuzzing-vs-pbt-boundary]]. Preserve build, retry, reduction and replay observations with their
configuration in the research history. Neither a historical time recipe nor a new agent session
justifies another experiment; use the continuation rules in [[stopping-algorithm]].
