# Fuzzing tests writer — scope, coverage layout and eval plan

Status: **research synthesis and design layout (2026-11-03)**. Nothing under
`roles/devbox/files/` was changed while producing it. The next iteration writes the agent prompt,
the skills and the evals from this document; until then the document is the specification of
*what* must exist, not of the prompt text.

Goal in the user's words: build a *fuzzing tests writer* agent plus a set of skills for Go, Python
and Rust, after several earlier attempts "went badly", and restrict fuzzing to the places where it
pays off rather than applying it everywhere.

Deliverables of this document:

1. an FPF framing of the work (what result the next iteration needs, which patterns govern it);
2. a condensed, source-linked synthesis of the research (nine reports, 3 100 lines, in
   `fuzzing-tests-writer/research/`), organised around five failure hypotheses;
3. the coverage layout: agent procedure, skills, reference documents, automation, repository
   placement;
4. an eval plan grounded in SYSE.46 and in the eval tooling actually available in Claude Code;
5. open questions and the plan for the next iteration.

Evidence convention: every claim in §3 cites a research annex (`R1`–`R9`) and, through it, a
primary source with an exact locator. Items the annexes mark **UNVERIFIED** are repeated with that
label. Several documentation hosts (`fuzzingbook.org`, `go.dev`, `llvm.org`, `docs.rs`,
`hypothesis.readthedocs.io`, `rust-fuzz.github.io`, `google.github.io`, `arxiv.org`) were not
reachable from the research session; the annexes read the same documents from their GitHub source
repositories and say so per source. Paper bodies that exist only on those hosts (Böhme's STADS,
Klees et al., Mañes et al.) are cited at abstract level and must be re-checked before a skill
quotes a number from them.

---

## 0. Executive summary

| # | Finding | Consequence for the design |
|---|---|---|
| 1 | Fuzzing pays off on a narrow class of code: deterministic, fast (≈1 000 exec/s per core, <10 is broken), in-process, consuming untrusted or format-defined input, with an oracle stronger than "crash" in memory-safe languages. Everything else gets property tests, unit tests or nothing (R1 §5.1). | The agent opens with an **applicability gate** that returns one of `fuzz(method, oracle)` / `property-test` / `unit-test` / `do-not-fuzz` with the reason; the gate is a skill, and the "do-not-fuzz" rows are first-class eval cases. |
| 2 | In Go, Rust and Python the crash oracle finds a bounded bug set: panics, index/slice out of range, unwrap/None, integer overflow (Rust, only with debug assertions), infinite loops, unbounded allocation. Logic bugs appear only with round-trip, differential, metamorphic or model-based oracles (R1 §3.9, R7 §3.6, R8 §3.2, R9 §3.7). | An **oracle ladder** is mandatory in every harness; a crash-only target is accepted only for untrusted byte decoders where denial of service is the risk. |
| 3 | Byte mutation stalls at the first checksum, magic number, length field or parse step; the remedy is one of three mechanically different moves: generate from a model, mutate inside the structure, or disable the check under a fuzzing build flag (R3 §5.1, R5 §5.i). Generators over a byte stream (`arbitrary`, Hypothesis strategies, `rapid.MakeFuzz`, go-fuzz-headers) are the cheapest option in all three languages. | An **input-shape triage** table decides technique and seed source before any harness is written; "random bytes into a typed API" is a rejected plan. |
| 4 | No engine stops by itself and no document gives a numeric threshold. The theory of "done" is statistical (Good–Turing `p0 = f1/n`, Chao1), the engines expose only plateau proxies (`new interesting`, `NEW`/`cov`/`ft`, `cycles_wo_finds`), and greybox adaptivity makes Good–Turing an under-estimate (R2 §3.1, R6 §5.2). | A **stopping algorithm** with budget classes, a sanity gate, a windowed discovery rate, an escalation ladder and a fixed report template; thresholds are marked *sourced* or *proposed default* and are the first thing evals tune. |
| 5 | Harness conventions are ecosystem-specific and unforgiving: Go `testdata/fuzz/<FuzzName>/` is a regression suite run by plain `go test`; cargo-fuzz needs `#![no_main]`, nightly and debug assertions; Hypothesis pins bugs with `@example`, never the database; Atheris never stops without `-atheris_runs` (R7–R9 §5). | One **per-language skill** each, carrying layout, flags, skip-invalid idiom, CI recipe and a review checklist; the agent runs the seed corpus as unit tests before any campaign. |
| 6 | Two agent prompts for property-based testing already exist and agree on the discipline: Hypothesis' own `.claude/commands/hypothesis.md` and Anthropic's `agentic-pbt` (R8 §3.5). | Reuse their rules (few high-value properties, evidence before proposing, sound and ~90 % complete strategies, triage rubric before calling anything a bug) rather than inventing a fourth. |
| 7 | `claude plugin eval` evaluates a *plugin*, not a loose agent file; it supports scaffolded fixture workspaces, deterministic and LLM graders, a baseline arm and a CI threshold (R10). | Package the agent and skills as a plugin directory for behavioural evals; keep the repository's existing `trigger_evals.json` / `evals.json` machinery for skill triggering. |

---

## 1. FPF framing

### 1.1 Receiving use

The result of this document is consumed by one future piece of work: authoring, for the
`dot_ai` pipeline of this repository, an agent definition (`roles/devbox/files/dot_ai/agents/`,
with a Codex TOML adapter under `dot_codex/agents/`), a set of skills
(`roles/devbox/files/dot_ai/skills/`), their reference documents, supporting scripts under
`dot_claude/bin/`, and the evals that gate them. That work is sufficient (`C.39`) when it can
start from this document without re-harvesting sources, and when every rule it writes can be
traced to an annex entry. It does not need, and this document does not attempt, a general
textbook on fuzzing.

### 1.2 Entry patterns used

| Pattern | Why it governs here | What it produced |
|---|---|---|
| `G.2` SOTA-PORTFOLIO (Core) | The field is plural (greybox, grammar, property-based, symbolic, differential/metamorphic, stateful traditions) and the user explicitly asked for *where it applies and where it does not*, which a single-winner answer cannot give. | Nine source-linked annexes with corpus ledgers, claim sheets per tradition, disagreements kept visible, and candidate inventories (skills, eval cases) as stubs. |
| `RMP.7` Synthesize a research evidence corpus | Tool docs, a textbook and papers are different evidence kinds, and several blog posts restate one paper. | Each annex carries an independence note; this synthesis counts traditions, not documents. |
| `SYSE.47` Construct an agent's execution procedure | The deliverable is a procedure with observable inputs, returns and continuation predicates, and limits enforced outside the model's narrative (budgets, tool allow-list, hard caps passed to the engine). | §4.1. |
| `SYSE.46` Test an agent in representative work | Earlier attempts failed; the eval must contrast the new agent with a real baseline, include bounded-stop cases (do-not-fuzz, stop-now, blocked harness) and keep final cases outside tuning. | §5. |
| `C.11.DUA` | The design does not demand evidence beyond what a decision needs; where a threshold has no source it is declared a proposed default rather than invented as a citation. | The ✓/◇ marking in §3.4 and R2 §5.1. |

### 1.3 System characterisation

- **Name**: fuzzing-tests-writer capability (agent + skills + scripts + evals).
- **Boundary**: given a diff, module or named entry point in a Go, Python or Rust repository, it
  decides whether and how to fuzz, writes the harness and seed corpus, wires the seed corpus into
  the normal test run and a budgeted fuzz job, runs a bounded campaign, and returns a campaign
  report with bucketed findings. It does **not** own continuous-fuzzing infrastructure
  (OSS-Fuzz, ClusterFuzzLite), does not replace `unit_tests_writer`, and does not fuzz across
  network, database or filesystem boundaries.
- **Parts**: the agent procedure; three cross-cutting methodology skills; three per-language
  skills; reference documents; two scripts; eval fixtures and suites.
- **Crossings**: receives work from `/techne-test`-style orchestration or the user; produces
  files for the repository and a report for `code_reviewer` / the user; consumes the engine
  command lines (`go test -fuzz`, `cargo fuzz`, `python -m pytest`, Atheris harnesses) and their
  stdout.
- **Context rules**: British English; `techne-` prefix for any command; skills must stay
  vendor-neutral to be admitted to the Codex shared list; the global rules budget (32 KiB for
  Codex) is not touched because nothing here goes into the global rules.

### 1.4 Problem statement: why earlier attempts went badly

Five hypotheses were given to the research agents; the evidence verdicts:

| Hypothesis | Verdict from the annexes | Where it is addressed |
|---|---|---|
| **H1** fuzzing applied everywhere, no gate | Confirmed as the dominant risk: the Fuzzing Book's own evidence puts the yield at the input-processing boundary and says already-fuzzed targets return nothing (R4 §5.1); Google's harness guidance and the AFL++ docs enumerate hard stops (network, state, speed) (R1 §5.1). | Gate skill §4.2.1; eval family A §5.3. |
| **H2** no stopping rule | Confirmed and sharpened: there is no sourced numeric threshold anywhere; engines expose plateau proxies only; the right output is a *decision with a recorded budget*, not an open-ended run (R2 §4, R6 §4). | Campaign skill §4.2.2; script §4.4; eval family D. |
| **H3** random seeds for structured input | Confirmed with mechanism and numbers (prefix probability 1/96⁷; CRC gating; Luhn filter ≈10× vs repair 1×) (R4, R5, R3). | Structure skill §4.2.3; eval family C. |
| **H4** crash as the only oracle | Confirmed for all three languages with trophy-case and issue-tracker evidence; the Go stdlib's own fuzz tests are round-trip properties (R7 §3.6; R9 §3.7; R8 §3.2). | Oracle ladder inside the gate skill; eval family B. |
| **H5** harnesses that do not compile or follow conventions | Confirmed as a convention problem rather than a coding problem: each ecosystem has three or four non-obvious rules (Go one-package/one-target `-fuzz`, OSS-Fuzz shim ignoring `f.Add`; cargo-fuzz `-O` dropping overflow checks; Hypothesis `@reproduce_failure` blob being version-specific) (R7–R9). | Per-language skills; eval family E with compile/seed-run graders. |

A sixth cause not in the original list emerged from R8 and R6: **reporting**. Earlier agents
would have reported "N unique crashes"; the practice is bucket-level reporting with reproducers,
and Klees et al. show stack hashes over-count by ~46 per bug (R2 §3.3 C8, abstract level).

---

## 2. Research corpus

| Annex | Topic | Lines | Primary sources (by GitHub source of the rendered site unless noted) |
|---|---|---|---|
| R1 `01-methods-and-applicability.md` | Method families; applicability gate; oracle catalogue; evaluation hygiene; cost | 407 | google/fuzzing docs, libFuzzer flags, Go fuzz docs and design draft, rust-fuzz book and trophy case, Atheris, Hypothesis, OSS-Fuzz, AFL++, Fuzzing Book; Klees 2018, Schloegel 2024 guidelines, Böhme (abstract level) |
| R2 `02-stopping-and-corpus-lifecycle.md` | Saturation theory; what each engine exposes; corpus lifecycle; CI budgets; the stopping algorithm | 402 | Fuzzing Book "When To Stop Fuzzing", libFuzzer source, AFL++ docs, AFLFast, Go `internal/fuzz`, cargo-fuzz source, Hypothesis source, ClusterFuzzLite, OSS-Fuzz |
| R3 `03-structure-aware-generation.md` | Why bytes fail; grammars, typed generators, custom mutators, repair; seeds; shrinking; per-language snippets | 348 | libFuzzer structure-aware doc, libprotobuf-mutator, AFL++ custom mutators, `arbitrary`, Hypothesis, rapid, go-fuzz-headers, Fuzzing Book, Zest/AFLSmart (abstract) |
| R4 `04-fuzzingbook-part1-lexical.md` | Fuzzing Book Part I: fuzzer loop, coverage, mutation, greybox schedules, search-based, mutation analysis | 262 | uds-se/fuzzingbook notebooks + rendered HTML |
| R5 `05-fuzzingbook-part2-syntactic.md` | Part II: grammars, grammar coverage, parsing, probabilistic, generators/repair, greybox-with-grammars, reduction | 274 | same |
| R6 `06-fuzzingbook-parts3-5.md` | Parts III–V: constraints, invariants, concolic/symbolic, APIs, carving, configurations, fuzzing in the large, when to stop | 486 | same, plus Go fuzz docs, AFL++ docs, ClusterFuzz glossary |
| R7 `07-lang-go.md` | Go native fuzzing (verified on go1.24.7, re-verified against the go1.27.3 sources in §8), rapid, go-fuzz-headers, OSS-Fuzz shim, bug-class evidence | 290 | golang/website, golang/go source at tags, go-118-fuzz-build, rapid, OSS-Fuzz, golang/go issues |
| R8 `08-lang-python.md` | Hypothesis, Atheris, HypoFuzz, schemathesis, crosshair; stopping; conventions; existing agent prompts | 334 | Hypothesis source and docs, Atheris, hypofuzz, OSS-Fuzz Python projects, CPython/Pillow/ujson issues |
| R9 `09-lang-rust.md` | cargo-fuzz, libfuzzer-sys, `arbitrary`, bolero, proptest, afl.rs, honggfuzz, OSS-Fuzz/ClusterFuzzLite, trophy case, RustSec | 299 | rust-fuzz repos, proptest, bolero, OSS-Fuzz, advisory-db, rustc docs |
| R10 `10-eval-tooling-notes.md` | `claude plugin eval`, skill-creator scripts, headless mode, subagent frontmatter | 17 | code.claude.com docs, anthropics/skills |
| `00-research-brief.md` | The common brief the research agents followed (method, output format, H1–H5) | — | — |

Independence (RMP.7): the Google lineage (google/fuzzing, OSS-Fuzz, ClusterFuzz, libFuzzer) is one
tradition and restates itself across R1–R3; AFL++/AFLFast is a second; the Fuzzing Book is a
didactic synthesis that cites both and adds the statistical line (Böhme); the language ecosystems
are three independent empirical records (Go issue tracker, Rust trophy case/RustSec, Python
OSS-Fuzz projects); the property-based-testing tradition (QuickCheck → Hypothesis/proptest/rapid)
is separate and partly in tension with the greybox tradition on whether coverage feedback matters
for typed inputs (R1 §4.2, R9 §4 D6).

---

## 3. Findings that drive the design

This section is the condensed form; the annexes carry the claim sheets. Each subsection ends with
the design consequence.

### 3.1 Applicability gate (H1)

Evaluate top to bottom; the first "do not fuzz" row that matches wins (R1 §5.1, with R4 §5.1,
R6 §5.4, R7 §5.4, R8 §5.1, R9 §5.3 agreeing on every row):

| Target characteristic | Recommendation |
|---|---|
| Behaviour depends on network, database, external process, wall clock, unseeded randomness, environment, or writes to disk | **Do not fuzz as is.** Extract the pure core (parser, validator, state machine) and gate again on that. |
| Persistent threads or goroutines outliving one call; mutable global state the target cannot reset | **Do not fuzz** until refactored (stability < 90 % makes every result unreliable). |
| One execution slower than ≈100 ms after hoisting setup | **Do not fuzz**; property test with a small example budget if a property exists. |
| GUI/CLI glue, orchestration, configuration wiring, code whose only inputs are developer constants | **Do not fuzz.** Pairwise option testing for flag sets (`C(n,2)`), unit tests otherwise. |
| Thin wrapper over an upstream-fuzzed library (stdlib JSON/XML/URL/regexp, `serde` derive, `json.loads`) with no own transformation | **Do not fuzz the wrapper**; property-test the mapping if it has one. |
| Function whose contract permits panics (`Must*`, `unwrap` on programmer error, precondition asserts) | **Do not fuzz that entry**; fuzz the non-panicking variant or encode the precondition in the generator. |
| Memory-safe, total function (always returns `Result`/`(T, error)`/documented exception), no resource amplification, no oracle beyond crash | **Unit tests suffice.** |
| Finite enumerable domain (three enum arguments, seven weekdays) | **Exhaustive table test.** |
| Untrusted raw bytes: decoders, decompressors, archive/image/font parsers, wire frames | **Coverage-guided greybox** on bytes; oracles: crash + timeout + allocation limit + round trip where an encoder exists; real files as seeds; dictionary for tokens. |
| Structured text: JSON-like, YAML/TOML, URLs, regexes, templates, DSLs, headers | **Greybox + seeds + dictionary**; grammar or typed generation only if <50 % of the corpus passes validation after the first run; oracles: round trip, differential versus a reference, "never panics, returns error". |
| Typed API over ints/floats/strings/structs/enums | **Property-based test first** (Hypothesis, proptest, rapid) with invariant, postcondition, metamorphic or model-based properties; bridge into the engine (`fuzz_one_input`, `MakeFuzz`, `Arbitrary`) only on hot untrusted paths. |
| Numeric or algorithmic code | **Property test with metamorphic and differential oracles**; never crash-only. |
| Stateful API (containers, caches, protocol state machines, in-memory clients) | **Model-based state-machine testing** (`proptest-state-machine`, `RuleBasedStateMachine`, rapid `T.Repeat`), or an enum-of-operations trace under the coverage engine when sequences are long. |
| `unsafe`, cgo/FFI, C extensions | **Greybox with ASan** (UBSan too for Python native); the harness must touch every returned reference. |
| Two implementations of one specification exist | **Differential fuzzing**; confirm the specification defines all behaviours first. |

Preconditions every "fuzz" row assumes, checked before a harness is written: determinism; speed
≥ ~100 exec/s; isolation; an explicitly named oracle; a contract statement ("never panics; returns
error on invalid input" versus "may panic on precondition X"); seeds that pass validation; one
format or API family per target (split above 20–30 k reachable edges).

**Design consequence.** The gate is the first step of the agent procedure and the body of the
`fuzzing-applicability` skill. Its output is a one-line decision with the matching row quoted,
so an eval grader can match it.

### 3.2 Oracle ladder (H4)

Pick the strongest oracle the target admits and name it in the harness header (R1 §3.10/§5.2;
R4 §5.4; R6 §5.4; Hughes' ranking of property kinds in R1 §3.4 is partially verified):

model-based → differential → round trip → metamorphic → invariants/postconditions → resource
limits (timeout, RSS, allocation bound) → crash.

Ecosystem facts that change what the bottom rungs can see: Go records a worker killed by the OOM
killer as *no crash* and only the 1 s per-input timeout surfaces allocation bugs (R7 §3.1); cargo-fuzz
keeps debug assertions and overflow checks on by default but OSS-Fuzz's `-O` recipe turns them
off (R9 §3.1 C5, D4); Atheris reports any uncaught exception, so expected exception types must be
caught in the harness (R8 §3.2).

**Design consequence.** The gate skill carries the ladder, the contract-statement header, and
templates for round-trip, differential and metamorphic properties; the review checklist rejects a
"does not panic" harness on a typed API. The existing Hypothesis and `agentic-pbt` prompts supply
the property catalogue and the triage rubric (R8 §3.5).

### 3.3 Structure versus bytes (H3)

Decision by input shape (R3 §5.1, R5 §5.i):

| Input shape | Technique | Seeds | Shrinking |
|---|---|---|---|
| Opaque bytes | plain bytes + dictionary | real files, upstream corpora, `cmin` | engine minimiser |
| Text with keywords; lenient parser; flat format | seeds + bytes + dictionary; **no grammar** | real samples | engine minimiser |
| Recursive text with a strict parser and an existing grammar | grammar-generated seed corpus (bounded, coverage-driven) handed to the engine; grammar terminals as dictionary | grammar coverage: one input per expansion | grammar reducer or generator shrinker |
| Binary format with magic, length, CRC | fuzzing-build flag that skips the check **or** custom mutator with repair | real valid files | engine minimiser only if the repair hook runs on reproduction |
| Typed value, struct, argument tuple | `arbitrary` derive / Hypothesis `builds` + `composite` / rapid generators / go-fuzz-headers | explicit `f.Add` / `@example` boundary values | generator shrinker (proptest, Hypothesis, rapid twin) |
| Sequence of operations | `Vec<Op>` / `RuleBasedStateMachine` / `T.Repeat` | one trace per public method + recorded traces | state-machine shrinking; none under `go test -fuzz` |
| External schema (JSON Schema, OpenAPI, protobuf) | `hypothesis-jsonschema`, schemathesis, libprotobuf-mutator | schema-generated + fixtures | integrated |

Rules of thumb with their evidence: *construct, do not filter* (Luhn: filter ≈10 attempts per
valid number, repair 1; Hypothesis `filter_too_much` fires at 50 rejected draws); *bound size
explicitly*; *keep the byte-level harness beside the structured one* or the parser's error paths
are never fuzzed; *structure at seed-generation time, not per candidate* when throughput matters
(the Fuzzing Book's fragment mutation cost 94.9 s for 300 inputs against 0.1 s for bytes on a
lenient HTML parser, and reached *less* coverage) (R5 §0, §5.i). The only controlled
generator-versus-custom-mutator comparison found a mutator 1.47× ahead at 5 minutes and 1.01× at
24 hours (R3 §4.1).

Go is the outlier: `testing.F` accepts only basic types, custom mutators are an open proposal since
2021, so structure is decoded inside the target from `[]byte` at the cost of instrumented decoder
code, opaque corpus files and no structured shrinking (R7 §3.4, R3 §5.3).

**Design consequence.** The `structured-input-generation` skill carries the table, the seed-corpus
checklist (collect → synthesise → mix mostly-valid → keep small → dedupe → discoverability check →
maintain), one snippet per language, and a dry-run gate: if >~90 % of mutants are rejected at the
first check, change technique, not budget.

### 3.4 Stopping and moving on (H2)

What is sourced and what is a proposed default (R2 §5.1 gives the full procedure and the
per-engine table; R6 §5.2 the species mapping):

- **Theory.** Species = coverage element; Good–Turing `p0 = f1/n` is the probability that the next
  input discovers something new and an upper bound on residual risk; `1/p0` is the expected inputs
  to the next discovery; Chao1 estimates the asymptote but is unreliable early (R6 §0, verified in
  the notebook). Greybox adaptivity biases Good–Turing downward (Böhme et al. 2021, abstract level).
- **Observables.** No engine prints `f1`. Go prints `new interesting: k (total: T)` and, under
  `-json`, the same as `output` events (Go 1.27 adds an `OutputType` field); libFuzzer prints `cov`,
  `ft`, `corp`, `NEW`/`REDUCE` and `-print_final_stats=1`; AFL++ writes `fuzzer_stats` with
  `cycles_wo_finds`, `last_find`, `pending_favs`, `stability`; Hypothesis prints "Stopped because
  settings.max_examples=N" / "nothing left to do" / "< 1 % of test cases satisfied assumptions"
  under `--hypothesis-show-statistics` (R2 §3.2, R8 §3.1).
- **Sourced rules.** AFL++: at least one queue cycle without finds; "a day or a week" without a new
  path means not fruitful, "but often this just means switch strategy". Go: "it is up to you";
  expect `new interesting` to taper. Hypothesis is budgeted by count, not coverage, and must not be
  given plateau logic. libFuzzer has `-max_total_time`/`-runs` only. Sanity thresholds: <10 exec/s
  (libFuzzer guidance) or <100 (AFL++) means a broken harness; stability <90 % invalidates results;
  "no interesting inputs were found so far" means uninstrumented or all-rejecting.
- **Budgets in practice.** ClusterFuzzLite 600 s per PR (quits on first crash), 3 600 s batch,
  daily prune; cargo-fuzz book 300 s smoke; research norm ≥ 24 h with many trials.
- **Plateau is not saturation.** OSS-Fuzz lists four causes of "no new coverage for days": all
  reachable code covered, weak seeds, checksum/crypto blockers, too slow. The escalation ladder
  (seeds from the coverage report → dictionary → schedule/engine → structure-aware → split target →
  fuzzing-cfg bypass) runs before a target is declared done.

The algorithm the agent follows (R2 §5.1, condensed):

1. Choose the budget class first and pass the cap to the engine: `interactive` 10 min
   (proposed), `smoke` 300–600 s (sourced), `batch` 3 600 s (sourced), `deep` 24 h (sourced).
2. Sanity gate at 2 minutes: abort as `BLOCKED_HARNESS` on no interesting inputs, too slow, low
   stability, or a crash/timeout on the seeds.
3. Once per new harness: discoverability check with an empty corpus; coverage far below the seeded
   run means the target is not fuzzable as written.
4. Sample counters every 60 s; declare a plateau when no new coverage for
   `W = max(10 min, 25 % of elapsed)` **and** at least 10⁶ executions in the window (both proposed
   defaults; AFL++ additionally ≥ 1 quiet cycle, sourced).
5. Report the windowed discovery rate `p̂_W` and, where a per-feature dump exists, Good–Turing and
   Chao1 with the adaptivity caveat; never stop on the estimate alone.
6. Decide: `STOP_SATURATED_AT_BUDGET` when plateau holds, the expected executions to the next
   discovery exceed the remaining budget, and the escalation ladder is exhausted for the class;
   `STOP_BUDGET_EXHAUSTED` otherwise at the cap; `CONTINUE` else. Smoke class runs to the cap.
7. Crash path pre-empts: stop in smoke; elsewhere minimise and deduplicate by crash state within
   ≤ 10 % of the budget, verify reproduction, report unreproducible separately.
8. Across targets, allocate the next slice by recent discovery rate discounted by how often the
   target was already scheduled (the AFLFast energy idea); targets touched by the diff get a
   mandatory slice.

**Design consequence.** The `fuzzing-campaign` skill carries the algorithm, the per-engine
threshold table with ✓/◇ marks, the corpus lifecycle checklist and the report template; the
campaign script (§4.4) implements the sampling and the decision so the model never has to parse
logs by eye. The ◇ defaults are explicit tuning targets of the evals (§5.5).

### 3.5 Language facts the skills must carry (H5)

| | Go (1.27.3) | Rust | Python |
|---|---|---|---|
| Engine | `go test -fuzz` (amd64/arm64 on linux/darwin/windows/freebsd) | `cargo fuzz` (libFuzzer, nightly, x86-64/aarch64) | Atheris (libFuzzer, Linux/macOS, 3.11–3.14) |
| Argument types | `[]byte string bool byte rune float32/64 int* uint*` only; no structs, no custom mutators, no dictionaries | any `T: Arbitrary`; `fuzz_mutator!`/`fuzz_crossover!` | `bytes` + `FuzzedDataProvider`; custom mutators |
| Failure = | `t.Fail*`, panic, `os.Exit`, stack overflow, >1 s per input; OOM kill records nothing | panic/abort, ASan, timeout 1 200 s, RSS 2 048 MB; overflow only with debug assertions (default on, off with `-O`) | uncaught exception, timeout, RSS |
| Seeds and regression | `f.Add` + `testdata/fuzz/<FuzzName>/` (`go test fuzz v1`), run by plain `go test` as subtests; failing input written there and fails the baseline of every later `-fuzz` run until fixed | `fuzz/corpus/<t>` and `fuzz/artifacts/<t>` are git-ignored by `cargo fuzz init`; commit minimised crashes as `#[test]` fixtures (or use bolero, whose `__fuzz__` is meant to be committed); proptest commits `proptest-regressions/` (seeds, not values) | pin bugs as `@example`; never commit `@reproduce_failure` (version-specific blob); `.hypothesis/` stays out of VCS (CI profile sets `database=None`); Atheris `tests/fuzz/<name>_fuzzer.py`, `corpus/<name>/`, `<name>.dict` |
| Skip-invalid idiom | `t.Skip("reason")` or `return` | `let Ok(x) = parse(d) else { return Corpus::Reject }` | `except DecodeError: return` |
| Invocation that works | `go test -run='^$' -fuzz='^FuzzX$' -fuzztime=10m -parallel=N ./pkg` (one package, one target, anchored, budgeted) | `cargo fuzz run t fuzz/seeds/t -- -max_total_time=300 -max_len=65536`; keep `--debug-assertions` with `-O` | `python f_fuzzer.py corpus/f -atheris_runs=N`; Hypothesis `CI=1` auto-profile (`derandomize`, `deadline=None`, `print_blob`) |
| Property-based twin | `pgregory.net/rapid` (v1.3.0, 2026-03); `rapid.MakeFuzz` bridges into `f.Fuzz`; `testing/quick` frozen; gopter dormant | `proptest` (+ `proptest-state-machine`, `proptest-arbitrary-interop`); bolero runs one target as `#[test]` and under libFuzzer/AFL/honggfuzz | Hypothesis (`@given`, `RuleBasedStateMachine`, `target()`); HypoFuzz for coverage-guided continuation (non-commercial licence) |
| Continuous fuzzing | OSS-Fuzz rebuilds native targets with `go-118-fuzz-build`, where `F.Add` is a no-op and named types panic; seeds must also ship as `seed_corpus.zip` | OSS-Fuzz `cargo fuzz build -O` (add `--debug-assertions`); pin a nightly date in CI | OSS-Fuzz `compile_python_fuzzer`; `hypothesis.fuzz_one_input` lets one `@given` test run under Atheris |
| Structure | go-fuzz-headers `ConsumeFuzzer`/`GenerateStruct`, `rapid.MakeFuzz`; `file2fuzz` imports raw corpora | `#[derive(Arbitrary)]` behind an optional feature; `size_hint`; `Vec<Op>` traces | strategies (`builds`, `composite`, `recursive`, `from_regex`, `from_lark`), schemathesis for OpenAPI |
| Evidence of yield | slice-bounds panics dominate; steady stream of unbounded allocation (archive/tar CVE-2022-2879, x/net/html CVE-2025-58190, debug/gosym #81191), infinite loops, round-trip inconsistencies (net/netip #67126) | trophy case ≈367 rows: arith overflow, out-of-range, OOM, stack overflow, logic via round trip (rust-url #729); 8 security-marked rows, all `unsafe`/FFI | wrong exception types, exponential parsing (CPython #90863), wrong results via differential (ujson #440), native memory errors (Pillow CVE-2020-35653) |

Go 1.27.3 specifics beyond 1.24: `F.Attr`/`F.Output` (1.25), `F.ArtifactDir` and
`go test -artifacts -outputdir` (1.26, a sanctioned place for campaign artefacts), `OutputType` on
`-json` output events (1.27). No fuzzing-engine change in 1.25–1.27 (R7 §8).

### 3.6 Reporting and claim hygiene (H5, H2)

Report buckets, not crashes: signature = sanitizer/panic type + top frames, count, first seen,
reproducible yes/flaky, minimised reproducer path, one-line reproduce command; product identifier
(module, commit, toolchain, OS/arch, sanitizer flags); campaign numbers (engine, seeds, dictionary,
wall time, executions, exec/s, corpus growth, stop reason, residual-risk caveat); coverage with
reachable-but-unreached areas; and a closing "what I need from you" section (R6 §5.3, R2 §5.3).
Never report corpus size as coverage; one short run is not evidence of cleanliness; timeouts and
OOMs are one bug each per target because they cannot be deduplicated (R1 §5.4).

---

## 4. Coverage layout

### 4.1 Agent procedure (`fuzzing_tests_writer`)

Written per SYSE.47: each step names its evidence in, its return out, and the predicate that
decides the continuation. Limits that matter are enforced outside the model: the engine cap is a
command-line flag, the campaign script refuses to run without one, and the tool allow-list excludes
network and destructive commands.

| Step | Evidence in | Action | Return | Continuation predicate |
|---|---|---|---|---|
| 0 Context | diff or named entry points; language(s) detected | load the matching per-language skill and the three methodology skills; read existing `fuzz/`, `testdata/fuzz/`, `tests/fuzz/`, `.clusterfuzzlite/` | inventory of existing targets and corpora | existing failing seed entry → step 6 first (never fuzz over an unfixed crasher) |
| 1 Gate | one candidate entry point at a time | apply §3.1 top to bottom; write the contract statement | `fuzz(method, oracle)` / `property-test` / `unit-test` / `do-not-fuzz` + quoted row | non-fuzz outcomes end this entry with a one-paragraph recommendation (and a hand-off to `unit_tests_writer` when tests are still wanted) |
| 2 Shape | input shape, available fixtures, grammars, schemas | apply §3.3; pick technique, seed source, shrinking plan | shape row + seed plan | >~90 % first-check rejection in a 1-minute dry run → change row, not budget |
| 3 Harness | per-language skill template and checklist | write harness + seeds + dictionary; wire seed corpus into the normal test run | files written | `go vet` / `cargo fuzz build` / `python -c import` clean **and** the seed corpus passes as unit tests, else fix before any campaign |
| 4 Campaign | budget class from the caller (default `interactive`) | run the campaign script with the cap; it samples, applies the sanity gate and the plateau test | script JSON: decision, counters, artefacts | `BLOCKED_HARNESS` → step 3; `CONTINUE` is impossible past the cap; crash → step 6 |
| 5 Escalate | plateau + coverage report | one rung of the ladder (§3.4) per plateau, at most two rungs in `interactive` | new seeds/dictionary or a new harness entry | rung iv–vi starts a new (target, corpus) ledger entry |
| 6 Triage | artefacts, crash states | minimise, reproduce three times, bucket, convert to regression fixture per ecosystem | bucket list with reproducers | unreproducible → separate list; `Must*`-contract panics and sub-1 s "hangs" are triaged out, not filed |
| 7 Report | all of the above | fill the campaign report template; list decisions needed | report | the "What I need from you" section is last (the repository's Stop hook enforces this) |

Frontmatter decisions for the Claude definition (agent-builder archetype "Code-Writing", with
`permissionMode: acceptEdits`): `tools: Read, Write, Edit, Grep, Glob, Bash`, no `WebFetch`;
`model: opus` for the gate and shape steps is justified by the decision density, with the
complexity-escalation pattern of `unit_tests_writer` kept for parity; `skills:` lists the six new
skills plus `agent-communication`, `shared-utils`, `agent-base-protocol`, `code-writing-protocols`,
`lint-discipline`, `code-comments`, and the existing `go-engineer`/`python-engineer`/`go-testing`/
`python-testing` for idiom. `maxTurns` is set because the campaign is bounded by design. The Codex
TOML adapter mirrors the Claude file as the other 29 do; the Gemini copy comes from `dot_ai` for
free.

Relation to existing agents: `unit_tests_writer` keeps ownership of example-based tests and
receives the hand-off for non-fuzz outcomes; `code_reviewer` gets the three review checklists
(one per language) appended to its skill list; `/techne-test` gains a `fuzz` argument that routes
to this agent, or a new `/techne-fuzz` command is added — the second is preferred because the
complexity check and the model selection differ.

### 4.2 Skills

Three cross-cutting methodology skills (vendor-neutral, admitted to `devbox_codex_shared_skills`)
and three per-language skills. Names are proposals that fit the existing `go-testing` /
`python-testing` naming; every skill carries `problem:` and `related:` frontmatter and an
`evals/` directory from day one.

| Skill | Carries | Hypotheses | Size target | Sources |
|---|---|---|---|---|
| 4.2.1 `fuzzing-applicability` | §3.1 gate table with the seven preconditions; §3.2 oracle ladder, contract-statement header, property catalogue (round trip, inverse, equivalent implementations, idempotence, commutativity, invariants, metamorphic, model-based) and the triage rubric from the Hypothesis/agentic-pbt prompts; anti-pattern list with the evidence behind each | H1, H4 | ≤ 250 lines | R1 §5.1–5.2, R4 §5.1/5.4, R6 §5.4, R8 §3.5 |
| 4.2.2 `fuzzing-campaign` | budget classes; stopping algorithm; per-engine observable/threshold table (✓/◇); escalation ladder; corpus lifecycle checklist (before/during/after); crash dedup and minimisation policy; report template; claim-hygiene rules; attention allocation across targets | H2, H5 | ≤ 300 lines + `references/engine-output-cheatsheet.md` | R2 §5, R6 §5.2–5.3, R1 §5.4 |
| 4.2.3 `structured-input-generation` | §3.3 shape table; seed-corpus checklist; construct-not-filter, bound-size, keep-the-byte-path rules; grammar coverage as corpus-adequacy criterion; generate-then-repair pattern; custom-mutator template; structured reduction checklist; one snippet per language | H3, H5 | ≤ 300 lines + `references/grammar-and-repair.md` | R3 §5, R5 §5.i–5.iii |
| 4.2.4 `go-fuzzing` | `testing.F` contract and 1.27.3 facts; harness skeleton; ten-point review checklist; native-vs-rapid-vs-table decision; corpus/`testdata/fuzz` and `$GOCACHE/fuzz` semantics; invocation template; `-json` parsing incl. `OutputType`; OSS-Fuzz shim differences; CI recipe; `F.ArtifactDir` for campaign artefacts | H3, H5 | ≤ 250 lines | R7 §5, §8 |
| 4.2.5 `python-fuzzing` | Hypothesis-vs-Atheris-vs-parametrised decision; skeletons for both; settings and profiles (`ci`, nightly), stop reasons and what each implies; health checks that must never be suppressed; strategies for structure; `fuzz_one_input` bridge; Atheris layout, `-atheris_runs`, native-extension ASan recipe; HypoFuzz with the licence note; schemathesis for HTTP APIs; review checklist; CI recipe | H3, H4, H5 | ≤ 300 lines | R8 §5 |
| 4.2.6 `rust-fuzzing` | proptest-vs-cargo-fuzz-vs-bolero decision; `fuzz_target!` + `Arbitrary` skeleton and proptest skeleton; twelve-point review checklist; layout and git-ignore facts; debug-assertions rule; `cmin`/`tmin`/`coverage`/`fmt`; regression-fixture conversion; nightly pinning; OSS-Fuzz/ClusterFuzzLite recipe | H3, H4, H5 | ≤ 300 lines | R9 §5 |

Deliberately **not** separate skills: `property-based-testing` (folded into the gate skill's
property catalogue and the per-language skills, because the libraries are language-specific and
the discipline is one page), `fuzz-claim-hygiene` (part of the campaign skill's report section),
`grammar-and-repair` (a reference file of the structure skill). Existing `go-testing` and
`python-testing` gain a short pointer paragraph to the fuzzing skills rather than fuzz content.

### 4.3 Reference documents

Reference files live next to the skill that cites them (`<skill>/references/`), so Codex and
Gemini receive them with the skill; nothing goes into `dot_claude/docs/` except an index.

| Document | Derived from | Used by |
|---|---|---|
| `fuzzingbook-map.md` — one paragraph per chapter: lesson, when it applies, what the agent should and should not attempt | R4–R6 | all methodology skills |
| `engine-output-cheatsheet.md` — Go, libFuzzer, AFL++, honggfuzz, Hypothesis output lines and flags with meaning and the stop-relevant fields | R2 §3.2, R7 §3.3, R8 §3.1, R9 §3.1 C13–C14 | campaign skill, campaign script |
| `bug-class-evidence.md` — the Go, Rust and Python bug-class tables with issue links, as the argument for the oracle ladder | R7 §3.6, R9 §3.7, R8 §3.2 | gate skill |
| `grammar-and-repair.md` — derivation trees, expansion coverage, pre/post repair, structured reduction, with the Fuzzing Book numbers as illustrations | R5 | structure skill |
| `stopping-theory.md` — Good–Turing, Chao1, extrapolation formulas, the Enigma/HTMLParser figures, the adaptivity caveat | R2 §3.1, R6 §3 (WhenToStopFuzzing) | campaign skill |
| the ten research annexes themselves stay in `docs/design/fuzzing-tests-writer/research/` as the audit trail; skills cite them by file and section rather than copying prose | — | authors of the next iteration |

### 4.4 Automation

Two stdlib-only Python scripts under `roles/devbox/files/dot_claude/bin/` (the existing uv
project), with unit tests under the same `bin/` suite so `make test-claude-hooks` covers them:

1. **`fuzz_campaign.py`** — `run --engine {go,libfuzzer,atheris,hypothesis} --budget {interactive,smoke,batch,deep} --target … -- <engine args>`. Refuses to start without a cap; injects `-fuzztime` / `-max_total_time` / `-atheris_runs` / `max_examples` from the class; streams the engine's output; samples counters every 60 s (Go via `-json` `output` events, libFuzzer via `pulse`/`NEW`/`REDUCE` lines and `-print_final_stats=1`, Hypothesis via `--hypothesis-show-statistics`); applies the sanity gate and the plateau test with the ◇ defaults as flags; writes `campaign.json` (decision, counters per window, `p̂_W`, artefacts) and renders the report template to Markdown. Also `discoverability` (seeded versus empty-corpus run at equal budget) and `triage` (minimise, reproduce three times, bucket by crash state, convert to the ecosystem's regression fixture).
2. **`fuzz_corpus.py`** — per-engine wrappers for `cmin`/`merge`, `tmin`, raw-seed import (`file2fuzz` for Go, directory copy for cargo-fuzz and Atheris), seed statistics (count, bytes, largest), and the grammar-coverage adequacy count when a grammar file is given.

Both scripts are deliberately engine-agnostic at the interface so the per-language skills only
fill in flags. Mutation-score self-assessment (R4 §5.6: 10–30 statement-deletion mutants against
the harness oracle) is a candidate third command once the first two are stable; it is listed as
optional because no evidence shows an agent needs it to pass the evals.

Repository integration: `make validate-claude` must accept the new agent/skill cross-references;
`make validate-skills` must see `evals/` in each new skill; the Codex shared-skill list in
`roles/devbox/defaults/main/codex.yml` gains the six names; `tests/deploy/test_codex_assets.py`
checks the 29→30 agent count.

### 4.5 Placement summary

| Artefact | Path |
|---|---|
| Agent (Claude/Gemini source) | `roles/devbox/files/dot_ai/agents/fuzzing_tests_writer.md` |
| Agent (Codex adapter) | `roles/devbox/files/dot_codex/agents/fuzzing-tests-writer.toml` |
| Command | `roles/devbox/files/dot_ai/commands/techne-fuzz.md` |
| Skills | `roles/devbox/files/dot_ai/skills/{fuzzing-applicability,fuzzing-campaign,structured-input-generation,go-fuzzing,python-fuzzing,rust-fuzzing}/` |
| Scripts | `roles/devbox/files/dot_claude/bin/fuzz_campaign.py`, `fuzz_corpus.py` (+ tests) |
| Eval fixtures and plugin wrapper | `tests/fuzzing_agent_evals/` (see §5.4) |
| This design and its annexes | `docs/design/fuzzing-tests-writer-agent.md`, `docs/design/fuzzing-tests-writer/research/` |

---

## 5. Eval plan

### 5.1 Claim, baseline and protected effects (SYSE.46 §4.1)

- **Claim under test**: given a Go, Python or Rust repository and an entry point, the agent (a)
  decides correctly whether to fuzz and how, (b) produces a harness that compiles, whose seed corpus
  passes as unit tests, and that carries an oracle beyond crash where one exists, (c) runs a
  bounded campaign and stops with a defensible decision, (d) follows the ecosystem's corpus and CI
  conventions, (e) reports buckets with reproducers.
- **Baselines**: B0 the bare model with no skills and the same tools; B1 the current
  `unit_tests_writer` asked to "add fuzz tests". `claude plugin eval` runs a without-plugin arm
  natively, which gives B0 for free; B1 is one extra arm driven headlessly.
- **Protected effects**: no network, no writes outside the fixture workspace, no engine run without
  a cap. These are enforced by the eval sandbox and the campaign script, and graded as failures if
  the trace shows them.
- **Separated measures**: decision quality, artefact quality, convention compliance, stop
  decision, report quality, cost and turns. Combined only in a dashboard, never into one scalar.

### 5.2 Fixtures

One small repository per language under `tests/fuzzing_agent_evals/fixtures/<lang>/`, vendored
dependencies (the eval sandbox limits network), each containing the same catalogue of entry
points so that cross-language cases are comparable:

| Entry point | Expected gate outcome | Planted defect (for artefact graders) |
|---|---|---|
| binary frame parser with length prefix and CRC, plus encoder | fuzz: greybox, round-trip oracle, CRC handled by flag or repair | out-of-range on a truncated length; encoder/decoder asymmetry on one field |
| text config parser (`KEY=VALUE`, lenient) | fuzz: seeds + bytes + dictionary, no grammar | `%` look-ahead at end of string (the `cgi_decode` class) |
| expression language with a strict parser and a grammar file in the repo | fuzz: grammar-generated seeds + engine | stack overflow at depth N |
| typed money arithmetic with documented laws | property test, no fuzz target | commutativity broken for one currency |
| `IsWeekend(time)` / three-enum pure function | exhaustive table test | none |
| HTTP handler that calls a database client | do not fuzz as is; extract the pure validator | none |
| thin wrapper over the stdlib JSON decoder | do not fuzz the wrapper | none |
| `MustCompilePattern` / `CompilePattern` pair | fuzz the non-panicking variant only | none |
| LRU cache with `get/put/evict` | model-based state machine | eviction order bug |
| FFI/unsafe wrapper (Rust) or C extension stub (Python) | greybox with ASan, touch every returned reference | one-byte over-read |
| an existing fuzz target with a committed failing seed (Go `testdata/fuzz/<hash>`, Rust `crash-*`, Hypothesis printed blob) | reproduce and fix or report; never delete the seed | the original bug still present |
| a pre-recorded campaign log per engine (plateau, still-productive, blocked, slow, unstable) | the matching decision from §3.4 | n/a |

The last row needs no live engine: the logs are fixtures fed to the agent (and to the campaign
script's unit tests). Live-engine cases run with the `interactive` budget capped at 60 s inside
the eval to keep cost bounded; the stop-decision logic is exercised on recorded logs, not on long
runs.

### 5.3 Case families and graders

Graders follow R10: deterministic where the artefact is long (file existence, regex on produced
files, `tool_used` with `Bash(go test *)` and friends, exit status written to a file by the
agent), LLM judge only for the decision prose and the report. Each case is run three times per
arm (the tool's default); pass thresholds are per family.

| Family | Cases (from annex §6 lists) | Deterministic graders | Judge criteria |
|---|---|---|---|
| **A Gate (H1)** — 12 cases, half "do not fuzz" | R1 E1/E3/E5/E7/E12/E14, R7 E2/E3/E9, R8 E6/E7, R9 E1/E2 | `file_exists` negative (no `Fuzz*`/`fuzz_target!`/`*_fuzzer.py` created in do-not-fuzz cases); regex on last message for the quoted gate row | decision names the matching row and the reason; proposes the right alternative (property test, table test, extraction) |
| **B Oracle (H4)** — 8 cases | R4 E5/E6/E7, R7 E1, R8 E1/E2, R9 E4/E8 | regex on the harness file: at least one assertion that is not "does not panic"; contract statement present in the header comment | oracle is the strongest the target admits; expected-exception classification is explicit |
| **C Structure and seeds (H3)** — 10 cases | R3 E1/E2/E4/E6/E7/E12, R5 E1/E2/E4/E9 | seeds present in the ecosystem location; count ≥ 3; no random-byte seeds (regex); dictionary file present where tokens exist; for the CRC case either the `cfg(fuzzing)`/build-tag bypass or a repair hook | technique matches the shape row; "construct, do not filter" respected; the byte-level harness kept beside the structured one |
| **D Stopping (H2)** — 10 recorded-log cases | R2 E1–E4/E6–E8/E10, R6 E1–E3/E10, R7 E5 | regex on the decision token (`STOP_SATURATED_AT_BUDGET` / `STOP_BUDGET_EXHAUSTED` / `BLOCKED_HARNESS` / `CONTINUE`); no re-run of the same command in the trace | the justification cites the observable (window, exec/s, stability) and names the next escalation rung; Hypothesis cases get no plateau logic |
| **E Conventions and compile (H5)** — 12 cases | R7 E4/E6/E8, R8 E9/E10/E12, R9 E3/E7/E9/E10/E12, R4 E10 | `go vet` + `go test -run='^Fuzz'` pass (exit code written to a file by the agent and graded by regex); `cargo fuzz build` or `cargo test` pass; `pytest` pass; correct paths; `-run='^$' -fuzz='^FuzzX$'` form in CI snippets; `--debug-assertions` present with `-O`; no `@reproduce_failure` committed | CI recipe matches the ecosystem's smoke/batch split |
| **F Reporting** — 4 cases | R2 E8, R6 E9, R1 E13, R8 E13 | regex: bucket table present, reproduce command present, product identifier present, "What I need from you" last | buckets ≤ a handful for a 37-artefact input; crash count never reported as bug count |
| **G Triage false positives** — 3 cases | R7 E7, R1 E7, R8 E13 | no issue filed for the `Must*` panic / sub-1 s "hang" (regex on report) | reasoning cites the contract or the timeout budget |

Totals: ~59 cases; 30 % tagged `holdout` and run only before a release (the hold-out mechanism is
`--tag`, which R10 notes is not a documented feature but is the only one available).

### 5.4 Tooling

1. **Skill triggering** — each skill ships `evals/trigger_evals.json` (≈20 queries, near-miss
   negatives such as "add table-driven tests for the parser", "speed up the CI test job",
   "fuzzy-match these strings") and `evals/evals.json`; `make validate-skills` checks structure,
   `make eval-skills SKILL=…` runs Anthropic's `run_eval.py`, `make improve-skills` tunes the
   description. This is the existing machinery and needs no new code.
2. **Behavioural evals** — a plugin directory `tests/fuzzing_agent_evals/plugin/` that symlinks or
   copies the agent and the six skills (`claude plugin eval` needs a plugin target), with
   `evals/<case>/prompt.md`, `graders/*.md`, and `case.yaml` whose `context.scaffold_script`
   copies the fixture repository into the workspace. Run locally with `--scaffold
   --allow-tools "Bash(go test *),Bash(go vet *),Bash(cargo *),Bash(python *),Bash(pytest *)"`;
   in CI with `--trust-plugin --json results.json --threshold 0.8 --model <pinned>
   --judge-model <pinned> --no-publish --max-cost-usd <ceiling>`. The delegation grader
   (`tool_used: Agent` with `subagent_type` matching) checks that an orchestrating session actually
   hands off to the agent for fuzz requests and does not for plain unit-test requests.
3. **Headless driver** — a small script over `claude -p --bare --agents <file> --add-dir <skills>
   --allowedTools … --output-format json --max-turns N --max-budget-usd M`, run from inside each
   fixture, for the B1 baseline arm and for ad-hoc runs on recorded logs; it writes the same
   per-case JSON so the two tools' results can be compared.
4. **Campaign script unit tests** — the recorded engine logs double as fixtures for
   `fuzz_campaign.py`'s parser and decision logic, under the existing `bin/` pytest suite, so the
   deterministic half of family D is tested without a model at all.

### 5.5 What the evals tune

The proposed defaults (◇ in R2 §5.1): plateau window `max(10 min, 25 % elapsed)`, the 10⁶
execution floor, the 2-minute sanity gate, the 50 % discoverability criterion, the ≤ 10 % triage
budget, the 90 % first-check rejection trigger. Each is a script flag; family D cases are written
so that a wrong default flips a decision. Tuning happens on the non-holdout cases only.

### 5.6 Acceptance and reporting

A release of the agent is acceptable when, on the hold-out set, at the pinned model and three
runs per case: family A has no false "fuzz" on a do-not-fuzz case in any run; family E compiles
and passes seeds in every run; families B, C, D, F, G score ≥ 0.8 on the plugin-eval aggregate;
and the with-plugin delta over B0 is positive on every family. Results are kept as
`aggregate-result.json` per run with the model and date, so a model rollout is not read as a
regression.

---

## 6. Open questions and risks

| # | Item | Why it matters | Resolution path |
|---|---|---|---|
| 1 | Paper bodies unverified (Klees 2018 figures, Böhme 2020/2021 magnitudes, Mañes taxonomy, Hughes' property ranking) | skills must not quote numbers from them until read | re-fetch when the hosts are reachable; until then the skills cite the Fuzzing Book chapter and the engine docs, which were read |
| 2 | libFuzzer status-line legend (`ft`, `lim`, `L`) read from flag source, prose manual unreachable | cheatsheet accuracy | verify against `llvm/docs/LibFuzzer.rst` before the cheatsheet is written |
| 3 | Go: whether a `t.Skip`-ped input can still be kept as interesting; one unexplained unminimised crasher in three local runs | wording of the skip idiom; minimisation expectations | read `internal/fuzz/worker.go` paths for skipped results; treat minimisation as best-effort in the checklist |
| 4 | Go OSS-Fuzz shim ignores `f.Add` and panics on named types | a locally correct target is seed-less upstream | the Go skill says to ship both `testdata/fuzz` and `seed_corpus.zip` when `.clusterfuzzlite/` or an OSS-Fuzz project exists |
| 5 | cargo-fuzz on stable with `--sanitizer none` is unverified; sanitizer stabilisation (rust-lang/rust#123617) open | CI recipe | keep "nightly, pinned date" as the rule with a dated re-check note |
| 6 | HypoFuzz is free only for non-commercial use | agent must not add it to a work-profile pipeline silently | the Python skill states the licence before recommending it; the `work` profile can disable the recommendation via a skill variable if needed |
| 7 | No per-language OSS-Fuzz yield statistics exist | the "what fuzzing finds in memory-safe code" argument rests on trophy lists and issue trackers | acceptable for a gate; revisit if a study appears |
| 8 | Generated-corpus commit policy differs per ecosystem (Go writes regressions into the repo; cargo-fuzz git-ignores corpus; proptest commits seeds) | agents that copy one ecosystem's habit to another create noise or lose regressions | per-tool rule in each language skill, graded in family E |
| 9 | `claude plugin eval` requires Claude Code ≥ 2.1.269 and bubblewrap/socat on Linux for granted Bash | CI image | add to the CI job that runs the behavioural evals; the trigger evals need neither |
| 10 | The agent's own model choice (opus for gate/shape) raises cost per case | eval budget | measure on the first non-holdout run; the `--max-cost-usd` ceiling protects CI |

---

## 7. Next iteration

Ordered so that each step has a gate before the next starts.

1. **Skills first, methodology before language**: write `fuzzing-applicability`,
   `fuzzing-campaign`, `structured-input-generation` from §3 and the annexes, each with
   `evals/trigger_evals.json` and `evals/evals.json`; run `make validate-skills` and
   `make eval-skills` per skill. Follow `skill-builder` and its cached Anthropic authoring notes;
   keep every rule traceable to an annex section in a trailing "Sources" list.
2. **Language skills**: `go-fuzzing` (1.27.3), `python-fuzzing`, `rust-fuzzing`; verify every
   command line in a scratch module with the local toolchains (Go and cargo are available in the
   dev container; Atheris and Hypothesis need a venv).
3. **Scripts**: `fuzz_campaign.py` and `fuzz_corpus.py` with the recorded-log fixtures and unit
   tests; `uv lock` for `bin/` if a dependency is added (none is planned).
4. **Agent**: `fuzzing_tests_writer.md` per `agent-builder` (mandatory sections, hand-off
   protocol, complexity check), the Codex TOML, `techne-fuzz.md`; `make validate-claude`;
   register in `codex.yml`; update the agent count test and the README/CLAUDE.md tables.
5. **Evals**: fixtures, plugin wrapper, graders, headless driver; first full run against B0 and B1;
   tune the ◇ defaults on the non-holdout set; record results.
6. **Vendor guidance pass**: reconcile the prompt and skills with the current Anthropic sub-agent
   and skill authoring docs, OpenAI's Codex custom-agent format, and Google's Antigravity rules
   format, through the existing adapters; the shared core stays provider-neutral.
7. **Deploy and live test**: `make <profile> EXTRA_VARS='--tags ai,claude,codex,agy'`, then
   `make test-live ENGINES=claude,codex` so each engine observably loads the new skills.

The research annexes are frozen as of 2026-11-03; a `SoTA-Echoing` refresh (G.2 §11) is due
when any of: Go custom-mutator proposal #48815 lands, Rust sanitizers stabilise, Hypothesis ships an
Atheris backend, or the unreachable paper hosts become readable.
