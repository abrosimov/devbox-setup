---
note_id: "20261103150908"
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
aliases: ["R8"]
tags: [fuzzing, design/research, h2, h3, h4, h5]
topic: "Hypothesis, Atheris, HypoFuzz and the Python ecosystem"
addresses: ["[[H2-no-stopping-rule]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]", "[[H5-harness-conventions]]"]
related: ["[[research-index]]", "[[research-corpus]]"]
---
# Python: fuzzing and property-based testing ecosystem (Hypothesis, Atheris, HypoFuzz and the rest)

Research date: 2026-11-03. Sources fetched live where possible (GitHub raw files, PyPI). The following hosts were
unreachable from this session and anything attributed to them is marked UNVERIFIED or was replaced by the
equivalent repository file: hypothesis.readthedocs.io, hypothesis.works, hypofuzz.com, llvm.org,
google.github.io, security/opensource.googleblog.com, arxiv.org, red.anthropic.com.

## 0. Summary for the design doc (≤ 25 lines)

1. Three tools, three jobs. **Hypothesis** (6.170.14, Python ≥ 3.11) = property-based testing inside pytest:
   typed/structured inputs, shrinking, example database, no coverage feedback by default, stops at
   `max_examples` (default 100). **Atheris** (3.1.0, Python 3.11–3.14, Linux/macOS) = libFuzzer for Python:
   coverage-guided, byte-oriented, runs forever, the only option that also instruments C extensions with ASan.
   **HypoFuzz** = coverage-guided (branch, `sys.monitoring`) fuzzing of *unmodified* Hypothesis tests, runs
   until interrupted, writes failures to the Hypothesis database so plain `pytest` replays them. Licence: free
   only for non-commercial use.
2. Decision rule (H1): fixed small set of known cases → parametrised test. Invariant/round-trip/oracle over a
   typed or structured domain → Hypothesis. Parser/decoder over bytes or text, or any C-extension boundary →
   Atheris (+ASan when native). Existing Hypothesis suite + spare CPU → HypoFuzz. Glue code with no property
   of its own (a view that forwards to the ORM, a wrapper around `json.loads`) → do not fuzz.
3. What fuzzing finds in Python is almost never a "crash": uncaught exceptions of the wrong type, exponential
   or infinite loops (CPython parser #90863, Pygments recursion), wrong results found by differential or
   round-trip oracles (ujson #440 integer wraparound; NumPy `random.wald` returning 0/negative), and memory
   errors only in native extensions (Pillow PCX overrun, CVE-2020-35653). Oracle choice is the whole game (H4).
4. Hypothesis' stopping rule is explicit and observable: generation ends at `max_examples` valid cases, or
   "nothing left to do" when its choice tree is exhausted, or when < 1 % of cases satisfy assumptions
   (99 %-confidence test); shrinking is capped at 500 shrinks / 300 s. `--hypothesis-show-statistics` prints
   "Stopped because …". Atheris/libFuzzer never stop on their own; CI must pass `-atheris_runs=N` or
   `-max_total_time` (H2).
5. Structured input is solved on the Hypothesis side by strategies (`builds`, `from_type`, `@composite`,
   `recursive`, `from_regex`, `from_lark`) and on the Atheris side by `FuzzedDataProvider` or by driving a
   Hypothesis strategy through `test.hypothesis.fuzz_one_input` (the OSS-Fuzz ujson project does exactly
   this). Random bytes into a typed API is the documented anti-pattern (H3).
6. Filtering is the main self-inflicted failure: `.filter`/`assume` retries are not counted but trigger
   `HealthCheck.filter_too_much` at 50 rejected draws; the fix is to construct, not reject (H3, H5).
7. Repro and CI conventions are settled: do not commit `.hypothesis/` (use `GitHubArtifactDatabase` or a
   networked DB); on CI Hypothesis auto-loads a `ci` profile (`derandomize=True, deadline=None,
   database=None, print_blob=True`); pin found bugs as `@example(...)`, never leave `@reproduce_failure`
   in the tree (its blob is version-specific). Atheris: `tests/fuzz/<name>_fuzzer.py`, `corpus/<name>/`,
   `<name>.dict`, run `-atheris_runs=N` in CI, continuous runs via OSS-Fuzz/ClusterFuzz (H5).
8. Two agent prompts for this exact job already exist and agree: Hypothesis' own `.claude/commands/hypothesis.md`
   and Anthropic's `agentic-pbt` `hypo.md` (arXiv 2510.09907). Both insist on: few high-value properties,
   evidence from docstrings/callers before proposing a property, strategies "sound and ~90 % complete",
   no unnecessary constraints, a triage rubric before calling anything a bug. Reported validity of
   agent-found bugs: 56 % valid / 32 % worth reporting on a 50-report sample (UNVERIFIED, search snippet).
9. Not fuzzing: `pytest-randomly` (ordering/seed reset) and `Faker` (realistic fake data, no oracle, no
   shrinking, no feedback); `pythonfuzz` archived 2021; `python-afl` uses `sys.settrace`, slow, single-threaded;
   `schemathesis` = Hypothesis applied to OpenAPI/GraphQL with built-in checks; `crosshair` = symbolic backend
   for Hypothesis (`backend="crosshair"`), pure-Python, deterministic code only.

## 1. Scope and question answered

What an agent that writes Python fuzz/property tests must know about the Python ecosystem: tool positioning,
APIs and settings that control budget and reproduction, conventions (file layout, pytest, CI), oracles that
actually find bugs in a memory-safe language, and the stopping behaviour it can observe. Out of scope: Go and
Rust, general fuzzing theory (covered by sibling reports), API-level details of `hypothesis.extra.*`.

## 2. Corpus ledger

| id | source + edition/date | locator | used for | status |
|---|---|---|---|---|
| H1 | Hypothesis source, `hypothesis/src/hypothesis/_settings.py`, master @ 2026-11-03 | docstrings of `settings.*`, `Phase`, `HealthCheck`, `default`/`ci` profiles | settings semantics, CI profile | include |
| H2 | Hypothesis docs, `hypothesis/docs/explanation/test-case-count.rst`, master | whole page | stopping rule | include |
| H3 | Hypothesis docs, `explanation/domain.rst` | whole page | domain vs distribution, do not narrow | include |
| H4 | Hypothesis docs, `tutorial/adapting-strategies.rst` | whole page | `.map/.filter/assume` | include |
| H5 | Hypothesis docs, `tutorial/replaying-failures.rst` | whole page | database, `@example`, `@reproduce_failure` | include |
| H6 | Hypothesis docs, `tutorial/flaky.rst` | whole page | FlakyFailure causes | include |
| H7 | Hypothesis docs, `tutorial/settings.rst` | whole page | profiles | include |
| H8 | Hypothesis docs, `tutorial/custom-strategies.rst` | whole page | `@composite`, `recursive`, `data()` | include |
| H9 | Hypothesis docs, `how-to/suppress-healthchecks.rst` | whole page | which checks not to suppress | include |
| H10 | Hypothesis docs, `how-to/external-fuzzers.rst` | whole page | `fuzz_one_input` + Atheris recipe | include |
| H11 | Hypothesis source, `core.py` | docstrings `fuzz_one_input`, `example`, `seed`, `reproduce_failure`; failure messages | reproduction | include |
| H12 | Hypothesis source, `control.py` | `assume`, `target`, `note`, `event` | targeted PBT | include |
| H13 | Hypothesis source, `strategies/_internal/strategies.py` | `filter` (3 attempts), `.example()` warning | filter cost | include |
| H14 | Hypothesis source, `internal/conjecture/engine.py` | `should_generate_more`, `ExitReason`, constants | stopping rule, health-check thresholds | include |
| H15 | Hypothesis source, `extra/ghostwriter.py` | module docstring, `hypothesis write --help` | ghostwriter limits | include |
| H16 | Hypothesis source, `stateful.py` | docstrings; `_repr_step` | stateful testing | include |
| H17 | Hypothesis source, `database.py` | class docstrings | DB in CI | include |
| H18 | Hypothesis source, `statistics.py` | report format | observability | include |
| H19 | Hypothesis source, `strategies/_internal/core.py` | `text`, `characters`, `builds`, `from_type`, `recursive`, `from_regex`, `register_type_strategy` | strategies | include |
| H20 | Hypothesis docs, `reference/integrations.rst` | pytest options, ghostwriter caveat | pytest integration | include |
| H21 | Hypothesis docs, `reference/strategies.rst` | strategy list, `hypothesis.extra.*` list | strategy inventory | include |
| H22 | Hypothesis docs, `tutorial/introduction.rst` | whole page | "what to test" guidance | include |
| H23 | Hypothesis repo, `.claude/commands/hypothesis.md`, master | whole file | official agent prompt | include |
| H24 | Hypothesis repo, `website/content/pages/testimonials.md` | whole file | real bugs | include (thin) |
| H25 | PyPI `hypothesis` page, 2026-11-03 | header | version 6.170.14 (2026-10-30), Python ≥ 3.11 | include |
| H26 | GitHub issue HypothesisWorks/hypothesis#3912 "Implement an Atheris fuzzing backend" (2024-03-09 → closed 2025-11-04) | thread | Atheris↔Hypothesis integration status | include |
| HF1–3 | Zac-HD/hypofuzz `README.md`, `pyproject.toml`, `LICENSE`, master | whole files | positioning, deps, licence | include |
| HF4–11 | hypofuzz `src/hypofuzz/docs/{quickstart,features,compatibility,cli_output_fuzz.txt,manual/operating,manual/database,manual/behavior,manual/collection}.rst` | whole pages | operation, DB, stopping | include |
| HF12 | hypofuzz `docs/literature.rst` | whole page | lineage (AFLFast, Entropic, swarm, FuzzFactory, Nezha) | include |
| HF13 | hypofuzz `src/hypofuzz/coverage.py` | header + `trace_branch` | coverage mechanism | include |
| A1 | google/atheris `README.md`, master (2026) | sections Setup/Fuzz, instrumentation, FuzzedDataProvider, coverage, hooks | Atheris API | include |
| A2 | google/atheris `native_extension_fuzzing.md` | whole | ASan/LD_PRELOAD | include |
| A3 | google/atheris `hall_of_fame.md` | whole | real bugs | include |
| A4 | google/atheris `hooking.md` | whole | regex/str hooks (dev doc) | park |
| A5 | atheris `example_fuzzers/fuzzing_example.py` | whole | minimal harness | include |
| A6 | atheris `example_fuzzers/idna_fuzzer/idna_uts46_fuzzer.py` | whole | differential harness | include |
| A7 | PyPI `atheris`, 2026-11-03 | header | 3.1.0 (2026-06-17), Py 3.11–3.14, wheels 3.12–3.14 manylinux x86-64 | include |
| A8 | Google Open Source blog "Announcing Atheris" (2020-12) | search snippet only | announcement claims | UNVERIFIED (host blocked) |
| O1 | google/oss-fuzz `docs/getting-started/new-project-guide/python_lang.md` | whole | OSS-Fuzz Python integration | include |
| O2 | oss-fuzz `docs/getting-started/new_project_guide.md` | corpus/dict/options sections | naming conventions | include |
| O3 | oss-fuzz `docs/advanced-topics/ideal_integration.md` | checklist | repo conventions | include |
| O4 | oss-fuzz `docs/advanced-topics/reproducing.md` | reproduce command, `-timeout=65`, `-rss_limit_mb=2560` | repro | include |
| O5 | oss-fuzz `infra/base-images/base-builder/compile_python_fuzzer` | whole | how Python fuzzers are packaged | include |
| O6 | oss-fuzz `projects/ujson/{build.sh,ujson_fuzzer.py,json_differential_fuzzer.py,hypothesis_structured_fuzzer.py}` | whole | worked examples of all three harness styles | include |
| G1 | google/fuzzing `docs/good-fuzz-target.md` | whole | target rules, exec/s | include |
| G2 | google/fuzzing `docs/structure-aware-fuzzing.md` | motivation | why bytes fail on structure | include |
| B1 | python/cpython#90863 "Parser hanging on stacked { tokens" (2022-02-10) | thread | DoS bug found by Atheris (per A3) | include |
| B2 | python-pillow/Pillow PR #5174 (merged 2021-01-02) | thread | PCX buffer overrun, CVE-2020-35653, found by OSS-Fuzz | include |
| B3 | ultrajson/ultrajson#440 (2020-11-10, closed 2022-06-01) | thread | wrong integer decoding | include |
| P1 | mmaaz-git/agentic-pbt `README.md`, `hypo.md`, `paper/README.md` | whole | agent prompt + eval design | include |
| P2 | arXiv 2510.09907 "Agentic Property-Based Testing: Finding Bugs Across the Python Ecosystem" (Maaz, DeVoe, Hatfield-Dodds, Carlini, 2025-10-10) | search snippets | numbers | UNVERIFIED (host blocked) |
| P3 | red.anthropic.com/2026/property-based-testing | search snippets | 56 %/32 % validity; NumPy `wald` fix in 2.3.4 | UNVERIFIED (host blocked) |
| X1 | schemathesis `README.md` + `docs/reference/checks.md` | whole | API PBT checks | include |
| X2 | pschanely/CrossHair `README.md`, `doc/source/limitations.rst`, `diff_behavior.rst` | whole | symbolic | include |
| X3 | pschanely/hypothesis-crosshair `README.md` | whole | backend usage | include |
| X4 | fuzzitdev/pythonfuzz `README.md` (archived 2021-04-30) | whole | status | include |
| X5 | jwilk/python-afl `README.md` | whole | mechanism/limits | include |
| X6 | pytest-dev/pytest-randomly `README.md` | whole | "not fuzzing" | include |
| X7 | joke2k/faker `README.md` | first line | "not fuzzing" | include |
| X8 | uds-se/fuzzingbook `notebooks/` listing | names | teaching material | include |
| L1 | llvm.org/docs/LibFuzzer.html | — | flag defaults (`-timeout` 1200 s, `-rss_limit_mb` 2048, `crash-<sha1>`) | UNVERIFIED (host and GitHub mirror both failed); only O4's OSS-Fuzz values are verified |

## 3. Claim sheets

### 3.1 Hypothesis — property-based testing (QuickCheck lineage, structure-aware blackbox)

| # | Claim | Source | Validity region | Failure modes | Conf. |
|---|---|---|---|---|---|
| 1 | `max_examples` default 100: "Once this many satisfying test cases have been considered without finding any failing test case" Hypothesis stops; fewer if a bug is found or the search space is exhausted, more because `.filter()`/`assume()` rejects are not counted. | H1, H2 | all `@given` tests | agents assume "100 runs" = 100 executions; the count is valid cases only | high |
| 2 | Generation stops when `valid_test_cases >= max_examples`, or the choice tree is exhausted (`ExitReason.finished`, "nothing left to do"), or `invalid+overrun` exceeds a threshold derived to be "99 % confident the true valid rate is below 1 %" (`ExitReason.max_iterations`, "< 1 % of test cases satisfied assumptions"). After a first bug it keeps generating at most 10 s / `min(first_bug+1000, last_bug*2)` calls to find more bugs. | H14 | — | exhaustion tracking is "good, but not perfect" (H2) | high |
| 3 | Shrinking is bounded: `MAX_SHRINKS = 500`, `MAX_SHRINKING_SECONDS = 300`; minimal failing case is always re-run once (flakiness check). | H14, H2 | — | slow tests make shrink hit the time cap; use `deadline=None` plus smaller domain | high |
| 4 | `deadline` default 200 ms per test case, `None` disables; exceeding it raises `DeadlineExceeded`; "Unreliable test timings!" is a Flaky path. | H1, H11 | — | GC/JIT noise on CI; the `ci` profile sets `deadline=None` for that reason | high |
| 5 | A `ci` profile is auto-loaded when `CI` (or GITHUB_ACTIONS, GITLAB_CI, CIRCLECI, BUILDKITE, TF_BUILD, …) is set: `derandomize=True, deadline=None, database=None, print_blob=True, suppress_health_check=[too_slow]`. | H1 | Hypothesis ≥ the version introducing the profile (present in master) | an agent's conftest that `load_profile("default")` silently undoes this | high |
| 6 | `derandomize=True` seeds from a hash of the test function: same cases every run "until Hypothesis, Python, or the test function changes". Intended for deterministic CI; `@seed` overrides it and is for reproduction. | H1, H11 | — | derandomised CI never explores new inputs; pair with a nightly non-derandomised or HypoFuzz run | high |
| 7 | Phases: `explicit, reuse, generate, target, shrink, explain`; `target` requires `generate`, `explain` requires `shrink`. `phases=[Phase.generate]` skips DB replay and shrinking (fast smoke). | H1, H2 | — | disabling `reuse` loses regression replay | high |
| 8 | Example database default `.hypothesis/examples` (directory DB); failing cases replay before new generation. "The database is best thought of as a cache that you never need to invalidate" and "We … recommend against relying on the database for the correctness of your tests" — pin with `@example`. | H1, H5, H17 | — | committing `.hypothesis/` only "makes sense when pinning an exact Hypothesis version"; the docs recommend a network DB instead | high |
| 9 | CI sharing: `GitHubArtifactDatabase` (needs `GITHUB_TOKEN`, wrap in `ReadOnlyDatabase`, upload artefact `if: always()`), `MultiplexedDatabase(local, ReadOnly(shared))`, `RedisExampleDatabase`. | H17, H5 | GitHub Actions / networked CI | official `download-artifact` cannot fetch earlier runs; docs use `dawidd6/action-download-artifact` | high |
| 10 | Health checks: `filter_too_much` fires at 50 invalid draws; `data_too_large` at 20 overruns; `too_slow` when generation exceeds `max(1 s, 5×deadline)`; `large_base_example` when the minimal input > 4 KiB of choices; `function_scoped_fixture` and `differing_executors` are correctness checks and should never be suppressed; `nested_given` is quadratic. | H1, H14, H9 | — | blanket `suppress_health_check=list(HealthCheck)` hides shallow strategies | high |
| 11 | `.filter` retries 3 times inside one test case before marking it invalid; `assume` discards the whole case; "Where possible, you should use `.filter`" and never an early `return` (counted as a pass). Simple filters are rewritten into efficient sampling. | H4, H13 | — | `assume` with low acceptance → `Unsatisfiable`/`filter_too_much` | high |
| 12 | Domain guidance: "Hypothesis lets you control the domain of inputs … but not the distribution"; start with "the most-general strategy"; narrow only after measured slowdowns; "Far better to find bugs slowly, than not find them at all." | H3 | — | over-constrained strategies make tests pass vacuously (agent failure mode) | high |
| 13 | `text()` default alphabet is full Unicode minus surrogates ("excludes surrogate characters because they are invalid in UTF-8"), not normalised; `characters()` unfiltered "any character can be produced"; `booleans()` shrink to `False`; `sampled_from` shrinks toward earlier items; `recursive(base, extend, max_leaves=100)`; `builds()` infers strategies from type annotations for missing required args; `from_type()` resolves registry → typing specials → subtypes → `builds` from annotations, raises `ResolutionFailed` otherwise. | H19 | — | NaN in `floats()` by default is confirmed indirectly (H22 shows `[1.0, nan, 0]` as a found counterexample); exact `allow_nan` docstring UNVERIFIED | med-high |
| 14 | Structured strategies: `@composite(draw)`, `recursive`, `from_regex(fullmatch=True)`, `from_lark` (`hypothesis.extra.lark`), `st.data()` (prefer `@composite`; `data()` is incompatible with `@example` and prints poorly). | H8, H19, H21 | — | — | high |
| 15 | `target(observation, label=)` maximises a finite int/float per label; noticeable above `max_examples=1000`, obvious at ~10 000 per label. | H12 | numeric error metrics, counters | useless at the default 100 examples | high |
| 16 | Stateful: `RuleBasedStateMachine` with `@initialize`, `@rule(target=Bundle)`, `@precondition` ("more efficient than `assume` inside a rule"), `@invariant`, `consumes`, `multiple`; `stateful_step_count` default 50 steps per example; expose as `TestFoo = FooMachine.TestCase`; failures print `state = M(); state.rule(...); state.teardown()`. | H16, H1 | APIs with state (collections, caches, connections) | model that reimplements the SUT is not an independent oracle (H23) | high |
| 17 | `@example(...)` runs before generation, does not count towards `max_examples`, is not shrunk, and "If an explicit example fails, Hypothesis will stop … without generating any random inputs". `.xfail` and `.via` exist. | H11, H5 | — | — | high |
| 18 | Reproduction: failure output says "You can reproduce this test case by temporarily adding @reproduce_failure(...)" (only with `print_blob=True`, i.e. CI) or "@seed(...)"; the blob "is not stable across Hypothesis versions" — convert to `@example`. `--hypothesis-seed=N` on the pytest CLI. | H11, H5, H20 | — | leaving `@reproduce_failure` in the tree → `DidNotReproduce` after upgrade | high |
| 19 | Flakiness is fatal: `FlakyFailure` (failure not reproducible on replay) and `FlakyStrategyDefinition`; causes listed: global state, dependencies between inputs, unreset filesystem/DB state, unmanaged randomness; remedy: isolate or use `st.shared`. | H6, H11 | — | — | high |
| 20 | pytest plugin flags: `--hypothesis-show-statistics` (prints per-phase "N passing, M failing, K invalid test cases", "Typical runtimes", "Stopped because settings.max_examples=100" / "nothing left to do", and `event()` frequencies), `--hypothesis-profile`, `--hypothesis-seed`, `--hypothesis-verbosity`, `--hypothesis-explain`. | H20, H18, H14 | — | — | high |
| 21 | Ghostwriter (`hypothesis write`, needs `hypothesis[cli]`): `--roundtrip`, `--equivalent`, `--errors-equivalent`, `--idempotent`, `--binary-op`, default "fuzz" style ("valid input only leads to expected exceptions"); infers strategies from type hints, docstrings, then argument names, falling back to `st.nothing()` with `# TODO` comments; "intended as a starting point for human authorship". | H15, H20 | typed public functions | unresolved args stop the test from running at all | high |
| 22 | `test.hypothesis.fuzz_one_input(bytes)`: runs one case from a bytestring, returns `None` for invalid buffers, else a canonical pruned buffer; `deadline`, `derandomize`, `max_examples` do not apply; the database *is* used (only "failing inputs which would be valid shrinks for a known failure"), so "All you need to do to reproduce, minimize, and de-duplicate all the failures found via fuzzing is run your test suite!" Since 6.124.1 the buffer is interpreted by a `BytestringProvider` closer to byte mutation. For pure Python "we recommend HypoFuzz instead". | H10, H11, H26 | existing `@given` tests driven by Atheris/python-afl | parsing of the buffer still makes some mutations invalid; no dedicated `fuzz_with_atheris` helper (declined in #3912) | high |
| 23 | Extras: `hypothesis.extra.{numpy, pandas, array_api, django (from_model/from_form/from_field), lark, pytz, dateutil}`; `provisional.{domains, urls}`. | H21 | — | — | high |
| 24 | Real bugs: mariadb-dyncol off-by-one at 4095/4096 bytes (H24); NumPy `random.wald` returning 0/negative values from catastrophic cancellation, fixed in NumPy 2.3.4 (P3, UNVERIFIED locator). | H24, P3 | — | testimonials page is otherwise non-specific | med |

### 3.2 Atheris — coverage-guided greybox for Python (libFuzzer lineage)

| # | Claim | Source | Validity region | Failure modes | Conf. |
|---|---|---|---|---|---|
| 1 | API: `atheris.Setup(sys.argv, TestOneInput, internal_libfuzzer=None)`; `TestOneInput` "Must take a single `bytes` argument"; `atheris.Fuzz()` "does not return". Remaining argv are libFuzzer flags. | A1 | Linux 32/64-bit, macOS; Python 3.11–3.14 (3.1.0 wheels: 3.12–3.14 manylinux x86-64) | no Windows; older Pythons only via old PyPI releases | high |
| 2 | Coverage "by instrumenting bytecode"; three entry points: `with atheris.instrument_imports(): import lib` (must wrap the import; "cannot be used to instrument any previously imported module, including modules required by Atheris"), `@atheris.instrument_func`, `atheris.instrument_all()` (experimental, "might take a while", place "right before `atheris.Setup()`"). | A1, A5 | — | instrumenting everything slows the loop; instrumenting nothing yields "No interesting inputs were found" ("the first 2 calls to `TestOneInput` didn't produce any coverage events") | high |
| 3 | Failure model: "Atheris will report a failure if the Python code under test throws an uncaught exception" — prints `=== Uncaught Python exception: ===` + traceback and libFuzzer writes the artefact. Expected exceptions must be caught in the harness (`except zlib.error: return`; `except ValueError: return` in ujson). | A1, O6 | — | catching `Exception` broadly hides real bugs (A6 does so by design and documents it) | high |
| 4 | `FuzzedDataProvider(data)`: `ConsumeBytes(n)`, `ConsumeUnicode(n)` ("Might contain surrogate pair characters"), `ConsumeUnicodeNoSurrogates(n)`, `ConsumeInt(n_bytes)`, `ConsumeIntInRange(min,max)`, `ConsumeIntList(count,bytes)`, `ConsumeFloat()` ("Might produce … NaN and Inf"), `ConsumeProbability()`, `ConsumeBool()`, `PickValueInList(l)`; motivation "Often, a `bytes` object is not convenient input". | A1 | typed/structured inputs | consuming after exhaustion yields zeros/empties — harness must not assert on it | high |
| 5 | Native extensions: build with Clang `-fsanitize=address,fuzzer-no-link`; `LD_PRELOAD` Atheris' `asan_with_fuzzer.so` (else coverage goes to ASan not libFuzzer); set `detect_leaks=0` ("Python is known to leak certain data"); Option A "not yet supported on Mac"; verify with `nm <so> | grep asan`. `Setup(..., enable_python_coverage=False)` when only native code matters (O6 ujson). | A2, O6 | C/C++ extensions | pure-Python projects must *not* preload (O1: "can lead to unexpected startup crashes") | high |
| 6 | Run control: use `-atheris_runs=N` not `-runs=N` for consistent exit/coverage reports; "Coverage reports are only generated when your fuzzer exits gracefully"; coverage.py "will significantly slow down your fuzzer". | A1 | CI smoke runs | — | high |
| 7 | libFuzzer flags Atheris passes through (`-max_len`, `-dict`, `-timeout`, `-rss_limit_mb`, `-jobs`, `-max_total_time`, `-merge=1`; artefacts `crash-<sha1>`, `timeout-*`, `oom-*`) | L1 | — | — | UNVERIFIED (docs unreachable); OSS-Fuzz uses `-timeout=65` / `-rss_limit_mb=2560` for reproduction (O4, verified) |
| 8 | Experimental hooks: `atheris.enabled_hooks.add("RegEx")` and `"str"` (`startswith/endswith` only) feed comparison operands back to the fuzzer. | A1, A4 | regex-heavy parsers | experimental | med |
| 9 | Custom mutators/crossover supported (`custom_mutator=` in `Setup`, `atheris.Mutate()`), incl. libprotobuf-mutator contrib. | A1 | checksummed/compressed inputs | manual work per format (G2) | high |
| 10 | Real bugs (hall of fame): Pillow PCX heap overrun CVE-2020-35653 (B2, "found by OSS-Fuzz"); ujson stack/heap overflows and oversized-integer mis-decoding (B3: `33333333303333333333` → `14886589229623781717`); CPython `PyUnicode_DecodeUTF8Stateful` wrong-size malloc; CPython 3.10 parser exponential backtracking on `{{{{…:` (B1); Pygments infinite recursion; idna/libidn2 outdated Unicode tables. | A3, B1–B3 | — | B1/B3 threads do not themselves mention Atheris; attribution rests on A3 | med-high |
| 11 | OSS-Fuzz: `language: python3`, base image `base-builder-python` (Atheris preinstalled; `pip3 install hypothesis` if used), only `libfuzzer` engine, sanitizers `address`/`undefined`; `build.sh` = `pip3 install .` + `compile_python_fuzzer $SRC/**/*_fuzzer.py` (PyInstaller `--onefile` + wrapper that sets `LD_PRELOAD` and `ASAN_OPTIONS`); corpus `<target>_seed_corpus.zip`, dictionary `<target>.dict`, `.options` `[libfuzzer] dict=…` in `$OUT`. | O1, O2, O5, O6 | OSS-Fuzz / ClusterFuzz | — | high |
| 12 | Good-target rules: tolerate any input, no `exit()`, deterministic, "order of 1000 executions per second per one CPU core", < 1.5 GB RSS, "the narrower the target the better", one target per format, size limits inside the target, seed corpus + dictionary. | G1, O3 | all engines | Python targets are often 10–100× slower than this; still must avoid timeouts/OOM "Otherwise fuzzing will stall quickly" | high |

### 3.3 HypoFuzz — coverage-guided fuzzing of Hypothesis tests (bridge)

| # | Claim | Source | Validity region | Failure modes | Conf. |
|---|---|---|---|---|---|
| 1 | Pure-Python; `pip install hypofuzz`; adds `hypothesis fuzz` to the Hypothesis CLI; collects via pytest (`hypothesis fuzz -- -k parse`), runs all cores (`-n`), dashboard (`--dashboard-only`, `--no-dashboard`, `--port`). "This process will run forever unless stopped with e.g. ctrl-C." | HF4, HF7, HF11 | existing `@given` suites, Python ≥ 3.10, `hypothesis[cli,watchdog] >= 6.140.2`, pytest ≥ 7 | xunit-style setup/teardown and unittest `subTest`/`load_tests` unsupported; pytest plugins not loaded at collection (`-n auto` must not be passed) | high |
| 2 | Branch coverage via `sys.monitoring` on 3.12+ (`BRANCH` event, tool id 4), `sys.settrace` line-arcs before; `hypothesis.event()` counts as a "virtual" branch; `target()` metrics retained as seeds. | HF13, HF10, HF5 | — | — | high |
| 3 | Adaptive scheduling across tests ("focus on the ones where we're discovering new behaviours fastest"), lineage AFLFast/FairFuzz/Entropic, swarm testing, FuzzFactory/IJON (→ `event`/`target`), Nezha (differential), delta debugging. Hypothesis' core described as "a blackbox structure-aware fuzzer"; HypoFuzz "looks for semantics errors" not only crashes. | HF5, HF12 | — | mutation logic "minimum-viable at the moment" | high |
| 4 | Failures go to "the standard location in the Hypothesis database", so `pytest` replays them without HypoFuzz; "critical that the fuzzer is using the *same* database as Hypothesis"; Redis recommended for distributed workers. | HF9 | — | DB mismatch = silent loss of findings | high |
| 5 | Operation: run "after every commit, for an hour" or "once a day for an hour"; "at least 'over lunch,' … more typically 'overnight'"; restart workers every 12–24 h; "the sixtieth minute is likely to be several times more valuable than the first". No automatic stop; the dashboard is the saturation signal. | HF8 | — | no documented saturation criterion — agent needs its own (see §5) | high |
| 6 | Licence `LicenseRef-HypoFuzz`: free for non-commercial / non-profit-governed OSS; any commercial org, including internal CI, needs a paid licence. | HF3 | — | agent must not add HypoFuzz to a commercial CI without flagging licensing | high |

### 3.4 Others (brief)

| Tool | What it is | Why it is / is not fuzzing | Source |
|---|---|---|---|
| schemathesis | Property-based API testing from OpenAPI/GraphQL/gRPC schemas, built on Hypothesis; CLI `schemathesis run <schema>` or `@schema.parametrize()`; checks: `not_a_server_error`, `status_code_conformance`, `content_type_conformance`, `response_schema_conformance`, `response_headers_conformance`, `negative_data_rejection`, `positive_data_acceptance`, `use_after_free`, `ensure_resource_availability`, `ignored_auth`, `unsupported_method`, `missing_required_header`; stateful links. | The right tool for HTTP APIs: oracles are built in; do not hand-write Hypothesis tests against views when a schema exists. | X1 |
| crosshair-tool / hypothesis-crosshair | Symbolic execution with an SMT solver over "symbolic inputs" (proxy values); `pip install hypothesis-crosshair`, `@settings(backend="crosshair")`; when symbolic exploration stops, Hypothesis "runs its remaining examples … with its normal random generation". `crosshair diffbehavior f g` finds inputs where two functions differ. Limits: "absence of a counterexample does not guarantee that the property holds", "Only deterministic behavior", top-level definitions only, it really executes the code. | Complementary to Hypothesis for small pure-Python logic with hard equality branches; useless across C extensions or I/O. | X2, X3 |
| pythonfuzz | "coverage-guided fuzzer for testing python packages", port of jsfuzz/go-fuzz; `@PythonFuzz` decorator. Archived 2021-04-30. | Do not recommend; dead. | X4 |
| python-afl | AFL fork server + `sys.settrace` instrumentation; `afl.init()`, persistent `while afl.loop(N)`, `py-afl-fuzz`; "instrumentation is a bit slow", "Multi-threaded code is not supported". | Works, but Atheris supersedes it (bytecode instrumentation, libFuzzer in-process). | X5 |
| fuzzingbook | Textbook notebooks (`Fuzzer`, `Coverage`, `MutationFuzzer`, `GreyboxFuzzer`, `GrammarFuzzer`, `WhenToStopFuzzing`, `PythonFuzzer`, …). | Teaching classes; use the ideas (grammar fuzzing, stopping), not the code, in production. | X8 |
| pytest-randomly | Shuffles test order and resets `random.seed` (+ Faker, NumPy legacy, factory_boy) per test. | Not fuzzing: no generation of SUT inputs, no oracle, no feedback, no shrinking. Hypothesis is not among the libraries it reseeds. | X6 |
| Faker | "generates fake data for you" (names, addresses). | Not fuzzing: realistic data by design, no edge cases, no oracle, no shrinking, no replay. Fine as a `builds()` ingredient when realism matters. | X7 |

### 3.5 Agents writing Hypothesis tests (two independent prompts + one evaluation)

| # | Claim | Source | Conf. |
|---|---|---|---|
| 1 | Hypothesis' official command: "a small number of high-value tests"; propose only properties the agent "strongly believes are true" with evidence from docstrings/comments/usage/type hints; explore public API → documented core → other core → private helpers; property catalogue: round-trip, inverse, equivalent implementations, idempotence, commutativity, invariants, confluence, metamorphic, single entry point, stateful; properties a unit test covers equally well "are not particularly valuable"; strategies sound and ~90 % complete; "Only place constraints on Hypothesis strategies if required by the code"; stateful model "as simple as possible, usually a plain list or dict"; after confirming a bug add the minimal input as `@example`; if nothing valuable is found, say so and stop. | H23 | high |
| 2 | Anthropic `hypo.md`: pipeline analyse → understand (introspection, follow private import chains) → propose → write → run → triage (reproducibility, legitimacy, impact) → report; "prefer sound but incomplete properties", "Do not constrain strategies unnecessarily", `math.isclose`/`pytest.approx` for floats; outcomes bugs / no bugs / inconclusive; "One real bug discovery > 100 passing tests". Evaluation on 100 packages (15 PyPI + 15 stdlib + 70 random); Claude Opus 4.1 graded reports with a rubric. | P1 | high |
| 3 | Reported validity: 56 % of 50 manually reviewed reports were valid bugs, 32 % worth reporting; bugs in NumPy, pandas, SciPy, Google and Amazon SDKs. | P2, P3 | UNVERIFIED (snippets only) |

## 4. Disagreements and open questions

1. **Commit `.hypothesis/` or not.** `DirectoryBasedExampleDatabase` docstring allows tracking `.hypothesis/examples` but says it "only makes sense when pinning an exact Hypothesis version" and recommends a network-backed DB (H17); the `ci` profile sets `database=None` (H1), i.e. CI does not even write one unless the project configures a shared DB. The tutorial's advice is unambiguous: never rely on the DB for correctness, pin with `@example` (H5). Recommendation: gitignore `.hypothesis/`, use `GitHubArtifactDatabase`/Redis when cross-run memory is wanted.
2. **`-runs` vs `-atheris_runs`.** Atheris documents `-atheris_runs` as the reliable run limit (A1); libFuzzer's `-runs` still terminates but Atheris' coverage/exit reporting is tied to its own counter. Agents should emit `-atheris_runs=N`.
3. **Does HypoFuzz honour `max_examples`/`deadline`?** Not stated in any fetched page (HF4–HF11). `fuzz_one_input` explicitly ignores `deadline`, `derandomize`, `max_examples` (H11); HypoFuzz presumably likewise. OPEN — verify before promising budget semantics under HypoFuzz.
4. **Atheris backend for Hypothesis.** Issue #3912 was closed (2025-11-04) without a `fuzz_with_atheris` helper; the fix was making `fuzz_one_input` bytestring-friendly (`BytestringProvider`). The `PrimitiveProvider` interface "requires more flexibility than is offered by `FuzzedDataProvider`" (H26). So the bridge is: Atheris drives `fuzz_one_input`; expect some mutations to be parsed as invalid.
5. **Validity of agent-found bugs.** 56 % vs "≈81 % of high-priority reports" appear in different summaries of P2; which subset each measures is unknown (UNVERIFIED). Design the eval to measure both "valid" and "worth reporting".
6. **Determinism vs exploration in CI.** Hypothesis' `ci` profile derandomises (H1); fuzzing doctrine wants fresh randomness. No contradiction if the pipeline has both a deterministic PR gate and a scheduled non-derandomised/HypoFuzz run (HF8) — but the agent must configure both explicitly.
7. **libFuzzer flag defaults** (timeout 1200 s, rss 2048 MB, artefact names) could not be verified from llvm.org in this session; OSS-Fuzz's reproduction values (`-timeout=65`, `-rss_limit_mb=2560`) are verified (O4).

## 5. Implications for the agent / skills

### 5.1 Decision rule — Hypothesis vs Atheris vs plain parametrised test (H1, H4)

| Signal in the target | Choose | Why (source) |
|---|---|---|
| Behaviour fully specified by ≤ ~10 known cases; no structural input space | `@pytest.mark.parametrize` | H22: PBT "is not always a replacement"; H23: unit-test-equivalent properties "are not particularly valuable" |
| Typed function/class with a statable relation (round-trip, idempotence, oracle, invariant, metamorphic) | Hypothesis `@given` | H22/H23 property catalogue; shrinking + DB replay (H5) |
| API with state (add/remove, open/close, cache) | Hypothesis `RuleBasedStateMachine` | H16 |
| Numeric error/metric to drive towards an extreme | Hypothesis `target()` with `max_examples ≥ 1000` | H12 |
| Parser/decoder/decompressor consuming `bytes`/`str`; any C/C++ extension boundary | Atheris (+ASan if native), `FuzzedDataProvider` for options | A1, A2, O6, G1 |
| Structured grammar input but the deep logic is Python | Hypothesis strategy, run under HypoFuzz (or Atheris via `fuzz_one_input` when a C extension is involved) | H10, HF5, O6 `hypothesis_structured_fuzzer.py` |
| HTTP API with an OpenAPI/GraphQL schema | schemathesis | X1 |
| Glue: forwards to a framework/ORM/stdlib with no transformation of its own; function whose only risk is in a well-fuzzed dependency (`json.loads`) | Do not fuzz; at most a parametrised test of the error mapping | H23 "If nothing valuable turns up, say so and stop"; G1 narrow targets |
| Already has Hypothesis tests and CPU to spare, non-commercial or licensed | HypoFuzz | HF1, HF3 |

### 5.2 Hypothesis test skeleton (≤ 15 lines) — H5

```python
# tests/test_codec_properties.py
from hypothesis import given, settings, example, strategies as st
from mylib.codec import encode, decode, DecodeError

@given(st.binary(max_size=4096))                      # no narrower than the real domain (H3)
@example(b"")                                         # pin known edge/past bugs (H5, H23)
@settings(max_examples=500, deadline=None)            # budget explicit; deadline off for slow code
def test_roundtrip(payload):
    assert decode(encode(payload)) == payload

@given(st.binary())
def test_decode_rejects_garbage_cleanly(blob):
    try:
        decode(blob)                                  # "must not raise except DecodeError"
    except DecodeError:
        pass                                          # any other exception propagates = failure
```

### 5.3 Atheris harness skeleton (≤ 15 lines) — H5, H3

```python
#!/usr/bin/env python3
# tests/fuzz/decode_fuzzer.py   (OSS-Fuzz convention: *_fuzzer.py)
import sys, atheris
with atheris.instrument_imports():            # only the code under test (A1)
    from mylib.codec import decode, DecodeError

def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    strict = fdp.ConsumeBool()                # structured knobs first (A1)
    try:
        decode(fdp.ConsumeBytes(len(data)), strict=strict)   # rest of buffer
    except DecodeError:
        return                                # expected; anything else is a finding (A1)

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()   # run: python tests/fuzz/decode_fuzzer.py corpus/decode -atheris_runs=100000
```

### 5.4 Rules the skills should carry (with hypothesis addressed)

| Rule | H |
|---|---|
| Applicability gate: before writing, name the property and the evidence (docstring/caller/type) for it; if no property beyond "does not crash" exists and the input is not a parser, stop and say so. | H1 |
| Prefer construction to rejection: `st.integers(min_value=…)`, `.filter` over `assume`, `assume` over `return`; if `filter_too_much` fires, rewrite the strategy rather than suppress. Never suppress `function_scoped_fixture` / `differing_executors`. | H3, H5 |
| Strategies "sound and ~90 % complete"; no `max_size`/alphabet restriction unless the code requires it; justify every constraint in a comment. | H3 |
| Oracle catalogue, in order of yield: round-trip; reference/slow implementation; differential (two libraries, e.g. `json` vs `ujson` — O6); idempotence/commutativity/associativity; metamorphic; invariant after stateful sequence; last resort "valid input raises only the documented exception type". | H4 |
| Budget: default `max_examples=100` for the PR gate; raise (500–2000) for cheap pure functions and for `target()`; set `deadline=None` whenever a single call may exceed 200 ms; `phases=[explicit, reuse, generate]` for a fast smoke profile; `--hypothesis-show-statistics` to read "Stopped because …" and the invalid ratio. | H2 |
| Stop signals the agent can observe: Hypothesis → "Stopped because settings.max_examples=N" (budget exhausted; consider raising only if the test is cheap) vs "nothing left to do" (domain exhausted; do not raise) vs "< 1 % of test cases satisfied assumptions" (strategy is wrong; fix it). Atheris → never stops; CI uses `-atheris_runs=N`/`-max_total_time`; treat a run with a long plateau of no new coverage (libFuzzer `cov:` / `ft:` unchanged — L1 UNVERIFIED wording) as saturated and move to the next target or improve the corpus/dictionary. HypoFuzz → dashboard; run ≥ 1 h, restart workers every 12–24 h. | H2 |
| Reproduction: convert every confirmed failure into `@example(...)`; never commit `@reproduce_failure`; on CI rely on `print_blob` + `@seed`; for Atheris keep the `crash-*` artefact under `tests/fuzz/corpus/<target>/` so it becomes a regression seed (O3 "extended over time with inputs that previously triggered bugs"). | H5 |
| Layout: Hypothesis tests live beside unit tests (`tests/test_*_properties.py` or in the existing module, following suite conventions — H23); Atheris harnesses in `tests/fuzz/<name>_fuzzer.py` with `corpus/<name>/` and `<name>.dict`, matching the OSS-Fuzz discovery glob `*_fuzzer.py` (O1, O6). | H5 |
| Flakiness: any `FlakyFailure` is a defect in the test (global state, unreset fixtures, randomness) — fix, do not retry. Function-scoped pytest fixtures run once per *test*, not per example. | H5 |
| Native code: never preload ASan for pure-Python targets; for extensions build with `-fsanitize=address,fuzzer-no-link`, preload `asan_with_fuzzer.so`, `ASAN_OPTIONS=detect_leaks=0`, and `enable_python_coverage=False` when only native coverage matters. | H5 |
| Licensing: HypoFuzz is non-commercial-only without a licence; the agent must say so before adding it to a pipeline. | — |

### 5.5 Review checklist for a Python property/fuzz test

1. Is there a named property with cited evidence, or only "does not raise"? If the latter, is the target a parser/decoder (then OK as an Atheris harness) — otherwise reject.
2. Domain: is any `max_size`, alphabet, `min_value`, `.filter` justified by the code's contract? Would the bug-triggering class (empty, huge, NaN, surrogate-free but non-ASCII Unicode, negative zero, 2^63 boundaries) still be generated?
3. Rejection cost: `assume` usage minimal; no early `return` masquerading as a skip; health checks not blanket-suppressed.
4. Oracle independence: does the "expected" value reuse the implementation under test? Stateful model simpler than the SUT?
5. Exceptions: are only the documented exception types caught? Is a broad `except Exception` deliberate and documented (differential harness)?
6. Budget & time: `deadline` appropriate; `max_examples` matches cost; `target()` only with ≥ 1000 examples.
7. Determinism: no global state, no wall-clock/network, fixtures scoped correctly; test passes twice in a row and under `--hypothesis-seed=0`.
8. Reproduction: confirmed failures pinned as `@example`; no `@reproduce_failure` committed; Atheris crash files added to corpus.
9. Layout & naming per §5.4; Atheris harness instruments only the library, calls `Setup` before `Fuzz`, consumes structured knobs via `FuzzedDataProvider`.
10. Observability: statistics output reviewed once ("Stopped because …", invalid %, event distribution); fuzz harness shown to produce coverage events (no "No interesting inputs").

### 5.6 CI recipe sketch

| Stage | What | Source |
|---|---|---|
| PR gate (minutes) | `pytest` with Hypothesis auto `ci` profile (`CI=1`: derandomised, no deadline, blob printed). Optionally `MultiplexedDatabase(DirectoryBased(".hypothesis/examples"), ReadOnlyDatabase(GitHubArtifactDatabase(owner, repo)))` and upload `.hypothesis/examples` `if: always()`. | H1, H17 |
| PR gate, fuzz smoke | For each `tests/fuzz/*_fuzzer.py`: `python <fuzzer> corpus/<name> -atheris_runs=10000` (regression over corpus + short exploration); fail on any `crash-*`. | A1, O3 |
| Nightly (hours) | Non-derandomised Hypothesis profile with `max_examples` ×10; or `hypothesis fuzz --no-dashboard -n <cores>` for 1 h with a shared Redis/GitHub-artifact DB (licence permitting). | H7, HF8, HF9 |
| Continuous | OSS-Fuzz (`language: python3`, `base-builder-python`, `compile_python_fuzzer`) for public projects; ClusterFuzz/ClusterFuzzLite otherwise. | O1, O5 |
| On failure | Hypothesis: copy the printed `@example`/blob, reproduce locally, commit `@example`. Atheris: run `python <fuzzer> crash-<sha1>` (OSS-Fuzz: `infra/helper.py reproduce <project> <target> <testcase>`, with `-timeout=65` / `-rss_limit_mb=2560` for timeouts/OOM). | H5, O4 |

## 6. Candidate eval cases

| # | Input the agent sees | Expected behaviour |
|---|---|---|
| 1 | `def parse_cron(expr: str) -> CronSpec` with docstring describing the 5-field grammar and `raise CronError` on invalid input; `format_cron(spec) -> str` exists | Hypothesis: `from_regex`/`@composite` grammar strategy; round-trip `parse(format(s)) == s`; separate test that arbitrary `st.text()` raises only `CronError`. Not Atheris (pure Python, typed, property available). |
| 2 | `def fast_median(xs: list[float]) -> float` next to `statistics.median` | Hypothesis oracle test vs `statistics.median` with `st.lists(st.floats(allow_nan=False), min_size=1)`, `math.isclose`; justify `allow_nan=False` and `min_size=1` from the contract. |
| 3 | `class LRUCache` with `get/put/evict`, capacity | `RuleBasedStateMachine` with a `dict` + order list as model; invariant `len(cache) <= capacity`; `TestLRU = LRUMachine.TestCase`. |
| 4 | Pure-Python PNG chunk reader `read_chunks(data: bytes)` with CRC checks | Atheris harness is wrong as-is (CRC blocks progress — G2); expected: Hypothesis `@composite` that builds valid chunks with correct CRC and mutates fields, plus a CRC-corrupting metamorphic test; optionally Atheris via `fuzz_one_input`. |
| 5 | C-extension `fastimg.decode_jpeg(buf: bytes)` | Atheris harness, `instrument_imports` around the import, ASan build + `LD_PRELOAD asan_with_fuzzer.so`, `detect_leaks=0`, `enable_python_coverage=False`; seed corpus of small JPEGs; `except fastimg.DecodeError: return`. |
| 6 | Django view: `def order_detail(request, pk): return render(request, "x.html", {"o": get_object_or_404(Order, pk=pk)})` | **Do not fuzz.** No property beyond framework behaviour; recommend a parametrised test for 200/404 and, if an OpenAPI schema exists, schemathesis for the API layer. |
| 7 | `def load_config(path): return json.loads(Path(path).read_text())` | **Do not fuzz.** The only parser is stdlib `json`; recommend one test for the error mapping (if `load_config` wraps `JSONDecodeError`) and stop. |
| 8 | Existing suite has 40 `@given` tests; user asks "fuzz this harder" | Prefer HypoFuzz (`hypothesis fuzz -- -k <module>`, ≥ 1 h, shared DB) after stating the licence condition; do not rewrite tests as Atheris harnesses. |
| 9 | Hypothesis run prints "Stopped because settings.max_examples=100, but < 1 % of test cases satisfied assumptions" | Diagnose the strategy (replace `assume` chain with constructive strategy), not raise `max_examples` or suppress `filter_too_much`. |
| 10 | Hypothesis run prints "Stopped because nothing left to do" after 16 cases on `st.sampled_from(16 enum members)` | Recognise domain exhaustion; do not increase budget; consider whether a parametrised test is clearer. |
| 11 | Atheris smoke in CI has run 24 h with the libFuzzer coverage counters flat for the last 20 h, no crashes | Declare the target saturated for this corpus: add a dictionary / seed inputs or split the target; move budget to another target. |
| 12 | A failing Hypothesis test on CI printed `@reproduce_failure('6.170.14', b'...')` | Reproduce locally with that decorator temporarily, then commit the concrete input as `@example(...)`, remove the blob. |
| 13 | Agent-proposed property "`sorted(xs)` preserves `xs`" on a function documented to sort *in place* | Triage as test error, not a bug (legitimacy step of the rubric); fix the property. |

## 7. Micro-examples (source-linked)

1. **OSS-Fuzz ujson, three harness styles in one project (O6).** `ujson_fuzzer.py`: `FuzzedDataProvider.ConsumeUnicode` → `ujson.loads`, `except ValueError: return`, then `ujson.dumps`, with `Setup(..., enable_python_coverage=False)` because the interesting code is native. `json_differential_fuzzer.py`: parse with `json` and `ujson`, skip if either raises, re-serialise both with `json.dumps`, raise "Decoding/encoding disagreement!" — the docstring records the known oversized-integer wraparound (B3). `hypothesis_structured_fuzzer.py` (Zac Hatfield-Dodds, 2021): a Hypothesis JSON strategy checks `ujson.decode(ujson.encode(obj)) == obj` across encoder options; "polyglot" — runs under pytest to replay/minimise and under Atheris via `fuzz_one_input` on OSS-Fuzz; note "Hypothesis uses a separate cache to Atheris/LibFuzzer seeds, so this is strictly complementary".
2. **Atheris idna/libidn2 differential (A6).** `FuzzedDataProvider` yields `transitional = ConsumeBool()`, `std3 = ConsumeBool()`, `original = "a." + ConsumeUnicode(253)`; encode with both libraries under UTS#46; `except Exception: return` for inputs either rejects; raise `RuntimeError("IDNA encoding disagrees with libidn2 encoding")` and likewise for decode. Hall of fame (A3) attributes to this family the finding that libidn2 used outdated Unicode tables — the "bug" was in the C reference, a known risk of differential oracles.
3. **CPython parser DoS (B1, A3).** Input `{{{{{{{{{{{{{{{{{{{{{:` made 3.10's parser take ~2 s, a few more braces ~22 s, longer inputs > 1 h; fixed as bpo-46707 "Avoid potential exponential backtracking in some syntax errors" (GH-31241). A timeout, not an exception, was the oracle — the harness must let libFuzzer's timeout fire rather than catching `SyntaxError` and returning early.
4. **Hypothesis stopping and health-check numbers (H14, H2).** `MIN_TEST_CALLS = 10`; `MAX_SHRINKS = 500`; `MAX_SHRINKING_SECONDS = 300`; health check sample: 10 valid / 50 invalid / 20 overrun draws; `too_slow` limit `max(1 s, 5 × deadline)`; exit strings: `settings.max_examples=N`, `…, but < 1 % of test cases satisfied assumptions`, `nothing left to do`, `shrunk test case 500 times`, `test was flaky`, `shrinking was very slow`. A test over 20 integers "runs 20 times rather than 100".
5. **Hypothesis `ci` profile (H1).** Triggered by `CI` or vendor variables (`GITHUB_ACTIONS`, `GITLAB_CI`, `CIRCLECI`, `BUILDKITE`, `TF_BUILD`, `CIRRUS_CI`, `CODEBUILD_BUILD_ID`, `HEROKU_TEST_RUN_ID`, `TEAMCITY_VERSION`, `bamboo.buildKey`): `derandomize=True, deadline=None, database=None, print_blob=True, suppress_health_check=[HealthCheck.too_slow]`.
