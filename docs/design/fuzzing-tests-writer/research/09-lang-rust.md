# Rust fuzzing and property-based testing ecosystem — what a fuzz-writing agent must know

Research date: 2026-11-03. Method note: the hosts `rust-fuzz.github.io`, `docs.rs`, `proptest-rs.github.io`, `google.github.io`, `llvm.org` and `dwrensha.github.io` were not resolvable from this session, so every "book" or "docs" claim below was taken from the **source repositories on GitHub** (raw Markdown / Rust source) that render those sites. Locators therefore name repo paths; the rendered URL is given where known. No toolchain was available locally (Bash was denied), so nothing was executed; anything that would need a run is marked UNVERIFIED.

## 0. Summary for the design doc

1. **Three tools, three niches; the agent needs a decision rule, not a default.** `cargo fuzz` (libFuzzer via `libfuzzer-sys`) is the community's recommended coverage-guided fuzzer, needs **nightly** (README, S2) and is positioned for parsers/decoders/`unsafe`/FFI with ASan. `proptest` is typed, stable-toolchain, runs under `cargo test`, 256 cases by default, persists failing **seeds** in `proptest-regressions/` (S6). `bolero` is the only tool that runs the *same* target as a `#[test]` (replaying a committed `__fuzz__/<target>/{corpus,crashes}` directory plus 1 s of random inputs) and under libFuzzer/AFL/honggfuzz/Kani (S5). Addresses H1/H5.
2. **Oracle gap is real in Rust (H4).** With no `unsafe`, the only crash oracles are panics (OOB index, `unwrap`, overflow with debug assertions, `debug_assert!`), stack overflow, OOM/timeout. The trophy case (~367 rows, S11) is dominated by `panic/arith/oom/so/loop`; only 8 rows are marked security, all in `unsafe`/FFI/C++ code. Round-trip and differential properties are the way to find logic bugs: rust-url #729 (round-trip), lzma-rs (reference mismatch), reth/ruint (encode-decode mismatch) — S11, S18.
3. **cargo-fuzz enables debug assertions (and therefore overflow checks) by default**: `-a/--debug-assertions` help text "(default if not -O)"; `project.rs` adds `-Cdebug-assertions` when `!release || debug_assertions || careful`; rustc defaults `overflow-checks` to the `debug-assertions` value (S2, S14). `-O` turns them off, which is why OSS-Fuzz's guide says to add `--debug-assertions` to `cargo fuzz build -O` (S9). An agent that builds with `-O` alone loses the main Rust oracle.
4. **Structure-aware input is first-class (H3):** `fuzz_target!(|x: T|)` with `#[derive(Arbitrary)]`; `arbitrary` is deterministic, pads with zeros when bytes run out, and `libfuzzer-sys` rejects (`-1`) inputs too short for `size_hint` so the fuzzer does not explore "not enough bytes" paths (S3, S4). The Rust Fuzz Book records that a `fuzz_mutator!`-based custom mutator gave better coverage over time than `Arbitrary` generation in one experiment (S1 structure-aware chapter) — the two are not mutually exclusive.
5. **Stopping/continuation (H2):** libFuzzer has no built-in saturation rule; the libFuzzer tutorial says to judge by `cov:` no longer growing and to time-box with `-max_total_time` (S13). The Rust Fuzz Book's CI recipe runs each target 300 s with `-max_total_time`, pins `cargo-fuzz` to a version but **not** the nightly date (S1 ci.md). ClusterFuzzLite layers `code-change` (600 s) / `batch` (3600 s) / `prune` / `coverage` modes (S10). `cargo fuzz cmin` = `-merge=1`; `tmin` = `-minimize_crash=1 -runs=N`; `cargo fuzz coverage` = `-Cinstrument-coverage` over the corpus + `llvm-profdata merge` (S2 project.rs, S1 coverage.md).
6. **Layout conventions the generator must respect (H5):** `fuzz/Cargo.toml` (`<name>-fuzz`, `publish=false`, `[[bin]] test=false doc=false bench=false`), `fuzz/fuzz_targets/<t>.rs` starting `#![no_main]`, `fuzz/corpus/<t>/`, `fuzz/artifacts/<t>/crash-<sha1>`, `fuzz/coverage/<t>/`; the generated `.gitignore` excludes `target corpus artifacts coverage` (S2 templates.rs). So the **default is not to commit corpus/artifacts**; crash inputs become regression tests by copying them under `tests/` (community pattern, S19) or by using bolero, whose corpus is meant to be committed (S5).
7. **Reproduction**: `cargo fuzz run <t> fuzz/artifacts/<t>/crash-…` (artifact passed as positional input); `cargo fuzz fmt <t> <input>` prints the `Debug` of the typed input via `RUST_LIBFUZZER_DEBUG_PATH` (S2, S3).
8. **Decision rule** (§5.3): pure typed invariant, stable-only CI → `proptest`; byte/format parser, decoder, `unsafe`, FFI → `cargo fuzz` + ASan (+ `Arbitrary` for typed APIs); want one harness in `cargo test` *and* under a fuzzer, or private fns → `bolero`; `serde` derive with no custom impl, CLI arg parsing in `main`, code with I/O or process exit → unit tests / do not fuzz.
9. **Open:** sanitizer stabilisation (rust-lang/rust#123617) is still open; `cargo-fuzz` code carries a placeholder "release that stabilised sanitizers = u32::MAX" (S2 rustc_version.rs). Whether `cargo fuzz build -s none` works on stable is UNVERIFIED (afl.rs demonstrably builds on stable with the same `-C passes=sancov-module` flags, S15).

## 1. Scope and question answered

What an agent that writes Rust fuzz and property tests must know about: cargo-fuzz/libfuzzer-sys, afl.rs, honggfuzz-rs, `arbitrary`, bolero, proptest (+ state-machine, arbitrary-interop), quickcheck; OSS-Fuzz / ClusterFuzzLite / CI integration; the bug classes fuzzing actually finds in safe vs unsafe Rust; conventions (layout, determinism, corpus/artifact handling, minimisation, coverage); and a decision rule between the tools. Kani and Miri are covered only as "related, not fuzzing".

## 2. Corpus ledger

| id | source + edition/date | locator | used for | status |
|---|---|---|---|---|
| S1 | The Rust Fuzz Book, repo `rust-fuzz/book` master, fetched 2026-11-03 (renders at rust-fuzz.github.io/book) | `src/SUMMARY.md`, `introduction.md`, `cargo-fuzz.md`, `cargo-fuzz/{setup,tutorial,guide,structure-aware-fuzzing,oracles-accessing-data,coverage,targets,ci}.md`, `afl.md`, `afl/{setup,tutorial}.md`, `trophy-case.md` | cargo-fuzz workflow, nightly rationale, structure-aware chapter, CI recipe, afl.rs | include |
| S2 | `rust-fuzz/cargo-fuzz` main; CHANGELOG latest 0.13.2 (2026-06-09) | `README.md`, `src/options.rs`, `src/options/run.rs`, `src/project.rs`, `src/templates.rs`, `src/rustc_version.rs`, `CHANGELOG.md` | exact flags, defaults, rustflags, layout, cmin/tmin/coverage internals | include |
| S3 | `rust-fuzz/libfuzzer` main (libfuzzer-sys 0.4.x) | `README.md`, `src/lib.rs`, vendored `libfuzzer/FuzzerFlags.def` | `fuzz_target!`, `Corpus`, `fuzz_mutator!`, `fuzz_crossover!`, libFuzzer flag defaults | include |
| S4 | `rust-fuzz/arbitrary` main; CHANGELOG latest 1.5.0 (2026-10-05); MSRV 1.71→raised in 1.5.0 | `README.md`, `src/lib.rs`, `src/unstructured.rs`, `CHANGELOG.md` | trait semantics, out-of-data behaviour, determinism, derive attrs | include |
| S5 | `camshaft/bolero` master (README, book `book/src/**`, `lib/bolero/src/lib.rs`, `lib/bolero/src/test/mod.rs`, `lib/bolero-engine/src/{rng,target_location}.rs`, `bin/cargo-bolero/src/{test,test_target}.rs`) | as listed | unified harness, `cargo test` replay, `__fuzz__` layout, engines, stable support | include |
| S6 | `proptest-rs/proptest` main (`proptest/README.md`; book `book/src/proptest/{failure-persistence,limitations,state-machine,tips-and-best-practices,forking}.md`, `tutorial/config.md`; `proptest/src/test_runner/config.rs`; `proptest-state-machine/README.md`); MSRV 1.88 | as listed | strategies vs QuickCheck, config defaults, persistence, state-machine testing, limitations | include |
| S7 | `graydon/proptest-arbitrary-interop` README | `README.md` | reuse of `Arbitrary` impls as proptest strategies | include |
| S8 | `BurntSushi/quickcheck` README (MSRV 1.85) | `README.md` | status, shrinking, limits, its own pointer to proptest/arbitrary | include |
| S9 | OSS-Fuzz, `google/oss-fuzz` master | `docs/getting-started/new-project-guide/rust_lang.md`, `infra/base-images/base-builder/{install_rust.sh,cargo}` | Rust integration, `-O` + `--debug-assertions`, nightly in builder, coverage wrapper | include |
| S10 | ClusterFuzzLite, `google/clusterfuzzlite` main | `docs/build-integration/rust_lang.md` (same text as S9 guide), `docs/running-clusterfuzzlite/github_actions.md` | CI modes and budgets | include |
| S11 | `rust-fuzz/trophy-case` master README (≈367 rows) | README table + legend | bug classes, fuzzers used, security marking | include |
| S12 | RustSec advisory-db main: RUSTSEC-2018-0004 (claxon), RUSTSEC-2022-0068 (capnp; via osv.dev summary), RUSTSEC-2023-0063 & RUSTSEC-2026-0037 (quinn-proto), RUSTSEC-2026-0041 (lz4_flex) | `crates/<crate>/<id>.md` | advisories tied to fuzzing (and to its absence) | include |
| S13 | `google/fuzzing` master: `docs/good-fuzz-target.md`, `tutorial/libFuzzerTutorial.md`, `docs/structure-aware-fuzzing.md` | as listed | target hygiene, reading libFuzzer output, `-max_len` default, when to stop | include |
| S14 | rustc book `src/doc/rustc/src/codegen-options/index.md`; unstable book `compiler-flags/sanitizer.md`; rust-lang/rust PR #123617 (open at fetch) | as listed | `debug-assertions`/`overflow-checks` defaults; `-Zsanitizer` nightly status | include |
| S15 | `rust-fuzz/afl.rs` master: README, `CHANGES.md` (0.18.2, AFL++ 4.40c), `cargo-afl/src/main.rs` | as listed | AFL++ flags, stable vs nightly, `fuzz_with_reset!`, CMPLOG | include |
| S16 | `rust-fuzz/honggfuzz-rs` master README | `README.md` | third engine; stable support; sanitizers via RUSTFLAGS | include |
| S17 | `rust-lang/miri` README; `model-checking/kani` README | as listed | relation, not fuzzing | include |
| S18 | Issue trackers: servo/rust-url #729; ron-rs/ron #307; 3Hren/msgpack-rust #151; chronotope/chrono #941; rust-url PR 108 (via S1 tutorial) | GitHub issue pages | micro-examples of bug classes and oracles | include |
| S19 | Community regression patterns: `ruzstd` `src/tests/fuzz_regressions.rs`; regex-automata `tests/fuzz/sparse.rs` (`include_bytes!` of minimised crashes); rust-lightning PR #4645 | via web search results | "artifact → `#[test]`" convention | include (secondary) |
| S20 | Third-party "cargo fuzz" skill pages (trailofbits et al.) | web search | only confirm `cargo +nightly fuzz run --sanitizer none` idiom | park (restatement) |
| S21 | rust-lang project goals "Stabilize MemorySanitizer and ThreadSanitizer" 2025h2/2026 | goals.rust-lang.org pages via search | ASan/LSan "close to stabilised"; new `x86_64-unknown-linux-gnuasan` Tier 2 target | include (context) |

## 3. Claim sheets

### 3.1 cargo-fuzz + libfuzzer-sys (coverage-guided greybox, libFuzzer lineage)

| # | Claim | Source | Validity region / failure modes | Confidence |
|---|---|---|---|---|
| C1 | cargo-fuzz "is itself not a fuzzer, but a tool to invoke a fuzzer"; the only supported engine is libFuzzer via `libfuzzer-sys` (0.13.2 added `--fuzz-engine` to `init`, with a `libafl_libfuzzer` template variant). | S1 `cargo-fuzz.md`; S2 CHANGELOG 0.13.2, templates.rs | — | high |
| C2 | Nightly required: README says it "uses unstable command-line flags"; setup.md says because of `-Z` for address sanitisation. Code: `-Zsanitizer=<s>` unless `has_sanitizers_on_stable()`, whose threshold is a `u32::MAX` placeholder; nightly detected by `-nightly ` in `rustc -V` or `RUSTC_BOOTSTRAP`. | S2 README, rustc_version.rs, project.rs; S1 setup.md | With `--sanitizer none` no `-Z` flag is emitted (only `-C` flags and `--cfg fuzzing`); whether that builds on stable is UNVERIFIED. | high (nightly) / low (stable with `-s none`) |
| C3 | Platforms: README "only works on x86-64 and Aarch64" and "Unix-like" only; setup.md lists x86-64 Linux, x86-64/aarch64 macOS and Windows (MSVC ASan); 0.13.0 added "basic support for fuzzing on windows via `--no-include-main-msvc`". | S2 README, CHANGELOG 0.13.0; S1 setup.md | README is stale on Windows (see §4 D1). | high |
| C4 | Build flags always set: `-Cpasses=sancov-module`, `-Cllvm-args=-sanitizer-coverage-level=4`, `-inline-8bit-counters`, `-pc-table`, `-trace-compares` (unless `--no-trace-compares`), `--cfg fuzzing` (unless `--no-cfg-fuzzing`), `-Cllvm-args=-simplifycfg-branch-fold-threshold=0`; `-Ccodegen-units=1` in non-dev builds; default build is cargo `--release` profile with `profile.release.debug="line-tables-only"`; `-Cdebug-assertions` added when `!release || debug_assertions || careful`; user `RUSTFLAGS` appended last (can override). | S2 project.rs | — | high |
| C5 | **Debug assertions on by default**: `-a/--debug-assertions` help: "Build artifacts with debug assertions and overflow checks enabled (default if not -O)"; `-O/--release` turns them off; CHANGELOG 0.8.0: builds default to optimisations *and* debug assertions. rustc: `overflow-checks` "enabled if debug-assertions are enabled, disabled otherwise". | S2 options.rs, CHANGELOG 0.8.0; S14 codegen-options | Agents that copy OSS-Fuzz's `cargo fuzz build -O` without `--debug-assertions` lose integer-overflow and `debug_assert!` oracles. | high |
| C6 | Sanitizer option `-s/--sanitizer`: `address` (default), `leak`, `memory` (adds `-Zsanitizer-memory-track-origins`, needs `-Zbuild-std`), `thread`, `none`. ASAN_OPTIONS gets `detect_odr_violation=0`. | S2 options.rs, project.rs | ASan matters only across `unsafe`/FFI (see 3.7); costs ~2× throughput (S20, restatement). | high |
| C7 | Layout: `fuzz/Cargo.toml` package `<name>-fuzz` v0.0.0 `publish=false`, `cargo-fuzz = true` metadata, dep `libfuzzer-sys = "0.4"`, path dep on parent; per target `[[bin]] name/path = "fuzz_targets/<t>.rs"`, `test=false doc=false bench=false`; target file begins `#![no_main]` + `use libfuzzer_sys::fuzz_target;`; `.gitignore`: `target corpus artifacts coverage`. Workspaces: add `fuzz` to `workspace.members` or `cargo fuzz init --fuzzing-workspace=true` (default since 0.11.4 is *not* a separate workspace). | S2 templates.rs, README, CHANGELOG 0.11.4 | A target file without `#![no_main]`, or a workspace that omits `fuzz`, fails to build (H5). | high |
| C8 | Directories: corpus `fuzz/corpus/<t>`, artifacts `fuzz/artifacts/<t>/` (trailing slash required by libFuzzer, passed as `-artifact_prefix=`), coverage `fuzz/coverage/<t>/{raw,coverage.profdata}`; `--fuzz-dir` relocates. | S2 project.rs, CHANGELOG 0.10.2 | — | high |
| C9 | Commands: `init`, `add`, `build`, `run <t> [corpus dirs or artifact files] [-- libFuzzer args]`, `-j/--jobs N` → `-fork=N`, `fmt <t> <input>` (Debug of input via `RUST_LIBFUZZER_DEBUG_PATH`), `tmin <t> <input>` → `-minimize_crash=1 -runs=N`, `cmin <t>` → `-merge=1` into temp dir then swap, `coverage <t>` → `-Cinstrument-coverage`, one `.profraw` per corpus file, `llvm-profdata merge -sparse`, then `cargo cov -- show <bin> --format=html -instr-profile=…` (needs `llvm-tools-preview`, cargo-fuzz ≥ 0.10). Single-letter aliases since 0.13.0. `list` lists targets. | S2 README, project.rs, CHANGELOG; S1 coverage.md | `cargo fuzz run` sets no `-runs`/`-max_total_time` itself; budgets are pass-through only. | high |
| C10 | `fuzz_target!` forms: `|data: &[u8]|`; `|x: T|` for any `T: Arbitrary` (decoded with `arbitrary_take_rest`; **early-exit `-1` if `len < size_hint` lower bound** "so the fuzzer avoids exploring not-enough-input-bytes paths"; decode failure also returns `-1`); `init:` block run once; return `Corpus::Keep`/`Corpus::Reject` (`()` ⇒ keep). Docs: "The parsing might fail and return an `Err`, but it shouldn't ever panic or segfault." | S3 lib.rs | Typed targets never see the raw bytes; reject (`-1`) tells libFuzzer not to add to corpus. | high |
| C11 | `fuzz_mutator!(|data, size, max_size, seed|)` must mutate in place, return new size ≤ `max_size`, and "produce the same mutation given the same `seed`"; `libfuzzer_sys::fuzzer_mutate` exposes `LLVMFuzzerMutate`. `fuzz_crossover!` combines two inputs; same determinism rule. Canonical example: decompress → mutate → recompress. | S3 lib.rs; S1 structure-aware; S13 structure-aware-fuzzing.md | Non-deterministic mutators break reproduction. | high |
| C12 | `#[cfg(fuzzing)]` is set for every instrumented crate incl. dependencies (`--cfg fuzzing`); use `#[cfg(not(fuzzing))]` to skip e.g. signature checks; fuzz-only deps go in `[target.'cfg(fuzzing)'.dependencies]`; share helpers with `#[cfg(any(test, fuzzing))]`. 0.12.0 removed `cfg(fuzzing_repro)` on reproduce because it forced recompiles. | S1 guide.md; S9 rust_lang.md; S2 CHANGELOG 0.12.0 | — | high |
| C13 | libFuzzer flag defaults (vendored): `-max_len=0` (guess from corpus; tutorial: "assumes all inputs are 4096 bytes or smaller" absent a corpus), `-len_control=100`, `-runs=-1`, `-max_total_time=0`, `-timeout=1200`, `-rss_limit_mb=2048`, `-malloc_limit_mb=0` (= rss limit), `-dict=`, `-only_ascii=0`, `-seed=0` (random), `-use_value_profile=0`, `-reduce_inputs=1`, `-fork=0`, `-jobs/-workers=0`, exit codes timeout 70 / error 77; list all with `-- -help=1`. | S3 FuzzerFlags.def; S13 libFuzzerTutorial; S1 guide.md | Defaults mean a 2 GiB allocation from an untrusted length is reported as OOM; one slow input ≥ 20 min as timeout. | high |
| C14 | Reading output: `cov:` = coverage points ("think of them as basic blocks"), `corp: N/Sb` = retained inputs/total size, `NEW` = input added coverage, `RELOAD` = picked up others' finds, `INITED cov:` after seed corpus load. Stop heuristics: "fuzzer stops finding new coverage every few seconds", "running millions of inputs but can not find many new code paths"; time-box with `-max_total_time`. | S13 libFuzzerTutorial | Meaning of `ft:` (features), `lim:` (current max len), `L:` (avg len), `exec/s`, `rss` — UNVERIFIED from a primary source here (LibFuzzer.rst unreachable). | medium |
| C15 | Reproduce: artifact path is a positional "corpus" arg → `cargo fuzz run <t> fuzz/artifacts/<t>/crash-<sha1>`; cargo-fuzz prints "Reproduce with: cargo fuzz run{fuzz_dir}{options} {target} {artifact}" preserving build flags (fixed for tmin in 0.11.1). Tutorial: "Test unit written to …/fuzz/artifacts/<t>/crash-e9b1b5…"; "It is generally a good idea to check in the files generated by `init`." | S2 project.rs, CHANGELOG; S1 tutorial.md | — | high |
| C16 | CI recipe (book): GitHub Actions matrix over target names, nightly channel (unpinned date), `cargo-fuzz` pinned (0.12.0 in the chapter) and cached, `cargo fuzz build` then `cargo fuzz run <t> -- -max_total_time=300`, upload `fuzz/artifacts` on failure. | S1 ci.md | Unpinned nightly can break builds unrelated to code changes (see §5.5). | high |
| C17 | Oracles that access data: for callback/reference-returning APIs ASan only fires on *access*, so the harness must read every element (via `core::hint::black_box`); the `touched` crate helps. | S1 oracles-accessing-data.md | FFI/unsafe-API targets only. | high |

### 3.2 `arbitrary` (structure-aware generation from bytes)

| # | Claim | Source | Validity / failure modes | Confidence |
|---|---|---|---|---|
| A1 | Purpose: "produce well-typed, structured values, from raw, byte buffers"; intended for AFL/libFuzzer; derive (`features=["derive"]`) recommended over hand impls; field attrs `#[arbitrary(default)]`, `#[arbitrary(value = …)]`, `#[arbitrary(with = fn_or_closure)]`, `#[arbitrary(skip)]` on enum variants (1.4.0). | S4 README, CHANGELOG | — | high |
| A2 | Out-of-data: implementations "may fill out the rest of `Self` with dummy values" to "avoid infinite recursion"; `Unstructured` pads reads with zeros, `int_in_range` returns `range.start()`, `choose` first item, `ratio` true, `bytes()` errors (`NotEnoughData`); `exhausted_entropy` test shows `false/0/None`. Bias: "probability distribution … is not necessarily uniform"; 1.4.2 documented this. | S4 lib.rs, unstructured.rs, CHANGELOG 1.4.2 | Short inputs collapse to all-zero values → corpus full of near-identical structures unless the harness rejects (`Corpus::Reject`) or libfuzzer-sys's size_hint exit cuts them (C10). | high |
| A3 | Determinism: "`Unstructured` is deterministic: given the same raw data, the same series of API calls will return the same results." Design intent: small input change ⇒ small output change, so byte-level mutation still explores structure; but "makes no guarantee that it will yield bytes … in any particular order". | S4 unstructured.rs | Hand impls that read from external state break reproducibility. | high |
| A4 | API: `arbitrary(&mut Unstructured)`, `arbitrary_take_rest` (last consumer, may use all bytes), `size_hint(depth) -> (usize, Option<usize>)` ("must be possible to construct every possible output using only inputs of lengths bounded by these"), `try_size_hint` (1.4.0, keeps recursion-limit info); `arbitrary_len` for collection sizes ("Do not use `int_in_range` to generate the size of a collection"); `arbitrary_iter`/`arbitrary_take_rest_iter`; `choose`, `choose_index`, `ratio`, `peek_bytes`, `take_rest`, `is_empty`. | S4 lib.rs, unstructured.rs | Wrong `size_hint` ⇒ either useless early exits or none. | high |
| A5 | MSRV 1.71.0 stated in README; 1.5.0 (2026-10-05) raised MSRV via `syn` 3 (exact value truncated in fetch). | S4 README, CHANGELOG | Pin `arbitrary = "1"` in both lib (optional feature) and fuzz crate. | medium |
| A6 | Book pattern: `#[cfg_attr(feature = "arbitrary", derive(arbitrary::Arbitrary))]` on the library type with `arbitrary = { version = "1", optional = true, features = ["derive"] }`; the fuzz crate enables the feature. Example targets: `Rgb` → HSL → `Rgb` round trip; `Vec<AllocatorMethod>` driving an allocator; differential map vs `HashMap` with `mutatis`-based custom mutator. | S1 structure-aware chapter | — | high |
| A7 | The chapter reports "an experiment has shown that `fuzz_mutator!`-based mutation provides better coverage over time" than generation, while noting the two are complementary. | S1 structure-aware chapter | One experiment, unspecified target: weak generalisation. | medium |

### 3.3 bolero (unified harness; PBT + fuzzing)

| # | Claim | Source | Validity / failure modes | Confidence |
|---|---|---|---|---|
| B1 | "fuzz and property testing front-end for Rust"; a target is an ordinary `#[test]` calling `bolero::check!()` with `.with_type::<T>()` (needs `TypeGenerator`), `.with_generator(gen)`, `.with_arbitrary::<T>()` (feature `arbitrary`), `.for_each(|x| …)`; `.cloned()` for owned values; `fuzz!` is deprecated in favour of `check!`. Can live inside the crate (private functions testable) or in `tests/<target>/main.rs`. | S5 README, lib.rs, private-testing.md | Macro form `check!(|input| …)` "can trip up some editors". | high |
| B2 | Engines: `cargo bolero test <t> --engine libfuzzer|afl|honggfuzz|kani` (libfuzzer default); Kani targets need `#[cfg_attr(kani, kani::proof)]`. | S5 unified-interface.md | Kani is bounded model checking, not fuzzing (see 3.8). | high |
| B3 | Stable: "doesn't require nightly" — `cargo bolero test t --sanitizer NONE`; a sanitizer flag makes it run `cargo +nightly`; `--toolchain nightly-2020-01-01` pins. | S5 rust-stable.md | — | high |
| B4 | Under plain `cargo test` the `TestEngine` replays, in order: fixed seed (if `BOLERO_RANDOM_SEED`), files under `<dir of file!()>/__fuzz__/<test_name>/` → `crashes`, `afl_state/crashes`, `afl_state/hangs`, `corpus`, `afl_state/queue`; then random inputs for `test_time` (default **1 s**, or `BOLERO_RANDOM_ITERATIONS` iterations), `max_len` default 4096 (1024 under Miri); shrinks failures; prints `[BOLERO_RANDOM_SEED=…]`. Book: corpus "should either be committed to the project repository" or stored externally (S3-style). Test name derivation strips `test_`/`fuzz_` prefixes and `_test`/`_fuzz` suffixes. | S5 test/mod.rs, rng.rs, target_location.rs, corpus-replay.md | 1 s of random inputs per test is a smoke test, not fuzzing; CI value comes from the committed corpus/crashes. | high |
| B5 | `cargo bolero test` options: `-e/--engine`, `-S` seed, `-r/--runs`, `-T` time, `-l/--max-input-length`, `-t/--timeout` (default 10 s), `-j/--jobs`, `--corpus-dir`, `--crashes-dir`, `-E/--engine-args`; `cargo bolero new`, `reduce`, `list` exist (files `new.rs`, `reduce.rs`, `list.rs`). | S5 test.rs, directory listing | — | high |
| B6 | Structured testing: derive `TypeGenerator` for an `Operation` enum, `check!().with_type::<Vec<Operation>>()` (default len `0..=64`; `gen::<Vec<_>>().with().len(0..=200)`), run same ops against `HashSet` and assert `set.iter().eq(oracle.iter())` — "checks that `MySet` behaves correctly, not just that it doesn't panic". Fibonacci tutorial: "basic fuzz testing can only get you so far" (a `42`-returning stub passes) → add known-value and differential oracles. | S5 structured-testing.md, fibonacci.md | — | high |
| B7 | Shrinking supported "for all of its testing engines"; Miri: `MIRIFLAGS="-Zmiri-disable-isolation" cargo +nightly miri test` to read the corpus; "significantly slower". | S5 input-shrinking.md, miri.md | — | high |
| B8 | Trophy case lists bolero finds (chrono `checked_add_days` panic found "cargo-bolero-fuzzing my web server, without actually trying to fuzz chrono itself"; risuto DoS ×2). | S11; S18 chrono #941 | — | high |

### 3.4 proptest (property-based testing, QuickCheck/Hypothesis lineage)

| # | Claim | Source | Validity / failure modes | Confidence |
|---|---|---|---|---|
| P1 | Core difference from QuickCheck: values come from explicit `Strategy` objects, not the type alone → many strategies per type, per-value ranges, composition by tuple+`prop_map`, constraint-aware shrinking; cost: "up to an order of magnitude slower" generation because intermediate state is kept for shrinking. | S6 README "Differences between QuickCheck and Proptest" | — | high |
| P2 | `proptest!` macro with `#![proptest_config(ProptestConfig::with_cases(1000))]`; `prop_compose!`; `prop_oneof!`; regex strategies (`"[0-9]{4}-…"`); `proptest-derive` for `Arbitrary`. | S6 README, tutorial/config.md, SUMMARY | — | high |
| P3 | Config defaults (`config.rs`): `cases=256`, `max_local_rejects=65536`, `max_global_rejects=1024`, `max_flat_map_regens=1_000_000`, `max_shrink_iters=u32::MAX` (≈ 4× cases; `0` disables), `max_shrink_time=0`, `timeout=0`, `fork=false`, `verbose=0`; env `PROPTEST_CASES`, `PROPTEST_MAX_SHRINK_ITERS`, `PROPTEST_MAX_SHRINK_TIME`, `PROPTEST_FORK`, `PROPTEST_TIMEOUT`, `PROPTEST_VERBOSE`, `PROPTEST_RNG_ALGORITHM` (`xs`/`cc`), `PROPTEST_DISABLE_FAILURE_PERSISTENCE`. | S6 config.rs | — | high |
| P4 | Persistence: default `FileFailurePersistence::SourceParallel("proptest-regressions")`; stores the **seed**, not the value ("works even if the strategy changes"); replayed before new cases; "recommends committing these files to source control so collaborators and CI replay the same cases"; all tests in a file share one persistence file. | S6 failure-persistence.md, config.rs | Changing a strategy changes what a seed produces: the regression may silently stop reproducing (derived). | high |
| P5 | Forking/timeouts: in-process by default, so stack overflow/abort/infinite loop kills the run with no minimal case; `fork`/`timeout` features (default-on) run each case in a subprocess; `timeout` implies `fork`; costs speed/debuggability. | S6 forking.md | Use for recursive parsers. | high |
| P6 | Limitations (own words): random sampling "virtually always pass[es]" `i64::abs` with `i64::MIN`; hand-picked unit tests still needed; a `.{1,4096}` string strategy "may suit fuzzing a C parser but rarely produces input that reaches a code generator". There is **no** "proptest vs fuzzing" chapter; this is the closest statement. | S6 limitations.md, SUMMARY | — | high |
| P7 | State-machine testing (`proptest-state-machine`): `ReferenceStateMachine` {`State`, `Transition`, `init_state`, `transitions`, `apply`, `preconditions`} + `StateMachineTest` {`init_test`, `apply`, `check_invariants`, `teardown`}, `prop_state_machine!` with a count or range of transitions; shrinking deletes from the end, then shrinks transitions, then initial state; `PROPTEST_VERBOSE=1` prints transitions. | S6 state-machine.md, state-machine README | Override `preconditions` when validity depends on state, or shrinking yields invalid sequences. | high |
| P8 | Status: "fairly close to being feature-complete", passive maintenance; MSRV 1.88 (≤ stable−7 policy). Tip: `opt-level=3` for `proptest`/`rand_chacha` under `[profile.test]`; `RefCell` for shared resources. | S6 README, tips | — | high |
| P9 | `proptest-arbitrary-interop`: `arb::<T>()` turns an `arbitrary::Arbitrary` impl into a proptest `Strategy`; only for owned types (`ArbInterop`), zero-copy impls excluded. | S7 | Shrinking quality not discussed (UNVERIFIED). | medium |
| P10 | quickcheck: `#[quickcheck]` attribute; `QUICKCHECK_TESTS`, `QUICKCHECK_MAX_TESTS` ("if it can't find 100 valid tests after 10,000 tries it gives up"), `QUICKCHECK_MIN_TESTS_PASSED`; shrinking via `Arbitrary::shrink` (binary search for lists/numbers); ≤ 8 params; stack overflows not caught; `Arbitrary` impls are "implementation details". Its README itself points to proptest for better shrinking and to the Rust Fuzz Book/`arbitrary` for fuzzing. MSRV 1.85. | S8 | Neither proptest nor quickcheck appears as a finder in the trophy case (S11). | high |

### 3.5 afl.rs and honggfuzz-rs (other greybox engines)

| # | Claim | Source | Validity / failure modes | Confidence |
|---|---|---|---|---|
| F1 | afl.rs = AFL++ (4.40c bundled in 0.18.0; latest 0.18.2) for Rust: `cargo install cargo-afl`, `cargo afl build`, `cargo afl fuzz -i in -o out target/…`, replay `cargo afl run t < out/default/crashes/<f>`; `fuzz!` reads stdin, catches panics and `process::abort`s so AFL counts them; AFL "requires at least one seed input"; persistent mode since 0.4.0; `fuzz_with_reset!` clears static state (stability metric); CMPLOG default-on; `cargo afl system-config`; x86-64 Linux/macOS, ARM64 macOS. | S15; S1 afl/{setup,tutorial}.md | — | high |
| F2 | Toolchain: cargo-afl always sets `-C debug-assertions -C overflow_checks -C codegen-units=1 -C opt-level=3 -C target-cpu=native --cfg fuzzing` plus `-C passes=sancov-module -C llvm-args=-sanitizer-coverage-{level=3,trace-pc-guard,prune-blocks=0,trace-compares}`; **builds on stable** (only `-C` flags) unless AFL++ LLVM plugins/CMPLOG are used, which assert nightly ("cargo-afl must be compiled with nightly for CMPLOG and other advanced AFL++ features"). | S15 main.rs | Book pages do not state stable support explicitly (D2). | high |
| F3 | When to prefer AFL++ over libFuzzer: **no primary source states a rule**. Observable differentiators: stable toolchain (F2), file/stdin-based targets, AFL++'s own scheduling/CMPLOG, forking vs in-process. | S1 afl.md (silent), S15 | UNVERIFIED as a community rule; treat as derived. | low |
| F4 | honggfuzz-rs: `cargo install honggfuzz`, `cargo hfuzz run <t>`, `run-debug` replays crashes under `rust-lldb`; stable/beta/nightly; Linux/macOS/BSD/Android/WSL; sanitizers via `RUSTFLAGS="-Z sanitizer=address"` (nightly) "recommended for testing `unsafe` Rust code". Needs binutils/libunwind/liblzma dev packages. | S16 | — | high |

### 3.6 OSS-Fuzz / ClusterFuzzLite / CI

| # | Claim | Source | Validity / failure modes | Confidence |
|---|---|---|---|---|
| O1 | OSS-Fuzz Rust: `project.yaml` `language: rust`, `sanitizers: [address]`, `fuzzing_engines: [libfuzzer]` — "the only supported fuzzing engine and sanitizer"; Dockerfile `FROM gcr.io/oss-fuzz-base/base-builder-rust` (latest nightly + `cargo fuzz --locked` preinstalled; `RUSTUP_TOOLCHAIN` env chooses the channel); `build.sh`: `cargo fuzz build -O` ("You may also want to pass the `--debug-assertions` flag to enable more checks while fuzzing"), copy `fuzz/target/x86_64-unknown-linux-gnu/release/<t>` to `$OUT` (loop over `fuzz/fuzz_targets/*.rs`). | S9 | Coverage builds: the `cargo` wrapper sets `-C debug-assertions=no` and builds non-release "because release builds produce malformed instrumentation profile data". | high |
| O2 | ClusterFuzzLite's Rust page is the same text; GitHub Actions: `build_fuzzers@v1` (`language`, `sanitizer`) + `run_fuzzers@v1` with `mode: code-change` (`fuzz-seconds: 600`, PRs), `batch` (3600 s, cron), `prune`, `coverage` (`sanitizer: coverage`); optional `storage-repo` keeps `/corpus/<fuzz_target>/`; else artifacts. Examples show `language: c++` with "Change this to the language you are fuzzing". | S10 | — | high |
| O3 | Rust Fuzz Book CI: see C16. Nightly is *unpinned* there; bolero documents `--toolchain nightly-YYYY-MM-DD`; OSS-Fuzz uses "latest nightly". | S1 ci.md, S5, S9 | Design choice (§5.5). | high |

### 3.7 What fuzzing finds in Rust (bug classes, oracles)

| # | Claim | Source | Validity / failure modes | Confidence |
|---|---|---|---|---|
| R1 | Trophy-case categories: `arith` (overflow), `oor`, `oom`, `so`, `loop`, `uaf`, `uninit`, `segfault`, `unwrap`, `utf-8`, `logic`, `panic`, `other`. "Denial of service, including panics and out-of-memory, are not considered security issues." ≈367 rows; 8 marked security (capnproto-rust ×2, claxon, lz4_flex, sxd-document, symbolic-minidump (C++), v_escape, zune-jpeg) — all memory-safety in `unsafe`/FFI. Top crates: image 14, brotli-rs 11, minidump/pdf/rav1e 10. Fuzzers: libfuzzer dominant, afl, honggfuzz, bolero, test-fuzz; **no proptest/quickcheck rows**. | S11 | Selection bias (self-reported). | high |
| R2 | Safe-Rust examples: chrono date-arithmetic overflow (`arith`, libfuzzer); rmpv "Unchecked vector pre-allocation" — `Vec::with_capacity` from a 2.9 GB length field, 15 input bytes, AFL (`oom`); ron stack overflow on 10 000 `{` (`so`; fix = explicit depth limit, PR #420); image-gif infinite loop (`loop`); regex #84 `unwrap`, #417 `utf-8` boundary slicing; bincode invalid-duration panic; zip arithmetic overflow; url #729 "failed round trip parse" (`logic`): input `p:/.//:/` serialises to `p://:/` which fails to re-parse; lzma-rs mismatch vs reference impl; reth/ruint encode-decode mismatch (test-fuzz). | S11; S18 | — | high |
| R3 | Unsafe/FFI examples: capnp RUSTSEC-2022-0068 OOB read (CVE-2022-46149), claxon RUSTSEC-2018-0004 uninitialised-memory disclosure (afl + libdiffuzz), lz4_flex RUSTSEC-2026-0041 uninitialised-memory exposure in the default `unsafe` decoder (CVE-2026-32829), sxd-document UAF, zune-jpeg/v_escape heap overflow. The advisory texts themselves do not credit fuzzing; the trophy case does. | S11, S12 | ASan is what makes these observable; without it an OOB read in `unsafe` may be silent. | high (trophy) / medium (credit) |
| R4 | Absence of fuzzing cited in advisories: quinn-proto RUSTSEC-2023-0063 "this issue was not found by our fuzzing infrastructure"; RUSTSEC-2026-0037 "we did not have sufficient fuzzing coverage to find this issue … We have since added a fuzzing target to cover this code path" (unreviewed `unwrap()` in transport-parameter parsing). | S12 | Evidence for H1/H3: targets must reach the parsing path. | high |
| R5 | Oracle mechanics in safe Rust: panics (index OOB, `unwrap`/`expect`, explicit `panic!`, `assert!`/`debug_assert!`, integer overflow **only with overflow checks**, slicing inside a UTF-8 char), stack overflow (SIGSEGV via guard page → libFuzzer "deadly signal"), OOM (`-rss_limit_mb`/`-malloc_limit_mb`), timeout (`-timeout`). UB classes need `unsafe`/FFI and a sanitizer or Miri. | S14 codegen-options; S3 flags; S17 Miri; S1 tutorial output ("index out of bounds … ==ERROR: libFuzzer: deadly signal") | — | high |
| R6 | Good-target hygiene (language-neutral, applies verbatim): deterministic; ≥ ~1000 exec/s/core, "< 10 exec/s you are probably doing something wrong"; "must not `exit()` or `abort()` on any input"; bound input size in the target; < 1.5 GB RSS; no stderr/stdout output; avoid threads; keep targets narrow; seed corpus small and representative; "Monitor the code coverage achieved by the corpus and try to keep it close to 100%"; use a dictionary for keyword/magic formats; extend the seed corpus when fixing bugs. | S13 good-fuzz-target.md | — | high |

### 3.8 Related, not fuzzing

| Tool | What it is | Relation | Source |
|---|---|---|---|
| Miri | "an Undefined Behavior detection tool for Rust"; OOB/UAF, uninit, misalignment, invalid values, data races, leaks; "tests one of many possible executions"; `cargo miri test` | Run property/fuzz *harnesses* under Miri (bolero documents it) to turn UB into a detectable failure on the inputs exercised; slow | S17, S5 miri.md |
| Kani | "bit-precise model checker"; `#[kani::proof]` + `kani::any()`; checks panics, overflow, UB, assertions "for all possible values" | bolero can run a `check!` target under `--engine kani`; exhaustive but bounded, not sampling | S17, S5 |

## 4. Disagreements and open questions

| id | Topic | Positions | Resolution for the design |
|---|---|---|---|
| D1 | cargo-fuzz on Windows | README: "Only Unix-like operating systems are supported"; setup.md and CHANGELOG 0.13.0: Windows via MSVC ASan / `--no-include-main-msvc` | Treat Windows as best-effort; CI recipe on Linux. |
| D2 | Nightly requirement | All docs say nightly; code emits `-Zsanitizer` and never takes the stable branch (placeholder); PR #123617 (ASan/LSan stabilisation) open; afl.rs builds on stable with the same sancov `-C` flags. Whether `cargo fuzz build -s none` works on stable: UNVERIFIED. | Skill states "nightly" as the rule today and carries a dated note to re-check #123617. |
| D3 | Generation (`Arbitrary`) vs custom mutation | Rust Fuzz Book: one experiment favours `fuzz_mutator!` for coverage over time; `arbitrary` is designed so byte mutation still works; `google/fuzzing` presents custom mutators as the heavy, per-format option. | Default to `Arbitrary` (cheap, typed); escalate to `fuzz_mutator!` for compressed/checksummed/encoded containers. |
| D4 | Debug assertions in OSS-Fuzz builds | cargo-fuzz default = on; OSS-Fuzz guide uses `-O` (off) and only *suggests* `--debug-assertions`; coverage wrapper forces them off. | Agent-generated `build.sh` passes `-O --debug-assertions`; note the coverage-build exception. |
| D5 | Should corpus/artifacts be committed? | cargo-fuzz `.gitignore` excludes `corpus artifacts coverage`; bolero: corpus "should either be committed … or stored externally"; proptest: commit `proptest-regressions`; ClusterFuzzLite: external storage repo. | Per-tool rule in §5.2. |
| D6 | PBT vs fuzzing positioning | proptest has no fuzzing-comparison chapter; its limitations chapter concedes broad string strategies suit "fuzzing a C parser" more than typed code. Trophy case has no proptest finds. | Use the decision table, not a "fuzzing is better" claim. |
| D7 | Stopping rule | No tool defines one; libFuzzer tutorial gives heuristics (`cov` flat); CI budgets are conventions (300 s book, 600/3600 s ClusterFuzzLite). | Design must define its own rule (§5.4). |
| Q1 | libFuzzer status-line legend (`ft`, `lim`, `L`) | LibFuzzer.rst unreachable; only `cov`/`corp` confirmed. | Re-verify when llvm.org is allowed. |
| Q2 | afl.rs vs libFuzzer selection rule | No primary statement. | Keep F3 as derived guidance. |
| Q3 | bolero `cargo bolero reduce` semantics and `__fuzz__` subdir creation | Files exist (`reduce.rs`); engine reads `corpus`/`crashes`; creation code not seen. | UNVERIFIED detail; low impact. |

## 5. Implications for the agent / skills

### 5.1 Skeletons the skill should carry

`fuzz_target!` with `Arbitrary` (H3, H5) — `fuzz/fuzz_targets/parse_roundtrip.rs`:

```rust
#![no_main]
use libfuzzer_sys::{fuzz_target, Corpus};
use arbitrary::Arbitrary;
use mycrate::{Config, parse, serialize};

#[derive(Arbitrary, Debug)]
struct Input { cfg: Config, #[arbitrary(with = |u: &mut arbitrary::Unstructured| u.bytes(u.len().min(4096)).map(<[u8]>::to_vec))] body: Vec<u8> }

fuzz_target!(|inp: Input| -> Corpus {
    let Ok(doc) = parse(&inp.cfg, &inp.body) else { return Corpus::Reject };
    let out = serialize(&doc);
    assert_eq!(parse(&inp.cfg, &out).expect("re-parse"), doc, "round trip");
    Corpus::Keep
});
```
(`#![no_main]`, typed input, early `Reject` on invalid input, bounded body, round-trip oracle; `Config` derives `Arbitrary` behind an optional `arbitrary` feature — S1, S3, S4.)

proptest skeleton (H4, H5) — in `src/lib.rs` `#[cfg(test)]` or `tests/`:

```rust
use proptest::prelude::*;

prop_compose! {
    fn valid_date()(y in 0u32..=9999, m in 1u32..=12, d in 1u32..=28) -> (u32,u32,u32) { (y,m,d) }
}
proptest! {
    #![proptest_config(ProptestConfig { cases: 512, ..ProptestConfig::default() })]
    #[test]
    fn roundtrip((y,m,d) in valid_date()) {
        let s = format!("{y:04}-{m:02}-{d:02}");
        prop_assert_eq!(parse_date(&s), Some((y,m,d)));
    }
    #[test]
    fn never_panics(s in "\\PC*") { let _ = parse_date(&s); }
}
```
(Commit the generated `proptest-regressions/` — S6.)

### 5.2 Rules and checklists

**Applicability gate (H1)** — write a fuzz target only if all hold: (a) a pure-ish entry point taking bytes/str/typed value with no I/O, network, clock, randomness or process exit; (b) an oracle beyond "no crash" exists *or* the code is a parser/decoder/`unsafe`/FFI where panics/UB are the bug class; (c) it can run ≥ ~100s exec/s (S13 R6). Otherwise choose proptest (typed invariant) or unit tests.

**Review checklist for a Rust `cargo fuzz` target (H5)**

1. File starts `#![no_main]`; imports `libfuzzer_sys::fuzz_target`; `fuzz/Cargo.toml` has the `[[bin]]` with `test=false doc=false bench=false`; `fuzz` is in `workspace.members` (or `--fuzzing-workspace`). (C7)
2. Invalid input is *handled*, never asserted: `if let Ok(..)`/`let Ok(..) else { return Corpus::Reject }`; only invariants are `assert!`ed. (C10)
3. Input size bounded in the target (early return above N bytes, `arbitrary_len`/`u.bytes(min(..))`) and `-max_len` set in the run/CI command; untrusted lengths never drive `Vec::with_capacity` in the *harness*. (R2 rmpv, R6)
4. Deterministic: no `HashMap` iteration-order dependence in the oracle, no `rand`, no time, no env; threads only via one-time `init:`. (R6, C10)
5. Oracle present: round-trip (`parse(serialize(x)) == x`), differential (reference impl / `std` collection), metamorphic, or explicit invariant; "no panic" alone only for parsers/decoders/unsafe. (R2, B6)
6. Typed APIs use `#[derive(Arbitrary)]` behind an optional `arbitrary` feature on the library crate; `size_hint` sane for hand impls. (A6, A4)
7. Build keeps debug assertions: never `-O` without `--debug-assertions`; `--sanitizer address` when `unsafe`/FFI is in scope, `-s none` for pure safe Rust if throughput matters. (C5, C6)
8. No stdout/stderr output in the hot path; no `process::exit`/`abort`. (R6)
9. Seed corpus: a few small valid inputs in `fuzz/corpus/<t>/` (or generated from unit-test fixtures); dictionary `-dict=` for keyword formats. (R6, C13)
10. Reproduction path documented: `cargo fuzz run <t> fuzz/artifacts/<t>/crash-…`, `cargo fuzz fmt <t> <file>` for typed inputs, `cargo fuzz tmin` before filing. (C9, C15)
11. Crash inputs turned into regression tests: copy minimised artifact to `tests/fuzz_regressions/<t>/` and add a `#[test]` that runs the same body over every file (`include_bytes!` per named case, or directory scan) — stable toolchain, no cargo-fuzz needed in `cargo test`. (S19) With bolero, commit `__fuzz__/<t>/crashes` instead. (B4)
12. Coverage checked once: `cargo fuzz coverage <t>` + `llvm-cov show`, confirm the function under test and its error branches are hit; if not, fix seeds/`Arbitrary` shape before running longer. (C9, R6)

**Corpus/artifact policy (D5):** cargo-fuzz — do not commit `fuzz/corpus` or `fuzz/artifacts` (generated `.gitignore`); commit *minimised* crash inputs as regression fixtures; optionally keep a small hand-made seed set in `fuzz/seeds/<t>/` and pass it as the corpus dir. bolero — commit `__fuzz__`. proptest — commit `proptest-regressions`. CI at scale — ClusterFuzzLite storage repo.

### 5.3 Decision rule (H1)

| Situation | Choose | Why (source) |
|---|---|---|
| Typed function with an algebraic/round-trip invariant; must run on stable in `cargo test`; moderate input space | `proptest` (`prop_compose!`, 256–1000 cases) | shrinking, persistence, stable (P1–P4) |
| Stateful API (collection, cache, protocol state) with a simple model | `proptest-state-machine` or bolero `Vec<Op>` + `std` oracle | P7, B6 |
| Byte/text parser, decoder, decompressor, deserialiser, anything with `unsafe` or FFI | `cargo fuzz` + ASan (+ `Arbitrary` for options/typed sub-inputs; `fuzz_mutator!` for encoded containers) | coverage guidance, sanitizers, trophy-case evidence (C4–C6, R1–R3, D3) |
| Want one harness as unit test *and* fuzz target, test private fns, or no nightly in CI | `bolero` (`--sanitizer NONE` on stable; libfuzzer/afl/honggfuzz on demand) | B1–B5 |
| Existing `Arbitrary` impls, want PBT too | `proptest-arbitrary-interop::arb::<T>()` | P9 |
| Need stable-only *coverage-guided* fuzzing with a file-based target | `cargo afl` (no plugins/CMPLOG) or honggfuzz-rs | F2, F4 |
| `serde` derive with no custom `Deserialize`/`Serialize`; thin CLI `main` arg parsing; code dominated by I/O; function already total and trivial | **Do not fuzz**: unit tests / existing crate tests; if anything, proptest a round-trip on the owning type | H1; P6 ("unit tests still needed") |
| Want proof for all inputs of a small `unsafe` function | Kani (via bolero `--engine kani`) / Miri over the corpus | 3.8 |

### 5.4 Stopping / continuation rule (H2) — proposed, derived

Run with `-max_total_time=T` (smoke: 60–300 s per target in PR CI; batch: ≥ 1 h). Treat a target as **saturated for this corpus** when, over the last ≥ 25 % of the budget (min 60 s), no `NEW` lines appear and `cov:` is flat (S13 heuristic), *and* `cargo fuzz coverage` shows the intended functions reached. Then: `cargo fuzz cmin`, and either add seeds/dictionary/`Arbitrary` shape to reach uncovered branches, or move to the next target. Stop a target immediately on any artifact (crash/timeout/oom): `tmin`, reproduce, file. Never report "ran N iterations" as evidence without the coverage check.

### 5.5 CI recipe sketch (H5)

```yaml
# .github/workflows/fuzz-smoke.yml (derived from rust-fuzz/book ci.md + ClusterFuzzLite budgets)
on: [push, pull_request]
jobs:
  fuzz:
    runs-on: ubuntu-latest
    strategy: { matrix: { target: [parse_roundtrip, decode_frame] } }
    steps:
      - uses: actions/checkout@v4
      - run: rustup toolchain install nightly-2026-10-01 --profile minimal && rustup default nightly-2026-10-01   # pin a date; bump deliberately
      - run: cargo install cargo-fuzz --locked --version 0.13.2
      - run: cargo fuzz build --debug-assertions ${{ matrix.target }}          # compile check (debug assertions explicit even though default)
      - run: cargo fuzz run ${{ matrix.target }} fuzz/seeds/${{ matrix.target }} -- -max_total_time=300 -max_len=65536 -rss_limit_mb=2048
      - if: failure()
        uses: actions/upload-artifact@v4
        with: { name: fuzz-artifacts-${{ matrix.target }}-${{ github.sha }}, path: fuzz/artifacts }
```
Pinning issue: the book's workflow uses the floating `nightly` channel (S1 ci.md) and OSS-Fuzz builds with the latest nightly (S9); a nightly regression then fails fuzz CI unrelated to the change. Pin `nightly-YYYY-MM-DD` (bolero documents `--toolchain nightly-…`, S5) and schedule a bump; keep `cargo test` (proptest/bolero replay of committed regressions) on stable so the oracle survives a broken nightly. For long-running fuzzing use ClusterFuzzLite `batch`/`prune`/`coverage` with a storage repo (S10) rather than ever-longer PR jobs.

### 5.6 Skills to write (mapping)

| Skill | Carries | H |
|---|---|---|
| `rust-fuzz-applicability` | gate table 5.3, "do not fuzz" cases, oracle catalogue (round-trip/differential/model) | H1, H4 |
| `rust-cargo-fuzz-harness` | layout C7/C8, skeleton 5.1, checklist 5.2, flags C4–C6/C13, `Arbitrary` rules A1–A6, `fuzz_mutator!` escalation | H3, H5 |
| `rust-proptest` | P1–P8 skeleton, config/env, persistence, state-machine | H4, H5 |
| `rust-bolero` | B1–B7, when it beats the other two | H5 |
| `rust-fuzz-run-and-stop` | C9/C14/5.4: read output, cmin/tmin/coverage, saturation rule, regression-fixture conversion | H2 |
| `rust-fuzz-ci` | 5.5, OSS-Fuzz/ClusterFuzzLite O1–O3, nightly pinning | H5 |

## 6. Candidate eval cases

| # | Input the agent sees | Expected behaviour |
|---|---|---|
| E1 | Crate with `#[derive(Serialize, Deserialize)] struct Config { … }` and no custom impls; "add fuzzing" | **Do not write a cargo-fuzz target.** Explain that derive code is serde's, already fuzzed upstream; at most a proptest/`serde_json` round-trip on `Config` if it has validation invariants; otherwise unit tests. (H1) |
| E2 | Binary `main.rs` using `clap` to parse args then calling `run(opts)` which does file I/O | Do not fuzz `main`/arg parsing; if `run` has a pure core (e.g. a parser), propose extracting it and fuzzing that; else unit/integration tests. (H1) |
| E3 | `fn decode(&[u8]) -> Result<Frame, Error>` with `Vec::with_capacity(len as usize)` from the header | cargo-fuzz target with `-max_len`, bounded body; expect it to flag/produce an OOM finding and recommend length validation (rmpv #151 pattern); regression fixture added. (H3/H4) |
| E4 | Safe `fn to_hsl(Rgb) -> Hsl` / `from_hsl` | proptest (or bolero `with_type`) round-trip with tolerance; no nightly fuzz target. (H1/H4) |
| E5 | Module with `unsafe { slice::from_raw_parts(ptr, n) }` in an FFI binding over a C decoder | cargo-fuzz with `--sanitizer address`, harness reads every returned element (`black_box`), ASan rationale stated. (H4) |
| E6 | Custom `BTreeMap`-like structure with insert/remove/get | `proptest-state-machine` or bolero `Vec<Op>` vs `std::collections::BTreeMap` oracle; shrinking of op sequences explained. (H4) |
| E7 | Agent is shown 10 min of libFuzzer output: `cov:` constant since minute 2, `corp:` constant, no artifacts; `cargo fuzz coverage` shows `parse_header` 100 %, `parse_body` 0 % | "Stop now" for this corpus; diagnose unreachable `parse_body` (seed/`Arbitrary` shape/checksum), add seeds or a `fuzz_mutator!`, then rerun; do not just extend the time. (H2/H3) |
| E8 | Existing target asserts `parse(data).is_ok()` on raw bytes | Rewrite: `if let Ok(x) = parse(data)` and add a real property; flag that the old target "finds" nothing but invalid input. (H4/H5) |
| E9 | Proposed harness calls `std::process::exit(1)` on error and prints every input | Reject: violates libFuzzer target rules (no exit, no output); fix. (H5) |
| E10 | CI YAML with `rustup default nightly` and `cargo fuzz build -O` | Point out missing debug assertions and unpinned nightly; propose 5.5. (H5) |
| E11 | Request to fuzz an `async fn handle(req: Request) -> Response` on tokio | Only if a deterministic single-thread runtime wraps it and `Request` derives `Arbitrary`; otherwise proptest on the pure handler core. (H1/H5) |
| E12 | A `cargo fuzz run` produced `crash-…`; agent asked "what next" | `tmin`, reproduce with `cargo fuzz run t <artifact>`, `fmt` for typed input, add `#[test]` regression with the bytes, fix, rerun; do not commit `fuzz/artifacts` wholesale. (H5) |

## 7. Micro-examples

1. **Round-trip oracle beats crash oracle (rust-url #729, S18).** A libFuzzer target asserted `parsed == Url::parse(parsed.as_str())`. Input `p:/.//:/` serialised to `p://:/` ("the `/.` was lost") which no longer parses; a later run found the shorter `A:/.//:`. No panic involved — pure logic bug found only because of the property. Pattern for the skill: `if let Ok(p) = parse(s) { assert_eq!(p, parse(&p.to_string()).unwrap()) }`.
2. **Untrusted length → OOM (rmpv, msgpack-rust #151, S18).** AFL input `[219, 175, 142, 142, 201, 219, 128, 0, 50, …]` (15 bytes) made `read_value` pre-allocate 2 945 355 465 bytes ("2 GiB are allocated even when the serialized data is only 20 bytes long"); fixed by replacing `with_capacity` with `new` (PR #221, rmpv 0.4.2). Under cargo-fuzz this surfaces as a `-rss_limit_mb`/`-malloc_limit_mb` report; the harness must *not* itself pre-allocate from the input.
3. **Recursion → stack overflow (ron #307, S18).** `ron::from_str::<Value>` on 10 000 `{` overflowed the stack; "Found by fuzzing"; maintainers concluded "in the end there has to be some limit or we crash" and added a user-settable depth limit (PR #420). proptest would need `fork`/`timeout` to even report this (P5); libFuzzer reports it as a deadly signal.
4. **Typed target, Rust Fuzz Book (S1 structure-aware).** Library: `#[cfg_attr(feature = "arbitrary", derive(arbitrary::Arbitrary))] struct Rgb {r,g,b}`; fuzz crate enables `arbitrary`; target `libfuzzer_sys::fuzz_target!(|color: Rgb| { let hsl = color.to_hsl(); let rgb = hsl.to_rgb(); assert_eq!(color, rgb); })`. Shows the optional-feature wiring and a round-trip property in ≤ 5 lines.
5. **Absent coverage, real CVE (quinn-proto RUSTSEC-2026-0037, S12).** Panic from unreviewed `unwrap()` in transport-parameter parsing shipped despite an existing fuzzing set-up: "we did not have sufficient fuzzing coverage to find this issue … We have since added a fuzzing target to cover this code path." Supports the checklist item "coverage checked once" and H1's corollary: fuzzing *the right entry points* matters more than fuzzing at all.
