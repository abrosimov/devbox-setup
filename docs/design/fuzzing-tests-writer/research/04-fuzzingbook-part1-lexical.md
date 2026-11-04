---
note_id: "20261103150904"
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
aliases: ["R4"]
tags: [fuzzing, design/research, h1, h2, h3, h4]
topic: "The Fuzzing Book, Part I: lexical fuzzing"
addresses: ["[[H1-no-applicability-gate]]", "[[H2-no-stopping-rule]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]"]
related: ["[[research-index]]", "[[research-corpus]]"]
---
# The Fuzzing Book, Part I "Lexical Fuzzing" + introductory chapters — what it gives a fuzzing-tests-writer agent

Report 04 for the fuzzing-agent design document. Sources are the Fuzzing Book chapters (Zeller, Gopinath, Böhme, Fraser, Holler), read from the project's GitHub mirror because `www.fuzzingbook.org` is not resolvable from this session (see §2). Canonical URLs are given in the form `https://www.fuzzingbook.org/html/<Chapter>.html`; the content read is byte-identical in substance to those pages (same notebooks, rendered by nbconvert).

## 0. Summary for the design doc (≤ 25 lines)

1. Part I is a *mechanics* text: it teaches the loop (generate → run → classify → keep what adds coverage) and gives three lesson-level rules that map directly onto H1–H4. It says almost nothing about harness engineering (H5) and nothing about Go/Rust/Python ecosystems — that must come from other reports.
2. **Applicability (H1):** the book's own evidence says random/lexical fuzzing pays off on *input processing* ("Bugs fuzzers find are mainly due to errors and deficiencies in input processing", Fuzzer §Lessons Learned) and on code that has not been fuzzed before (troff exercise: "it has been fuzzed this way before – and all errors found are already fixed"). Deep logic behind a validating front end is unreachable by byte-level fuzzing (MutationFuzzer: 1 in 96^7 chance of a valid `http://` prefix ≈ 42 years at measured speed). The agent needs an explicit gate: "parses/decodes untrusted bytes, or has a cheap checkable property" → fuzz; "already saturated by OSS-Fuzz / pure glue code" → do not.
3. **Stopping rule (H2):** the book measures *cumulative coverage over number of inputs* and treats the plateau as the signal (Coverage: "on average, we get full coverage after 40–60 fuzzing inputs"; MutationFuzzer/Greybox: population grows only while new coverage sets appear). The design should make "coverage-set count unchanged for N inputs / T seconds" the primary stop/switch criterion, and the AFLFast path-frequency histogram the secondary one (rare paths still appearing → keep going).
4. **Seeds (H3):** one valid seed plus 2–10 stacked mutations keeps ~80 % of candidates valid (MutationFuzzer: 0.8 ratio in the 20-trial demo), vs. essentially 0 % for random bytes. Coverage-guided retention turns the population into "each and every input now is valid and has a different coverage". Dictionaries of keywords are the next cheap step; grammar/structure-aware mutation is deferred to Part III (parked here).
5. **Oracles (H4):** the book is explicit that "fuzzing is great at finding internal errors that can be detected even without checking the result" and that you should "enable as many automatic checkers as possible" (ASan, assertions, `repOK()`, type checkers). It also shows that coverage "does not care about assertions at all" and that a weak oracle scores 20 % vs 100 % under mutation analysis. For memory-safe targets the agent must add property/invariant oracles and should use mutation analysis (a small sample of statement-deletion mutants) to self-assess oracle strength.
6. **Power schedules:** uniform vs AFLFast exponential (`e(s)=1/f(p(s))^a`, a=5 in the demo) vs directed (AFLGo). Only the *idea* belongs in the agent (prefer rare-path seeds; direct energy towards a target when a specific location matters); the implementation belongs to the engine (libFuzzer/AFL++/go-fuzz/cargo-fuzz), not to the agent.
7. **Search-based fuzzing** (branch distance, hillclimbing, GA) is academic for this agent: modern engines implement value-profile/cmp-tracing instead. Keep only the diagnostic insight — equality comparisons against computed values are "needles" that plain random mutation will not hit — as a trigger to add dictionaries/`-use_value_profile`/structured generators.
8. **Mutation analysis** is practical for an agent only in a reduced form: 10–30 hand-picked or sampled mutants on the function under test, run against the harness with its oracle, to answer "would this harness notice a wrong result?". Full mutation scoring (thousands of mutants, equivalent-mutant estimation) should stay in a reference doc.
9. Three eval case families fall straight out of the chapters: (a) the `cgi_decode` incomplete-`%xx` bug (fuzzing should find it; coverage of manual tests will not); (b) the URL/`http_program` case (agent must refuse random-byte seeds and start from a valid URL); (c) the "weak vs strong oracle" triangle case (agent must flag a crash-only harness as insufficient).
10. Everything quantitative in the chapters comes from toy Python programs with no timing budget — treat the numbers as *illustrations* of shape (plateau, ratio), never as thresholds to copy.

## 1. Scope and question answered

Chapters read: Intro_Testing, Fuzzer, Coverage, MutationFuzzer, GreyboxFuzzer, SearchBasedFuzzer, MutationAnalysis. For each: stated lessons, core algorithm, validity region/limits, coverage definition and fuzzer-quality criteria, oracle guidance; plus the practicality of mutation analysis for an agent. Not in scope (parked): Part II/III (grammar, parsing, probabilistic, greybox-with-grammars, reducing), symbolic/concolic chapters, the engine documentation (AFL++/libFuzzer/go test -fuzz/cargo-fuzz/Hypothesis).

Method note: the chapters' *prose and code* were read fully (notebook JSON, master branch). The *executed outputs* were read for Coverage, MutationFuzzer and GreyboxFuzzer from the rendered HTML (partially — the pages are 450–800 kB and large fragments are CSS/SVG/base64); where an output number was not seen it is marked UNVERIFIED.

## 2. Corpus ledger

| id | source + edition/date | locator | used for | status |
|---|---|---|---|---|
| FB-INTRO | The Fuzzing Book, "Introduction to Software Testing" (notebook `Intro_Testing.ipynb`, master, fetched 2026-11-03) | https://www.fuzzingbook.org/html/Intro_Testing.html — mirror https://raw.githubusercontent.com/uds-se/fuzzingbook/master/notebooks/Intro_Testing.ipynb | oracles, limits of testing, inputs to test | include |
| FB-FUZZ | "Fuzzing: Breaking Things with Random Inputs" (`Fuzzer.ipynb`, master, fetched 2026-11-03) | https://www.fuzzingbook.org/html/Fuzzer.html — mirror …/notebooks/Fuzzer.ipynb | Miller history, bug classes, checkers, Runner/Fuzzer architecture | include |
| FB-COV | "Code Coverage" (`Coverage.ipynb`; rendered page "Last change: 2024-11-09") | https://www.fuzzingbook.org/html/Coverage.html — mirror …/notebooks/Coverage.ipynb and …/docs/html/Coverage.html | coverage definitions, measurement, plateau, black/white-box | include |
| FB-MUT | "Mutation-Based Fuzzing" (`MutationFuzzer.ipynb`; rendered page "Last change: 2024-11-09") | https://www.fuzzingbook.org/html/MutationFuzzer.html — mirror …/notebooks/MutationFuzzer.ipynb and …/docs/html/MutationFuzzer.html | validity argument, mutators, coverage-guided loop | include |
| FB-GREY | "Greybox Fuzzing" (`GreyboxFuzzer.ipynb`, master; rendered HTML partially read) | https://www.fuzzingbook.org/html/GreyboxFuzzer.html — mirror …/notebooks/GreyboxFuzzer.ipynb and …/docs/html/GreyboxFuzzer.html | AFL model, power schedules, AFLFast, AFLGo, dictionaries | include |
| FB-SBF | "Search-Based Fuzzing" (`SearchBasedFuzzer.ipynb`, master) | https://www.fuzzingbook.org/html/SearchBasedFuzzer.html — mirror …/notebooks/SearchBasedFuzzer.ipynb | fitness functions, hillclimbing, GA, limits | include (mostly park for agent) |
| FB-MA | "Mutation Analysis" (`MutationAnalysis.ipynb`, master) | https://www.fuzzingbook.org/html/MutationAnalysis.html — mirror …/notebooks/MutationAnalysis.ipynb | test-suite/oracle quality beyond coverage | include |
| FB-TOC | Table of contents | https://www.fuzzingbook.org/html/00_Table_of_Contents.html | chapter placement (Part I vs III) | not fetched (host blocked); placement taken from chapter "Next Steps" text | park |
| P-MILLER | Miller, Fredriksen, So, "An Empirical Study of the Reliability of UNIX Utilities", CACM 1990 | cited in FB-FUZZ §Background | "about a third" figure | cited via FB-FUZZ only — paper itself UNVERIFIED here |
| P-BOEHME16 | Böhme & Paul, "A Probabilistic Analysis of the Efficiency of Automated Software Testing", IEEE TSE 42:345–360, 2016 | cited in FB-GREY §Background | theoretical backing for "rare paths" | park (other report) |
| P-AFLFAST | Böhme, Pham, Roychoudhury, "Coverage-based Greybox Fuzzing as Markov Chain", CCS 2016 | named in FB-GREY as "AFLFast" | exponential schedule | park — paper not read here; schedule formula taken from FB-GREY |
| P-AFLGO | Böhme et al., "Directed Greybox Fuzzing", CCS 2017 | named in FB-GREY as "AFLGo" | directed schedule | park |
| P-PEZZE | Pezzè & Young, *Software Testing and Analysis*, 2008 | cited in FB-COV §Background, §Other Coverage Criteria | further coverage criteria; origin of `cgi_decode` | park |
| P-JIA11 / P-PAPA19 | Jia & Harman 2011 survey; Papadakis et al. 2019 overview of mutation testing | cited in FB-MA §Background | depth on mutation analysis | park |
| FB-GGF | "Greybox Fuzzing with Grammars" (Part III) | referenced from FB-GREY ("smart greybox fuzzing", AFLSmart) | structure-aware mutation | park — out of this report's scope, needed for H3 |

Access note: `www.fuzzingbook.org` failed DNS resolution in this session (not in the allowed domain list); every chapter was read from `raw.githubusercontent.com/uds-se/fuzzingbook`. If a reviewer wants the canonical pages, the host must be allowed.

## 3. Claim sheets

Confidence scale: **high** = verbatim or near-verbatim from the chapter; **med** = paraphrase of chapter prose; **low** = inferred from code or partial output.

### 3.1 Intro_Testing — oracles and the limits of testing (FB-INTRO)

| # | Claim | Locator | Validity region | Failure modes | Conf. |
|---|---|---|---|---|---|
| I1 | Lessons Learned (verbatim): "The aim of testing is to execute a program such that we find bugs." / "Test execution, test generation, and checking test results can be automated." / "Testing is incomplete; it provides no 100% guarantee that the code is free of errors." | FB-INTRO §Lessons Learned | universal | — | high |
| I2 | Oracle ladder used in the chapter: (a) manual inspection; (b) `assert my_sqrt(4) == 2`; (c) tolerance comparison `assertEquals(x, y, epsilon=1e-8)` (chapter: "a true Python programmer would use the function `math.isclose()`"); (d) a *run-time check in the implementation* `my_sqrt_checked()` verifying `root*root ≈ x` on every call. The chapter does **not** compare against `math.sqrt` (no reference-implementation oracle). | §Simple Testing → Checking a Function; §Run-Time Verification | numeric functions with a cheap inverse property | floating-point: exact equality fails; run-time checks "ensure correctness only if there is a result" — they cannot detect non-termination; checks may be disabled in production | high |
| I3 | Random testing is "unbiased" but "unlikely to generate special values that drastically alter program behavior"; exercises insist "always be sure to include extreme values" (0, negatives, `float('inf')`, non-numeric strings). | §Generating Tests; Exercises 2 and 4 | any numeric/string input | pure random misses 0, −1, ∞, empty | high |
| I4 | Concrete defects found in `my_sqrt`: `my_sqrt(0)` → division by zero; negative input → infinite loop; `inf` → non-termination. Fix adds precondition `assert 0 <= x` and the `x == 0` special case. | §Debugging / §Run-Time Verification / Exercise 4 | — | shows that *hangs* are a bug class the harness must detect (timeout), not only exceptions | high |
| I5 | "System input vs function input": a program-level wrapper (`sqrt_program`) must validate what a function-level test may assume (`"xyzzy"`, negatives) — the layer the harness targets decides which inputs are legal. | §System Input vs Function Input | choosing harness entry point | fuzzing an internal function with inputs its callers never produce yields false positives | med |
| I6 | Manual testing "is limited to few executions and must be repeated after every change" → automate; the chapter frames generated tests as complementary, not replacements, for manual ones. | §Automating Test Execution | — | — | med |

Oracle takeaway for the agent: the chapter's strongest oracle is **an inverse-property check** (square the root), not a reference implementation. That pattern (round-trip / inverse) is exactly what H4 needs in memory-safe languages.

### 3.2 Fuzzer — random inputs, what they find, and how to check (FB-FUZZ)

| # | Claim | Locator | Validity region | Failure modes | Conf. |
|---|---|---|---|---|---|
| F1 | Lessons Learned (near-verbatim): random fuzzing is "a simple, cost-effective way to quickly test arbitrary programs for their robustness"; "Bugs fuzzers find are mainly due to errors and deficiencies in *input processing*."; "To catch errors, have as many *consistency checkers* as possible." | §Lessons Learned | programs that consume external input | deep logic past a parser is not reached (see FB-MUT) | high |
| F2 | Miller's experiment (1989/90): students built a `fuzz` generator; "about a third" of UNIX utilities fuzzed "had problems, such as crashing or hanging", `bc` included. The chapter calls the paper "a must-read… with observations as valid today as they were 30 years ago". Follow-up studies (1995/2000/2020) are **not** discussed in the notebook text read — UNVERIFIED here. | §A Testing Assignment; §Background | historical baseline | — | high (the 1/3 figure), UNVERIFIED (follow-ups) |
| F3 | Basic algorithm: `fuzzer(max_length=100, char_start=32, char_range=32)`: pick `string_length = random.randrange(0, max_length+1)`; append `chr(random.randrange(char_start, char_start+char_range))` that many times. Character set is a parameter (digits-only via `fuzzer(100, ord('0'), 10)`). | §A Simple Fuzzer | smoke-testing any string/file consumer | produces mostly invalid input | high |
| F4 | Bug classes (all demonstrated with Python simulations of C faults): **buffer overflows** (`crash_if_too_long`), **missing error checks** (`hang_if_no_space`: `getchar()` returning EOF is not handled → infinite loop; detected with a timeout), **rogue numbers** (`collapse_if_too_large`: unchecked sizes → huge allocation / negative value). | §Bugs Fuzzers Find | C/C++ and any code doing manual length/size handling | in Python the same faults surface as exceptions or hangs — "a clearer signal than silent corruption" | high |
| F5 | Outcome taxonomy: `PASS`, `FAIL`, `UNRESOLVED` ("the run could not take place, for example because the input was invalid"). `bc` on 100 random inputs: most print error messages, **none** return a non-zero exit code. | §Fuzzing External Programs; §A Fuzzing Architecture | — | a program that rejects input loudly but exits 0 looks like PASS; the harness must decide which rejections are UNRESOLVED | high |
| F6 | Checkers: **generic** — AddressSanitizer catches out-of-bounds reads (the chapter ties memory checkers to finding Heartbleed; its `heartbeat()` simulation shows an *information leak* with no bounds violation); **program-specific** — assertions and `repOK()` representation invariants (airport code = 3 uppercase letters; red-black tree consistency); **static** — MyPy type checks. Advice: "enable as many automatic checkers as possible" since CPU time is cheap compared with missed errors; "complex properties still need `repOK()` assertions and a good test generator". | §Catching Errors (Generic Checkers, Program-Specific Checkers, Static Code Checkers) | all | crash-only oracle misses leaks and wrong results; sanitizers are C/C++-only; `repOK()` must exist or be written | high |
| F7 | Safety: fuzzing can be dangerous (file-removal command example) — run "in a safe environment that you can reset at will, such as a Docker container". | §Fuzzing External Programs | any program with side effects | — | high |
| F8 | Architecture: `Runner.run(inp) -> (result, outcome)`; `Fuzzer.fuzz()`, `run(runner)`, `runs(runner, trials)`; `RandomFuzzer(min_length, max_length, char_start, char_range)`; `ProgramRunner` for external programs. | §A Fuzzing Architecture | — | — | high |
| F9 | Limits stated: "some inputs (such as the single dot) are very improbable"; real `troff`: "it is very unlikely that you'll find a bug … Like most other open source code, it has been fuzzed this way before – and all errors found are already fixed." Next steps name mutations (more valid inputs), grammars (many more valid inputs), reduction (debuggable failures). | §Exercises 1–3; §Next Steps | — | *diminishing returns on already-fuzzed targets* — a direct H1 signal | high |

### 3.3 Coverage — definitions, measurement, plateau, black vs white box (FB-COV)

| # | Claim | Locator | Validity region | Failure modes | Conf. |
|---|---|---|---|---|---|
| C1 | Lessons Learned (near-verbatim): "Coverage metrics are a simple and fully automated means to approximate how much functionality of a program is actually executed during a test run."; "A number of coverage metrics exist, the most important ones being statement coverage and branch coverage."; "In Python, it is very easy to access the program state during execution, including the currently executed code." | §Lessons Learned | — | — | high |
| C2 | Definitions: statement coverage — "each statement in the code must be executed by at least one test input"; branch coverage — every `if`/`while` decision evaluated both true and false. Further criteria named (not defined): sequences of branches, loop iteration counts (zero/one/many), data flows → Pezzè & Young. | §Black-Box Testing / §White-Box Testing / §Other Coverage Criteria | — | criteria beyond branch are not treated as practical in the chapter | high |
| C3 | Measurement: Python via `sys.settrace` recording `(function, line)` pairs in a `Coverage` context manager; `trace()` ordered list, `coverage()` set, set algebra across runs. C via `cc --coverage`, run, `gcov`, parse `#####` lines. "almost every programming language has some facility to measure coverage". | §Tracing Executions; §Getting Coverage from External Programs | any language | line granularity hides intra-line branches | high |
| C4 | **Plateau**: cumulative coverage of `cgi_decode()` under random `fuzzer()` inputs, averaged over 100 runs: "We see that on average, we get full coverage after 40–60 fuzzing inputs." Branch coverage takes longer than statement coverage (Exercise 2). | §Coverage of Basic Fuzzing; Exercise 2 | small decoder, random printable inputs | numbers specific to a ~30-line function; the *shape* (steep rise then plateau) is the transferable fact | high |
| C5 | **Coverage did not find the bug**: random fuzzing of `cgi_decode()` quickly raises `IndexError` when `%` sits in the last two positions; "none of the manual tests we had designed earlier would trigger this bug", and statement/branch coverage criteria had been satisfied. "Where fuzzing is great at, though, is in finding internal errors that can be detected even without checking the result." Fix: `c == '%' and i + 2 < len(s)` (C: `*s == '%' && s[1] != '\0' && s[2] != '\0'`). | §Finding Errors with Basic Fuzzing; Exercise 1 | decoders/parsers with look-ahead | 100 % line coverage ≠ bug-free; coverage needs an oracle | high |
| C6 | Black-box tests derive from the specification (misses implementation details), white-box from code structure (misses unimplemented features); for `cgi_decode` both lead to similar tests. | §Black-Box Testing; §White-Box Testing | — | — | med |
| C7 | Coverage "approximates the likelihood that a test finds a bug" because bugs are too rare to count directly — it is a proxy, and it does not check results. | §Next Steps; prose | — | see FB-MA | med |

### 3.4 MutationFuzzer — validity, mutation operators, coverage-guided retention (FB-MUT)

| # | Claim | Locator | Validity region | Failure modes | Conf. |
|---|---|---|---|---|---|
| M1 | Lessons Learned (near-verbatim): "Randomly generated inputs are frequently invalid – and thus exercise mostly input processing functionality."; "Mutations from existing valid inputs have much higher chances to be valid, and thus to exercise functionality beyond input processing." | §Lessons Learned | — | — | high |
| M2 | Probability argument: `http_program(url)` requires scheme `http`/`https` and non-empty netloc. With `fuzzer(char_start=32, char_range=96)`: P(`http://`) = 1/96^7 = 1 : 75,144,747,810,816; P(`https://`) = 1/96^8; combined ≈ 1.34 × 10⁻¹⁴ → expected `74370059689055.02` runs ≈ `42.39` years at measured per-run time. "Even if we parallelize things a lot, we're still in for months to years of waiting." | §Fuzzing a URL Parser | any input with a fixed-prefix or keyword grammar | random-byte seeds never reach past the scheme check — H3 in one number | high |
| M3 | Mutators: `delete_random_character`, `insert_random_character` (printable 32–126), `flip_random_character` (XOR one bit in 0–6); `mutate(s)` applies one chosen at random. `MutationFuzzer(seed, min_mutations=2, max_mutations=10)`. | §Mutating Inputs; §Multiple Mutations | strings/bytes | character-level only; no splice/arith/interesting-values (those come in FB-GREY's AFL description) | high |
| M4 | Validity under mutation: single mutation estimated to need ≈ `3 * 96 * len(seed)` ≈ 10,944 trials to produce `https://` from `http://` seed; 50 stacked mutations make the seed "hardly recognizable anymore"; "The higher variety in inputs, though, increases the risk of having an invalid input." Demo: of 20 `MutationFuzzer` candidates, ratio valid = `0.8`. | §Multiple Mutations | — | validity decays with mutation depth; keep stacking small (2–10) | high (0.8 is one 20-trial run — illustrative only) |
| M5 | **Coverage-guided loop** (`MutationCoverageFuzzer`): population = seeds; `create_candidate()` = pick random population member, apply `randint(min_mutations, max_mutations)` mutations; `run()` executes, and `if outcome == PASS and frozenset(coverage) not in coverages_seen: population.append(inp)`. `fuzz()` yields each seed once, then candidates. Result after 10,000 trials on `http_program`: population of 14 URLs — "Success! In our population, each and every input now is valid and has a different coverage." Larger programs are explored "one path after the other". "All that is needed is a means to capture the coverage." | §Guiding by Coverage | any target with per-run coverage | retention keys on *whole coverage set*, so two inputs with the same set are duplicates — a weak notion vs AFL's per-edge new-bits; `PASS`-only retention drops crashing inputs from the corpus (fine: they are findings) | high |
| M6 | On `cgi_decode()` (Exercise 1): "After 10,000 runs, we have managed to synthesize a + character and a valid %xx form" — but can "still do better". | Exercise 1 | — | a decoder with 3 branches took 10k byte-level mutations to find `%xx` — magic-token problem | high |
| M7 | AFL "has become one of the most successful fuzzing tools"; core idea: keep mutating inputs that find "new paths through the program execution". Variants: AFLFast, AFLGo, AFLSmart. | §Guiding by Coverage (AFL paragraph) | — | — | high |

### 3.5 GreyboxFuzzer — AFL model, power schedules, directed fuzzing (FB-GREY)

| # | Claim | Locator | Validity region | Failure modes | Conf. |
|---|---|---|---|---|---|
| G1 | Lessons Learned (verbatim): "A *greybox fuzzer* generates thousands of inputs per second."; "The *power schedule* allows *steering and controlling* the fuzzer."; "The *mutator* defines the fuzzer's search space." | §Lessons Learned | — | — | high |
| G2 | Taxonomy: blackbox = no program knowledge; greybox = lightweight instrumentation ("coverage-feedback to learn how to reach deeper"), no "heavyweight program analysis or constraint solving"; whitebox = symbolic/constraint-based. AFL instruments after conditional jumps, tracks branch ids + coarse hit counts; mutates seeds or **splices** first half of one input with second half of another; inputs that increase coverage join the corpus. | §AFL: An Effective Greybox Fuzzer | compiled/instrumentable targets; Python coverage via tracing | needs instrumentation and a fast, deterministic harness ("thousands of inputs per second") | high |
| G3 | Energy = "the likelihood with which a seed is chosen from the population". `PowerSchedule.assignEnergy` (uniform: 1 each), `normalizedEnergy` (divide by sum), `choose` (`random.choices(population, weights)`). `Seed(data, coverage, distance=-1, energy=0.0)`. | §Power Schedules and Energy | — | — | high |
| G4 | Loop: `AdvancedMutationFuzzer.create_candidate()`: seed = schedule.choose(population); stack `trials = min(len(candidate), 1 << randint(1, 5))` mutations (i.e. 2–32, capped by length); `GreyboxFuzzer.run()`: if coverage set new → wrap as `Seed`, append. | §Fuzzer loop | — | same whole-set retention as FB-MUT | high |
| G5 | **AFLFast exponential schedule**: `e(s) = 1 / f(p(s))^a`, `p(s)` = path id (MD5 of sorted coverage), `f(p)` = how often generated inputs exercised that path, `a` = exponent (demo a=5). Idea ("boosted greybox fuzzing"): give more energy to seeds on "unusual" paths "not taken very often". Output: boosted vs original on `crashme`, n=10,000: rarest path count 1 vs 62; timings 1.54 s vs 1.43 s; the chapter says the boosted fuzzer "achieves coverage much faster". Warning: large exponents cause overflow/FP imprecision. | §Boosted Greybox Fuzzing | corpus with skewed path frequencies (most inputs hit the same few paths) | if all paths equally frequent, no gain; exponent too large → numeric issues | high (formula/idea), med (speed claim — plot not read) |
| G6 | Experiments: `crashme` n=30,000 — greybox covers more statements than blackbox (exact numbers UNVERIFIED — plot not read); `HTMLParser` n=5,000 from empty seed `" "` — "Both greybox fuzzers clearly outperform the blackbox fuzzer… the greybox fuzzer 'discovers' interesting inputs along the way"; but "many important keywords, such as `<html>` are still missing" → dictionaries / grammars. `DictMutator.insert_from_dictionary` adds keywords. | §Greybox Fuzzer experiments; §Dictionaries | parsers with keywords | byte mutation finds special chars but not multi-byte tokens; dictionary is the cheap fix, structure-aware mutation (Part III, AFLSmart) the real one | high |
| G7 | **Directed greybox fuzzing** (AFLGo idea): "Sometimes, you just want the fuzzer to reach some dangerous location in the source code" → treat as "an optimization problem". Distance = average over functions in the seed's coverage of their call-graph distance to the target; `DirectedSchedule`: `energy = (1/distance)^exponent`; `AFLGoSchedule` normalises energy between min and max distance. Maze, n=20,000, 16.13 s: "Out of 4071 seeds, 649 solved the maze, 438 were valid but did not solve the maze, and 2984 were invalid"; "In contrast to all previous power schedules, this one generates hundreds of solutions." Classic greybox "probably" solves it zero times. | §Directed Greybox Fuzzing; §Solving Mazes | a known target location (patch, sanitiser site, suspicious function) and a call graph | needs static distance computation; unhelpful without a target | high |
| G8 | Next steps split the field: cover *specified* functionality (grammars) vs *implemented* functionality (search-based, symbolic). | §Next Steps | — | — | high |

### 3.6 SearchBasedFuzzer — fitness, local and global search (FB-SBF)

| # | Claim | Locator | Validity region | Failure modes | Conf. |
|---|---|---|---|---|---|
| S1 | Lessons Learned (verbatim): "A meta-heuristic search problem consists of an algorithm, a representation, and a fitness function."; "For test generation, fitness functions typically estimate how close an execution comes to a target location… computed during execution through instrumentation."; "Local search algorithms like hillclimbing work well when the neighborhood is well-defined and not too large."; "Global search algorithms like genetic algorithms are very flexible and scale up well to larger test problems." | §Lessons Learned | — | — | high |
| S2 | Needle problem: `test_me(x, y)` true iff `x == 2*(y+1)`; for random values "the chances of them satisfying the condition… are rather slim" (no number given). Fitness `abs(x - 2*(y+1))`. | §Test Generation as a Search Problem | equality against a computed value | random/mutation fuzzing without value feedback is blind here | high |
| S3 | Algorithms: hillclimbing (evaluate 8 neighbours, move to first better); steepest ascent (evaluate all, pick best — fewer iterations, more tests each); restarts (needed because "the search can get stuck"); randomised (1+1)EA accepting `<=` to cross plateaus. Example: "Found optimum after 58743 iterations at -100000, -50001". Widening range 1000→100000 makes it "likely longer than we are prepared to wait". | §Hillclimbing and variants | small, well-defined neighbourhoods | local optima, plateaus, large neighbourhoods | high |
| S4 | Branch-distance table: `a==b`: true `abs(a-b)`, false 1; `a!=b`: true 1, false `abs(a-b)`; `a<b`: true `b-a+1`, false `a-b`; `a<=b`: true `b-a`, false `a-b+1`; `a>b`: true `a-b+1`, false `b-a` (no `>=` row). `in` → distance to closest element; `and` → sum, `or` → min ("short-circuit evaluation and side effects make this hard in practice"). Normalise `x/(1+x)`. Instrumentation replaces comparisons with `evaluate_condition(num, op, lhs, rhs)` via an AST `BranchTransformer`. Approach level is **not** in this chapter. | §Fitness Functions; §Instrumentation | numeric comparisons visible to instrumentation | flag/boolean comparisons give no gradient; instrumentation of side-effecting operands | high |
| S5 | `cgi_decode` target "valid two-digit hex code": fitness = sum of normalised distances over 5 targeted branches (unexecuted branch = 1.0). Hillclimber "always solves the problem" for printable ASCII; with UTF-16 alphabet and limit 100 it "usually takes really unreasonably long". GA: pop 100 × 10-char strings, tournament size 10, single-point crossover p=0.7, per-gene mutation p=1/len with Gaussian σ=100, ≤1000 generations; the shown run stalls at fitness 5.0. | §Evolutionary Search | — | alphabet size kills local search; GA not shown converging | high |

### 3.7 MutationAnalysis — judging test quality beyond coverage (FB-MA)

| # | Claim | Locator | Validity region | Failure modes | Conf. |
|---|---|---|---|---|---|
| A1 | Lessons Learned (verbatim): "We have learned why structural coverage is insufficient to evaluate the quality of test suites."; "We have learned how to use Mutation Analysis for evaluating test suite quality."; "We have learned the limitations of Mutation Analysis -- Equivalent and Redundant mutants, and how to estimate them." | §Lessons Learned | — | — | high |
| A2 | Why coverage fails: one "can have great coverage without ever checking a result for correctness"; a test ending in `assert True` (or try/except + `assert True`) gets full coverage and detects nothing; coverage "does not care about assertions at all". Triangle example: `strong_oracle()` checks the exact category, `weak_oracle()` only "not Equilateral" — identical coverage. | §Why Structural Coverage is Not Enough | — | — | high |
| A3 | Definitions: mutants = program variants with small artificial ("seeded") faults; killed = detected by a failing assertion or error; mutation score = killed / valid mutants (code: `(n_mutations - undetected) / n_mutations`); invalid (non-compiling) mutants discarded. Results: triangle weak oracle 20 % (1 of 5), strong oracle 100 %; `gcd` with two asserts ≈ 42–43 %. | §Seeding Artificial Faults; §Mutation Score | — | — | high |
| A4 | Operators implemented: **statement deletion** (replace `return`/assign/`raise`/`assert`/`pass`/`break`/`continue` with `pass`) in `StmtDeletionMutator`/`MuFunctionAnalyzer`/`MuProgramAnalyzer`; **binary-operator replacement** (`Add↔Sub`, `Mult↔Div`) only as Exercise 1. Constant change / condition negation not implemented. Each mutant run under a 1-second timeout. | §Mutating Python Code; Exercise 1 | source available via `inspect.getsource` | hanging mutants (timeout), non-compiling mutants | high |
| A5 | Equivalent mutants: with a 70 % score "anywhere from 0 to 30% of mutants might be equivalent". Remedies: manual inspection when survivors are few; statistical sampling `n ≥ 0.25·(1.96/Δ)²` (Δ=0.1 → 96 mutants; Δ=0.01 → 9,604), suggested above ~1,000 survivors; Chao's estimator for killable vs "immortal" mutants (immortals depend on the oracle; approach true equivalents only under a strong oracle). | §Equivalent Mutants; §Estimating | — | score is an upper bound on weakness, not exact | high |
| A6 | Use for generated tests: treat the test suite as a program that "accepts" the program under test and *fuzz the suite* by mutating the program; any surviving mutant is a weakness. Mutation scores can judge "static test suites, test generators such as fuzzers, and static and symbolic execution tools". "naive fuzzing generates weak oracles" → symbolic/concolic fuzzing and dynamic invariants as strengtheners. Exercise 2: coverage-first optimisation (run a test only on mutants in code it covers). | §Mutation Analysis as Fuzzing the Test Suite; §Background prose; Exercise 2 | agent self-assessment of a harness oracle | cost grows with program size; no timing numbers given | high |
| A7 | Background: Competent Programmer / Finite Neighbourhood Hypothesis (real faults are small single-token changes) and Coupling Effect (tests that catch small faults catch compound ones); origins Lipton et al. 1971; surveys Jia & Harman 2011, Papadakis et al. 2019. | §Background | — | both hypotheses are assumptions, not theorems | high |

## 4. Disagreements and open questions

| # | Issue | Positions | Status |
|---|---|---|---|
| D1 | **What "new coverage" means for retention.** FB-MUT/FB-GREY retain an input when its *whole coverage set* is unseen; AFL (as described in FB-GREY) retains on *new branch ids / hit-count buckets*. The book's variant is simpler but admits far more near-duplicate seeds and ignores hit counts. | book (pedagogical) vs AFL (production) | not a contradiction, but the agent must not copy the book's criterion when reasoning about an engine's corpus — use the engine's own "new coverage/feature" notion |
| D2 | **Is coverage a quality measure?** FB-COV: coverage "approximates the likelihood that a test finds a bug"; FB-MA: coverage "does not care about assertions at all" and a 100 %-coverage suite can detect nothing. | the same authors, different chapters | resolved by reading them as *necessary vs sufficient*: coverage plateau = stop searching for *reachability*; mutation score = measure of *detection* |
| D3 | **Search-based vs greybox for needles.** FB-SBF solves `x == 2*(y+1)` with branch distance; FB-GREY never discusses comparison feedback. Modern engines (libFuzzer `-use_value_profile`, AFL++ cmplog, go-fuzz/`go test -fuzz` comparison instrumentation) fold this into greybox fuzzing — UNVERIFIED here, belongs to the engine reports. | — | open: which of the three target engines expose this, and whether the agent should rely on it or add dictionaries |
| D4 | **Numbers are from toy programs.** "40–60 inputs to full coverage", "0.8 valid", "649 solved" are single runs on ≤ 50-line functions with no wall-clock budget. | — | do not transfer as thresholds; transfer the measurement *method* (cumulative coverage vs inputs; path-frequency histogram) |
| D5 | **Follow-up Miller studies** (1995, 2000, 2020) are often cited in secondary sources; the chapter text read does not contain them. | — | UNVERIFIED; another report should source them directly if the "fuzzing still finds bugs 30 years on" claim is wanted |
| D6 | **PASS-only retention** (FB-MUT keeps only `PASS` inputs in the population) vs engines that keep crashing inputs as separate artefacts. | — | design decision: crashes go to a findings list, not the seed corpus; consistent with both |

## 5. Implications for the agent / skills

Legend: (a) agent reasoning procedure (always-on), (b) general "fuzzing methodology" skill, (c) reference document linked from the skill, (x) academic — leave out. Hypotheses marked.

### 5.1 Applicability gate — H1

| Rule / artefact | Where | Source | H |
|---|---|---|---|
| Fuzz-worthiness checklist, in this order: (1) does the target consume *untrusted or externally produced* bytes/strings (parser, decoder, protocol, file format, CLI args)? (2) does it do its own length/size/index arithmetic or manual error handling (buffer, EOF, "rogue number" classes)? (3) is there a *cheap automatic checker* available (sanitiser, assertion, invariant, inverse property)? (4) has it *already been fuzzed* (OSS-Fuzz, existing `fuzz/` dir, `FuzzXxx` functions)? If 1–3 are no, or 4 is yes without new code, answer "do not fuzz; write example/property tests instead". | (a) + (b) decision table | F1, F4, F9, C5 | H1 |
| "Input processing first" heuristic: expected yield is highest at the boundary where external data is decoded; deep business logic behind a validator is low yield for lexical fuzzing unless the harness enters *after* validation with typed/structured inputs. | (b) | F1, M1, M2 | H1, H3 |
| Entry-point choice: harness the layer whose precondition matches the inputs you can generate (system input vs function input); an internal function with a precondition (`assert 0 <= x`) needs the precondition encoded in the generator, or you fuzz the assert. | (b) | I4, I5 | H1, H5 |
| Safety rule: fuzz in a resettable environment; never fuzz commands with destructive side effects outside a sandbox. | (a) | F7 | H5 |

### 5.2 Stopping / switching rule — H2

| Rule / artefact | Where | Source | H |
|---|---|---|---|
| Primary metric: **cumulative coverage (distinct coverage sets or edges) vs. number of executions**. Record it at fixed intervals; the curve's shape is steep-then-flat. Stop (or switch seed corpus / target / mutator) when no new coverage for a window that is large relative to the time-to-plateau observed so far (the book's toy plateau: 40–60 inputs; real engines: minutes–hours — thresholds come from engine reports, not from here). | (a) procedure + (b) | C4, M5, G4 | H2 |
| Secondary metric: **path-frequency histogram**. If a few paths dominate and rare paths keep appearing, the corpus is not saturated — continue, prefer rare-path seeds (AFLFast idea). If the histogram is flat and static, saturated. | (b) | G5 | H2 |
| Saturation is *per mutator*: "the mutator defines the search space". A plateau under byte-level mutation is a signal to change the mutator (add dictionary, structure-aware generator), not necessarily to stop the target. | (a) | G1, G6, M6 | H2, H3 |
| Diminishing-returns prior: a target already fuzzed by the community with the same technique will likely plateau immediately with no findings; treat a fast plateau + zero findings on such a target as "done", not as a failure of the agent. | (b) | F9 | H1, H2 |
| Hang detection is part of the stop logic: use a per-execution timeout; a hang is a finding (missing EOF check, non-terminating loop on 0/negative/inf), not an UNRESOLVED run. | (b) | F4, I4 | H4 |

### 5.3 Seeds and mutators — H3

| Rule / artefact | Where | Source | H |
|---|---|---|---|
| Never start from random bytes for structured input: quote the 1/96^7 argument in the skill as the rationale. Minimum seed corpus = one *valid*, *representative* input per major format feature (the book: one URL; `cgi_decode`: strings containing `+`, `%xx`, plain chars). | (a) + (b) | M2, M6 | H3 |
| Mutation depth: 2–10 stacked character/byte mutations (delete/insert/flip) keep most candidates valid; deeper stacks destroy structure. Engines do this already — the agent's job is the *seed quality*, not the mutator parameters. | (b) | M3, M4, G4 | H3 |
| Dictionary step: when the target has keywords/tokens (`<html>`, `%xx`, scheme names, opcodes), supply a dictionary before considering grammar-based generation. The HTMLParser result (special chars found, keywords missing) is the canonical illustration. | (b) + (c) snippet list of token sources (grammar, constants in code, protocol spec) | G6 | H3 |
| Coverage-guided retention explains *why* seeds improve: after guidance "each and every input now is valid and has a different coverage" — the agent should inspect the engine's corpus after a run and expect this property; if the corpus is full of invalid inputs, the harness is rejecting too late (validate early, return UNRESOLVED/skip) or the seeds are wrong. | (a) | M5, F5 | H3, H5 |
| Directed fuzzing: when the goal is a *specific* location (a patch, a suspicious function), note that classic coverage-guided fuzzing may never reach it (maze: ~0 solutions) and either (i) seed from an input known to get close, or (ii) write the harness to call the nearer function directly. AFLGo-style energy is engine-internal — do not reimplement. | (b) | G7 | H1, H3 |

### 5.4 Oracles and checkers — H4

| Rule / artefact | Where | Source | H |
|---|---|---|---|
| Checker ladder the harness must climb, from cheapest: (1) generic runtime checkers (ASan/UBSan/MSan for C/C++ and Rust `unsafe`; Go race detector; Python exceptions — "enable as many automatic checkers as possible"); (2) program-specific invariants (`repOK()`-style representation checks, assertions in the code under test, kept **enabled** under fuzzing); (3) inverse/round-trip property (`sqrt(x)^2 ≈ x`, decode(encode(x)) == x) with tolerance where floating point is involved; (4) exact-category/strong oracle (triangle `strong_oracle`) or reference implementation. A crash-only harness in a memory-safe language sits at rung 1 with almost nothing on it. | (a) procedure + (b) | F6, I2, A2 | H4 |
| Outcome taxonomy PASS / FAIL / UNRESOLVED must be explicit in the harness: expected input rejections are UNRESOLVED/skip, never FAIL; exit code 0 with an error message is not evidence of a check (the `bc` case). | (b) + (c) | F5 | H4, H5 |
| Information leaks and wrong results are invisible to crash oracles — the `heartbeat()` example shows a leak with no bounds violation. Add an output-shape check (length, type, invariants) to every harness. | (b) | F6 | H4 |
| Bug-class table (buffer overflow, missing error check/hang, rogue number, incomplete look-ahead `%` at end of string, division by zero at 0, infinite loop on negative/inf) as a prompt for *what to assert* and *which extreme values to seed*. | (c) | F4, C5, I3, I4 | H3, H4 |

### 5.5 Self-assessment of a fuzzing session (quality criteria the chapters use)

| Criterion | How the book measures it | Agent use | Source | H |
|---|---|---|---|---|
| Reachability | cumulative statement/branch coverage vs inputs; set difference between runs | report plateau point; diff coverage before/after seed or dictionary change | C3, C4 | H2 |
| Corpus health | fraction of population that is valid; distinct coverage sets | expect ≈ all-valid after guidance | M4, M5 | H3 |
| Search diversity | path-frequency histogram; rare-path counts | detect "stuck on one path" | G5 | H2 |
| Detection power | mutation score of the harness's oracle on seeded faults | run a *small* mutant sample (statement deletion, operator swap) against the harness; a score near the crash-only baseline means the oracle is weak | A3, A6 | H4 |
| Throughput | "thousands of inputs per second" is the expectation for greybox | a harness doing I/O or sleeping is wrong | G1 | H5 |

### 5.6 Mutation analysis — practical form for an agent

Belongs in (b) as a short procedure and (c) for the theory:
- Practical: 10–30 mutants of the function under test (statement deletion + arithmetic/relational operator swap), each run against the harness **with its oracle** for a bounded budget; report killed/total and *list the survivors* (survivors tell the agent which property is missing). Use the 1-second-per-mutant timeout idea. (A4, A6)
- Not practical / (x): full mutation scoring of a module, Chao estimation, sampling formulas for Δ=0.01 (9,604 mutants). Keep in (c) with the one caveat the agent must know: a surviving mutant may be equivalent, so inspect before adding an assertion. (A5)
- Framing to carry: "mutation analysis fuzzes the test suite" — it is the only measurement in Part I that targets H4 directly. (A6)

### 5.7 Leave out (academic for this agent)

- Hillclimbing/steepest-ascent/GA implementations, branch-distance normalisation, the AST instrumentation (`BranchTransformer`) — engines own this; keep only the diagnostic "equality against computed value = needle → dictionary / value profile / structured generator" (S2, S4). (x) with a one-line pointer in (c).
- Power-schedule and directed-schedule *code*; MD5 path ids; energy normalisation. Keep the two ideas (rare-path preference; directed energy needs a target) in (b). (x)
- `sys.settrace` coverage class, gcov parsing — each target language's coverage tooling replaces it (c, language skills).
- Miller history beyond one sentence of motivation. (c)

## 6. Candidate eval cases

| # | Input the agent sees | Expected behaviour | Source | H |
|---|---|---|---|---|
| E1 | A ~30-line percent-decoder (`cgi_decode` port in Go/Python/Rust) with a hand-written unit-test file reaching 100 % line coverage; asked "should we fuzz this?" | Yes: it decodes untrusted strings with look-ahead index arithmetic. Harness must seed `"a+b"`, `"%41"`, plain text; expected finding: `%` in the last two positions → index out of range / panic; the fix condition `i + 2 < len(s)` or equivalent. The agent must say that existing coverage does not disprove the bug. | C5, C4 | H1, H3, H4 |
| E2 | A URL-accepting entry point (`http_program`-like) and a proposed harness that generates random printable strings of length ≤ 100 | Agent rejects the seed strategy, cites the prefix-probability argument, and starts from ≥ 1 valid URL per scheme plus a dictionary (`http://`, `https://`, `?`, `#`, `@`, `:`); expects the engine corpus to be mostly valid after the run. | M2, M5 | H3 |
| E3 | A fuzz run log: coverage counter unchanged for the last 90 % of executions, path histogram flat, zero findings; target is a widely used library that already ships an OSS-Fuzz harness for this entry point | Correct answer is "stop now": corpus saturated for this mutator and target has been fuzzed before; propose either a different entry point/mutator or end. Not "run longer". | C4, G5, F9 | H1, H2 |
| E4 | A fuzz run log: path-frequency histogram shows one path hit 95 % of the time, several paths hit once, coverage still rising slowly | Correct answer is "continue"; recommend favouring rare-path seeds (engine's schedule / corpus minimisation) rather than stopping. | G5 | H2 |
| E5 | A Go/Rust harness whose body is `_ = Parse(data)` (crash-only) on a memory-safe parser | Agent flags the oracle as weak: adds round-trip (`Format(Parse(x)) == canonical(x)`), invariant checks on the result, and `UNRESOLVED` handling for expected rejections; optionally runs 10–20 statement-deletion mutants and reports which survive. | F6, A2, A3, I2 | H4 |
| E6 | Two candidate harnesses for a triangle-classification function: one asserts only "not Equilateral when sides differ", the other asserts the exact category | Agent prefers the strong oracle and can justify it by a small mutation experiment (expected ≈ 20 % vs 100 % kill rate on the chapter's five mutants). | A3 | H4 |
| E7 | A numeric routine (`my_sqrt`) with a fuzz harness that generates floats in `[1, 1e6]` only | Agent adds extreme values to seeds (0, negatives, `inf`, NaN), a per-execution timeout, and the inverse-property oracle with tolerance; expected findings: division by zero at 0, non-termination for negatives/`inf`. | I3, I4, I2 | H3, H4 |
| E8 | A pure in-memory function with no external input (e.g. a date formatter called with typed, already-validated arguments) and a request to "add fuzzing like everywhere else" | Agent answers "do not fuzz with lexical/byte fuzzing"; recommends property-based tests over typed generators instead, or no fuzzing. Rationale: no input-processing surface, no cheap checker beyond crash. | F1, I5 | H1 |
| E9 | A request to reach one specific function deep in a parser (recent patch) with a general corpus; after N executions the function is never hit | Agent recognises the directed-fuzzing situation: seed from an input known to reach the neighbourhood, or harness the nearer function directly; does not simply extend the time budget. | G7 | H1, H3 |
| E10 | A harness that writes temp files and shells out to a CLI on every input | Agent rejects it on throughput and safety grounds ("thousands of inputs per second"; resettable environment), restructures to in-process calls. | G1, F7 | H5 |

## 7. Micro-examples

**7.1 Coverage-guided mutation loop (the book's minimal form)** — FB-MUT §Guiding by Coverage, https://www.fuzzingbook.org/html/MutationFuzzer.html

```python
def run(self, runner):                       # MutationCoverageFuzzer
    result, outcome = super().run(runner)    # one execution
    new_coverage = frozenset(runner.coverage())
    if outcome == Runner.PASS and new_coverage not in self.coverages_seen:
        self.population.append(self.inp)     # keep what adds coverage
        self.coverages_seen.add(new_coverage)
    return result
# create_candidate(): seed = random.choice(population);
#   apply randint(min_mutations=2, max_mutations=10) of {delete, insert, flip}
```
Observed after 10,000 trials on `http_program`: 14-member population, "each and every input now is valid and has a different coverage". Use in the skill: this is what a healthy engine corpus looks like.

**7.2 AFLFast exponential power schedule** — FB-GREY §Boosted Greybox Fuzzing, https://www.fuzzingbook.org/html/GreyboxFuzzer.html

```python
class AFLFastSchedule(PowerSchedule):
    def __init__(self, exponent): self.exponent = exponent
    def assignEnergy(self, population):
        for seed in population:                     # e(s) = 1 / f(p(s))^a
            seed.energy = 1 / (self.path_frequency[getPathID(seed.coverage)] ** self.exponent)
```
With a=5 on `crashme`, the rarest path's frequency drops from 62 (uniform) to 1 (boosted) over 10,000 inputs — the histogram, not the formula, is what the agent should look at.

**7.3 Weak vs strong oracle under mutation analysis** — FB-MA §Why Structural Coverage is Not Enough / §Mutation Score, https://www.fuzzingbook.org/html/MutationAnalysis.html

Same coverage for both suites; five statement-deletion mutants of `triangle()`: `weak_oracle()` (asserts only "not Equilateral" for unequal sides) kills 1/5 = 20 %, `strong_oracle()` (asserts exact category) kills 5/5 = 100 %. The agent's self-check: a crash-only harness is a `weak_oracle()`.

**7.4 The bug coverage could not see** — FB-COV §Finding Errors with Basic Fuzzing, https://www.fuzzingbook.org/html/Coverage.html

`cgi_decode("%4")` → reads `s[i+1]`, `s[i+2]` past the end → `IndexError` (C: out-of-bounds read). Manual tests achieved statement and branch coverage; "none of the manual tests we had designed earlier would trigger this bug". Fix: `c == '%' and i + 2 < len(s)`.
