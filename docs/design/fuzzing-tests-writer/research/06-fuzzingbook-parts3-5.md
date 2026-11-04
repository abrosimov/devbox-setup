---
note_id: "20261103150906"
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
aliases: ["R6"]
tags: [fuzzing, design/research, h1, h2, h3, h4, h5]
topic: "The Fuzzing Book, Parts III-V: semantic, domain-specific, managing"
addresses: ["[[H1-no-applicability-gate]]", "[[H2-no-stopping-rule]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]", "[[H5-harness-conventions]]"]
related: ["[[research-index]]", "[[research-corpus]]"]
---
# The Fuzzing Book, Parts III–V: semantic fuzzing, domain-specific fuzzing, managing fuzzing

Research input for the "fuzzing tests writer" agent design (Go / Python / Rust). Sources are the
Fuzzing Book chapters as published in the `uds-se/fuzzingbook` repository (`master`, fetched
2026-11-03) — `www.fuzzingbook.org` itself was not resolvable from this session, so every chapter was
read as `notebooks/<Chapter>.ipynb` (source) and, for the priority chapter, `docs/notebooks/<Chapter>.ipynb`
(rendered, with cell outputs). Content is identical to the HTML edition; locators below give the
canonical HTML URL plus the section heading.

## 0. Summary for the design doc

1. **Stopping rule (H2): the book gives an estimator, not a threshold.** Species = distinct execution trace (hash of the coverage set; "AFL uses a similar measure of progress"). Good–Turing discovery probability `GT = f1/n` (f1 = traces seen by exactly one input, n = inputs run); `1−GT` = sample coverage; `1/GT` = expected inputs until the next new trace; Chao1 `Ŝ = S(n) + f1²/(2f2)` (or `S(n)+f1(f1−1)/2` when f2 = 0) estimates the asymptotic number of traces, so `S(n)/Ŝ` is "how far we are"; extrapolation `Ŝ(n+m) = S(n) + f̂0[1−(1−f1/(n f̂0+f1))^m]` predicts the pay-off of m more inputs. GT "is also an estimate of the maximum residual risk" (Böhme, STADS 2018). Only verbal rule: when the discovery probability is too low "we might as well abort the campaign"; Chao1 "isn't always accurate — particularly at the beginning of a fuzzing campaign".
2. **Numbers to carry:** Enigma: 100 messages → 72 of 17 576 trigrams, 63 singletons → GT 0.63; at n = 2000 GT 0.401 vs empirical 0.412, 1/GT ≈ 2.5. HTMLParser, 50 000 random inputs: GT "highly accurate" against 100×500-sample empirical estimate; Chao1 at 200 000 inputs: S(n) 61, Ŝ 65.5 (93.13 %), truth at 400 000 = 67; statement-coverage exercise: 130 covered/196 predicted after 100 inputs, 153 after 400 (early over-estimate).
3. **The estimator needs a per-input trace, which greybox engines do not keep.** Go `-fuzz` (`new interesting: 11 (total: 202)`), libFuzzer (`NEW`, `cov`, `ft`; UNVERIFIED) and AFL++ (`corpus count`, `last new find`, `cycles done` turning green, `stability`) expose coverage-expanding inputs only, never singleton counts. Exact GT/Chao1 is cheap for Python (coverage.py per Hypothesis example); elsewhere use the engines' plateau signals (discovery-rate per window, age of last find, ≥ 1 AFL++ cycle without finds) and label residual risk as not quantified. Greybox sampling is adaptive and biases GT downward (Böhme et al. 2021, UNVERIFIED).
4. **Campaign reporting (H5) = FuzzingInTheLarge's data model:** product id (name, version, platform, OS), steps to reproduce (input + command), stack trace, coverage; crashes grouped into **buckets by signature** (sanitizer message ∧ top stack frames ∧ address predicate, lower frames generalised to `?` over 3–4 iterations), bucket size, tracker link. ClusterFuzz's "crash state" is the same idea. The agent's report must be bucket-level, never a raw crash list.
5. **Typed-API fuzzing (H3/H4/H5):** APIFuzzer generates *calls* from per-type grammars (int/float/string/list, range hooks) and `eval`s them; default oracle = exception, better = round-trip assertions (`geturl() == url`) via post-expansion hooks; warns that recombined arguments violate implicit preconditions → false alarms. No call-sequence / stateful material in the book.
6. **Seeds from real executions (H3):** Carver records calls via `sys.settrace`, serialises args by `repr`/pickle, replays via `eval`; "about a quarter" of carved calls replay; carved values become an API grammar; Exercise 1 records return values → regression assertions. Unit-level replay is "orders of magnitude faster" than system runs.
7. **Oracles beyond crash (H4):** DynamicInvariants mines a 27-pattern catalogue (`X > 0`, `X == Y + Z`, `X == len(Y)`, …) and keeps what holds on all observed calls; quality "depends on the diversity of observed values"; one call `sum2(2,2)` yields `a == b`. Mined invariants are regression oracles, not correctness oracles.
8. **Applicability gate (H1):** ConfigurationFuzzer — option spaces are finite: 30 autopep8 options → 435 unordered pairs (chapter prints 870 = n(n−1)); mypy 140+ options → "20,000+" tests ≈ 3 h at 1 s each; "Programs rarely have conditions involving three or more configuration settings" (uncited). Flags → pairwise; payload → fuzz.
9. **Semantic constraints (H3):** ISLa adds `forall/exists`, `str.len`, `str.to.int`, `before()`, `<a>..<b>` paths to a grammar, with solver and checker; examples: equal XML tag ids, length-prefixed strings, define-before-use; no checksum example; Python-only, no timing data ("constraints … much more versatile than adding generator code"). For Go/Rust the transferable lesson is fix-up code for lengths, checksums and identifier consistency, plus a checker run on seeds.
10. **Concolic/symbolic:** "broad but shallow", "much larger runtime cost", good for magic-value checks — agent should know they exist and reach for dictionaries/CmpLog first. GrammarMiner, taint tracking, compiler/web/GUI fuzzing: reference only.
11. **Gaps for other streams:** stateful/sequence API fuzzing; libFuzzer and Hypothesis docs (hosts blocked here); numeric stopping thresholds (none in the book or AFL++ docs — a design decision).

## 1. Scope and question answered

Which lessons of Fuzzing Book Parts III (Semantic Fuzzing), IV (Domain-Specific Fuzzing) and V
(Managing Fuzzing) should shape the agent's procedure, its skills and its eval plan; in particular:
the species-discovery stopping estimator (WhenToStopFuzzing), crash collection/triage/reporting
(FuzzingInTheLarge), typed API fuzzing (APIFuzzer), execution carving (Carver), mined invariants as
oracles (DynamicInvariants), combinatorial option testing (ConfigurationFuzzer) and grammar
constraints (FuzzingWithConstraints). The remaining chapters are summarised for "know it exists".

## 2. Corpus ledger

| id | source + edition/date | locator | used for | status |
|---|---|---|---|---|
| FB-STOP | Zeller, Gopinath, Böhme, Fraser, Holler, *The Fuzzing Book*, "When To Stop Fuzzing", web edition, repo `master` 2026-11-03 | https://www.fuzzingbook.org/html/WhenToStopFuzzing.html (§§ The Enigma Machine … Lessons Learned) | estimator, numbers, recommendation | include |
| FB-LARGE | *ibid.*, "Fuzzing in the Large" | https://www.fuzzingbook.org/html/FuzzingInTheLarge.html | crash server, buckets, report | include |
| FB-API | *ibid.*, "Fuzzing APIs" | https://www.fuzzingbook.org/html/APIFuzzer.html | typed API generation, oracles | include |
| FB-CARVE | *ibid.*, "Carving Unit Tests" | https://www.fuzzingbook.org/html/Carver.html | seeds/tests from executions | include |
| FB-INV | *ibid.*, "Mining Function Specifications" | https://www.fuzzingbook.org/html/DynamicInvariants.html | invariant catalogue, oracle use | include |
| FB-CONF | *ibid.*, "Testing Configurations" | https://www.fuzzingbook.org/html/ConfigurationFuzzer.html | pairwise numbers, applicability | include |
| FB-ISLA | *ibid.*, "Fuzzing with Constraints" | https://www.fuzzingbook.org/html/FuzzingWithConstraints.html | constraint syntax/examples | include |
| FB-GM | *ibid.*, "Mining Input Grammars" | https://www.fuzzingbook.org/html/GrammarMiner.html | short treatment | include (short) |
| FB-IF | *ibid.*, "Tracking Information Flow" | https://www.fuzzingbook.org/html/InformationFlow.html | short treatment | include (short) |
| FB-CONC | *ibid.*, "Concolic Fuzzing" | https://www.fuzzingbook.org/html/ConcolicFuzzer.html | short treatment | include (short) |
| FB-SYM | *ibid.*, "Symbolic Fuzzing" | https://www.fuzzingbook.org/html/SymbolicFuzzer.html | short treatment | include (short) |
| FB-PY | *ibid.*, "Testing Compilers" | https://www.fuzzingbook.org/html/PythonFuzzer.html | short treatment | include (short) |
| FB-WEB | *ibid.*, "Testing Web Applications" | https://www.fuzzingbook.org/html/WebFuzzer.html | short treatment | include (short) |
| FB-GUI | *ibid.*, "Testing Graphical User Interfaces" | https://www.fuzzingbook.org/html/GUIFuzzer.html | short treatment | include (short) |
| GO-FUZZ | go.dev, "Go Fuzzing" doc (golang/website `_content/doc/security/fuzz/index.md`, `master`, 2026-11-03) | https://go.dev/doc/security/fuzz/ | what Go reports (species proxy) | include |
| AFL-APPROACH | AFL++ docs `afl-fuzz_approach.md` (`stable`, 2026-11-03) | https://aflplus.plus/docs/afl-fuzz_approach/ § Understanding the status screen | AFL++ stop signals | include |
| AFL-DEPTH | AFL++ docs `fuzzing_in_depth.md` (`stable`, 2026-11-03) | https://aflplus.plus/docs/fuzzing_in_depth/ §§ 3g, 3h, 4 | how long to fuzz, triage | include |
| CF-GLOSS | ClusterFuzz docs `reference/glossary.md` (`master`, 2026-11-03) | https://google.github.io/clusterfuzz/reference/glossary/ | crash state = dedup signature | include |
| STADS | Böhme, "STADS: Software Testing as Species Discovery", ACM TOSEM 27(2), 2018 (cited by FB-STOP; not read directly) | FB-STOP § Background | residual-risk claim | park (secondary via FB-STOP) |
| GOOD53 / CHAO84 / CHAO87 / SHEN03 | Good 1953 Biometrika 40:237–264; Chao 1984 Scand. J. Stat. 11:265–270; Chao 1987 Biometrics 43:783–791; Shen, Chao, Lin 2003 Ecology 84(3):798–804 (cited by FB-STOP) | FB-STOP § Background | provenance of formulas | park |
| LIBFUZZER | llvm.org/docs/LibFuzzer.html | — | `NEW`/`cov`/`ft` semantics | **UNVERIFIED** (host blocked; GitHub mirror 404) |
| HYPO | hypothesis.readthedocs.io (statistics, Phase, max_examples) | — | Hypothesis stop reasons | **UNVERIFIED** (host blocked; GitHub mirror 404) |
| BOEHME21 | Böhme, Liyanage, Wüstholz, "Estimating Residual Risk in Greybox Fuzzing", ESEC/FSE 2021 | — | adaptive-bias correction of GT | **UNVERIFIED** (from memory) |

## 3. Claim sheets

### 3.1 WhenToStopFuzzing (FB-STOP) — species discovery, Good–Turing, Chao1

**Lessons Learned (verbatim, FB-STOP § Lessons Learned):**
- "One can measure the *progress* of a fuzzing campaign (as species over time, i.e., S(n))."
- "One can measure the *effectiveness* of a fuzzing campaign (as asymptotic total number of species S)."
- "One can estimate the *effectiveness* of a fuzzing campaign using the Chao1-estimator Ŝ."
- "One can extrapolate the *progress* of a fuzzing campaign, Ŝ(n+m*)."
- "One can estimate the *residual risk* (i.e., the probability that a bug exists that has not been found) using the Good-Turing estimator GT of the species discovery probability."

**Core algorithm (as implemented in the chapter):**
1. Run the target on each input under coverage; `getTraceHash()` = MD5 of the pickled coverage
   set. Inputs with identical coverage sets share one species ("a+b" and "a+b+c" collide for
   `cgi_decode`, "abc" differs).
2. `population_trace_coverage(population, function)` keeps the set of all traces, a set of
   singleton traces (seen once) and doubleton traces (seen twice); records the cumulative series
   `S(n)`, `f1(n)`, `f2(n)` after each input.
3. Discovery probability (Good–Turing): `GT = f1 / n` — "the number f1 of trigrams observed exactly
   once divided by the total number n of messages cracked"; "called the missing probability mass or
   the discovery probability". Sample coverage = `1 − GT`. `1/GT` is "a maximum likelihood estimate of
   the expected number of messages before having to find a new trigram".
4. Asymptote (Chao1): `Ŝ = S(n) + f1²/(2·f2)` if `f2 > 0`, else `S(n) + f1·(f1−1)/2`.
   Progress = `S(n)/Ŝ`.
5. Extrapolation (Shen, Chao, Lin 2003): `f̂0 = Ŝ − S(n)`;
   `Ŝ(n+m) = S(n) + f̂0 · [1 − (1 − f1/(n·f̂0 + f1))^m]`.
6. Residual risk: "Let's say residual risk is the probability that the next test input reveals a
   vulnerability [that has not been found]"; Böhme "has shown that the Good-Turing estimate of the
   discovery probability is also an estimate of the maximum residual risk." Proof sketch: split each
   old species into a vulnerable and a non-vulnerable variant; "only species that do not expose a
   vulnerability have been discovered. Hence, the probability to discover a new species gives an upper
   bound on the probability to discover [a vulnerability]."
7. The chapter's stated uses of GT: (i) probability that the next input is new, (ii) proportion of
   generatable inputs whose species is already seen, (iii) number of inputs needed until the next
   discovery; and, in the same list, if that probability is too low "we might as well abort the campaign".

**"Enigma" running example — numbers (FB-STOP §§ Fuzzing the Enigma, Turing's Observations, Boosting):**
- Key space: trigrams over 26 letters = 17 576 species; `RandomFuzzer` brute-forces keys; "Bletchley
  cracks about 12 messages per second" (one message ≈ 0.079 s).
- After 100 messages: 72 of 17 576 trigrams observed; 63 observed once → GT = 63/100 = 0.63.
- After n = 2000 messages: GT printed `0.401`; empirical probability of a new trigram `0.412` —
  "pretty accurate"; `1 − gt = 0.599`; `1/gt = 2.49` messages until the next new trigram;
  802 of 1009 observed trigrams (79.485 %) seen once; most frequent trigram seen 152 times.
- Boosting: trying previously frequent trigrams first (`BoostedBletchleyPark`) cracks 23 messages
  within `max_attempts = 100000` versus 3 for plain brute force — the book's analogue of corpus
  prioritisation ("the trigram distribution is skewed").
- Interpretation given: "trigram discovery will slow down and eventually approach an asymptote (the
  total number of trigrams)".

**Evaluation on a program (FB-STOP §§ Trace Coverage … Extrapolating):**
- Subject: Python `HTMLParser`; 50 000 random inputs, length 1–100, alphabet = 94 printable ASCII.
- Trace coverage vs statement coverage: "more robust" (fewer sudden jumps), "more fine-grained" (more
  traces than statements), "grows more steadily"; statement coverage "exercises more than half the
  statements [in the first inputs]"; "AFL … uses a similar measure of progress" (hash over branches).
- GT vs empirical discovery probability: measured over 100 intervals with 500 fresh inputs each;
  "the Good-Turing estimate appears to be *highly accurate*"; "the empirical estimator has a much
  lower precision as indicated by the large swings".
- Chao1: at 200 000 inputs `S(n) = 61`, `Ŝ = 65.5` → "93.13 %" covered; after 400 000 inputs 67
  traces observed (so Chao1 under-estimated by ≈ 1.5 species). "The accuracy of Chao's estimator is
  quite reasonable"; "It isn't always accurate — particularly at the beginning of a fuzzing campaign
  when the discovery probability is still very high."
- Extrapolation from `trials/4` ≈ 3× ahead "closely matches the empirical value".
- Exercise 2 (statement coverage, 400 trials): after 100 inputs 130 statements (66.3 %), Chao1
  estimate 196; after 400 inputs 153 — an example of an early-campaign over-estimate.

**Actual recommendation on stopping:** no numeric threshold. The chapter answers "How do we know
when to stop?" with: progress `S(n)/Ŝ` (requires estimating Ŝ because "the percentage S(n)/S can
only be computed if we know the total number of species S. Even then, not all species may be
feasible"), discovery probability as residual-risk bound, and extrapolation to judge whether `m`
more inputs are worth it. Testing "is not verification": a clean campaign never proves absence.

**Validity region:** non-adaptive (random/blackbox) generation, where each input is an i.i.d. draw
— that is how the chapter's experiments are run. **Failure modes:** early-campaign Chao1 error;
species definition must be stable and deterministic (flaky coverage inflates f1); greybox fuzzers
are adaptive samplers, and the chapter is silent on the resulting bias (see § 4). **Cost:** one
coverage trace per input (an order of magnitude slower than bare execution for Python). **Needs:**
deterministic target, per-input coverage, hashable trace. **Confidence:** high for formulas and
numbers (read from rendered outputs); medium for "recommendation" (no explicit threshold exists).

### 3.2 FuzzingInTheLarge (FB-LARGE) — crash server, buckets, reports

**Lessons Learned (verbatim):** "When fuzzing (a) with several machines, (b) several programs,
(c) with several fuzzers, use a *crash server*"; "Crashes likely to be caused by the same failure
should be collected in *buckets*"; "Centrally collecting *fuzzer coverage* can help reveal issues
with fuzzers."

**Core mechanism (Mozilla FuzzManager 0.4.1, § Collecting Crashes, § Crash Buckets):**
1. Each fuzzer submits a `CrashInfo` (stdout, stderr, GDB/ASan output) with a
   `ProgramConfiguration` (product, version, platform, OS) and optionally the test-case file.
2. Data a report must carry (citing Bettenburg et al. 2008 "What makes a good bug report?"):
   product identifier, steps to reproduce (the input), stack trace, coverage; "expected behaviour" is
   trivial for crashes — "users do not expect crashes".
3. A **bucket** is defined by a **crash signature** = list of predicates; main features are the
   crash address (program counter) and stack-trace elements. Example signature: stderr matches
   `ERROR: AddressSanitizer: heap-buffer-overflow`, a list of frame function names, crash address
   `> 0xFF`.
4. **Optimize** generalises a signature by replacing varying lower frames with `?` while keeping
   the common (buggy) frames, checking that the widened signature does not swallow other buckets;
   "3 to 4 optimize iterations were needed" to absorb near-duplicate stacks.
5. Buckets carry size and bug-report status and link to Bugzilla; server pages: crashes (product,
   version, OS, details), crash detail, bucket, signatures, coverage per file and per line (grcov).
6. Privacy: in production, user inputs are not collected "for obvious privacy reasons".
Numbers: 20 trials for the out-of-bounds subject (seed 2048, sizes 1–1024 B), 1000 trials for the
maze subject; industry "thousands" of crashes.
**Validity region:** multi-machine / multi-target / multi-fuzzer campaigns; also single-machine
reporting discipline. **Failure modes:** over-general signatures merge distinct bugs; too specific
ones split one bug into many buckets. **Cost:** a server; locally, a script that buckets by frames.
**Cross-check (CF-GLOSS):** ClusterFuzz "Crash state: a signature that we generate from the crash
stacktrace for deduplication purposes"; "a crash is reliably reproducible if the target program
consistently crashes with the same crash state"; corpus = "a set of minimal test inputs that
generate maximal code coverage". **Confidence:** high.

### 3.3 APIFuzzer (FB-API) — fuzzing typed function APIs

**Lessons Learned (verbatim):** "To fuzz individual functions, one can easily set up grammars
that produce function calls."; "Fuzzing at the API level can be much faster than fuzzing at the
system level" — followed by the warning that generated arguments may violate implicit
preconditions and so produce false alarms.

**Core mechanism:** (1) a grammar whose start symbol expands to a call string, e.g.
`urlparse("<url>")`, generation decoupled from execution (`do_call` → `eval`); (2) per-type
grammars for int, float, ASCII string, with pre-expansion hooks for ranges (`random.randint`,
scaled `random.random()`), probabilities: empty string 0.05, empty list 0.05, single-element list
0.2, finite float 0.9; (3) `list_grammar(object_grammar)` composes containers; dicts/sets "defined
in a similar fashion"; (4) the same scheme emits C calls inside a generated C function; (5) oracles:
default = exceptions; stronger = assertions, e.g. `geturl()` returns the input and
scheme/host/path/query equal the generated parts — equalities enforced by post-expansion hooks
because a CFG cannot express them; (6) alternative: call the fuzzer per argument in a unit test —
easier oracles but "loses coverage and guided generation". Background: QuickCheck (Claessen 2000),
pointer to Python `hypothesis`.
**Validity region:** pure-ish functions with typed scalar/container arguments. **Failure modes:**
false alarms from implicit preconditions; nothing on call *sequences*, object state, resource
handles (gap for stateful APIs). **Needs:** callable in-process; a sense of which exceptions are
"expected". **Confidence:** high.

### 3.4 Carver (FB-CARVE) — tests and seeds from real executions

**Lessons Learned (verbatim):** "*Carving* allows for effective replay of function calls recorded
during a system test."; "A function call can be *orders of magnitude faster* than a system
invocation."; "*Serialization* allows creating persistent representations of complex objects.";
"Functions that heavily interact with their environment and/or access external resources are
difficult to carve."; "From carved calls, one can produce API grammars that arbitrarily combine
carved arguments."

**Core mechanism:** `Carver.__enter__` installs `sys.settrace`; on each `call` event store the
qualified function name and `frame.f_locals` in parameter order; `call_value()` uses `repr()`, or
`pickle.loads(<pickle.dumps bytes>)` when the repr contains `<`; `call_string()` renders `self` as a
method receiver; replay via `eval`. `CallGrammarMiner`: each parameter becomes a nonterminal whose
alternatives are the observed values; each function a `<call>` alternative; `GrammarCoverageFuzzer`
recombines (power(x∈{1,3}, y∈{2,4})). Exercise 1 (`ResultCarver`) records return values and
generates assertions for `urlparse()` — regression tests.
**Numbers:** "tens of thousands" of `urlparse()` calls per one `webbrowser()` run; "about a
quarter" of carved `webbrowser()` calls replayed successfully (others: out-of-scope internal names,
external resources, unpicklable objects). Background: Elbaum et al. 2006 (Java), Kampmann et al. 2018
(carving + API fuzzing).
**Validity region:** deterministic functions with serialisable arguments; integration/system tests
exist. **Failure modes:** globals and external state not recorded; time/randomness/environment
dependent values differ between runs; recombined arguments violate preconditions → false alarms to
filter manually. **Confidence:** high.

### 3.5 DynamicInvariants (FB-INV) — mined pre/postconditions as oracles

**Lessons Learned (paraphrased; notebook bullets):** type annotations and explicit invariants let
you check arguments and results; both can be mined by observing calls at runtime; mined-invariant
quality "depends on the diversity of observed values", which test generation can increase.

**Core mechanism:** `CallTracker` (`sys.settrace`) records args and return value;
`TypeAnnotator` writes observed types into the AST (conflicts → `Any`); `InvariantAnnotator`
instantiates every pattern in the catalogue with metavariables X, Y, Z bound to parameters and
`return_value`, evaluates on every observed call, keeps only patterns true on all; patterns without
`return_value` → `@precondition`, with it → `@postcondition`.
**Catalogue (verbatim):** `X < 0`, `X <= 0`, `X > 0`, `X >= 0`, `X == 0`, `X != 0`, `X == Y`,
`X > Y`, `X < Y`, `X >= Y`, `X <= Y`, `isinstance(X, bool|int|float|list|dict)`, `X == Y + Z`,
`X == Y * Z`, `X == Y - Z`, `X == Y / Z`, `X < Y < Z`, `X <= Y <= Z`, `X > Y > Z`, `X >= Y >= Z`,
`X == len(Y)`, `X == sum(Y)`, `X.startswith(Y)`.
**Examples:** `my_sqrt` from calls 25.0, 10.0 → `x > 0`, `return_value > 0`, both float, plus the
spurious `return_value <= x`, which a third call with 0.01 removes; `sum2(2, 2)` alone → `a == b`
(over-specialisation); `sum3` with mixed types → no invariants; annotated `my_sqrt` raises on
`-1.0` where the original hangs; a regression returning `-approx` fails the postcondition on 2.0.
"Chicken-and-egg": mining from generated tests needs a generator that already respects
preconditions; system-level tests break the cycle. Background: Daikon (Ernst 2001, "the mother of
function specification miners"), Eclat (Pacheco 2005), Ammons 2002; MonkeyType, PyAnnotate.
**Validity region:** regression / differential oracles; prerequisite for API fuzzing of code
without specs. **Failure modes:** overfitting; invariants describe current behaviour, including
bugs; catalogue limited to arithmetic/length/prefix relations. **Confidence:** high.

### 3.6 ConfigurationFuzzer (FB-CONF) — options and pairwise coverage

**Lessons Learned (paraphrased):** configurations are a testing target alongside input data;
options can be mined from a standard parser (`argparse`) into a grammar; covering pairs (or larger
combinations) is a grammar extension.

**Core mechanism:** `OptionGrammarMiner` traces `add_argument()` calls and interrupts at
`parse_args()`; grammar `<start> ::= (<option>)* <arguments>`, mutually exclusive groups as
`<group>`; types inferred (`int`/`str`); `OptionFuzzer` subclasses `GrammarCoverageFuzzer`.
Combinatorial: `pairwise()` enumerates option pairs and replaces `<option>` with them; general
`C(n,k)`.
**Numbers:** autopep8, 30 options → chapter prints 870 tests (`n(n−1)`, ordered; unordered pairs
= 435); mypy, 140+ options → "20,000+" tests → "about three hours" at 1 s each; "Programs rarely
have conditions involving three or more configuration settings" (no citation). Background: Pezzè
2008, Petke 2015, Sutton 2007, Dai 2010.
**Validity region:** finite, enumerable option sets; interaction faults. **Failure modes:**
`argparse` only, single parser, option dependencies unsupported; coverage-fuzzer stops exploring a
shared `<int>` once covered for one option (Exercise 4). **Confidence:** high (numbers), medium
(empirical claim unsourced).

### 3.7 FuzzingWithConstraints (FB-ISLA) — semantic constraints on grammars

**Lessons Learned (verbatim):** "Using ISLa, we can add and solve *constraints* to grammars,
allowing to express *semantic properties* of our test inputs"; "Declaring constraints (and have a
solver solve them) is much more versatile than adding generator code"; "Using ISLa is fun :-)".

**Core mechanism:** `ISLaSolver(grammar, constraint).solve()` yields derivation trees; `check()`
validates an input ("much more efficient than solving"). Syntax: `forall`/`exists TYPE VAR in
CONTEXT:`, pattern-restricted quantifiers, `{<ID> VAR}` naming, `<a>.<b>` child, `<a>..<b>`
descendant, `<A>.<B>[2]` index, `str.len`, `str.to.int`, `str.to_code`, `mod`, `before(A, B)`,
`count(...)`, SMT-LIB prefix form. Parameters `max_number_smt_instantiations` (default 10),
`max_number_free_instantiations` trade diversity for speed. CLI `isla solve grammar.py
--constraint '…'`.
**Examples (verbatim):** `str.len(<pagesize>) >= 6`; `str.to.int(<pagesize>) mod 7 = 0`;
`<pagesize> = <bufsize>`; `<xml-tree>.<open-tag>.<id> = <xml-tree>.<close-tag>.<id>`;
`str.to_code(<string>.<length>.<byte>) = str.len(<string>.<chars>)` (length-prefixed strings);
`before(declaration, <assgn>) and <rhs>.<var> = declaration.<lhs>.<var>` (define-before-use).
No checksum or uniqueness example in the chapter.
**Numbers:** Python ≥ 3.10; 10 solutions per run; the only solver-time figure in the book is in
FB-PY: a constraint demanding three statements in a function body "can take more than a minute".
Background: Steinhöfel & Zeller, "Input Invariants", ESEC/FSE 2022; github.com/rindPHI/isla.
**Validity region:** textual formats with context-sensitive rules (ids, lengths, ranges).
**Failure modes:** solver cost, little diversity at high SMT instantiation counts, ordering needs
`before()`, Python-only toolchain. **Confidence:** high.

### 3.8 Shorter chapters — lesson, applicability, agent stance

| Chapter | Lesson (source wording) | Applies when | Agent should |
|---|---|---|---|
| GrammarMiner (FB-GM) | Recover a grammar from variable values during parsing: "simple string inclusion checks are sufficient to obtain reasonably accurate grammars" (hand-written parsers); based on AUTOGRAM (Höschele 2017) | Python, hand-written recursive parsers, sample inputs exist | know it exists; prefer writing the grammar/generator from docs or tests |
| InformationFlow (FB-IF) | `tstr`/`ostr` taints as oracle: "Taints can be used in conjunction with fuzzing to provide a more robust indication of incorrect behavior" than crashes; taints lost in conversions, C calls, implicit flow | injection-style properties in Python | reference: oracle idea (untrusted data reaching a sink) |
| ConcolicFuzzer (FB-CONC) | "more information than taint analysis … at a much larger runtime cost"; limited by indirect control flow and internal calls; `ConcolicGrammarFuzzer` lifts string equalities into the grammar (finds table names `vehicles`, `months`, `years`) | magic values / equality checks block coverage | know it exists; in practice use dictionaries/`-dict`, CmpLog, Go corpus seeding |
| SymbolicFuzzer (FB-SYM) | "Symbolic execution can be broad but shallow"; suited to "programs that rely on specific values"; needs type annotations, unrolls loops (`max_depth=max_iter=max_tries=10` in examples) | small self-contained functions | do not attempt; mention as alternative |
| PythonFuzzer (FB-PY) | Generate ASTs, not text; "once program code is turned into an AST, it is fairly easy to generate, mutate, and evolve"; oracle only `has_distributive_law()`; ≈19 000 random runs vs evolutionary search | compilers, interpreters, linters, formatters | reference: structure-aware generation at AST level; differential oracle must come from elsewhere (Csmith cited) |
| WebFuzzer (FB-WEB) | Mine grammars from forms; oracle: HTTP 500 = FAIL, 200 = PASS, else UNRESOLVED; SQL injection checked by DB state | HTTP GET forms | out of scope for the agent |
| GUIFuzzer (FB-GUI) | UI as finite state machine encoded in a grammar; "cover all state transitions, which is equivalent to covering all expansion alternatives" | Selenium-reachable UIs | out of scope |

## 4. Disagreements and open questions

1. **Adaptive bias of GT under greybox fuzzing.** FB-STOP evaluates GT with a *random* fuzzer
   and says nothing about coverage-guided sampling. A greybox fuzzer mutates corpus members, so
   samples are not i.i.d.; Böhme et al. 2021 (BOEHME21, UNVERIFIED) report that GT then
   *underestimates* residual risk and propose a Laplace-style correction. Design consequence: for
   Go/libFuzzer/AFL++ the agent must label any GT number as a lower bound on risk.
2. **No numeric stopping threshold anywhere in the book.** AFL++ (AFL-DEPTH § 3h) is equally
   vague: unproductive "if no new path is found for a long time" (a day or a week), finish "at
   least one queue cycle without new finds" (AFL-APPROACH). The agent's rule has to be a
   design decision, not a citation.
3. **"Species" is engine-specific.** FB-STOP: full trace hash. AFL: edge-hit-count bucket map.
   Go: "expand the code coverage beyond what the existing generated corpus can reach"
   (coverage counters, GO-FUZZ). libFuzzer: features (UNVERIFIED). These give different S(n).
4. **Pair count 870 vs 435** (FB-CONF prints `n(n−1)`, text says pairs). Trivial, but the agent's
   skill should state the unordered count.
5. **Mined invariants vs correctness.** FB-INV presents them as regression oracles; nothing in the
   book claims they catch logic bugs in the *current* version. They answer H4 only partially.
6. **FuzzingInTheLarge is Mozilla-specific** (FuzzManager); ClusterFuzz's "crash state" is the
   same idea with a fixed top-frames signature (CF-GLOSS does not say how many frames; "top 3" is
   folklore — UNVERIFIED).
7. **Call sequences / stateful API fuzzing are absent** from FB-API and FB-CARVE (Carver records
   independent calls). Another research stream must cover Hypothesis stateful testing,
   proptest/bolero state machines, Go `f.Fuzz` with op-sequence decoding.
8. **libFuzzer and Hypothesis documentation were unreachable** from this session; statements
   about `NEW`/`cov`/`ft`, `-print_final_stats`, `Stopped because settings.max_examples=100` are
   from memory and must be re-verified before they enter a skill.

## 5. Implications for the agent / skills

### 5.1 Mapping

| # | Item | (a) agent procedure | (b) methodology skill | (c) reference doc | (d) leave out | H |
|---|---|---|---|---|---|---|
| 1 | Species-discovery estimator (GT, 1/GT, Chao1, extrapolation) | compute when a per-input trace is available; otherwise plateau proxies | `fuzz-stopping-rule` skill carries formulas + decision table (§ 5.2) | derivation + Enigma/HTMLParser numbers | — | H2 |
| 2 | Chao1 unreliable early | never report `S(n)/Ŝ` before GT has dropped well below 1 (chapter: 66 % claim at 100 inputs was wrong) | rule in same skill | — | — | H2 |
| 3 | Residual risk = GT upper bound; testing ≠ verification | final report always states residual-risk caveat | report template line | — | — | H2/H5 |
| 4 | Trace coverage steadier than statement coverage | use engine coverage counters, not line % as progress | — | note | — | H2 |
| 5 | Corpus prioritisation ("boosting") | ensure seed corpus is distilled (`afl-cmin`, `-merge=1`) | per-engine skill | — | — | H3 |
| 6 | Crash server data model | report = bucket list + product id + repro steps + coverage | `fuzz-campaign-report` template (§ 5.3) | FuzzManager/ClusterFuzz pointers | server itself | H5 |
| 7 | Signature generalisation with `?` frames | bucket by sanitizer type + top-k frames, then widen | triage checklist | — | — | H5 |
| 8 | API-call grammars per type | for typed targets, generate per-argument generators, compose calls | per-language skill (Hypothesis strategies / `arbitrary` / `f.Add` + decode) | — | `eval`-based execution | H3/H5 |
| 9 | Exceptions as default oracle + implicit-precondition false alarms | classify expected exceptions before running; add round-trip/assert oracles | oracle-selection skill | — | — | H4 |
| 10 | Carving: seeds and regression assertions from system tests | mine seeds from existing tests/fixtures/logs before fuzzing | seed-corpus skill | Carver limits (¼ replayable) | Python `settrace` tool | H3/H4 |
| 11 | Invariant catalogue | offer mined/declared postconditions as oracles in regression & differential mode | oracle-selection skill carries the 27 patterns | Daikon pointer | implementation | H4 |
| 12 | Pairwise option testing | gate: flags → combinatorial; payload → fuzz | applicability-gate skill with `C(n,2)` table | — | argparse miner | H1 |
| 13 | ISLa-style constraints | for length/id/range rules in text formats: fix-up functions or constraint tool | structure-aware-input skill | ISLa syntax cheat-sheet | ISLa itself for Go/Rust | H3 |
| 14 | Concolic/symbolic | mention as escalation when coverage stalls on comparisons; use dictionaries/CmpLog first | — | one-paragraph note | tools | H1 |
| 15 | GrammarMiner, taint, compiler/web/GUI fuzzing | — | — | one line each | yes | — |

### 5.2 Computing the stopping estimator from engine outputs

What counts as a species, what the engine gives, what the agent can do:

| Engine | Native "species" | Exposed by default | Exact GT/Chao1 possible? | Practical signal for the agent |
|---|---|---|---|---|
| Go `go test -fuzz` (GO-FUZZ) | input that "must expand the code coverage beyond what the existing generated corpus can reach" | `fuzz: elapsed: 3s, execs: 325017 (108336/sec), new interesting: 11 (total: 202)`; corpus in `$GOCACHE/fuzz`, seeds in `testdata/fuzz/<FuzzName>`; runs until failure/`-fuzztime`/interrupt | not from the engine (no per-input trace, singletons unknown). Possible by replaying `$GOCACHE/fuzz` + fresh mutations under `GOCOVERDIR` per input (expensive) | discovery rate Δ`new interesting`/Δ`execs` per window; `total` growth curve; age of last `new interesting`; treat `S(n)` = `total` and fit the asymptote |
| libFuzzer (LIBFUZZER, UNVERIFIED) | feature (edge + hit-count bucket); `NEW` lines, `cov:`, `ft:`, `corp:` | status lines; `-print_final_stats=1`; artefacts `crash-<sha1>` etc. | not natively; `-merge=1` with a control file lists features per input (UNVERIFIED) | rate of `NEW` per 1e6 execs; `ft:` curve; `-max_total_time` budget tied to the curve |
| AFL++ (AFL-APPROACH, AFL-DEPTH) | queue entry with new edge/hit-count tuple | status screen + `fuzzer_stats`: `cycles done` (green = idle "for a longer while"), `last new find`, `pending`/`pend fav`, `stability`, map density; `afl-showmap -C` for real coverage; `afl-whatsup`/`afl-health` verdict | `afl-showmap` per queue entry yields trace hashes for *corpus* members only — these are all distinct by construction, so singletons of the full sample are lost | "at least one queue cycle without new finds"; `cycles_wo_finds`; `last new find` age; stability < 100 % invalidates any species count |
| Hypothesis (HYPO, UNVERIFIED) | none (not coverage-guided); phases explicit/reuse/generate/target/shrink/explain; `max_examples=100` default; stop reason `Stopped because settings.max_examples=100` | `--hypothesis-show-statistics` | **yes**: wrap the test body with `coverage.py` per example, hash the arc set, maintain `S(n)`, `f1`, `f2`; this is the only engine where the book's algorithm is cheap to implement verbatim | GT per example count; raise `max_examples` until GT < target; `target()` phase for guided search |

Decision table (design proposal, not a citation):

```
if stability/determinism < 100 %            -> fix target first; no estimate is valid
if exact traces available (Python):
    GT = f1/n ; Shat = Chao1 ; progress = S(n)/Shat
    report GT, 1/GT, progress; stop when GT < eps AND extrapolation(m = next budget) adds < 1 species
else (Go/libFuzzer/AFL++):
    track S(n) = corpus size, d(n) = new finds per window
    stop candidate when d(n) == 0 over >= K windows AND (AFL++) >= 1 cycle without finds
    label residual risk as "unknown, lower-bounded by last observed discovery rate"
always: stopping ends THIS corpus/target; next action is new seeds, dictionary, or another target
```

### 5.3 From FuzzingInTheLarge to the agent's final report

Required sections (one per FB-LARGE data item, bucketed as the chapter does):

1. **Product identifier**: module/crate/package, commit hash, language toolchain version, OS/arch,
   sanitizer/race detector flags.
2. **Campaign**: engine, harness path, seed corpus origin and size, dictionary, wall time, execs,
   exec/s, corpus growth `S(n)` curve, final discovery-rate / GT, stop reason (budget, plateau,
   crash), residual-risk caveat (testing ≠ verification).
3. **Buckets**, not crashes: signature = sanitizer/panic type + top-k frames (generalised with
   `?` for varying lower frames, as FuzzManager's Optimize does), count, first seen, reproducible
   (yes/flaky), minimised reproducer path (`testdata/fuzz/FuzzX/<hash>`, `crash-<sha1>`,
   `fuzz/artifacts/...`), one-line reproduce command (`go test -run=FuzzX/<hash>`,
   `cargo fuzz run target artifact`, `pytest … --hypothesis-seed`), suggested severity, link slot
   for the tracker.
4. **Coverage**: per-file/function coverage of the harness run (grcov/`afl-showmap -C`/`go tool
   cover`/`coverage.py`), listing reachable-but-unreached areas → next seeds.
5. **What I need from you**: decisions (which bucket to file, whether to continue, new seeds).

### 5.4 Rules the skills should carry (compact)

- **H1 gate (FB-CONF, FB-SYM):** finite enumerable domain → exhaustive/pairwise, not fuzzing;
  magic-value-gated code → dictionary first, concolic last; option flags → pairwise `C(n,2)`.
- **H2 (FB-STOP):** compute `S(n)`, `f1`, `f2` where possible; `GT = f1/n`; Chao1 only after GT
  has fallen (early estimates were off by 50 % in the book's exercise); extrapolate before asking
  for more budget; stopping one corpus ≠ stopping the campaign.
- **H3 (FB-API, FB-CARVE, FB-ISLA):** seeds from carved real calls and existing tests; per-type
  generators composed into calls; semantic constraints (length prefix, id consistency, ranges)
  enforced by fix-ups or a constraint solver, with a checker run on the seeds first.
- **H4 (FB-API, FB-INV, FB-IF):** oracle ladder: expected-exception classification → round-trip
  (`geturl() == url`) → declared/mined postconditions (27-pattern catalogue) → taint/sink checks;
  mined invariants are regression oracles only.
- **H5 (FB-LARGE):** bucket by signature; report reproducers and commands; keep engine-native
  corpus/artefact locations; record product/version/platform.

## 6. Candidate eval cases

| # | Input the agent sees | Expected behaviour | H |
|---|---|---|---|
| 1 | Go log: `new interesting: 0 (total: 202)` for 40 min at 1e5 execs/s after an initial burst of 202 | Declare plateau for this corpus; report discovery rate ≈ 0, `S(n)=202`, residual risk "not quantifiable from engine output"; propose new seeds/dictionary/another target; do not just extend `-fuzztime` | H2 |
| 2 | Hypothesis test passes with `Stopped because settings.max_examples=100` | Do not call the target "fuzzed"; raise `max_examples`, compute GT from per-example coverage, stop at GT < ε; say so in the report | H2 |
| 3 | After 100 examples, agent's own Chao1 says Ŝ = 196 with S(n) = 130 | Must not report "66 % done"; cite early-campaign inaccuracy; continue until GT drops | H2 |
| 4 | CLI with 30 flags (cobra/argparse/clap) and a small text payload | Pairwise plan for flags (435 pairs; ≈ 3 h at 1 s each if 140 flags) + fuzz the payload; no random-byte fuzzing of the argv string | H1/H3 |
| 5 | Pure function with 3 enum arguments (12 combinations) | "Do not fuzz": exhaustive table test | H1 |
| 6 | Typed pair `parse_duration(str)->int` / `format_duration(int)->str` | Property test with round-trip oracle + postconditions (`ret >= 0`, …), expected-exception classification, not crash-only | H4 |
| 7 | Binary record with 2-byte length prefix and CRC32 trailer, seeds all rejected by the parser | Structure-aware generator with length/CRC fix-up after mutation (or constraint solver), checker run on seeds before fuzzing | H3 |
| 8 | Repository has an integration suite exercising the parser on real files | Carve/harvest those calls as seed corpus and regression assertions before writing new generators | H3/H4 |
| 9 | Campaign ends with 37 crash artefacts, many sharing frames | Report ≤ handful of buckets with signature (type + top frames), count, minimised reproducer, reproduce command, product id, coverage, residual-risk caveat | H5 |
| 10 | AFL++ screen shows stability 71 % | Stop estimating; fix nondeterminism (threads, uninitialised memory, persistent-mode state) first | H2/H5 |
| 11 | Coverage stuck before a `if magic == 0xCAFEBABE` check | Add dictionary/seed with magic, CmpLog; mention concolic as last resort, not first | H1/H3 |

## 7. Micro-examples

1. **Good–Turing on the Enigma (FB-STOP § Turing's Observations).** After 100 cracked messages,
   72 distinct trigrams, 63 seen once → `GT = 63/100 = 0.63`: a 63 % chance the next message uses
   an unseen key. After 2000 messages `GT = 0.401`, empirically measured `0.412`; `1/GT ≈ 2.5`
   messages until the next new trigram; sample coverage `1 − GT = 0.599`. The code is three lines:
   `singletons = len([k for k, v in observed.items() if int(v) == 1]); gt = singletons / n`.
2. **Chao1 on HTMLParser (FB-STOP § A Success Estimator).** At n = 200 000 random inputs:
   `S(n) = 61`, `Ŝ = 61 + f1²/(2f2) = 65.5`, progress 93.13 %. At n = 400 000, 67 traces were
   observed — Chao1 was below the truth, consistent with its known downward bias and the
   chapter's caution for early phases (exercise: 196 predicted vs 153 reached after 4× more inputs).
3. **Length-prefixed strings in ISLa (FB-ISLA § Matching Expansion Elements):**
   `str.to_code(<string>.<length>.<byte>) = str.len(<string>.<chars>)` — two length bytes
   `0x00 0x05` for "Hello"; the same constraint, passed to `solver.check()`, is an input validator.
4. **Pairwise budget (FB-CONF § Combinatorial Testing):** 30 autopep8 options → 435 unordered
   pairs (chapter prints 870 = n(n−1)); mypy's 140+ options → ≈ 20 000 pairs ≈ 3 h at one second
   per test — a budget an agent can state up front, unlike a fuzzing run.
5. **Mined postcondition as regression oracle (FB-INV § Some Examples):** three calls of
   `my_sqrt` (25.0, 10.0, 0.01) yield `x > 0`, `return_value > 0`, floats, and drop the spurious
   `return_value <= x`; the annotated function then fails on a regression returning `-approx` for
   `2.0`, and raises on `-1.0` where the original hangs.
6. **Bucket signature (FB-LARGE § Crash Buckets):** `stderr ~ "ERROR: AddressSanitizer:
   heap-buffer-overflow"` ∧ frames `[…, buggy_fn, ?, ?]` ∧ `address > 0xFF`; Optimize widened lower
   frames to `?` over 3–4 iterations until near-duplicate stacks merged without touching other buckets.
