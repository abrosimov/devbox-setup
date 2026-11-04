---
note_id: "20261103150407"
created: 2026-11-03
language: en
type: design
subtype: component
note_role: artifact
artifact_kind: skill
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Skill: rust-fuzzing", "rust-fuzzing"]
tags: [fuzzing, design/component, design/skill, lang/rust, h3, h4, h5]
addresses: ["[[H5-harness-conventions]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]"]
realises: ["[[language-facts-rust]]", "[[oracle-ladder]]"]
tested_by: ["[[eval-family-E-conventions]]", "[[eval-family-B-oracle]]"]
decided_by: ["[[FTW-D-002-six-skills]]"]
target_path: "roles/devbox/files/dot_ai/skills/rust-fuzzing/"
codex_shared: true
related: ["[[reference-documents]]"]
---
# Skill `rust-fuzzing`

**Problem**: Rust targets lose the overflow oracle through `-O`, miss `#![no_main]` or the
workspace member, commit the wrong directories, run on an unpinned nightly, and report `tmin`
output as minimal.

## Carries (from [[language-facts-rust]])

- proptest-vs-cargo-fuzz-vs-bolero decision (R9 §5.3).
- `fuzz_target!` + `Arbitrary` skeleton and proptest skeleton (R9 §5.1).
- Twelve-point review checklist (R9 §5.2): `#![no_main]`, `Corpus::Reject`, size bounds,
  determinism, oracle, `Arbitrary` behind a feature, debug assertions, no output/exit, seeds and
  dictionary, reproduction path, regression fixtures, coverage checked once.
- Layout and git-ignore facts; corpus/artifact commit policy per tool.
- `cmin` / `tmin` / `coverage` / `fmt`; reading libFuzzer output; stopping rule R9 §5.4.
- Nightly pinning and the CI recipe (R9 §5.5); OSS-Fuzz / ClusterFuzzLite integration.
- afl.rs / honggfuzz as stable-toolchain alternatives; Miri and Kani as related tools.

## Size and shape

≤ 300 lines.

## Evals shipped with the skill

Trigger queries: "cargo fuzz target for", "derive Arbitrary", "proptest for this struct",
"fuzz/artifacts crash what next"; negatives: "add a benchmark with criterion", "cargo test is
slow". Content evals: R9 §6 E1–E12.

Sources: R9 §5.
