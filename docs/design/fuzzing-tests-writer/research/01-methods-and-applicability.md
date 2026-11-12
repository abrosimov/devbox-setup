---
note_id: "20261103150901"
modified: 2026-11-10
created: 2026-11-03
language: en
type: research
subtype: annex
note_role: artifact
artifact_kind: research-report
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["R1"]
tags: [fuzzing, design/research, h1, h4]
topic: "Method families; applicability gate; oracle catalogue; evaluation hygiene; cost"
addresses: ["[[H1-no-applicability-gate]]", "[[H4-crash-only-oracle]]"]
related: ["[[research-index]]", "[[research-corpus]]"]
---
# Fuzzing method families and the applicability gate (Go / Rust / Python focus)

> Historical research from 2026-11-03; the body below is retained as provenance. Its proposals
> are not current requirements. The 2026-11-10 disposition is [[methodology-review]]: PBT and
> mutation analysis are excluded; saturation/escalation rules and provider recipes must not be
> imported into authoring. Current operations are specified in [[agent-procedure]].

Research report for the "fuzzing tests writer" agent design document. Written 2026-11-03.
Network note: in this session `llvm.org`, `go.dev`, `rust-fuzz.github.io`, `hypothesis.readthedocs.io`,
`google.github.io`, `fuzzingbook.org`, `arxiv.org` and all paper mirrors were unreachable. Every
primary document that has a GitHub source was read from GitHub instead (source files of the same
pages); papers whose only hosts were unreachable are marked **partially verified** (abstract and
search snippets only) or **UNVERIFIED**. The ledger in §2 says which is which.

## 0. Summary for the design doc

1. **Fuzzing pays off on a narrow class of code**: deterministic, fast (≈1,000 exec/s per core; <10/s is
   broken), in-process, no network/disk/time dependence, consuming untrusted or complex input, with an
   oracle stronger than "crash" in memory-safe languages (S1, S7, S27f). Everything else should get
   property tests, unit tests, or nothing. This is the gate H1 was missing; §5.1 is the decision table.
2. **In Go/Rust/Python the crash oracle finds a specific, bounded bug set**: panics (index/slice out of
   range, nil deref, unwrap), integer overflow (Rust, only with debug assertions on), infinite loops,
   unbounded allocation / OOM, stack overflow — i.e. robustness and DoS, not memory corruption. The Rust
   trophy case is ≈20 % arithmetic overflow, ≈19 % out-of-range, ≈17 % logic, ≈10 % panic, ≈10 % OOM,
   ≈6 % unwrap, <1 % UB/UAF/segfault; security-flagged entries are a small minority (S19). go-fuzz's
   ≈400 trophies show the same shape (S16). Logic bugs appear only when an oracle exists (round trip,
   two implementations) — confirms H4.
3. **Method choice follows input kind**: untrusted bytes → coverage-guided greybox; structured text →
   greybox + seeds + dictionary, or grammar/structure-aware when validation rejects most mutations;
   typed API → property-based testing (Hypothesis/proptest/rapid), optionally bridged into the
   coverage-guided engine; mutating/stateful API → model-based state-machine testing; numeric or
   algorithmic code → metamorphic + differential against a reference (S3, S21–S23, S29, S36).
4. **Oracle catalogue the agent must choose from** (§3.10, §5.2): crash/sanitizer; timeout and RSS
   limits (treated as bugs by OSS-Fuzz, S27d); round trip; differential; metamorphic relations;
   invariants/postconditions; model-based. Hughes' comparison ranks model-based and metamorphic
   properties as the most bug-finding kinds (S36, partially verified).
5. **"Never panics" vs "returns error"**: the correct contract per target must be stated before the
   harness is written; Go's security policy treats panics and resource exhaustion on untrusted input as
   security issues, and `t.Skip`/early-return on inputs the API rejects is the documented pattern (S9, S15).
6. **Do not fuzz**: thin wrappers around an upstream-fuzzed library (stdlib JSON, well-known parsers —
   "all errors found are already fixed", S29a); code whose behaviour depends on the network, a DB, the
   filesystem, wall-clock or unseeded RNG (S1, S27f, S30); GUI/CLI glue and orchestration/config code
   (S30b); targets with persistent threads or global state (S7); APIs with >20–30k reachable edges as
   one target (S1). Property tests or unit tests instead.
7. **Evaluation discipline for the agent's own claims**: crashes ≠ bugs (deduplicate and triage before
   reporting); one run is anecdote (Klees: most of 32 papers used too few trials; SoK guidelines:
   ≥10 trials, ≥24 h, same seeds, source-level coverage); report coverage from a neutral build, not
   corpus size (S30c, S31, S32).
8. **Cost reality**: a target is permanent code — needs seeds in VCS, a dictionary, a 5-minute CI smoke
   run plus seed-corpus regression on every `go test`/`cargo test`, triage of timeouts/OOMs (one each
   per target, often flaky), nightly Rust toolchain for cargo-fuzz, unbounded Go fuzz cache (S8, S10,
   S18f, S20, S27d, S39).
9. Skills to write (§5.5): `fuzz-applicability-gate`, `fuzz-oracles`, one per language
   (`go-fuzz`, `rust-cargo-fuzz`, `python-atheris-hypothesis`), `property-based-testing`,
   `stateful-model-testing`, `fuzz-claim-hygiene`.

## 1. Scope and question answered

Question: which fuzzing method families exist, what each needs from a target, and — above all — when
is fuzzing *not* the right tool, for an agent writing fuzz tests in Go, Rust and Python. Out of
scope (other agents): stopping rules in depth, seed-corpus construction, harness conventions per
ecosystem. They are touched only where they bear on applicability.

## 2. Corpus ledger

| id | source + edition/date | locator | used for | status |
|---|---|---|---|---|
| S1 | google/fuzzing, `docs/good-fuzz-target.md`, master, read 2026-11-03 | sections Basics, Determinism, Speed, Timeouts/OOMs/Shallow bugs, Coverage discoverability, Large APIs, Structure-aware | target contract, speed numbers, anti-patterns | include |
| S2 | google/fuzzing, `docs/why-fuzz.md`, master | whole page | bug classes fuzzing finds, "not a substitute for functional tests" | include |
| S3 | google/fuzzing, `docs/structure-aware-fuzzing.md`, master | compression, PNG, protobuf, API-trace sections | structure-aware, stateful via traces, cost | include |
| S4 | google/fuzzing, `docs/split-inputs.md`, master | FDP / hash / separator / protobuf | typed multi-argument inputs | include |
| S5 | google/fuzzing, `docs/intro-to-fuzzing.md`, master | Motivation, limitations | what fuzzing is good/bad at | include |
| S6 | google/fuzzing, `tutorial/libFuzzerTutorial.md`, master | OOM/timeout/dictionary sections | defaults (2 GB, 1200 s) | include |
| S7 | LibFuzzer manual (`docs/LibFuzzer.rst`, llvm-mirror/llvm copy ≈2019; current `llvm/docs/LibFuzzer.rst` unreachable) + `compiler-rt/lib/fuzzer/FuzzerFlags.def`, llvm-project main | Fuzz Target section; flags table; FAQ | target contract, flag defaults, threads | include (manual text is 2019 copy; flag defaults current) |
| S8 | Go, `go.dev/doc/security/fuzz` (golang/website `_content/doc/security/fuzz/index.md`) | Requirements, Suggestions, Corpus, Failures | Go contract, failure kinds, 1 s timeout | include |
| S9 | Go, `go.dev/doc/tutorial/fuzz` (golang/website `_content/doc/tutorial/fuzz.md`) | Reverse example | round-trip + validity oracle, `t.Skip` | include |
| S10 | Go blog "Fuzzing is Beta Ready" 2021 (`_content/blog/fuzz-beta.md`) | ParseQuery example, limitations | round-trip oracle, cache growth | include |
| S11 | Go design draft `golang/proposal/design/draft-fuzzing.md` | goals, types, non-goals | typed args, unsupported types, "≈400 go-fuzz bugs" | include |
| S12 | Go `src/testing/fuzz.go` doc comments, master | `F.Fuzz`, `F.Add` | "fast and deterministic", allowed types | include |
| S13 | Go `src/testing/quick/quick.go`, master | package doc | `testing/quick` frozen | include |
| S14 | golang/go issues #53871 (2022), #69066 (2024) | issue bodies | Go stdlib panics found by OSS-Fuzz; "panics on external input are security issues" | include |
| S15 | Go security policy (golang/website `_content/doc/security/policy.md`) | track examples | panics / stack exhaustion / unbounded reads as security issues | include |
| S16 | dvyukov/go-fuzz README, master | Trophies; Usage notes | ≈400 trophies by kind; round-trip, two-implementation, checksum advice | include |
| S17 | catenacyber/ngolo-fuzzing README | whole | auto-generated API-sequence targets for Go stdlib; limitation re `MustCompile` | include |
| S18 | rust-fuzz/book (`src/introduction.md`, `cargo-fuzz/{tutorial,guide,setup,coverage,ci,oracles-accessing-data,structure-aware-fuzzing,targets}.md`), master | per page | Rust tutorial bug, `cfg(fuzzing)`, CI smoke, coverage, Arbitrary/allocator example | include |
| S19 | rust-fuzz/trophy-case README, master | table + category legend | distribution of bug classes in Rust fuzzing | include (distribution is an estimate from the page, ±3 pp) |
| S20 | rust-fuzz/cargo-fuzz README + `src/project.rs`, main | README; `rustflags` | nightly requirement; `-Cdebug-assertions` default, sancov, `--cfg fuzzing` | include |
| S21 | rust-fuzz/arbitrary README, main | whole | bytes→typed values, derive | include |
| S22 | proptest README + book `limitations.md`, `state-machine.md`, main | per page | PBT limits; reference state machine | include |
| S23 | flyingmutant/rapid README, master | features, comparisons | Go PBT, `MakeFuzz` bridge, PBT vs fuzz framing | include |
| S24 | google/atheris README + `native_extension_fuzzing.md`, master | whole | Python oracle = uncaught exception; FDP; custom mutator zlib example; sanitizers only for native code | include |
| S25 | Hypothesis docs (pypi description; search snippets of `how-to/external-fuzzers`, `stateful`, `settings`, `healthchecks`) | per topic | PBT definition, `fuzz_one_input`, RuleBasedStateMachine, `max_examples=100` | include, **partially verified** (docs host unreachable) |
| S26 | Zac-HD/hypofuzz README | Motivation | coverage-guided PBT, one-target-per-core limit of AFL | include |
| S27 | OSS-Fuzz docs: (a) README, (b) `new_project_guide.md`, (c) `new-project-guide/{go,rust,python}_lang.md`, (d) `faq.md`, (e) `advanced-topics/ideal_integration.md`, (f) `further-reading/fuzzer_environment.md`, master | per page | stats, eligibility, per-language engine/sanitizer limits, timeouts/OOM as bugs, environment constraints | include |
| S28 | ClusterFuzz `docs/reference/glossary.md` | definitions | crash state, reproducibility, corpus pruning | include |
| S29 | The Fuzzing Book (Zeller et al.), notebooks on GitHub master: (a) Fuzzer, (b) MutationFuzzer, (c) GreyboxFuzzer, (d) Grammars, (e) SymbolicFuzzer, (f) ConcolicFuzzer, (g) WhenToStopFuzzing | Lessons Learned + named sections | method claim sheets, Good-Turing | include |
| S30 | AFL++ docs, stable: (a) `fuzzing_in_depth.md`, (b) `best_practices.md`, (c) `afl-fuzz_approach.md`, (d) `FAQ.md` | per page | network/GUI targets, stability, when to stop, coverage vs corpus count | include |
| S31 | Klees, Ruef, Cooper, Wei, Hicks, "Evaluating Fuzz Testing", CCS 2018 (arXiv 1808.09700) | abstract + search snippets | evaluation hygiene | include, **partially verified** |
| S32 | Schloegel et al., "SoK: Prudent Evaluation Practices for Fuzzing", IEEE S&P 2024 + `fuzz-evaluator/guidelines` README v1.0.3 (read) | guidelines | concrete evaluation checklist | include (guidelines read; paper body unverified) |
| S33 | Mañes et al., "The Art, Science, and Engineering of Fuzzing: A Survey", IEEE TSE 47(11) 2021 (preprint 2019) | SoftSec-KAIST/Fuzzing-Survey README only | taxonomy terms | **UNVERIFIED** body; used only for vocabulary from memory, flagged |
| S34 | Böhme, "STADS: Software Testing as Species Discovery", TOSEM 27(2) 2018 | via S29g + abstract snippet | discovery probability = max residual risk | include, **partially verified** |
| S35 | Böhme & Falk, "Fuzzing: On the Exponential Cost of Vulnerability Discovery", FSE 2020 | search snippets | each additional bug costs exponentially more | include, **partially verified** |
| S36 | Hughes, "How to Specify It!", TFP 2019 / LNCS 12053 | search snippets | five property kinds; model-based/metamorphic most effective | include, **partially verified** |
| S37 | Chen et al., "Metamorphic testing: a review…", ACM CSUR 51(1) 2018; Segura et al., "A Survey on Metamorphic Testing", TSE 42(9) 2016 | abstracts | MT definition, oracle problem | include, abstract-level |
| S38 | Csmith README (csmith-project) + Yang, Chen, Eide, Regehr, PLDI 2011 (snippet) | README; abstract | differential testing oracle condition (no UB) | include |
| S39 | Ding & Le Goues, "An Empirical Study of OSS-Fuzz Bugs", MSR 2021 (arXiv 2103.11518) | abstract snippets | timeouts/OOM flaky, CVEs rare | include, abstract-level |
| S40 | McKeeman, "Differential Testing for Software", Digital Technical Journal 10(1) 1998 | bibliographic only | origin of the term | **UNVERIFIED** |
| S41 | Claessen & Hughes, "QuickCheck", ICFP 2000 | bibliographic only | PBT lineage | **UNVERIFIED** |

Independence note (RMP.7): S1–S6, S27, S28 are one tradition (Google/ClusterFuzz) and largely restate
each other; S7 and S30 are the two engine manuals; S29 is the didactic synthesis; S31/S32/S34/S35 are
the independent academic evaluation line; S16/S19/S14 are independent empirical bug records; S36/S37/S38
are the PBT/MT/DT origins. Secondary blog posts were not used.

## 3. Claim sheets

Format per claim: statement — source — validity region — failure modes — confidence (H high / M medium / L low).

### 3.1 Blackbox random and mutation fuzzing

| # | claim | src | validity region | failure modes | conf |
|---|---|---|---|---|---|
| 1 | Random input "is a simple, cost-effective way to quickly test arbitrary programs"; Miller 1990: about a third of UNIX utilities crashed or hung | S29a Lessons Learned | programs that read a byte stream and have had no fuzzing before | "it is very unlikely that you'll find a bug in troff at this point … all errors found are already fixed" (S29a) — saturated targets yield nothing | H |
| 2 | "Bugs fuzzers find are mainly due to errors and deficiencies in input processing" | S29a | parsers, decoders | does not reach business logic behind validation | H |
| 3 | "Randomly generated inputs are frequently invalid … Mutations from existing valid inputs have much higher chances to be valid" (odds of a random `http://` prefix ≈ 1/96^7) | S29b | any target with a syntax check at the entrance | pure random never passes magic/prefix checks; needs seeds | H |
| 4 | Mutation finds buffer overflows, missing error checks, "rogue numbers", info leaks (HeartBleed) | S29a | C-like code; in memory-safe code the analogues are panics/OOM | — | H |
| 5 | Needs: a function that takes bytes; no instrumentation; speed is the only cost | S29a, S30a | quick first pass | no feedback → stalls at shallow depth | H |

### 3.2 Coverage-guided greybox (AFL / libFuzzer / Go native / cargo-fuzz / Atheris)

| # | claim | src | validity region | failure modes | conf |
|---|---|---|---|---|---|
| 1 | "a greybox fuzzer adds to the seed population generated inputs which increase code coverage"; lightweight branch instrumentation, no constraint solving; "generates thousands of inputs per second" | S29c | in-process, instrumentable, deterministic targets | needs compiler instrumentation (Go: AMD64/ARM64 only, S8; cargo-fuzz: nightly, S20) | H |
| 2 | Target contract: tolerate any input; never `exit()`/`abort()`; "must be as deterministic as possible"; ideally no global-state mutation; threads joined before return; persistent threads make results "unreliable" | S7, S1 | — | unseeded RNG, time, persistent threads → low stability, irreproducible crashes (S30c "stability") | H |
| 3 | Speed: "typical good targets run about 1,000 executions per second per core … Under 10 exec/s suggests a problem"; RAM < ≈1.5 GB; libFuzzer defaults `-rss_limit_mb=2048`, `-timeout=1200`; Go per-input timeout 1 s | S1, S7, S8 | — | slow targets never saturate; Go kills at 1 s so heavy setups register as failures | H |
| 4 | "A good seed corpus doesn't prove the target is fuzzable"; encrypted/checksummed inputs give seed coverage but the engine finds nothing; if ≈10⁹ seedless iterations give poor coverage → split target, dictionary, or structure-aware | S1 Coverage discoverability | — | checksums, compression, encryption, length-prefixed chunks (S3) | H |
| 5 | Large APIs: "Fuzzing scales super-linearly"; >20–30k reachable edges → several narrower targets; OSS-Fuzz: "the smaller fuzz target is, the better" | S1, S27d | — | monolithic "fuzz everything" target | H |
| 6 | Dictionaries help when inputs "consist of tokens or have lots of magic values" | S6, S7 | text formats, protocols | without them keyword-driven parsers stay shallow (S29c: `<html>` keywords missing) | H |
| 7 | OSS-Fuzz per-language envelope: Go/Rust/Python only `libfuzzer` engine; Go/Rust only `address` sanitizer; Python ASan/UBSan (for native code); native Go `F.Add()` seeds are ignored there | S27c | OSS-Fuzz | agent must not promise AFL++/honggfuzz/MSan for these languages | H |
| 8 | Stopping heuristics in engine docs: AFL++ "allow at least one queue cycle without any new finds"; "if no new path is found for a long time" fuzzing is unlikely fruitful; `corpus count` is "a bad indicator" of coverage — use `afl-showmap`/llvm-cov | S30a, S30c | — | reading corpus size as progress | H |
| 9 | Each additional vulnerability costs exponentially more machine time at constant time budget (≈4 CPU-years, ≈300 programs) | S35 | greybox campaigns | — | M (partially verified) |

### 3.3 Generation / grammar-based and structure-aware fuzzing

| # | claim | src | validity region | failure modes | conf |
|---|---|---|---|---|---|
| 1 | "Grammars are powerful tools to express and produce syntactically valid inputs"; outputs usable "as is, or used as seeds for mutation-based fuzzing" | S29d | nested/recursive text inputs (URLs, expressions, config languages) | "one quickly reaches the limits of what a grammar can express" — semantic constraints (port ranges, references, checksums) not expressible; grammars as strings are "fairly easy to introduce errors" into | H |
| 2 | Without structure awareness "any traditional mutation (e.g. bit flipping) leads to an invalid input rejected by the target API"; examples: compressed data, PNG chunk CRCs, protobuf/IDL | S3 | checksummed, compressed, serialised formats | "requires substantial manual work for every input type" | H |
| 3 | Rust: `Arbitrary` turns fuzzer bytes into typed values so a target "can take instances of `Rgb` directly"; `Vec<Op>` of enum commands drives a stateful allocator; the book notes `fuzz_mutator!` mutation "provides better coverage over time than `arbitrary`-based generation" | S18, S21 | typed Rust APIs | generation-only loses mutation locality | H |
| 4 | Python: Atheris `FuzzedDataProvider` (ints, floats incl. NaN/Inf, strings, picks); custom mutator for zlib finds the planted bug "in a matter of seconds" and never without it | S24 | typed Python APIs; compressed inputs | — | H |
| 5 | Go native fuzzing supports only `[]byte,string,bool,byte,rune,float32/64,int*,uint*`; "Interfaces, functions, and channels … will never be supported"; structs only via marshalers (future) | S8, S11, S12 | Go | agent must derive structs from bytes/strings itself or use rapid's generators + `MakeFuzz` (S23) | H |
| 6 | Splitting one byte input into several typed values: FDP (dynamic, breaks seed-file validity), hash-based (easy, but local mutation → large sub-input change), magic separator, protobuf | S4 | multi-argument functions | — | H |

### 3.4 Property-based testing (QuickCheck lineage: Hypothesis, proptest, rapid)

| # | claim | src | validity region | failure modes | conf |
|---|---|---|---|---|---|
| 1 | PBT: the library "picks which inputs to check, including edge cases"; failing cases shrink to "the simplest possible one"; replayed from an example database | S25, S22, S23 | typed functions with statable properties | "only a randomly sampled portion of the input space can be explored" — misses single-value edge cases (`i64::MIN`); "traditional unit testing with intelligently selected cases is still necessary" (S22) | H |
| 2 | Default budget is small: Hypothesis `max_examples=100` | S25 | fast feedback (seconds) | not a coverage search; HypoFuzz/`fuzz_one_input` or `rapid.MakeFuzz` add coverage guidance (S23, S25, S26) | H/M |
| 3 | rapid: "property-based tests give a fast feedback loop of seconds. Fuzzing runs slow, brute-force input generation, often over days"; rapid "lacks coverage-guided feedback" but generates complex structured data | S23 | Go typed APIs | — | H |
| 4 | "it can be hard or impossible to define a strategy which actually produces useful inputs" — a `.{1,4096}` string strategy "may be great to fuzz a C parser" but rarely reaches a code generator | S22 limitations | — | generator design is the cost | H |
| 5 | Five kinds of properties: invariants, postconditions, metamorphic, inductive, model-based; on eight buggy variants model-based and metamorphic were the strongest (model-based ≈100 %) | S36 | pure functions | invariants alone miss most bugs; generators and shrinkers must themselves be tested | M (partially verified) |
| 6 | Go's `testing/quick` "is frozen and is not accepting new features" | S13 | Go | do not recommend it; use rapid | H |

### 3.5 Symbolic / concolic execution

| # | claim | src | validity region | failure modes | conf |
|---|---|---|---|---|---|
| 1 | Solves path constraints to reach branches that random mutation cannot ("relying on randomness … is a bad idea when the space to be explored is huge"); "well suited for programs that rely on specific values to be present in the input" | S29e | magic values, narrow equality checks | "necessarily computation intensive"; "broad but shallow"; loops only unrolled to fixed depth | H |
| 2 | Concolic: "provide more information than taint analysis … at a much larger runtime cost"; "real-time analysis is often not possible"; implicit control flow and calls into native/unmodelled code discard symbolic information | S29f | small pure functions; hybrid with fuzzing | solver timeouts (Z3 30 s in the book), unsupported operators, type annotations required (S29e) | H |
| 3 | No mainstream production tooling for Go/Rust/Python harnesses; in C it is used as a fuzzing assistant (QSYM "can do concolic execution relatively fast", S30/`afl-based-fuzzers-overview`) | S5 overview page, S29f | — | agent should not generate concolic harnesses; use dictionaries/`-use_value_profile` (S7) as the cheap substitute | M |

### 3.6 Differential testing

| # | claim | src | validity region | failure modes | conf |
|---|---|---|---|---|---|
| 1 | "Any difference in the output of the applications implies that at least one of them has a bug"; used on cryptography libraries and JS engines, and across optimisation levels | S5, S2 | two or more implementations of one specification | the oracle holds only where behaviour is fully specified: Csmith must emit programs "free of undefined behaviors (believe us, that's not trivial)" (S38); otherwise every disagreement is noise | H |
| 2 | Csmith: >325 compiler bugs (PLDI 2011) | S38 | — | heavy test-case reduction and triage | M |
| 3 | go-fuzz guidance: compare two implementations for equal output; OpenSSL `BN_mod_exp` miscalculation found this way | S16, S2 | codecs, math, parsers with a reference (stdlib, C library via FFI, naive implementation) | implementation differences that are documented (ordering, float formatting) must be normalised | H |

### 3.7 Metamorphic testing

| # | claim | src | validity region | failure modes | conf |
|---|---|---|---|---|---|
| 1 | MT addresses the oracle problem: correctness checked "through relations between outputs" of related inputs rather than an expected value; MRs are "necessary properties of the target function … in relation to multiple inputs and their expected outputs" | S37 | numeric, search, optimisation, ML, compilers — anywhere the exact answer is unknown | MRs are necessary, not sufficient; identification is manual and domain-specific | H (definition), M (details) |
| 2 | Hughes: metamorphic properties among the two most effective kinds | S36 | pure functions | — | M |
| 3 | Round trip is the special case every codec has: `decode(encode(x)) == x` and `encode(decode(b))` stable (Go tutorial, Go blog, go-fuzz, rust `url` trophy "failed round-trip parse") | S9, S10, S16, S19 | encoders/decoders/formatters/parsers | one-way lossy formats need a weaker relation (idempotence after one round) | H |

### 3.8 Stateful / model-based testing

| # | claim | src | validity region | failure modes | conf |
|---|---|---|---|---|---|
| 1 | proptest-state-machine: a reference model and the SUT apply the same generated transitions; preconditions restrict valid transitions; "Invariants … will be checked after every transition"; recommended for "data structures with mutating APIs, database APIs, or client-server interactions" when "correctness is important" | S22 state-machine | mutating APIs | "takes a bit more time to run than simple prop tests"; model must be written | H |
| 2 | Hypothesis `RuleBasedStateMachine`: rules, bundles (values produced by earlier rules), `precondition` "better than using assume", `initialize` | S25 | Python stateful APIs | rules cannot take pytest fixtures/parametrize | M (snippets) |
| 3 | rapid: state-machine tests supported in Go | S23 | Go | — | H |
| 4 | Coverage-guided variant: a `Vec<Op>` enum (Rust `Arbitrary`) or a protobuf "trace" message "describing a sequence of API calls" replayed by the target; ngolo-fuzzing generates this for Go stdlib packages | S18, S3, S17 | APIs whose valid call sequences are easy to encode | ngolo's own limitation: it wrongly assumes a package never panics for arbitrary sequences (`regexp.MustCompile`) — must exclude functions whose contract permits panics | H |

### 3.9 What fuzzing finds in memory-safe languages (evidence)

| # | claim | src | detail | conf |
|---|---|---|---|---|
| 1 | Go: a failure is "a panic", `t.Fail`, an unrecoverable error "such as an `os.Exit` or stack overflow", or an execution over 1 s; the design draft adds race conditions | S8, S11 | no memory-corruption oracle exists in pure Go | H |
| 2 | go-fuzz trophies (≈400 entries): index/slice out of range (`fmt`, `image/png`), nil deref (`html/template`), hangs (`archive/tar: deadly hang`, `go/constant` hang), OOM/excessive allocation (`x/image/bmp`, `encoding/gob: makeslice`), wrong acceptance (`archive/zip` wrong checksum accepted, `net/http` invalid header chars), round-trip failures (`image/gif LoopCount`, `archive/tar Writer`), slow regexp (4 s) | S16 | all four classes the agent should expect: panic, hang, OOM, logic-via-oracle | H |
| 3 | Go stdlib bugs still found in 2022–2024 by OSS-Fuzz API-sequence targets: `math/big Float.GobDecode` index out of range on a 4-byte input (Security label, release-blocker, backported); `debug/buildinfo` slice bounds out of range | S14 | a maintainer: Go treats panics in functions that take external input as security issues | H |
| 4 | Go security policy lists as past security issues: `archive/zip` panic in `Reader.Open`, stack exhaustion in `go/parser` and `path/filepath.Glob`, unbounded reads in `encoding/binary.ReadUvarint` | S15 | DoS classes are "security" in Go → crash+timeout+OOM oracle is worth running on untrusted-input decoders | H |
| 5 | Rust trophy case (≈380–400 rows): ≈20 % arithmetic overflow, ≈19 % out-of-range index, ≈17 % logic, ≈10 % explicit panic/assert, ≈10 % OOM, ≈6 % unwrap-on-None/Err, ≈6 % UTF-8 boundary, ≈4 % infinite loop, ≈4 % stack overflow, <1 % uninit/UAF/segfault; "Security?" marked on a small minority | S19 | memory-unsafety is rare and tied to `unsafe`/FFI (`capnproto` OOB read, `sxd-document` UAF) | H for shape; M for exact percentages |
| 6 | cargo-fuzz passes `-Cdebug-assertions` unless `--release`; overflow panics therefore only appear in debug-assertion builds; `--cfg fuzzing` lets code disable signature/checksum checks under fuzzing | S20, S18 guide | agent must keep debug assertions on or the ≈20 % arithmetic class disappears | H |
| 7 | Rust book oracle chapter: "a high-quality harness should validate every reference obtained from the target library" (touch returned data through `black_box`) because ASan only fires on access | S18 oracles | FFI/unsafe-wrapping crates | H |
| 8 | Python: "Atheris will report a failure if the Python code under test throws an uncaught exception"; sanitizers add value only for native extensions, which "must be instrumented" | S24 | pure Python: oracle = exception/hang/recursion; must enumerate expected exceptions | H |
| 9 | OSS-Fuzz overall: >13,000 vulnerabilities and 50,000 bugs across 1,000 projects (May 2025); the MSR 2021 study (23,907 bugs, 316 projects): timeouts/OOM "unusually flaky", "flaky bugs are mostly unfixed", CVEs rare and mostly memory corruption | S27a, S39 | memory-safe share of OSS-Fuzz is small; no per-language breakdown found — **open question** | M |

### 3.10 Oracles beyond crash

| oracle | what it detects | needs from target | fits | sources |
|---|---|---|---|---|
| Crash / uncaught panic / exception | index OOR, nil/None, unwrap, assert, overflow (Rust debug), UTF-8 boundary | nothing | every target; the *only* oracle in a first byte-level target | S8, S19, S24 |
| Sanitizers (ASan/UBSan/MSan/LSan) | memory corruption, UB, leaks | C/C++/unsafe/FFI compiled with instrumentation; OSS-Fuzz: ASan only for Go/Rust | code with `unsafe`, cgo, C extensions | S2, S27c, S24 |
| Timeout | infinite loops, super-linear algorithms (regexp 4 s) | fixed per-input budget (Go 1 s; libFuzzer 1200 s default, lower it) | parsers, regex, decompressors | S8, S7, S16 |
| Memory / allocation limit | unbounded allocation from length fields (`makeslice`, bmp OOM) | `-rss_limit_mb`, `-malloc_limit_mb` | decoders of length-prefixed formats | S6, S7, S16 |
| Round trip | lossy/asymmetric encode–decode, normalisation bugs | both directions implemented; equality notion | codecs, marshal/unmarshal, parse/print, URL/query | S9, S10, S16, S19 |
| Differential | wrong results against a reference | second implementation of the same spec; normalised output; spec must define the behaviour (no UB) | crypto, math, parsers with stdlib/C reference, re-implementations | S5, S16, S38 |
| Metamorphic relation | wrong results without a reference | domain knowledge to write MRs | numeric, search, sorting, compression ratio monotonicity | S37, S36 |
| Invariant / postcondition | violated data-structure or output invariants | cheap checker function | containers, allocators, parsers (output valid UTF-8) | S9, S36, S22 |
| Model-based (state machine) | divergence from a simple model across call sequences | model + transition enum + preconditions | mutating APIs, protocols, caches, DBs | S22, S25, S18 |
| "Never panics" vs "returns error" | contract violation | an explicit statement of which it is | `Parse`-style APIs: never panic, may error; `Must*`: may panic by contract (exclude, S17) | S14, S15, S17 |

### 3.11 Evaluation evidence relevant to the agent

| # | claim | src | conf |
|---|---|---|---|
| 1 | Klees et al. examined 32 fuzzing papers (2012–2018) and "found problems in every evaluation": most did not run multiple trials; those that did used no statistical test; short, unjustified timeouts; "unique crashes" counted by AFL coverage or stack hash rather than distinct bugs; small disjoint benchmark sets; seed choice changed outcomes. They ran 30 trials themselves (confirmed via S32) and recommend statistical tests, ≥24 h, published seeds, ground-truth bugs | S31, S32 | M (partially verified); the specific cxxfilt figure "57,142 crashing inputs → 9 bugs" from memory: **UNVERIFIED** |
| 2 | fuzz-evaluator guidelines v1.0.3: "≥ 10 trials", "≥ 24h", same seeds for all fuzzers and publish them, "Do not use the number of (unique) crashing inputs as bug count", deduplicate to true bugs (vendor confirmation or manual triage), source-level coverage on a neutral (uninstrumented, unsanitised) binary, avoid "queue survivor bias", same compute per fuzzer | S32 | H |
| 3 | Residual risk (probability the next input reveals an unseen behaviour) is bounded by the Good-Turing discovery probability p₀ = f₁/n (singleton species / inputs); "If the probability to discovery a new species is too low, we might as well abort the campaign" | S29g, S34 | H (book), M (paper) |
| 4 | Variance: "Sometimes, the fuzzer that we claim to be superior does not seem to outperform the inferior fuzzer" in a single run | S29c | H |
| 5 | Crash state = stack-trace signature used for dedup; a crash is "reliably reproducible if the target program consistently crashes with the same crash state for the given input" | S28 | H |

### 3.12 Cost side and anti-patterns

| # | claim | src | conf |
|---|---|---|---|
| 1 | Timeouts and OOMs are reported as bugs "since they significantly reduce the efficiency of fuzzing"; no good dedup for them → one timeout + one OOM bug per target; limits adjustable per target `.options` | S27d | H |
| 2 | Targets with shallow bugs stall: "It should not have shallow, easily found bugs, or fuzzing stalls quickly" | S1 | H |
| 3 | Maintenance contract: targets live in the project repo, run with sanitizers in normal testing using the seed corpus; bug-triggering inputs go into the seed corpus as regression tests; dictionary "maintained alongside the fuzz target"; coverage monitored | S1, S27e | H |
| 4 | CI: rust-fuzz book recommends a 300 s smoke run per target on push/PR, uploading `fuzz/artifacts` on failure; Go runs seed entries on every `go test`; cargo-fuzz needs nightly and x86-64/aarch64 | S18 ci, S8, S20 | H |
| 5 | Go generated corpus in `$GOCACHE/fuzz` has "no limit to the number of files or total bytes" — several GB; `go clean -fuzzcache` | S10, S8 | H |
| 6 | "Fuzzing is not a substitute for explicitly testing functional requirements"; fuzz finds "programming errors unrelated to the project requirements" | S2 | H |
| 7 | Harness quality: "Writing a harness that actually exercises the interesting parts of the target is a skill of its own" | S30a | H |
| 8 | Instability: threads, time, `random()`, uninitialised memory, persistent state; AFL++ warns below 90 % stability; a target that keeps state between iterations gives phantom coverage | S30c, S30d | H |
| 9 | Debug output and disk I/O slow fuzzing; read from disk only in one-time init; never write | S1, S16 | H |
| 10 | OSS-Fuzz runtime: no package assumptions, "Everything except `/tmp` is read-only", no `/dev`, unknown cwd — any filesystem/network dependence breaks the target | S27f | H |

Anti-pattern list with the evidence behind each (the agent's "do not do" list):

| anti-pattern | why it fails | src |
|---|---|---|
| Fuzzing a function that only forwards to `json.Unmarshal`/`serde_json`/`json.loads` | the library is already fuzzed upstream ("all errors found are already fixed"); the wrapper adds ≈0 edges; shallow target | S29a, S1, S17 (stdlib already under OSS-Fuzz) — *inference from these, not a verbatim rule* |
| Fuzzing with the unit-test inputs as the only seeds and a short `-runs` | coverage-guided search needs time and diversity: "diversity is more important" than volume; seeds alone "don't prove the target is fuzzable" | S16, S1 |
| Asserting on internal state / exact output for arbitrary inputs | "you can't predict the output for arbitrary inputs, so the test checks properties instead" | S9 |
| One monolithic target over a whole API | super-linear scaling; split >20–30k edges; "the smaller fuzz target is, the better" | S1, S27d |
| Target depends on time/RNG/network/DB/files | non-determinism → low stability, irreproducible crashes; OSS-Fuzz runtime forbids it | S7, S30c, S27f |
| Calling `os.Exit`/`process::exit`/`sys.exit` or `log.Fatal` in the path | "must not exit() on any input" | S7, S1 |
| Treating a `Must*`/`unwrap`-by-contract panic as a bug | contract permits it; exclude or wrap (ngolo had to exclude `regexp.MustCompile`) | S17 |
| Building Rust targets with `--release` and no `-Cdebug-assertions` | loses the arithmetic-overflow class (≈20 % of trophies) | S20, S19 |
| Reporting "N unique crashes" | crashes ≠ bugs; dedup and triage first | S32, S31 |
| Judging progress by corpus size | "corpus count … is a bad indicator"; use coverage | S30a |

## 4. Disagreements and open questions

1. **Generation vs mutation for structured inputs.** The rust-fuzz book reports `fuzz_mutator!` mutation beating `Arbitrary` generation on coverage over time (S18); the Fuzzing Book treats grammar generation as the primary tool with mutation on top (S29d); Google's docs say structure-aware mutators are "one of the next big things" yet "require substantial manual work" (S3). Resolution for the agent: use typed generation (`Arbitrary`, FDP, PBT strategies) as the *default* because it is cheap and correct, and reach for a custom mutator only after a coverage plateau on a checksummed/compressed format.
2. **PBT and fuzzing: same thing or not.** rapid and proptest frame PBT as seconds-long sampling without coverage feedback (S22, S23); Hypothesis blurs it via `fuzz_one_input` and HypoFuzz (S25, S26). The design should treat them as one continuum with two budgets (test-suite budget vs campaign budget), not two tools.
3. **Is a panic a bug?** Go's policy and maintainers say yes on untrusted input (S14, S15); ngolo-fuzzing had to exclude `Must*` APIs (S17); Rust's trophy case counts `unwrap` and `panic` as bugs (S19) while RustSec debates whether a panic merits an advisory (search result, unverified). The agent must record the contract per function, not assume.
4. **How much of the OSS-Fuzz yield applies to memory-safe languages.** No per-language statistics were found; the 13k-vulnerability headline is dominated by C/C++ (S27a, S39). Open question; the Rust trophy case and go-fuzz list are the best available proxies.
5. **Klees numbers.** The paper body was unreachable; the "17 of 32 papers single-trial" and "57,142 crashes → 9 bugs" figures are from third-party summaries/memory and must be re-verified before they appear in a skill.
6. **Stopping rule.** Engine docs give heuristics (one full cycle without finds, S30c; "a long time", S30a); the statistical line gives p₀ = f₁/n (S29g, S34); Böhme & Falk say the next bug costs exponentially more (S35). They agree in direction but no document gives a threshold for p₀; a design choice is required (topic of the H2 agent).

## 5. Implications for the agent / skills

### 5.1 Applicability gate — decision table (addresses H1; the per-row oracle addresses H4)

Evaluate rows top to bottom; the first "do not fuzz" row that matches wins; otherwise the method cell applies. "PBT" = property-based test in the normal test suite (Hypothesis / proptest / rapid).

| target characteristic | recommendation | reason / source |
|---|---|---|
| **Hard stops** | | |
| Behaviour depends on network, DB, external process, wall-clock, unseeded RNG, environment, or writes to disk and cannot be injected | **do not fuzz** as is; extract the pure core (parser/validator/state machine) and gate again on that | determinism contract S1/S7; OSS-Fuzz runtime S27f; AFL++ "no direct support for network services" S30a/b |
| Persistent threads, background goroutines/tasks outliving one call, mutable global state that the target cannot reset | **do not fuzz** until refactored | "results will be unreliable" S7; stability S30c |
| One execution slower than ≈100 ms, or heavy per-input setup that cannot be hoisted into one-time init | **do not fuzz**; PBT with `max_examples` ≤100 if a property exists; else unit tests | <10 exec/s "suggests a problem" S1; Go kills at 1 s S8 |
| GUI/CLI glue, orchestration, config loading/wiring, code whose only inputs are developer-controlled constants | **do not fuzz**; unit/integration tests | S30b (GUI), S2 (functional tests first) |
| Thin wrapper that forwards to an upstream-fuzzed library (stdlib JSON/XML/URL/regexp, `serde`, `image`, well-known parsers) with no own validation/transformation logic | **do not fuzz** the wrapper; if it adds mapping logic, PBT the mapping with typed inputs | saturated targets yield nothing S29a; shallow/zero-edge target S1; stdlib already under OSS-Fuzz S14/S17 |
| Function whose contract permits panics (`Must*`, `unwrap` on programmer error, `assert` preconditions) | **do not fuzz** that entry; fuzz the non-panicking variant or filter inputs to the precondition | S17 |
| Memory-safe code, total function (always returns `(T, error)`/`Result`/raises a documented exception), no resource amplification, no oracle beyond crash | **unit tests suffice**; crash fuzzing will find nothing | the crash oracle set S19/S16 is empty for such code — *inference* |
| **Fuzz / property-test** | | |
| Untrusted raw bytes: decoders, decompressors, archive/image/font/media parsers, wire-frame parsers | **coverage-guided greybox** (`go test -fuzz` / `cargo fuzz` / Atheris) on `[]byte`; oracles: crash + timeout + RSS limit + round trip where an encoder exists; seeds = real files; dictionary if tokens/magic; structure-aware custom mutator only if checksummed/compressed/encrypted | S1, S3, S6, S16 trophies, S15 (DoS = security) |
| Structured text: JSON-like, YAML/TOML, URLs, query strings, regexes, templates, SQL/DSLs, HTTP headers, dates | **greybox + seeds + dictionary**; add grammar/typed generation if <50 % of corpus passes validation after the first run; oracles: round trip (`parse∘print`), differential vs stdlib/reference, "never panics, returns error" | S29b/d, S10 ParseQuery, S9 Reverse, S16 |
| Typed API: functions over ints/floats/strings/structs/enums, pure or near-pure | **PBT first** (Hypothesis / proptest / rapid) with invariant, postcondition, metamorphic or model-based properties; bridge to the engine (`fuzz_one_input`, `MakeFuzz`, `Arbitrary`) when the function is a hot untrusted-input path | S22, S23, S25, S36 |
| Numeric / algorithmic code (math, geometry, compression ratios, search, ranking, pricing) | **PBT with metamorphic + differential** (naive reference implementation); never crash-only | S36, S37, S38 |
| Stateful API: containers, caches, allocators, parsers with internal state, protocol state machines, DB/client wrappers (in-memory) | **model-based state-machine testing** (`proptest-state-machine`, `RuleBasedStateMachine`, rapid state machine); or enum-of-ops `Arbitrary`/protobuf trace under the coverage engine when sequences are long | S22, S25, S18, S3 |
| Code containing `unsafe`, cgo/FFI, C extensions | **greybox with ASan (+UBSan for Python native)**; harness must touch every returned reference; both OSS-Fuzz-supported | S18 oracles, S24, S27c |
| Two implementations of one spec exist (old/new, Go/C, pure/SIMD, two crates) | **differential fuzzing** under greybox; oracle = normalised equality; confirm the spec defines all behaviours first | S5, S38 |
| Security-sensitive decoder in Go/Rust where only DoS classes exist (stack depth, allocation from length fields) | **greybox with strict limits**: Go default 1 s; libFuzzer `-timeout` lowered (e.g. 10–60 s), `-rss_limit_mb` ≤ 2048, `-malloc_limit_mb` set; oracle = no timeout/OOM/stack overflow | S7 flags, S15 policy examples, S27d |

Minimum pre-conditions every "fuzz" row assumes (checklist the agent runs before writing a harness):

1. Determinism: same input → same path; RNG/clock injectable (S1, S7).
2. Speed ≥ ~100 exec/s after init hoisting; ideally ≥1,000 (S1).
3. Isolation: no network/DB/FS writes; reads only in one-time init (S1, S27f).
4. An oracle named explicitly from §3.10, beyond "no crash", unless the target is C/unsafe/FFI (S2, S19).
5. A contract statement: "never panics; returns error on invalid input" or "may panic on precondition X" (S14, S15, S17).
6. Seeds that pass validation and a dictionary if the format has tokens (S1, S6).
7. Expected per-target size: one format/one API family; split otherwise (S1, S27d).

### 5.2 Oracle selection rule (H4)

Pick the strongest oracle the target admits, in this order, and state which one is used in the harness
header: model-based → differential → round trip → metamorphic → invariants/postconditions → resource
limits → crash. In memory-safe code a harness with only the last two is acceptable *only* for untrusted
byte decoders (DoS surface, S15); otherwise the gate falls through to PBT.

### 5.3 Language-specific facts the per-language skills must carry (H5, H4)

| | Go | Rust | Python |
|---|---|---|---|
| engine | `go test -fuzz` (1.18+, AMD64/ARM64) | `cargo fuzz` (nightly, libFuzzer, x86-64/aarch64) | Atheris (libFuzzer) |
| arg types | bytes/string/bool/ints/floats only; no structs/interfaces (S8, S11) | anything via `Arbitrary` derive (S21) | `FuzzedDataProvider` (S24) |
| failure = | panic, `t.Fail`, `os.Exit`, stack overflow, >1 s per input (S8) | panic/abort, ASan report, timeout 1200 s, RSS 2 GB (S7); overflow only with `-Cdebug-assertions` (S20) | uncaught exception, timeout, RSS (S24, S7) |
| corpus location | `testdata/fuzz/<FuzzName>/` seeds (run on every `go test`); generated corpus in `$GOCACHE/fuzz`, unbounded (S8, S10) | `fuzz/corpus/<target>/`, crashes in `fuzz/artifacts/<target>/crash-<hash>` (S18 tutorial) | directory passed on the command line (libFuzzer convention) |
| skip-invalid idiom | early `return` or `t.Skip()` when the API rejects input (S9) | `if let Ok(s) = std::str::from_utf8(data)` then call (S18 tutorial); `#[cfg(fuzzing)]` to disable checksums (S18 guide) | return early from `TestOneInput`; custom mutator for compressed input (S24) |
| PBT library | rapid (`testing/quick` frozen, S13); `rapid.MakeFuzz` bridges (S23) | proptest (+ `proptest-state-machine`) (S22) | Hypothesis; `fuzz_one_input` bridges to Atheris; `hypothesis write` scaffolds (S25, S27c) |
| OSS-Fuzz envelope | libfuzzer + address only; `F.Add` ignored there (S27c) | libfuzzer + address only (S27c) | libfuzzer; ASan/UBSan for native code (S27c) |
| CI | seeds run with `go test`; `-fuzztime` smoke optional | 300 s smoke per target, upload artifacts on failure (S18 ci) | run seed corpus through `TestOneInput` in pytest; Hypothesis tests run normally |

### 5.4 Claim-hygiene rules for the agent's reports (H2 adjacent; from §3.11)

- Report **bugs**, not crashes: group by crash state (S28), reproduce each, minimise, then count.
- A result from one short run is not evidence a target is "clean"; state exec/s, runtime, coverage
  from a neutral build, number of trials (S32).
- Use p₀ = f₁/n (singleton coverage features / executions) or "one full queue cycle without a new
  find" as the saturation signal, and say which (S29g, S30c).
- Never report corpus size as coverage (S30a).

### 5.5 Skills to write (names provisional)

| skill | carries | hypothesis |
|---|---|---|
| `fuzz-applicability-gate` | §5.1 table + 7-point checklist; outputs one of {fuzz(method, oracle), PBT, unit, none} with the reason | H1 |
| `fuzz-oracles` | §3.10 table, §5.2 rule, round-trip/differential/metamorphic templates, the "contract statement" header | H4 |
| `go-fuzz`, `rust-cargo-fuzz`, `python-atheris-hypothesis` | §5.3 facts; corpus layout; flags/limits; skip-invalid idiom; `Must*` exclusion; debug-assertions | H5, H3 |
| `property-based-testing` | Hughes' five property kinds; generator-design pitfalls (S22); `max_examples` budget; bridge to engine | H4, H3 |
| `stateful-model-testing` | reference model + transition enum + preconditions + invariants; when sequences need the coverage engine | H3, H4 |
| `fuzz-claim-hygiene` | §5.4 | H2 |

## 6. Candidate eval cases

| # | input the agent sees | expected behaviour |
|---|---|---|
| 1 | Go: `func LoadConfig(path string) (*Config, error)` that reads a YAML file and calls `yaml.Unmarshal` | **do not fuzz**; reason: filesystem dependence + thin wrapper over an upstream-fuzzed parser; suggest unit tests for own validation; at most PBT on `validate(*Config)` |
| 2 | Go: `func ParseFrame(b []byte) (Frame, error)` custom binary protocol with length-prefixed fields | **fuzz**: `go test -fuzz` on `[]byte`, seeds from captured frames, oracles: no panic/timeout/OOM, `Encode(Decode(b))` round trip where Decode succeeds; file under `testdata/fuzz/FuzzParseFrame/` |
| 3 | Rust: `pub fn parse(&str) -> Result<Ast, Error>` for a small expression language, plus `Display` for `Ast` | **fuzz** with `cargo fuzz`, `str::from_utf8` guard, dictionary of keywords/operators, oracle: `parse(ast.to_string()) == Ok(ast)`; keep debug assertions |
| 4 | Rust: `pub fn mean(xs: &[f64]) -> f64` | **PBT** (proptest) with metamorphic relations (permutation invariance, scaling, `min ≤ mean ≤ max`) — not a fuzz target |
| 5 | Python: `def handler(event, context)` AWS Lambda that calls boto3 and writes to DynamoDB | **do not fuzz**; network/DB dependence; extract the pure transformation and PBT it with Hypothesis |
| 6 | Python: `class LRUCache` with `get/put/evict` | **model-based**: Hypothesis `RuleBasedStateMachine` against a dict+order model; invariant `len ≤ capacity` |
| 7 | Go: `func MustCompilePattern(s string) *Pattern` and `func CompilePattern(s string) (*Pattern, error)` | fuzz `CompilePattern` only; exclude `Must*` (contract permits panic) |
| 8 | Rust crate wrapping a C library via FFI (`extern "C"`) | **fuzz** with `cargo fuzz` (ASan default), harness touches every returned slice/reference (`black_box`) |
| 9 | Go: `func Reverse(s string) string` (tutorial) | **fuzz** with two properties: double reverse round trip, output valid UTF-8; `t.Skip`/early-return for invalid UTF-8 input after the fix |
| 10 | A target the agent wrote runs at 3 exec/s because it spins up an HTTP test server per input | **stop and refactor** (hoist server to init or remove network); do not run the campaign; cite the <10 exec/s rule |
| 11 | After 1 h the corpus has 12 entries, coverage flat since minute 5, all inputs fail a CRC check | **change method**, not budget: add `#[cfg(fuzzing)]`/build-tag to skip CRC, or a custom mutator fixing up CRC; do not keep running |
| 12 | Agent is asked to "fuzz the whole `pkg/api` package" (200 exported functions) | split into per-format/per-family targets; refuse the monolithic target (>20–30k edges rule) |
| 13 | Agent's report draft says "found 41 unique crashes" | rewrite: dedup by crash state, reproduce, report distinct bugs with minimised inputs |
| 14 | Python pure function `normalize_email(s: str) -> str` | **PBT** (idempotence `f(f(x)) == f(x)`, case-insensitivity MR); not an Atheris target unless it is on an untrusted hot path, then `fuzz_one_input` bridge |
| 15 | Go decoder where only DoS matters (`archive`-like, nested structures) | **fuzz** with crash+timeout+allocation oracle; justify via Go security policy classes (stack exhaustion, unbounded reads) |

## 7. Micro-examples

**7.1 Round-trip + validity oracle in Go (from the official tutorial, S9).** The fuzz target checks two
properties — "Reversing a string twice preserves the original value" and "The reversed string preserves
its state as valid UTF-8" — and found two bugs: byte-wise reversal producing invalid UTF-8 (`"\x9c\xdd"`),
then `[]rune` conversion replacing an invalid input byte so the round trip failed for `"\x91"`. Fix:
return an error when `!utf8.ValidString(s)`, and in the target `return` (or `t.Skip()`) on that error.

```go
f.Fuzz(func(t *testing.T, orig string) {
    rev, err1 := Reverse(orig)
    if err1 != nil { return }           // API rejects input: not a bug
    doubleRev, err2 := Reverse(rev)
    if err2 != nil { return }
    if orig != doubleRev { t.Errorf("Before: %q, after: %q", orig, doubleRev) }
    if utf8.ValidString(orig) && !utf8.ValidString(rev) {
        t.Errorf("Reverse produced invalid UTF-8 string %q", rev)
    }
})
```
Crashers are written to `testdata/fuzz/FuzzReverse/<hash>` as `go test fuzz v1` / `string("泃")` and
re-run by plain `go test` (S9).

**7.2 Typed, stateful target under a coverage-guided engine in Rust (S18 structure-aware chapter).**
For a custom allocator the book defines `enum AllocatorMethod { Malloc{size}, Free{index}, Realloc{index,size} }`
deriving `Arbitrary`, and the target takes `Vec<AllocatorMethod>` — "This works because `Vec<T>`
implements `Arbitrary` when `T` implements `Arbitrary`" — replaying each as a real call. Same idea in Go:
ngolo-fuzzing's protobuf "list of enum/union of each function" (S17), with the caveat that functions whose
contract allows panics must be excluded.

**7.3 Why the method, not the budget, must change on structured input (S24).** Atheris' zlib example:
`TestOneInput` decompresses and raises only if the result equals `'FU'`; plain byte mutation "will usually
fail at decompression" and never reaches the check, while a custom mutator that decompresses → mutates →
recompresses finds it "in a matter of seconds". The Go analogue in go-fuzz's README: "The chances that
go-fuzz will generate the correct checksum are very low", so recompute checksums inside the target (S16).

**7.4 What a memory-safe stdlib bug found by fuzzing looks like (S14).** `math/big Float.GobDecode` on
`[]byte{0x1, 0x0, 0x0, 0x0}` panicked with "index out of range [3] with length 2" in
`encoding/binary.bigEndian.Uint32`; found by an auto-generated API-sequence target on OSS-Fuzz; fixed by
"check buffer lengths in GobDecode"; labelled Security and backported — the oracle was the plain panic,
the input kind was untrusted bytes, the target was a decoder: exactly the gate's first "fuzz" row.
