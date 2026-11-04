---
note_id: "20261103150303"
created: 2026-11-03
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

Source: [[09-lang-rust|R9]] (cargo-fuzz 0.13.2, arbitrary 1.5.0, proptest MSRV 1.88, bolero; as of
2026-11-03; nothing was executed in the research session).

| Topic | Fact |
|---|---|
| Tools and the boundary | **cargo-fuzz** (libFuzzer via `libfuzzer-sys`): coverage-guided, needs nightly, parsers/decoders/`unsafe`/FFI with ASan — this agent's engine. **bolero**: hybrid harness front-end (one target as a `#[test]` replaying committed `__fuzz__/<t>/{corpus,crashes}` + 1 s random, and under libFuzzer/AFL/honggfuzz/Kani; stable with `--sanitizer NONE`) — in scope as a fuzz harness. **proptest** / `proptest-state-machine` / quickcheck: property-based testing — **out of scope** ([[fuzzing-vs-pbt-boundary]]). |
| Oracle gap | without `unsafe` the crash oracles are panics (OOB, `unwrap`, overflow with debug assertions, `debug_assert!`), stack overflow, OOM/timeout; trophy case ≈367 rows dominated by those; 8 security-marked rows, all `unsafe`/FFI/C++; logic bugs via round trip (rust-url #729) or reference mismatch. |
| Debug assertions | cargo-fuzz adds `-Cdebug-assertions` by default (overflow checks follow); `-O` turns them off, so OSS-Fuzz's `cargo fuzz build -O` recipe needs `--debug-assertions`; the coverage build forces them off. |
| Layout | `fuzz/Cargo.toml` (`<name>-fuzz`, `publish=false`, `[[bin]] test=false doc=false bench=false`), `fuzz/fuzz_targets/<t>.rs` starting `#![no_main]`, `fuzz/corpus/<t>/`, `fuzz/artifacts/<t>/crash-<sha1>`, `fuzz/coverage/<t>/`; generated `.gitignore` excludes `target corpus artifacts coverage`; add `fuzz` to `workspace.members`. |
| Typed input | `fuzz_target!(|x: T|)` with `#[derive(Arbitrary)]` behind an optional `arbitrary` feature on the library; `arbitrary` is deterministic, pads with zeros when bytes run out, `libfuzzer-sys` rejects inputs shorter than `size_hint`; return `Corpus::Reject` for invalid input; `fuzz_mutator!`/`fuzz_crossover!` for custom mutation (one experiment favours mutation for coverage over time). |
| Flags and output | `-- -max_total_time=S -max_len=N -rss_limit_mb=2048 -dict=…`; libFuzzer defaults `-timeout=1200`, `-rss_limit_mb=2048`, `-max_len` guessed from the corpus; output `cov:` / `ft:` / `corp:` / `NEW` / `REDUCE` (`ft`, `lim`, `L` legend UNVERIFIED — [[FTW-OQ-002-libfuzzer-legend]]). |
| Commands | `cargo fuzz init/add/build/run/list`; `cmin` = `-merge=1`; `tmin` = `-minimize_crash=1 -runs=255`; `coverage` = `-Cinstrument-coverage` over the corpus + `llvm-profdata merge`; `fmt` prints the `Debug` of a typed input; reproduce with `cargo fuzz run <t> fuzz/artifacts/<t>/crash-…`. |
| Regression fixtures | copy the minimised artefact into `tests/fuzz_regressions/<t>/` and replay it from a `#[test]` (stable, no cargo-fuzz needed in `cargo test`); or bolero's committed `__fuzz__`; proptest: commit `proptest-regressions/` (a changed strategy can silently stop a seed reproducing). |
| proptest (boundary facts only) | PBT track. Facts the boundary needs: it persists failing seeds in `proptest-regressions/`; it has no coverage feedback; no proptest/quickcheck finds appear in the trophy case; `proptest-arbitrary-interop` consumes this agent's `Arbitrary` impls on the PBT side. |
| CI | pin `nightly-YYYY-MM-DD` (the book's recipe uses floating `nightly`; OSS-Fuzz uses latest nightly) and `cargo-fuzz --version`; `cargo fuzz build --debug-assertions <t>` as compile check; 300 s smoke per target; upload `fuzz/artifacts` on failure; ClusterFuzzLite `code-change` 600 s / `batch` 3 600 s / `prune` / `coverage` with a storage repo for long runs; keep `cargo test` (proptest/bolero replay) on stable so the oracle survives a broken nightly. |
| Other engines | afl.rs builds on stable (only `-C` flags) unless CMPLOG/plugins; honggfuzz-rs stable; no primary source states a libFuzzer-vs-AFL selection rule. Miri and Kani are related, not fuzzing (run harnesses under Miri; bolero `--engine kani`). |
| Yield evidence | chrono overflow, rmpv 2.9 GB `with_capacity` from a 15-byte input, ron stack overflow on 10 000 `{`, regex `unwrap`/UTF-8 boundary, rust-url round trip; quinn-proto advisories credit *absent* fuzzing coverage (RUSTSEC-2026-0037). |

## Decision rule (R9 §5.3, restated for this agent's scope)

typed invariant → `out-of-scope: pbt-track`; stateful API with a simple model → `out-of-scope:
pbt-track` (a `Vec<Op>` fuzz target with `arbitrary` only when the charter names crash/invariant
objectives); byte/text parser, decoder, decompressor, deserialiser, `unsafe`, FFI → cargo-fuzz +
ASan (+ `Arbitrary`, `fuzz_mutator!` for encoded containers); one harness as unit test and fuzz
target, private functions, or no nightly → bolero as the harness front-end; `serde` derive with no
custom impl, CLI `main` arg parsing, I/O-dominated code → do not fuzz.

Skeletons R9 §5.1; twelve-point review checklist §5.2; CI recipe §5.5.
