---
note_id: "20261103150407"
created: 2026-11-03
modified: 2026-11-04
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
codex_shared: true
related: ["[[reference-documents]]"]
---
# Skill `rust-fuzzing`

**Problem**: Rust targets lose the overflow oracle through `-O`, miss `#![no_main]` or the
workspace member, commit the wrong directories, run on an unpinned nightly, report `tmin` output
as minimal, and proptest tests get written where a fuzz target was asked for.

## Carries (from [[language-facts-rust]])

- Scope rule: cargo-fuzz + ASan for byte/text parsers, decoders, decompressors, deserialisers,
  `unsafe`, FFI; bolero as a harness front-end when one target must run in `cargo test` and under a
  fuzzer; `out-of-scope: pbt-track` for typed laws and model-based state machines (proptest,
  `proptest-state-machine`, quickcheck) ([[fuzzing-vs-pbt-boundary]]).
- `fuzz_target!` + `#[derive(Arbitrary)]` skeleton (R9 §5.1, first block); `Vec<Op>` sequence
  pattern; `fuzz_mutator!` for encoded containers; `Corpus::Reject` for invalid input.
- Twelve-point review checklist (R9 §5.2).
- Layout and git-ignore facts; corpus/artefact commit policy; minimised crashes as `#[test]`
  fixtures or bolero's `__fuzz__`.
- Debug-assertions rule; `cmin` / `tmin` / `coverage` / `fmt`; reading libFuzzer output; stopping
  rule R9 §5.4 in the campaign skill's terms.
- Nightly pinning and the CI recipe (R9 §5.5); OSS-Fuzz / ClusterFuzzLite integration.
- afl.rs / honggfuzz as stable-toolchain alternatives; Miri and Kani as related tools.

## Size and shape

≤ 300 lines. The proptest skeleton of R9 §5.1 is **not** carried; it goes to the PBT track.

## Evals shipped with the skill

Trigger queries: "cargo fuzz target for", "derive Arbitrary", "fuzz/artifacts crash what next",
"ASan for this FFI wrapper"; negatives: "proptest for this struct", "add a benchmark with
criterion". Content evals: R9 §6 E1–E3, E5, E7–E12, with E4 and E6 restated as hand-offs.

Sources: R9 §5.
