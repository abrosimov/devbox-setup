---
note_id: "20261103150902"
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
aliases: ["R2"]
tags: [fuzzing, design/research, h2, h3, h5]
topic: "Saturation theory; engine observables; corpus lifecycle; CI budgets; stopping algorithm"
addresses: ["[[H2-no-stopping-rule]]", "[[H3-random-seeds-for-structured-input]]", "[[H5-harness-conventions]]"]
related: ["[[research-index]]", "[[research-corpus]]"]
---
# When to stop fuzzing, when to move on, and the corpus lifecycle around it

> Historical research from 2026-11-03; the body below is retained as provenance. Its proposals
> are not current requirements. The 2026-11-10 disposition is [[methodology-review]]: PBT and
> mutation analysis are excluded; saturation/escalation rules and provider recipes must not be
> imported into authoring. Current operations are specified in [[agent-procedure]].

Research input for the fuzzing-tests-writer agent design doc. Topic: an executable stopping
algorithm (inputs, thresholds, decision) per engine, plus the seed-corpus lifecycle.
Retrieval date: 2026-11-03. Network note: `fuzzingbook.org`, `llvm.org`, `arxiv.org`,
`mboehme.github.io`, `go.dev`, `aflplus.plus`, `hypothesis.readthedocs.io`, `google.github.io`
and `rust-fuzz.github.io` were **not resolvable** from this session; every primary source below
was instead read from its GitHub repository (sparse clones of the docs/source), which for tool
documentation is the same text. Böhme's three papers could not be fetched from any host; their
claims are taken from the fuzzingbook chapter he co-wrote (fully read) and from abstract-level
search snippets, and are marked accordingly.

## 0. Summary for the design doc (≤ 25 lines)

1. There is one theory of "done" in fuzzing and it is statistical, not temporal: treat coverage
   elements as *species*; the Good-Turing estimate `p0 = f1/n` (singleton species / inputs run)
   is the probability that the *next* input discovers something new and is an **upper bound on
   residual risk**; `1/p0` is the expected inputs until the next discovery (S1, S2). The agent
   should stop when `1/p0` exceeds the executions it can still afford at the observed exec/s.
2. Caveat the agent must carry: greybox fuzzers are *adaptive*, so blackbox estimators such as
   Good-Turing **systematically under-estimate** residual risk (S4, abstract-level). Treat `p0`
   as "optimistic lower edge", never as proof; report it, do not certify with it.
3. No engine prints `f1`. What they print: libFuzzer `cov/ft/corp/exec/s` + `NEW`/`REDUCE` lines
   and `stat::new_units_added`; AFL++ `fuzzer_stats` (`cycles_wo_finds`, `time_wo_finds`,
   `last_find`, `pending_favs`, `stability`, `execs_per_sec`) and the cycle-counter colour
   magenta→yellow→blue→green; Go `new interesting: N (total: M)`; honggfuzz `Cov Update: X ago`.
   The practical plateau signal is therefore *time/execs since last new coverage*, and the agent
   can compute `f1` itself only by counting per-feature incidence from a coverage dump.
4. Sourced stopping rules are coarse: AFL++ "at least one queue cycle without any new finds"
   (hours to a week) and "no new path for a day or a week → not fruitful any more, but often it
   just means switch strategy" (S8, S9). Go: "it is up to you"; expect `new interesting` to
   taper (S12). Hypothesis stops at `max_examples` (default 100) or on search-space exhaustion;
   it is budgeted by count per test, not by coverage (S15). libFuzzer has no built-in rule;
   `-max_total_time`/`-runs` are the only stops (S7).
5. Budgets that practice actually uses: ClusterFuzzLite PR fuzzing 600 s (quits on first
   crash), batch 3600 s on a schedule, daily `prune`, daily/weekly `coverage` (S17); CIFuzz 10
   min split across affected targets (S18); cargo-fuzz CI smoke 300 s (S14). Research evaluation
   norm: ≥ 24 h, many trials (S6). The agent's "deep" budget per target should be 24 h on a
   dedicated job, never a PR gate.
6. Cost law: with fixed time, each additional vulnerability/coverage unit costs exponentially
   more compute; re-finding known bugs is cheap (S3, abstract-level). Diminishing returns are
   structural, so "stop at this budget and record it" is the correct outcome, not a failure.
7. Plateau ≠ saturated. OSS-Fuzz FAQ lists four causes of "no new coverage for days": all
   reachable code covered, weak seed corpus, crypto/checksum blockers, too slow (S18). The agent
   must run an escalation ladder (seeds → dictionary → structure-aware → split target → other
   engine/schedule) *before* declaring a target done, and must consult a coverage report.
8. Corpus lifecycle is mechanical and should be a checklist: collect valid, small, diverse
   seeds; cmin/merge (`afl-cmin`, `-merge=1`, `cargo fuzz cmin`, ClusterFuzzLite `prune`) before
   and after; tmin crashers (`afl-tmin`, `-minimize_crash=1`, Go auto-minimise); commit the
   *regression* set (Go `testdata/fuzz/FuzzX/`, cargo `fuzz/corpus/<t>` or `seed_corpus.zip`),
   keep the *working* corpus out of the repo (Go `$GOCACHE/fuzz`, Hypothesis `.hypothesis/`).
9. Crash dedup: stack-based crash state (ClusterFuzz) is the practical key but Klees et al. show
   stack hashes over-count (~46 hashes/bug) and collide (~16 %); timeouts/OOMs cannot be
   deduped at all (one per target). Dedup is a triage aid; ground truth is "one fix".
10. Attention allocation across targets: use AFLFast's energy idea — spend on targets that still
    yield low-frequency behaviour, starve targets whose recent discovery rate is ~0; ClusterFuzz
    runs only *affected* fuzzers on a change and all fuzzers in batch (S11, S17).
11. Addresses H2 directly (stopping rule, saturation, moving on), H3/H5 via the corpus and
    reporting checklists. Section 5 contains the algorithm, checklist and report template.

## 1. Scope and question answered

Question: given an engine's own run-time statistics, when should the agent stop fuzzing a given
(target, corpus) pair; when should it instead change the corpus, the harness or the engine; and
what corpus artefacts must exist before, during and after. Out of scope: oracle design (H4),
applicability gate (H1) except where a stopping signal doubles as an applicability signal.
Engines covered: libFuzzer (incl. cargo-fuzz and Atheris), AFL++, Go native fuzzing, honggfuzz,
Hypothesis. Languages: Go, Python, Rust.

## 2. Corpus ledger

| id | source + edition/date | locator | used for | status |
|---|---|---|---|---|
| S1 | Zeller, Gopinath, Böhme, Fraser, Holler, *The Fuzzing Book*, chapter "When To Stop Fuzzing" (notebook source `notebooks/WhenToStopFuzzing.ipynb`, uds-se/fuzzingbook master, read 2026-11-03) | sections "Turing's Observations", "Estimating the Probability of Path Discovery", "Discovery Probability Quantifies Residual Risk", "A Success Estimator", "Extrapolating Fuzzing Success", "Lessons Learned", "Background" | Good-Turing, Chao1, extrapolation, residual-risk bound, single- vs multi-species | include |
| S2 | Böhme, "STADS: Software Testing as Species Discovery", ACM TOSEM 27(2), 2018 (arXiv 1803.02130) | abstract (via search); body cited through S1 | species framework, GT under adaptive bias "good estimator performance" | include, body UNVERIFIED |
| S3 | Böhme & Falk, "Fuzzing: On the Exponential Cost of Vulnerability Discovery", ESEC/FSE 2020 | abstract (via search) | cost law, budgeting | include, body UNVERIFIED |
| S4 | Böhme, Liyanage, Wüstholz, "Estimating Residual Risk in Greybox Fuzzing", ESEC/FSE 2021, pp. 230–241 | abstract (via search) | adaptive bias direction, improved estimators | include, body UNVERIFIED |
| S5 | Liyanage, Böhme, Tantithamthavorn, Lipp, "Reachable Coverage: Estimating Saturation in Fuzzing", ICSE 2023, pp. 371–383 | abstract/listing (via search) | "reachable coverage" as the denominator for % complete | park (abstract only) |
| S6 | Klees, Ruef, Cooper, Wei, Hicks, "Evaluating Fuzz Testing", CCS 2018 (+ Schloegel et al. "SoK: Prudent Evaluation Practices for Fuzzing", 2024, as restatement) | §5–§6 findings (via search snippets) | 24 h timeouts, multiple trials, stack-hash dedup unreliability | include, wording UNVERIFIED |
| S7 | libFuzzer source `FuzzerFlags.def`, `FuzzerLoop.cpp`, `FuzzerDriver.cpp` (vendored copy in rust-fuzz/libfuzzer master = compiler-rt/lib/fuzzer) | flag help strings; `Fuzzer::PrintStats`, `ReportNewCoverage`, `PrintFinalStats`, `MinimizeCrashInput` | output columns, `-merge`, `-minimize_crash`, `-max_total_time`, final stats | include |
| S7b | `llvm/docs/LibFuzzer.rst` prose ("Output", "Corpus") | not fetchable this session | — | UNVERIFIED; S7 code used instead |
| S8 | AFL++ `docs/afl-fuzz_approach.md` (AFLplusplus stable) | "Process timing", "Overall results", "Map coverage", "Stage progress", "Path geometry", "Interpreting output", `fuzzer_stats` field list | status-screen semantics, cycle colour, stopping advice | include |
| S9 | AFL++ `docs/fuzzing_in_depth.md` (stable) | §2a–c, §3c, §3f–h, §3j, §4, "CI fuzzing" list | seed collection, afl-cmin/afl-merge/afl-tmin, parallel schedules, how long, triage | include |
| S10 | AFL++ `docs/FAQ.md` (stable, via GitHub page) | "What are power schedules", "stability" | schedule recommendation, stability threshold | include |
| S11 | AFLFast `Readme.md` (mboehme/aflfast master) | "Power Schedules" table | energy formulas, attention-allocation analogy | include |
| S12 | Go, "Go Fuzzing" doc (`golang/website` `_content/doc/security/fuzz/index.md`) and tutorial (`_content/doc/tutorial/fuzz.md`) | "Running fuzz tests", "Command line output", "Failing input", "Custom settings", "Corpus file format", glossary | output semantics, corpus locations, regression behaviour | include |
| S13 | Go `src/cmd/go/alldocs.go`, `src/internal/fuzz/fuzz.go`, `minimize.go` (golang/go master) | `-fuzztime`, `-fuzzminimizetime`, `go clean -fuzzcache`; `coordinator.logStats`, minimiser | exact flag semantics, minimisation strategy | include |
| S14 | cargo-fuzz: rust-fuzz/book `src/cargo-fuzz/{guide,ci,coverage,tutorial}.md`; rust-fuzz/cargo-fuzz `src/project.rs`, `src/options/{cmin,tmin}.rs`, `README.md` | `exec_cmin`, `exec_tmin`; CI workflow | cmin = `-merge=1`, tmin = `-minimize_crash=1 -runs=255`, 300 s CI smoke, coverage dirs | include |
| S15 | Hypothesis (HypothesisWorks/hypothesis master, 2026): `hypothesis/src/hypothesis/_settings.py`, `database.py`; docs `explanation/test-case-count.rst`, `tutorial/settings.rst`, `tutorial/replaying-failures.rst`, `how-to/external-fuzzers.rst`, `changelog.rst` | property docstrings; "How many times will Hypothesis run my test?" | `max_examples`, phases, database, derandomize, CI profile, `.hypothesis` not committed | include |
| S16 | google/fuzzing `docs/good-fuzz-target.md`, `docs/glossary.md`, `docs/split-inputs.md` (master) | "Seed corpus", "Speed", "Coverage discoverability", "Large APIs", "Timeouts, OOMs, shallow bugs" | seed quality, exec/s targets, when to split | include |
| S17 | ClusterFuzzLite docs (google/clusterfuzzlite main): `docs/running_clusterfuzzlite.md`, `docs/running-clusterfuzzlite/github_actions.md`, `docs/developing_clusterfuzzlite.md` | "ClusterFuzzLite Modes", "Configuration options", workflow YAML, "Deleting unaffected fuzzers" | CI budgets, prune/coverage policy, affected-fuzzer logic | include |
| S18 | OSS-Fuzz docs (google/oss-fuzz master): `docs/faq.md`, `advanced-topics/ideal_integration.md`, `getting-started/new_project_guide.md`, `getting-started/continuous_integration.md`, `advanced-topics/corpora.md`, `advanced-topics/fuzz_introspector.md`, `new-project-guide/go_lang.md` | "What if my fuzzer does not find anything?", "Seed Corpus", "Regression Testing", CIFuzz | plateau diagnosis, seed corpus in VCS, regression driver, native Go support | include |
| S19 | ClusterFuzz `docs/reference/glossary.md` (google/clusterfuzz master) | "Crash state", "Corpus pruning", "Minimization", "Reliably reproducible" | dedup key, pruning definition | include |
| S20 | honggfuzz `docs/USAGE.md`, `display.c` (google/honggfuzz master) | flags `--run_time`, `-N`, `-M`; display labels | status fields, stopping flags | include |
| S21 | *The Fuzzing Book*, "Reducing Failure-Inducing Inputs" (`notebooks/Reducer.ipynb`) | "Why Reducing?", "Delta Debugging", "Grammar-Based Input Reduction", "Lessons Learned" | ddmin, 1-minimality, complexity, determinism prerequisite, dedup use | include |
| S22 | Fuzz-blockers registered report (Univ. Melbourne et al., FUZZING'23) and Fuzz Introspector README | via search | blockers mostly not input-related | park (not read) |
| S23 | Good 1953; Chao 1984, 1987; Shen, Chao, Lin 2003 | cited in S1 "Background" | estimator provenance | include via S1 only |

Independence note (RMP.7): S1, S2, S4, S5, S11 share one author (Böhme); S1 is the readable
restatement of S2; S4/S5 are refinements. S17, S18, S19 are one organisation's practice
(Google) and count as one tradition; S16 is the same lineage's harness guidance. S8/S9/S10/S11
are the AFL lineage. S12/S13 one source (Go team). S15 one source (Hypothesis).

## 3. Claim sheets

### 3.1 Saturation theory (species discovery)

| # | Claim | Source | Validity region | Failure modes | Confidence |
|---|---|---|---|---|---|
| T1 | Species model: an input belongs to a species (a trace hash, an edge, a feature); fuzzing is sampling; progress = species discovered `S(n)` after `n` inputs. | S1 "Estimating the Probability of Path Discovery"; S2 | Any fuzzer whose feedback can be counted per input | Needs incidence counts per species, not just the union | high |
| T2 | Good-Turing discovery probability `p0 = f1 / n` where `f1` = number of singletons (species seen exactly once), `n` = inputs executed; "the Good-Turing estimate can be computed during the campaign"; empirically "highly accurate" vs. an empirical estimate on HTMLParser (difference "probably below 0.03" in the Enigma run). | S1 "Turing's Observations", "Evaluating the Discovery Probability Estimate" | i.i.d. sampling (blackbox) | Adaptive sampling (greybox) breaks i.i.d. → see T6 | high |
| T3 | `1 - p0` is sample coverage ("progress towards completion"); `1/p0` is "a maximum likelihood estimate of the expected number of [inputs] ... before having to find a new [species]". | S1 same sections | as T2 | — | high |
| T4 | Residual risk = probability that the next input reveals an unfound vulnerability; Good-Turing on *any* species definition "is also an estimate of the maximum residual risk" (proof sketch: vulnerable sub-species are all still undiscovered, so discovery probability bounds them). Stopping heuristic stated verbatim: "If the probability to discovery a new species is too low, we might as well abort the campaign." | S1 "Discovery Probability Quantifies Residual Risk"; S2 | as T2 | Upper bound only; a low bound is not evidence of absence under adaptive bias | high |
| T5 | Chao1: `Ŝ = S(n) + f1²/(2 f2)` if `f2 > 0`, else `S(n) + f1(f1−1)/2`, estimates the asymptotic total number of species; percentage `S(n)/Ŝ` gives "% complete". Extrapolation (Shen–Chao–Lin): `Ŝ(n+m*) = S(n) + f̂0 [1 − (1 − f1/(n f̂0 + f1))^{m*}]`, `f̂0 = Ŝ − S(n)`. "It isn't always accurate — particularly at the beginning of a fuzzing campaign when the discovery probability is still very high." Multi-species variant uses `Q1`, `Q2` (incidence frequencies), estimators "almost identical". | S1 "A Success Estimator", "Extrapolating Fuzzing Success", exercises | after the early phase; needs `f2 > 0` | Early-campaign over/under shoot; `f2 = 0` degenerate form; adaptive bias | high (formulas), medium (accuracy claim transfers) |
| T6 | Greybox fuzzers are adaptive: "the probability to discover a specific error actually increases over time", so "existing estimators of discovery probability for blackbox fuzzing systematically and substantially under-estimate the true probability" of a new discovery; the paper proposes two estimator classes (a reset-based GT and a "mean local" GT/Laplace variant). | S4 abstract/snippets | greybox campaigns | Exact magnitudes UNVERIFIED (paper body not read) | medium |
| T7 | STADS' own evaluation reports "good estimator performance even for a fuzzer with adaptive sampling bias — AFL". Tension with T6 is recorded in §4. | S2 abstract snippet | AFL on the paper's subjects | — | low-medium |
| T8 | Cost law: "finding linearly more bugs in the same time requires exponentially more machines"; the same for coverage ("cover the same code exponentially faster, but uncovered code only linearly faster"); "re-discovering the same vulnerabilities is cheap but finding new vulnerabilities is expensive"; based on "over four CPU years" on ~300 programs with AFL and libFuzzer. | S3 abstract snippets | large campaigns, greybox | Assumes zero sync cost; body UNVERIFIED | medium |
| T9 | Reachable coverage (code the fuzzer can in principle reach) is the correct denominator for "% complete"; static reachability over/under-counts, so statistical species-richness estimators are proposed. | S5 abstract | — | Only abstract read | low |
| T10 | Trace coverage (hash of covered set) grows "more steadily" than statement coverage and each input yields exactly one species — "AFL uses a similar measure of progress". | S1 "Trace Coverage" | — | — | high |

### 3.2 What each engine exposes (practice)

| # | Claim | Source | Notes |
|---|---|---|---|
| P1 | libFuzzer status line: `#<runs>\t<Where> cov: <PCs covered> ft: <features> corp: <active units>/<bytes> [focus:] [lim: <current max mutation len>] [units:] exec/s: <n> rss: <Mb>`; `Where` ∈ `INITED`, `NEW   `, `REDUCE`, `pulse `, `RELOAD`, `DONE  `. `REDUCE` is printed when a new unit replaces an existing one with a smaller input (`II->Reduced`), `NEW` otherwise, both from `ReportNewCoverage`. | S7 `FuzzerLoop.cpp` `PrintStats`, `ReportNewCoverage` | `cov` is `TPC.GetTotalPCCoverage()`; `ft` is `Corpus.NumFeatures()` |
| P2 | libFuzzer stop flags: `-runs` "Number of individual test runs (-1 for infinite runs)"; `-max_total_time` "If positive, indicates the maximal total time in seconds to run the fuzzer"; loop breaks on either. No coverage-based stop exists. | S7 `FuzzerFlags.def`, `FuzzerLoop.cpp` (`TimedOut()`, `MaxNumberOfRuns`) | |
| P3 | libFuzzer early-failure signal: after the initial corpus, "WARNING: no interesting inputs were found so far. Is the code instrumented for coverage? This may also happen if the target rejected all inputs we tried so far". | S7 `FuzzerLoop.cpp` ~l.853 | use as applicability/harness-sanity check |
| P4 | `-print_final_stats=1` prints `stat::number_of_executed_units`, `stat::average_exec_per_sec`, `stat::new_units_added`, `stat::slowest_unit_time_sec`, `stat::peak_rss_mb`; `-print_coverage=1` "print coverage information as text at exit"; `-print_corpus_stats=1`. | S7 `PrintFinalStats`, flags | machine-readable end-of-run numbers for the report template |
| P5 | `-merge=1`: "the 2-nd, 3-rd, etc corpora will be merged into the 1-st corpus. Only interesting units will be taken. This flag can be used to minimize a corpus." `-set_cover_merge=1`: same but "uses the standard greedy algorithm for the set cover problem". `-merge_control_file` makes a killed merge resumable. | S7 flags | cargo-fuzz `cmin` wraps `-merge=1` (P12) |
| P6 | `-minimize_crash=1` "minimizes the provided crash input. Use with -runs=N or -max_total_time=N to limit the number attempts. Use with -exact_artifact_path"; the driver compares `DedupToken1/2` and stops with "mismatch in dedup tokens (looks like a different bug). Won't minimize further". `-cleanse_crash=1` replaces bytes to "contain fewer original bytes". | S7 flags, `FuzzerDriver.cpp` `MinimizeCrashInput` | |
| P7 | `-reduce_inputs=1` (default) "Try to reduce the size of inputs while preserving their full feature sets"; `-keep_seed=1` keeps seeds "even if they do not produce new coverage"; `-len_control=100` grows the length limit over time; `-max_len=0` guesses from the corpus; `-entropic=1` default power schedule; `-rss_limit_mb=2048`; `-jobs`/`-workers` for parallel runs, `-reload=1` reloads the shared corpus every second. | S7 flags | |
| P8 | AFL++ status: "last new find" (time since newest path); cycle counter "shown in magenta during the first pass, progresses to yellow if new finds are still being made in subsequent rounds, then blue when that ends - and finally, turns green after the fuzzer hasn't been seeing any action for a longer while". "Every fuzzing session should be allowed to complete at least one cycle; and ideally, should run much longer than that." | S8 "Overall results" | |
| P9 | AFL++ explicit stopping advice: "The fuzzing process will continue until you press Ctrl-C. At a minimum, you want to allow the fuzzer to at least one queue cycle without any new finds, which may take anywhere from a couple of hours to a week or so." And: "most fuzzing jobs should be expected to run for days or weeks; ... the first pass will probably take a day or so." | S8 "Interpreting output", "Process timing" | |
| P10 | AFL++ §3h "How long to fuzz a target?": "if no new path is found for a long time (e.g., for a day or a week), then you can expect that your fuzzing won't be fruitful anymore. However, often this just means that you should switch out secondaries for others, e.g., custom mutator modules, sync to very different fuzzers, etc." Keep `queue/` to seed other fuzzers. | S9 §3h | the "move on vs change strategy" fork |
| P11 | AFL++ sanity thresholds: no new paths "within several minutes of starting" ⇒ wrong invocation/`-m`/invalid seeds; exec speed "ideally over 500 execs/sec ... if it stays below 100, the job will probably take very long"; map density absolute "below 200 or so" ⇒ trivial/uninstrumented/bailing; "over 70%" ⇒ recompile with `AFL_INST_RATIO=10`; stability "over 90% or so" is fine (FAQ: "A value above 90% is usually fine"); `fuzzer_stats` exposes `cycles_done`, `cycles_wo_finds`, `time_wo_finds`, `last_find`, `last_edge_find`, `pending_favs`, `pending_total`, `stability`, `bitmap_cvg`, `execs_per_sec`, `saved_crashes`. "The `corpus count` value is a bad indicator for checking how good the coverage is" — use `afl-showmap -C`. "in nearly all cases you can never reach full coverage" (option-exclusive functionality needs separate campaigns). | S8, S9 §3g, S10 | |
| P12 | Go: output lines `fuzz: elapsed: …, gathering baseline coverage: i/N completed` then `fuzz: elapsed: T, execs: N (r/sec), new interesting: k (total: M)`; "For an input to be 'interesting', it must expand the code coverage beyond what the existing generated corpus can reach. It's typical for the number of new interesting inputs to grow quickly at the start and eventually slow down, with occasional bursts"; "You should expect to see the 'new interesting' number taper off over time". "it is up to you to decide how long to run fuzzing". Runs "until a failing input is found, or the user cancels". | S12 "Command line output", "Running fuzz tests" | Go emits no coverage count, only the interesting-input counter |
| P13 | Go flags: `-fuzztime t` ("Run enough iterations ... to take t ... Nx means run N times"), `-fuzzminimizetime` (default 60 s; `0` disables), `-parallel` (default GOMAXPROCS); `-fuzz` must match exactly one target; other tests run first; timeout per execution 1 s. Generated corpus in `$GOCACHE/fuzz`; `go clean -fuzzcache` "may make fuzzing less effective, temporarily". | S12 "Custom settings", S13 `alldocs.go` | |
| P14 | Go failing input: engine minimises "to the smallest possible and most human readable value" (byte/string only, tail-cut then byte-removal, S13 `minimize.go`), writes it to `testdata/fuzz/FuzzX/<hash>`, prints `To re-run: go test -run=FuzzX/<hash>`; "it will now be run by default with go test, serving as a regression test once the bug has been fixed." Seeds via `f.Add` or `testdata/fuzz/{FuzzTestName}`; `file2fuzz` converts binaries. | S12 "Failing input", "Corpus file format" | regression corpus lives in the repo by construction |
| P15 | cargo-fuzz: `cargo fuzz cmin <target>` runs the target with `-merge=1 <tmp> <corpus>` and swaps the minimised directory into `fuzz/corpus/<target>`; `cargo fuzz tmin <target> <input>` runs `-minimize_crash=1 -runs=255` (default) and says failure "just means that libfuzzer doesn't know how to minimize ... further"; `cargo fuzz coverage <target> [corpus]` replays `fuzz/corpus/<target>` without fuzzing and writes `fuzz/coverage/<target>/coverage.profdata`; crash artefacts under `fuzz/artifacts/<target>/crash-<sha1>`; libFuzzer flags pass through after `--` (`-- -max_total_time=…`). Book CI example: 300 s per target on push/PR, upload `fuzz/artifacts` on failure, labelled a "smoke test". | S14 `project.rs`, `tmin.rs`, book `coverage.md`, `ci.md`, `tutorial.md` | |
| P16 | honggfuzz: `--run_time` seconds (0 = no limit), `-N/--iterations` (0 = no limit), `--exit_upon_crash`, `-M/--minimize` ("It will most likely delete some corpus files (from the --input directory) if no --output is used!"); display shows `Iterations`, `Mode [3/3] Feedback Driven Mode` / `Corpus Minimization`, `Speed`, `Crashes`, `Timeouts`, `Corpus Size`, `Cov Update : <duration> ago`, `Coverage : edge/pc/cmp`. | S20 | `Cov Update` is the plateau signal |
| P17 | Hypothesis: `max_examples` — "Once this many satisfying test cases have been considered without finding any failing test case, Hypothesis will stop looking ... we might call your test function fewer times if we find a bug early or can tell that we've exhausted the search space; or more if we discard some test cases due to use of .filter(), assume()"; default 100 "chosen to suit a workflow where the test will be part of a suite that is regularly executed locally or on a CI server, balancing total running time against the chance of missing a bug". Phases: explicit, reuse, generate, target, shrink, explain. Failing cases saved to `.hypothesis/examples` (`DirectoryBasedExampleDatabase`) and replayed first; "Hypothesis generally recommends that the .hypothesis directory not be checked into version control" (auto `.gitignore` with `*`); `@example` is the correctness mechanism, the database "a cache that you never need to invalidate"; `GitHubArtifactDatabase` shares CI-found failures read-only with developers, "particularly useful for continuous fuzzing (i.e. with HypoFuzz)"; built-in `ci` profile: `derandomize=True, deadline=None, database=None, print_blob=True`; `derandomize` enables "quick deterministic tests on every commit, and a longer non-deterministic nightly testing run"; deadline default 200 ms. | S15 | Hypothesis has no coverage-plateau signal; HypoFuzz is the coverage-guided continuation |

### 3.3 Corpus lifecycle

| # | Claim | Source | Validity / failure modes |
|---|---|---|---|
| C1 | Good seeds: "a set of representative inputs ... should cover large portions of the API under test, ideally achieving 100% coverage"; "Avoid large seed inputs when smaller inputs are sufficient"; directory of files, subdirs allowed; extend when fixing bugs/adding features; "Monitor the code coverage achieved by the corpus and try to keep it close to 100%". | S16 "Seed corpus" | No hard byte limit is given (the oft-quoted "1 KB" rule is UNVERIFIED) |
| C2 | Coverage discoverability: a seed corpus with high coverage can still hide a non-fuzzable target (encrypted inputs); if fuzzing *without* seeds "for, say, a billion iterations" does not approach the seeded coverage, "consider splitting the target, using dictionaries, using structure-aware fuzzing". | S16 "Coverage discoverability" | The test the agent should run once per new harness |
| C3 | "The ideal corpus is a minimal set of inputs that provides maximal code coverage"; seed corpus "should be available in revision control ... regularly extended with the inputs that (used to) trigger bugs and/or touch new parts of the code"; "Fuzz targets should be regularly tested (not necessarily fuzzed!) ... with the seed corpus" via a standalone driver, with sanitizers. OSS-Fuzz ships it as `<target>_seed_corpus.zip` next to the binary; licence matters because corpus bytes "might appear in bug reports". | S18 ideal_integration, new_project_guide | |
| C4 | AFL++ collection: "Try to gather valid inputs for the target from wherever you can"; `afl-cmin` "remove inputs from the corpus that do not produce a new path/coverage" — "highly recommended, because afterwards the testcase corpus is not bloated with duplicates"; `afl-merge` appends only new-coverage inputs to an existing corpus "like libFuzzer's -merge=1"; `afl-tmin` per file "rather optional"; CI advice: "Keep the generated corpus, use afl-cmin and reuse it every time!" and do not run `-M` in short CI runs. | S9 §2a–c, CI list | |
| C5 | ClusterFuzzLite: batch fuzzing "allows a corpus of inputs to build up over time, which greatly improves the effectiveness of fuzzing"; "Corpus pruning is a helper function that minimizes the corpuses by removing corpus files (testcases) that do not increase the fuzzer's code coverage ... run corpus pruning once a day ... mandatory when you are using batch fuzzing but otherwise should not be used"; corpus stored in CI artefacts or a storage repo under `/corpus/<fuzz_target>/`; coverage reports built from the batch corpus, also used to pick *affected* fuzzers. | S17 | |
| C6 | ClusterFuzz glossary: Corpus pruning "takes a corpus and removes unnecessary inputs while maintaining the same code coverage"; Minimization "tries to minimize a testcase to its smallest possible size, such that it still triggers the same underlying bug"; Crash state "a signature that we generate from the crash stacktrace for deduplication purposes"; "reliably reproducible if the target program consistently crashes with the same crash state for the given input". Corpus (google/fuzzing) "In most contexts, ... a set of minimal test inputs that generate maximal code coverage"; cross-pollination "using a corpus for one fuzz target to expand a corpus for another". | S19, S16 glossary | |
| C7 | Delta debugging (ddmin) yields a 1-minimal input ("every character contained is required"); best case `O(log2 n)` tests, worst case `O(n²)`; "provided that the underlying test case is deterministic and runs quickly enough"; reduction "helps in identifying duplicates"; for syntactically complex inputs grammar-based reduction is "much faster and yields better results"; Hypothesis shrinking cited as the PBT counterpart. | S21 | Go's minimiser and libFuzzer's `-minimize_crash` are simpler than ddmin (tail cut + byte removal) |
| C8 | Dedup limits: OSS-Fuzz "do not have a good way to deduplicate timeout or OOM bugs. So, we report only one timeout and only one OOM bug per fuzz target"; Klees et al.: a single bug "would map to about 46 stack hashes, on average", ~16 % of hashes shared between bugs, ground truth should be patch-based. AFL++: "coverage-based grouping of crashes usually produces a small data set that can be quickly triaged manually"; `casr-afl` clusters reports. | S18 FAQ, S6, S9 §4 | |
| C9 | Stale corpus / renames: renaming a fuzz target restarts "from a fresh corpora (seed corpus only)" — copy the accumulated corpus first; `go clean -fuzzcache` likewise discards the generated corpus. Seed corpora are per fuzz-target identity, not per version; Hypothesis invalidates database entries on version or test-source change. | S18 FAQ, S13, S15 | |
| C10 | Hypothesis sharing: `ReadOnlyDatabase` lets local machines consume a CI database "without propagating changes back"; `MultiplexedDatabase` combines local + shared; `@reproduce_failure` blob is "not stable across Hypothesis versions"; prefer `@example`. | S15 database.py, replaying-failures | |

### 3.4 Continuous-fuzzing policy and cost

| # | Claim | Source |
|---|---|---|
| F1 | ClusterFuzzLite code-change mode: "defaults to fuzzing for 10 minutes", "quits after finding a single crash", runs only fuzzers whose covered files intersect the diff when coverage data exists ("If a fuzzer could not cover a file in the much longer time it has to do batch fuzzing, it is unlikely to cover it during the much shorter time it has to do code change fuzzing"); a build is "bad" if > 20 % of fuzzers crash trivially in ~10 s on no corpus. Batch: example cron every 6 h, `fuzz-seconds: 3600`, "run on a schedule such as once daily, rather than on code changes", reports all crashes; prune daily 600 s; coverage 600 s; continuous builds suppress pre-existing crashes in PR mode; `minimize-crashes` default false "reduces fuzzing time in batch fuzzing". | S17 |
| F2 | CIFuzz: "runs the fuzzers for a short amount of time" (10 min default divided among fuzzers unless coverage identifies affected ones); reports only crashes that are reproducible and absent from older builds; uses "30 day old/public regressions and corpora from OSS-Fuzz. This makes fuzzing more effective and gives you regression testing for free". | S18 continuous_integration |
| F3 | cargo-fuzz: CI run is "a smoke test ... for a small amount of time", 300 s per target on push/PR. | S14 ci.md |
| F4 | Go: no CI recommendation in the official doc beyond "it is up to you"; `go test` without `-fuzz` runs only the seed corpus "much like a unit test"; OSS-Fuzz supports native Go fuzz targets built as libFuzzer binaries (`compile_native_go_fuzzer`), where "`F.Add()` will not add seeds when fuzzing" — seeds must be shipped as `seed_corpus.zip`. The specific claim "Go recommends a dedicated job rather than every PR" was **not found** in go.dev text (UNVERIFIED). | S12, S18 go_lang |
| F5 | Evaluation norm: "consider longer (≥24 hour vs. 5 hour) timeouts; the timeout chosen changes which tool wins"; multiple trials with statistical tests (30 in the authors' own experiments). | S6 |
| F6 | OSS-Fuzz plateau diagnosis: "If your fuzz target is running for many days and does not find bugs or new coverage, it may mean ... We've covered all reachable code. In order to cover more code we need more fuzz targets. / The seed corpus is not good enough ... / crypto/crc stuff ... disabled in fuzzing mode / the fuzzer is running too slow". "the smaller fuzz target is, the better"; "many fuzz targets to test different components". Fuzz Introspector compares "static reachability potential ... against dynamic coverage" to "identify any potential blockers" and "offer suggestions on increasing coverage by adding new fuzz targets". | S18 FAQ, fuzz_introspector |
| F7 | Speed targets: "an order of 1000 executions per second per one CPU core"; "For lightweight targets, 10000 exec/s or more"; "less than 10 exec/s you are probably doing something wrong"; "typical good fuzz target would consume less than 1.5Gb"; "Any API with more than 20000-30000 reachable control flow edges should probably be considered large" → several targets; timeouts, OOMs and shallow bugs make fuzzing "stall quickly". | S16 |

### 3.5 Moving on: energy and attention

| # | Claim | Source |
|---|---|---|
| M1 | AFLFast: "most generated inputs exercise the same few 'high-frequency' paths"; AFL's constant schedule "assigns too much energy to seeds exercising high-frequency paths"; schedules (best first) `fast: p(i)=min(α(i)/β · 2^{s(i)}/f(i), M)`, `coe`, `explore: α(i)/β`, `quad`, `lin`, `exploit: α(i)`, where `s(i)` = times seed chosen, `f(i)` = inputs exercising the same path, `μ` = mean. Energy grows with how rarely a path is exercised and shrinks with how often the seed was already fuzzed. | S11 |
| M2 | AFL++ practice: run one `-M` plus `-S` secondaries each with a different schedule (`explore` default, `fast`, `coe`, `lin`, `quad`, `exploit`, `rare`); "The most effective modes are -p explore (default) and -p fast"; when stuck, "switch out secondaries", add CMPLOG/laf-intel, dictionaries, custom mutators. | S9 §3c, S10 |
| M3 | Target split triggers: large API (edge count, F7); option-exclusive functionality (P11); sub-inputs needed (regex + flags + subject; stylesheet + document; font + text) → split the byte stream rather than growing the corpus. | S16 split-inputs, S9 §3g |

## 4. Disagreements and open questions

1. **Is Good-Turing trustworthy under greybox adaptivity?** S2 (2018) reports "good estimator performance even for ... AFL"; S4 (2021, same group) says blackbox estimators "systematically and substantially under-estimate" discovery probability and proposes corrections. Resolution for the agent: use GT as a *reported* lower edge with the caveat, never as a stop-by-itself; prefer a windowed empirical discovery rate (which S4's "mean local" idea approximates) for the decision. Magnitudes unknown (paper bodies not read).
2. **Time-based vs. species-based rules.** Tool docs (S8, S9, S12) give only elapsed-time-without-finds rules; theory (S1) gives per-input probabilities. They are reconcilable through exec/s: a day without finds at 500 exec/s is `n ≈ 4·10⁷` inputs, i.e. `p0 ≲ 2.5·10⁻⁸` by the windowed estimate. The agent should express its threshold in inputs, then convert to time with the measured rate, so that slow targets are not declared saturated prematurely.
3. **One cycle without finds (AFL) vs. "a day or a week" (AFL).** Both in AFL++ docs; the first is the minimum, the second the "not fruitful" bar. Proposed: minimum for a *report*, the longer bar only for *deep* campaigns.
4. **Hypothesis is budgeted by count, not coverage.** `max_examples` is explicitly a suite-time trade-off (S15). There is no saturation signal; the docs point to HypoFuzz for coverage-guided continuation. The agent must not apply plateau logic to Hypothesis tests; it should pick a profile (default / `ci` / nightly) and move on.
5. **Stack-hash dedup.** ClusterFuzz uses crash state (S19); Klees et al. show it inflates and collides (S6). Open: how the agent should report crash counts — proposal: report *distinct crash states* and *distinct minimised inputs*, flag that both over-count.
6. **"Reachable coverage" denominator.** S5 argues neither static reachability nor observed coverage is the right denominator for "% done"; no engine exposes it. Fuzz Introspector's static-vs-dynamic comparison (S18) is the only practical tool and supports C/C++, Python, Java — not Go or Rust. Open for Go/Rust: the agent has only absolute coverage plus a hand-made list of "functions the harness should reach".
7. **Minimise crashes in batch?** ClusterFuzzLite's `minimize-crashes` defaults to false to save fuzzing time (S17), while Go minimises by default for 60 s (S13) and the fuzzingbook argues reduction is essential for debugging and dedup (S21). Proposal: minimise at report time, with a bounded budget, never inside the exploration budget.
8. **Go seeds under OSS-Fuzz.** `f.Add` seeds are ignored by the OSS-Fuzz native-Go build (S18); a Go project that wants both local `go test` regression and OSS-Fuzz needs the corpus files in `testdata/fuzz/` and a `seed_corpus.zip` built from them. Open: whether the agent should generate both.

## 5. Implications for the agent / skills

### 5.1 Stopping algorithm (addresses H2; sanity steps also serve H1/H5)

Notation: `n` = executions so far; `r` = exec/s (rolling); `B_t` = remaining wall-clock budget;
`B_n = r · B_t` = remaining executions; `Δ` = sampling interval; `W` = plateau window;
`k_W` = new species (edges/features/"interesting" inputs) discovered in the last `W`;
`n_W` = executions in the last `W`; `p̂_W = k_W / n_W` (windowed discovery rate, the
practical stand-in for GT's `p0`); `f1` = singleton species (only if a per-species incidence
count is available).

Procedure (one target, one corpus):

1. **Choose the budget class before starting.** `smoke` (PR/CI): 300–600 s per target
   [S14: 300 s; S17: 600 s default]. `batch` (scheduled): 3600 s per target or per run
   [S17 example]. `deep` (dedicated job, exploratory session): 24 h [S6 "≥24 hour"].
   `interactive` (agent exploring a new harness): 10 min hard cap (proposed default — long
   enough to pass the AFL "several minutes" sanity bar, short enough to iterate on the harness).
   Pass the cap to the engine: libFuzzer `-max_total_time=S`, Go `-fuzztime=Ss`, honggfuzz
   `--run_time S`, AFL++ `-V S` (UNVERIFIED flag name; otherwise external timeout).
2. **Sanity gate at t = 2 min (or 5 % of budget).** Abort-and-fix, do not keep fuzzing, if any
   holds: (a) libFuzzer prints "no interesting inputs were found so far" after INITED [S7];
   AFL++ "not finding new paths within several minutes" [S8]; Go `new interesting` still 0 and
   `total` equals the seed count; (b) `r` < 10 exec/s [S16 "probably doing something wrong"]
   or AFL++ < 100 exec/s [S8 "will probably take very long"] — fix the harness/persistent mode
   before spending budget; (c) AFL++ `stability` < 90 % [S8, S10]; (d) AFL++ map density
   absolute < 200 [S8]; (e) any timeout/OOM/shallow crash reproduced on seeds [S16 "fuzzing
   will stall quickly"; S17 bad-build check]. Outcome: `BLOCKED_HARNESS`, with the reason.
3. **Discoverability check once per new harness (interactive class only).** Run the same
   budget with an *empty* corpus; if coverage stays far below the seeded run, the target is
   not fuzzable as written — go to step 8 (split / dictionary / structure-aware) rather than to
   more time [S16 "Coverage discoverability"]. Proposed criterion: empty-corpus `cov`/`ft`
   < 50 % of seeded `cov`/`ft` at equal budget (proposed default; S16 gives no number).
4. **Sample every Δ = 60 s** (proposed) the engine's counters: libFuzzer `cov`, `ft`, `corp`,
   `exec/s` from `pulse`/`NEW`/`REDUCE` lines [S7]; AFL++ `fuzzer_stats` `last_find`,
   `last_edge_find`, `cycles_done`, `cycles_wo_finds`, `pending_favs`, `pending_total`,
   `execs_per_sec`, `bitmap_cvg` [S8]; Go `execs`, `new interesting`, `total` [S12];
   honggfuzz `Cov Update`, `Coverage edge/pc/cmp`, `Speed` [S20].
5. **Plateau test.** Declare a plateau when *all* of: (a) `k_W = 0` for window
   `W = max(10 min, 25 % of elapsed)` (proposed; the 25 % factor makes the window scale so
   that a long campaign is not stopped by a quiet quarter-hour); for AFL++ additionally
   `cycles_wo_finds ≥ 1` [S8 "at least one queue cycle without any new finds"] and
   `pending_favs = 0` (nothing favoured left to try; S8 describes `last_edge_execs`-based
   strategy switches firing once `pending_favs` reaches 0); (b) the plateau window contains at
   least `n_W ≥ 10⁶` executions (proposed floor; prevents "plateau" on slow targets where
   10 min is only 10⁴ inputs); (c) honggfuzz `Cov Update` age ≥ `W`.
6. **Residual-risk estimate (report-only, never sole trigger).** Compute `p̂_W = k_W/n_W` over
   the last non-empty window (if `k_W = 0`, use the last window with `k_W ≥ 1`, i.e. a
   "mean local" rate). If a per-species incidence dump exists (libFuzzer `features_dir`
   internal flag, AFL `afl-showmap -C` over the queue, custom counters in a Hypothesis
   harness), also compute GT `p0 = f1/n` and Chao1 `Ŝ` [S1]. Record the caveat that greybox
   adaptivity makes these under-estimates [S4]. Expected executions to next discovery
   `E = 1/p̂_W` [S1 "inverse of the GT-estimate"].
7. **Decision.** `STOP_SATURATED_AT_BUDGET` when plateau holds **and** `E > B_n` (one more
   discovery is not expected within the remaining budget) **and** step 8 has been exhausted
   for this budget class; `STOP_BUDGET_EXHAUSTED` when `B_t = 0` without plateau (report the
   last `p̂_W` so the next run knows it was still productive — per S3 this is where cost rises
   exponentially, so a budget stop is legitimate); `CONTINUE` otherwise. For `smoke` class skip
   steps 5–6: run to the cap and stop [S17 code-change mode semantics].
8. **Escalation ladder on plateau** (try at most one rung per plateau, then re-run steps 4–7;
   rung order sourced from S9 §3h, S16, S18 FAQ): (i) add seeds that reach uncovered regions
   shown by the coverage report (`cargo fuzz coverage`, Go `-test.coverprofile` on the corpus,
   `afl-showmap -C`, ClusterFuzzLite `coverage`); (ii) add/auto-generate a dictionary; (iii)
   switch power schedule/engine (`-p fast|explore|rare`, libFuzzer `-use_value_profile=1`,
   honggfuzz) and reseed from the other engine's queue [S9]; (iv) structure-aware mutator or
   typed-API harness; (v) split the target (sub-inputs, option-exclusive paths, > 20–30 k
   reachable edges) [S16]; (vi) disable checksums/crypto under a fuzzing cfg (`#[cfg(fuzzing)]`,
   build tag) [S14 guide, S18 FAQ]. Rungs (iv)–(vi) change the harness: they end *this*
   (target, corpus) campaign and start a new one with its own ledger entry.
9. **Crash path (pre-empts everything).** On first crash in `smoke` class: stop the target
   [S17]; in other classes: continue, but queue minimisation (`-minimize_crash=1 -runs=N`,
   `cargo fuzz tmin`, Go automatic 60 s, `afl-tmin`) and dedup by crash state + minimised
   input, bounded to ≤ 10 % of the budget (proposed; S17 disables minimisation in batch to
   protect fuzzing time). Verify reproducibility by re-running the artefact
   (`cargo fuzz run <t> <artifact>`, `go test -run=FuzzX/<hash>`, `./fuzzer <crash>`) before
   reporting; unreproducible crashes are reported separately [S17 `report-unreproducible-crashes`].
10. **Attention allocation across targets** (AFLFast analogy, M1): maintain per target the
    last `p̂_W`, time since last discovery, times already scheduled `s(t)`. Next slice goes to
    the target maximising `p̂_W · 2^{−s(t)}`-style energy: recently productive targets first,
    heavily fuzzed quiet ones last; targets whose covered files intersect the current diff get a
    mandatory slice [S17 affected-fuzzer rule]. Never let one saturated target consume the
    batch budget.

Default thresholds per engine (✓ = sourced, ◇ = proposed default):

| Observable | libFuzzer / cargo-fuzz / Atheris | AFL++ | Go native | honggfuzz | Hypothesis |
|---|---|---|---|---|---|
| Hard cap flag | `-max_total_time` / `-runs` ✓S7 | external timeout; `-V` ◇ | `-fuzztime` ✓S13 | `--run_time`, `-N` ✓S20 | `max_examples` ✓S15 |
| Smoke budget | 300 s ✓S14 / 600 s ✓S17 | 600 s ✓S17 | 300 s ◇ (no official value) | 600 s ◇ | default profile 100 ✓S15 |
| Batch budget | 3600 s ✓S17 | 3600 s ✓S17 | 3600 s ◇ | 3600 s ◇ | `ci` profile with `max_examples=1000` ✓S15 (doc example) |
| Deep budget | 24 h ✓S6 | 24 h ✓S6; "days or weeks" ✓S8 | 24 h ◇ | 24 h ◇ | nightly non-derandomised profile ✓S15; HypoFuzz for coverage-guided ✓S15 |
| Too slow | < 10 exec/s ✓S16; target ≈ 1000/s/core ✓S16 | < 100 ✓S8; ideal > 500 ✓S8 | < 10 ◇ | < 10 ◇ | deadline 200 ms per case ✓S15 |
| Sanity fail | "no interesting inputs were found" ✓S7 | no new paths in "several minutes" ✓S8; stability < 90 % ✓S10; density < 200 ✓S8 | `new interesting` = 0 after 2 min ◇ | `Cov Update` never updates ◇ | HealthCheck failures ✓S15 |
| Plateau signal | no `NEW`/`REDUCE`, `cov`/`ft` flat for W ◇ | `cycles_wo_finds ≥ 1` ✓S8 and `last_find ≥ W` ◇; "day or a week" for deep ✓S9 | `new interesting` flat for W ◇ ("taper off" ✓S12) | `Cov Update ≥ W` ◇ | none — stops at `max_examples` or exhaustion ✓S15 |
| W | max(10 min, 25 % elapsed) ◇ | same, plus ≥ 1 cycle ✓S8 | same ◇ | same ◇ | n/a |
| Min execs in W | 10⁶ ◇ | 10⁶ ◇ | 10⁶ ◇ | 10⁶ ◇ | n/a |
| Risk estimate | `p̂_W`; GT needs feature dump ◇ | `p̂_W` from `last_edge_execs`/`execs_done` ✓S8 fields | `p̂_W` from `execs`/`new interesting` ◇ | `p̂_W` ◇ | report `max_examples` and discard ratio only ◇ |
| Stop rule | plateau ∧ `1/p̂_W > B_n` ◇ (grounded in S1 T3) | same, after ≥ 1 quiet cycle ✓S8 | same ◇ | same ◇ | always stop at budget ✓S15 |
| Crash minimisation | `-minimize_crash=1 -runs=255` ✓S14 | `afl-tmin` ✓S9 | automatic, 60 s ✓S13 | manual | automatic shrink ✓S15 |

### 5.2 Corpus lifecycle checklist (addresses H3, H5)

Before fuzzing
- [ ] Collect **valid, small, diverse** seeds from tests, fixtures, docs, bug reports [S9 §2a, S16]; prefer the smallest input per feature [S16]; record provenance and licence [S18].
- [ ] Put seeds where the engine and `go test`/`cargo test`/pytest will find them: Go `testdata/fuzz/FuzzX/` (format `go test fuzz v1`) or `f.Add` [S12]; cargo-fuzz `fuzz/corpus/<target>/` [S14]; libFuzzer/OSS-Fuzz `<target>_seed_corpus.zip` [S18]; AFL++ `-i INPUTS_UNIQUE` [S9]; Hypothesis: `@example(...)` for must-run inputs, never the database [S15].
- [ ] Minimise the seed set: `afl-cmin` [S9], `-merge=1 NEW OLD` [S7], `cargo fuzz cmin` [S14]; optional `afl-tmin` per file [S9].
- [ ] Add a dictionary for token-driven formats [S9 §3a, S18 ideal_integration]; AFL++ can auto-generate (`AFL_LLVM_DICT2FILE`, `afl-clang-lto`).
- [ ] Run the discoverability check (empty corpus vs. seeded) once [S16].
- [ ] Confirm determinism and no global state [S12, S16]; fix timeouts/OOM/shallow bugs first [S16].

During fuzzing
- [ ] Keep the **working corpus out of the repo**: Go `$GOCACHE/fuzz` [S12]; AFL `out/*/queue` [S8]; Hypothesis `.hypothesis/` (auto-gitignored) [S15]; cargo `fuzz/corpus` is the exception — commit it only after `cmin`, or keep a separate storage repo as ClusterFuzzLite does (`/corpus/<fuzz_target>/`) [S17].
- [ ] Parallel instances share one corpus dir (`-jobs`/`-workers`, `-reload=1`; AFL `-M/-S` same `-o`; ClusterFuzzLite `parallel-fuzzing`) [S7, S9, S17].
- [ ] Prune daily if batch fuzzing accumulates (`prune` mode / `-merge=1` / `afl-cmin`) [S17 "mandatory when batch fuzzing"].

After a run
- [ ] Minimise crashers (`-minimize_crash`, `cargo fuzz tmin`, `afl-tmin`; Go does it) [S7, S14, S9, S13]; check the dedup token / crash state did not change [S7, S19]; verify reproduction from the artefact path.
- [ ] Commit the **regression set**: Go writes `testdata/fuzz/FuzzX/<hash>` and `go test` replays it [S12]; cargo: add the minimised crash input to `fuzz/corpus/<target>` (or a `regressions/` dir replayed by a unit test) — the book gives no convention (UNVERIFIED), OSS-Fuzz's "standalone driver over the seed corpus" is the model [S18]; Hypothesis: convert the printed failing case into `@example` (the `@reproduce_failure` blob is version-unstable) [S15].
- [ ] Merge new-coverage inputs back into the committed seed corpus (`-merge=1`/`afl-merge`/`cargo fuzz cmin`), then re-`cmin` [S7, S9, S14].
- [ ] Generate a coverage report from the corpus (`cargo fuzz coverage`, Go coverprofile over seeds, `afl-showmap -C`, ClusterFuzzLite `coverage`) and keep the uncovered-function list for the next escalation [S14, S9, S17].
- [ ] Staleness rules: a renamed target or `go clean -fuzzcache` loses the generated corpus — copy before renaming [S18, S13]; a changed input format invalidates seeds — re-run the sanity gate; Hypothesis database entries drop on version/test change [S15].

### 5.3 Report template ("this target is done at this budget")

```
Target: <package>::<FuzzName>   Engine: <libFuzzer|AFL++|go|honggfuzz|hypothesis>  Budget class: <smoke|batch|deep>
Executions: <n> over <T> (mean <r> exec/s; min <r_min>)     Workers: <k>
Seeds: <count>/<bytes> at <path>  (cmin'd: yes/no, dictionary: <path|none>)
Coverage: <cov edges / ft features | bitmap_cvg % | interesting total>; plateaued at <X> after <Y execs / Y time>
  windowed discovery rate p̂_W = <k_W>/<n_W> = <value>; E[execs to next discovery] = <1/p̂_W>
  Good-Turing p0 = f1/n = <value>  (f1=<..>, Chao1 Ŝ=<..>, S(n)/Ŝ=<..>%)  [under-estimate under greybox adaptivity]
Sanity: stability <..%>, density <..>, slowest unit <..s>, peak RSS <..Mb>
Findings: <c> distinct crash states (<m> minimised inputs, <u> unreproducible), <t> timeouts, <o> OOMs
Escalation tried: [seeds] [dictionary] [schedule/engine] [structure-aware] [split] [fuzzing-cfg]
Decision: STOP_SATURATED_AT_BUDGET | STOP_BUDGET_EXHAUSTED | BLOCKED_HARNESS | CONTINUE
Corpus committed at: <repo path>  (regression inputs: <paths>)   Working corpus: <path, not committed>
Next: <new harness to write | larger budget class | nothing>
```
Fields map to engine outputs: libFuzzer `-print_final_stats=1` (`stat::number_of_executed_units`,
`stat::average_exec_per_sec`, `stat::new_units_added`, `stat::slowest_unit_time_sec`,
`stat::peak_rss_mb`) [S7]; AFL++ `fuzzer_stats` names [S8]; Go last status line [S12].

### 5.4 Skill boundaries suggested by this topic

- `fuzz-stopping-rule` (engine-neutral algorithm 5.1 + the thresholds table) — H2.
- `fuzz-corpus-lifecycle` (checklist 5.2, per-engine paths and commands) — H3, H5.
- Per-language adapters that only fill the table rows: `go-fuzz-conventions`
  (`testdata/fuzz`, `-fuzztime`, OSS-Fuzz `seed_corpus.zip` vs `f.Add`), `rust-cargo-fuzz`
  (`cmin`/`tmin`/`coverage`, `#[cfg(fuzzing)]`), `python-atheris-hypothesis` (`max_examples`
  profiles, `fuzz_one_input` bridge, database policy) — H5.
- `fuzz-report` (template 5.3) so every campaign ends with the same artefact — H2.

## 6. Candidate eval cases

| # | Input the agent sees | Expected behaviour |
|---|---|---|
| E1 | libFuzzer log: `#2 INITED cov: 11 ft: 11 corp: 1/1b`, then 3 min of `pulse` lines with `cov: 11 ft: 11`, no `NEW`; and earlier "WARNING: no interesting inputs were found so far" | Stop at sanity gate, classify `BLOCKED_HARNESS` (uninstrumented or rejecting all inputs); do not extend budget [S7, step 2] |
| E2 | Go: `fuzz: elapsed: 3m45s, execs: 7246222 (32357/sec), new interesting: 8 (total: 41)`; last change in `new interesting` at 1m10s; budget class `interactive` 10 min | Plateau after W = 10 min not yet reached → `CONTINUE` to cap; at cap report `p̂_W = 0/…`, last productive window rate, `STOP_BUDGET_EXHAUSTED`-with-plateau; recommend one escalation rung before a batch run |
| E3 | AFL++ `fuzzer_stats`: `cycles_done 3, cycles_wo_finds 2, pending_favs 0, stability 97.5, execs_per_sec 1800, last_find 26400` (7.3 h), run_time 20 h, deep budget 24 h | Plateau satisfied (≥ 1 quiet cycle, no pending favs); `E = 1/p̂_W` from last productive window vs. `B_n = 1800 × 4 h` → likely `STOP_SATURATED_AT_BUDGET`; report, keep `queue/`, suggest switching secondaries/engine next time [S8, S9] |
| E4 | AFL++ status: exec speed 42/sec, stability 61 % | Do not fuzz further; fix harness (persistent mode, threads/uninitialised memory) — `BLOCKED_HARNESS` [S8] |
| E5 | cargo-fuzz: `fuzz/corpus/parse` has 48 000 files, CI job takes 12 min to load | Run `cargo fuzz cmin parse`, commit the minimised corpus, add nightly batch + daily prune rather than per-PR deep runs [S14, S17] |
| E6 | Hypothesis test with `@settings(max_examples=100000)` on a 50 ms property, in the PR suite | Correct answer is "do not budget it this way": default profile for PR, `ci`/nightly profile for more examples, HypoFuzz for coverage-guided; no plateau logic [S15] |
| E7 | Target: TLS record parser whose first step verifies an HMAC; seeded coverage 70 %, empty-corpus coverage 4 % after 10 min | Discoverability failure → do not grow the corpus; add `cfg(fuzzing)` bypass or split the target below the MAC check [S16, S18 FAQ] |
| E8 | Crash triage: 37 crash files from libFuzzer, 3 distinct top-3 stack frames, one is "timeout" | Report 3 crash states, minimise one representative each, one timeout bug total; caveat stack-hash over/under-counting [S19, S18 FAQ, S6] |
| E9 | PR touches only `internal/cache`; coverage report shows fuzz target `FuzzParser` never covers it | Skip `FuzzParser` in PR fuzzing (unaffected), run only affected targets [S17] |
| E10 | Repo has 12 fuzz targets, nightly budget 2 h total | Allocate by recent discovery rate, never equal slices; saturated targets get a 5-min regression slice only (energy rule, step 10) |

## 7. Micro-examples

**ME1 — Good-Turing from counters (S1 formulas).** Suppose a libFuzzer feature dump
(`features_dir`) or an `afl-showmap -C` pass gives per-feature incidence counts after
`n = 2 000 000` executions: 1 480 features total, `f1 = 12` seen once, `f2 = 9` seen twice.
Then `p0 = 12 / 2·10⁶ = 6·10⁻⁶`; expected executions to the next discovery `1/p0 ≈ 1.7·10⁵`;
at 5 000 exec/s that is ≈ 33 s, so the campaign is *not* saturated — keep going. Chao1:
`Ŝ = 1480 + 12²/(2·9) = 1488`, i.e. `S(n)/Ŝ ≈ 99.5 %` of the (fuzzer-reachable) feature
population. If instead `f1 = 0` for the last `10⁶` executions, `p̂_W = 0` and the last productive
window must be used; the report says "no singleton features; discovery rate below 10⁻⁶ per
input; greybox under-estimate caveat (S4)".

**ME2 — Reading Go's taper (S12 tutorial output, verbatim).**
```
fuzz: elapsed: 3s,    execs: 86342  (28778/sec), new interesting: 2 (total: 35)
fuzz: elapsed: 6s,    execs: 193490 (35714/sec), new interesting: 4 (total: 37)
fuzz: elapsed: 9s,    execs: 304390 (36961/sec), new interesting: 4 (total: 37)
...
fuzz: elapsed: 3m45s, execs: 7246222 (32357/sec), new interesting: 8 (total: 41)
```
`k_W` over the last window is read as Δ(new interesting); with 8 discoveries in 7.2 M
executions the lifetime rate is `1.1·10⁻⁶`, but the windowed rate between 9 s and 3m45s is
`4 / 6.9·10⁶ ≈ 5.8·10⁻⁷` and falling. With `-fuzztime 30s` the run ends by cap, not by
plateau; the agent must record "budget exhausted while still (slowly) productive" rather
than "saturated" (S12: "it is up to you to decide how long").

**ME3 — AFL++ cycle colour as a state machine (S8).** magenta = first pass incomplete →
never stop ("Every fuzzing session should be allowed to complete at least one cycle");
yellow = later passes still finding → continue; blue = a pass finished with no finds →
minimum stopping condition met ("at least one queue cycle without any new finds"); green =
long inactivity → stop or escalate (S9 §3h: "often this just means that you should switch
out secondaries"). In `fuzzer_stats` the same information is `cycles_done`,
`cycles_wo_finds`, `time_wo_finds`, `last_find`.

**ME4 — cargo-fuzz corpus round trip (S14 source).** `cargo fuzz run parse -- -max_total_time=3600`
→ `cargo fuzz cmin parse` (runs `<bin> -merge=1 <tmp> fuzz/corpus/parse`, swaps dirs) →
`cargo fuzz coverage parse` (replays `fuzz/corpus/parse`, writes
`fuzz/coverage/parse/coverage.profdata`) → on a crash `cargo fuzz tmin parse fuzz/artifacts/parse/crash-<sha1>`
(runs `-minimize_crash=1 -runs=255`) → `cargo fuzz run parse fuzz/artifacts/parse/minimized-from-<hash>`
to confirm reproduction → commit the minimised input.

**ME5 — Hypothesis budget is a count (S15).** `test-case-count.rst`: a test over
`st.integers(0, 19)` runs 20 times, not 100 ("exhausts the search space"); a test with
`assume(n % 2 == 0)` runs ≈ 200 times for 100 counted cases. The `ci` profile is
`derandomize=True, deadline=None, database=None, print_blob=True`; the documented way to
spend more is `settings.register_profile("ci", settings.get_profile("ci"), max_examples=1000)`.
Nothing here measures coverage; a "plateau" does not exist for the agent to observe.
