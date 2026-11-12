---
name: rust-fuzzing
description: Build, qualify, run and replay cargo-fuzz targets with verified checks and instrumentation, preserving useful corpus and failure artefacts.
---

# Rust fuzzing

Produce a cargo-fuzz harness, qualification evidence and replayable inputs for the assigned Rust
target. Follow the existing research scope and effort limits. New corpora can support bounded
reconnaissance before a precise hypothesis exists. PBT, proptest bridges and mutation analysis
are outside this workflow; fuzz-input mutation and bounded decoding remain available.

## Establish the local basis

- Read repository instructions, `Cargo.toml`, lockfiles, `rust-toolchain.toml`, existing `fuzz/`
  configuration and the target contract. Prefer existing commands and fuzz targets.
- Record `rustc --version`, cargo-fuzz version, target triple, features, sanitiser, profile and
  relevant commit/dirty changes. Check the installed `cargo fuzz --help` and subcommand help.
- Use the project's compatible installed toolchain. The documented sanitised cargo-fuzz path uses
  nightly; an uninstrumented stable build is not equivalent. Do not switch the global default,
  install toolchains/dependencies or regenerate locks without existing authorisation.
- Recover the previous result and unfinished operation. Choose the current contribution: inspect
  unfamiliar inputs, exercise a stated behaviour or answer a formulated question.

## Construct and qualify

Place a target in the existing fuzz package using `#![no_main]` and
`libfuzzer_sys::fuzz_target!`. Feed `&[u8]` to the owned boundary or decode it deterministically.
Use a fuzzing decoder such as `arbitrary` only where supported by the target's existing dependencies
or authorised additions. Bound collection sizes, recursion and operation sequences; keep the raw
bytes and decoder version. Reset state between inputs.

Interpret expected parse errors and API preconditions from the contract. An `unwrap()` on ordinary
invalid-input rejection can create a harness failure. Keep unexpected panics and sanitiser reports
visible; do not mask them with blanket panic-catching. Define semantic equality for round trips
and shared domains for differential checks rather than asserting identical serialised spelling.

Build the actual target with its intended features/profile. Check that features requested on the
fuzz package reach the product crate and that relied-on checks remain enabled: a disabled
`debug_assert!` cannot support an oracle claim. Do not add `cfg(fuzzing)` production bypasses merely
to reach deeper paths. Keep invalid-input coverage alongside valid structured generation.

Replay independently expected valid and rejected inputs and any known failing input. Demonstrate
that the intended product call and oracle execute; successful compilation alone is insufficient.
For native/unsafe findings retain the sanitiser configuration and diagnostic. Verify instrumentation
of the code involved rather than extrapolating from one instrumented dependency.

## Execute and replay

Examples use an already installed compatible nightly, target `decode`, and an existing fuzz package.
Use the project's pinned toolchain in place of `nightly`, actual paths and justified limits.

```text
cargo +nightly fuzz list
cargo +nightly fuzz build decode
cargo +nightly fuzz run decode fuzz/corpus/decode/valid-seed
cargo +nightly fuzz run decode fuzz/corpus/decode -- -max_total_time=30
cargo +nightly fuzz run decode fuzz/artifacts/decode/<saved-crash>
```

The arguments after `--` go to libFuzzer. A file is replayed; a corpus directory enables search.
Verify that each expected case actually ran. For ordinary replay of all retained seeds, use explicit
files or the repository's runner; plain `cargo test` does not automatically execute cargo-fuzz corpora.
`-max_total_time` bounds search; `-timeout` checks a single input. Set resource and size limits to
the experiment, and retain setup, compilation and reduction effort in its record.

For justified failure reduction, inspect `cargo fuzz tmin --help`, preserve the original, then use
the target and failing file with a finite attempt limit. Record both cargo-fuzz's outer attempts
and any per-attempt engine limits; their product is not a universal research deadline. Reproduce
the same relevant symptom independently before accepting the reduced file. Corpus minimisation
is a separate operation and must not discard a useful structured example merely for shared coverage.

## Preserve and continue

Keep useful corpus inputs and original failure artefacts in durable repository-approved locations,
with their target, configuration, provenance and verified replay command. A discovered input need
not crash to remain useful for replay. The engine's active corpus is not the only retention policy.

On interruption, preserve the question/learning aim, operative method, completed replays, unfinished
check, original and last verified reduced input, assumptions and cumulative effort. On return,
inspect changed code, features, decoder and oracle conditions; reuse unaffected evidence and perform
the next justified operation. Another commit or session does not reset the research. New input
families may justify a different in-scope question while earlier questions stay closed.

Return harness changes, actual commands/exits, build and instrumentation evidence, useful corpus,
reproducers and replay results. Separate confirmed product failure, harness/oracle error, environment
failure, unconfirmed failure and no finding. Report product defects; correct authored harness
defects within scope. State unfinished work and the research disposition separately from process
exit. Retention does not grant commit or publication authority.

## Primary references

Checked 2026-11-12; installed subcommand help governs the actual invocation:

- [Rust Fuzz Book setup](https://rust-fuzz.github.io/book/cargo-fuzz/setup.html) — toolchain prerequisites.
- [Tutorial](https://rust-fuzz.github.io/book/cargo-fuzz/tutorial.html) and
  [guide](https://rust-fuzz.github.io/book/cargo-fuzz/guide.html) — targets, features and engine arguments.
- [cargo-fuzz commands](https://github.com/rust-fuzz/cargo-fuzz/tree/main/src/options) — build, replay
  and reduction argument definitions when the book leaves a command ambiguous.
- [libFuzzer options](https://llvm.org/docs/LibFuzzer.html#options) — corpus/file replay and run limits.
