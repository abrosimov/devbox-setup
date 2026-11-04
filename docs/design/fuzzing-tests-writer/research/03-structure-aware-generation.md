---
note_id: "20261103150903"
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
aliases: ["R3"]
tags: [fuzzing, design/research, h3, h5]
topic: "Grammars, typed generators, custom mutators, repair; seeds; shrinking"
addresses: ["[[H3-random-seeds-for-structured-input]]", "[[H5-harness-conventions]]"]
related: ["[[research-index]]", "[[research-corpus]]"]
---
# Structure-aware input generation: seeds and mutation for structured inputs (Go, Python, Rust)

## 0. Summary for the design doc (≤ 25 lines)

1. **Byte mutation fails on structured input for a mechanical reason**: the first checksum, magic, length field or parse step rejects almost every mutant, so coverage stops at the input-validation layer (S1 §"Example: Compression", §"Example: PNG"; S2 §"Coverage discoverability"; S16 "Lessons Learned"; S49 README). This confirms H3 and is the single most cited failure cause in the primary docs.
2. **There are three mechanically distinct remedies, not one**: (a) *generate from a model* (grammar / typed generator over a byte stream: fuzzingbook grammars, Rust `arbitrary`, Hypothesis, Go `rapid`); (b) *mutate inside the structure* (custom mutator: parse → mutate → re-serialise; libprotobuf-mutator; AFL++ `post_process`; derivation-tree mutation); (c) *disable the check under a fuzzing build flag* (`FUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION`, `--cfg fuzzing`). The agent must choose explicitly; "random bytes" is only right when the target really consumes opaque bytes.
3. **Generators over a byte stream are the cheapest structure-aware option in all three languages**: `arbitrary::Unstructured` (Rust), Hypothesis strategies + `fuzz_one_input` or Atheris `FuzzedDataProvider` (Python), `rapid.MakeFuzz` / go-fuzz-headers `GenerateStruct` (Go). They give validity by construction, work with any byte-level engine, and need no mutator code. Known cost: the engine still mutates bytes, so edits are "semantically random"; the one controlled comparison found a custom mutator 1.47× ahead at 5 min but only 1.01× at 24 h (S21).
4. **Context-free grammars are not enough for checksums, lengths or matching identifiers**; the fuzzingbook remedy is *generate-then-repair* (post-expansion functions that fix a Luhn digit or a closing tag), which beats *generate-then-reject* by an order of magnitude in retries (S6). The same principle appears as libprotobuf-mutator `PostProcessor` and AFL++ `afl_custom_post_process`.
5. **Stateful/protocol targets need sequence inputs**: encode a *trace of operations* as the structured input (`Vec<Op>` in Rust, `RuleBasedStateMachine` in Python, `rapid.T.Repeat` state machines in Go) rather than one message. libFuzzer's own doc ranks byte-encoded traces as simplest but brittle and protobuf traces as more maintainable (S1 §"Fuzzing Stateful APIs").
6. **Go is the outlier**: `testing.F` accepts only basic types (S36); structured inputs must be decoded from `[]byte` in the target, with the known cost that the decoder's own code is instrumented and corpus files become opaque (S39). Custom mutator support is an open proposal since 2021 (S39). Use `rapid.MakeFuzz` or go-fuzz-headers; expect no structured shrinking from `go test -fuzz` (minimisation is byte-level, S37).
7. **Shrinking**: byte-level `tmin` / `-minimize_crash` / ddmin breaks structure and mostly produces unparseable candidates (S15 §"Lexical Reduction vs. Syntactic Rules"). Hypothesis, proptest and rapid shrink *inside the generator* so every shrunk value is still valid (S28, S23, S44). Rust `arbitrary` and `cargo fuzz tmin` do not: Rust structured targets should carry a proptest/bolero twin if minimal counter-examples matter.
8. **Seed corpus rules the docs agree on**: small files (AFL: "under 1 kB is ideal", S49), functionally distinct (dedupe with `afl-cmin` / `-merge=1` / `cargo fuzz cmin`), covering every format feature / API branch ideally to 100 % (S2), "valid and invalid" mix (S4), grown with every bug-triggering input (S57), and the fuzz target must still discover coverage *without* the seeds (S2). Herrera et al. 2021: minimised corpora beat singleton, empty and thousand-file corpora (S55). Grammar-coverage generation (one input per expansion alternative) is a principled way to *synthesise* a diverse seed set when no real data exists (S11).
9. **Agent decision rule (§5.1)**: classify the input shape first (opaque bytes / text with keywords / binary format with integrity fields / typed value or API / sequence of operations / external schema) and pick the technique and seed source from the table; refuse plain byte fuzzing for the last four shapes.
10. Blocked hosts (fuzzingbook.org, llvm.org, docs.rs, readthedocs, go.dev, hypothesis.works, arxiv) were replaced by their GitHub sources; two papers (S34, S55) are cited from abstracts only and marked accordingly.

## 1. Scope and question answered

Question: when random bytes are not enough — inputs must vary according to a data structure, grammar, schema, protocol or API contract — how should a fuzz-test-writing agent (Go, Python, Rust) build the seed corpus and the mutation/generation strategy, and how should it shrink structured failures?

Covered: problem evidence; five approach families (grammar-based, typed/structured libraries, custom mutators, format/protocol/stateful, seeds from real data); shrinking; decision guidance and per-language mapping. Not covered: oracles beyond validity (another report), symbolic execution, engine internals.

Network constraint: in this session fuzzingbook.org, llvm.org, docs.rs, rust-fuzz.github.io, hypothesis.readthedocs.io, hypothesis.works, go.dev, go.googlesource.com, google.github.io, arxiv.org, proptest-rs.github.io and author blogs did not resolve. Every one of those sources was read instead from its canonical GitHub repository (uds-se/fuzzingbook notebooks and `docs/code` exports, llvm-mirror/llvm `docs/LibFuzzer.rst` (2019 snapshot), rust-fuzz/*, HypothesisWorks/hypothesis incl. `website/content`, golang/website `_content`, proptest-rs/proptest `book/`). Where only a code export without prose was available, the ledger says so. All fetches on 2026-11-03.

## 2. Corpus ledger

| id | source + edition/date | locator | used for | status |
|---|---|---|---|---|
| S1 | google/fuzzing, `docs/structure-aware-fuzzing.md` (master, 2026-11-03) | §§ "Example: Compression", "Example: PNG", "Example: Protocol Buffers", "Protocol Buffers As Intermediate Format", "Example: SQLite", "Fuzzing Stateful APIs" (gRPC, Envoy, Chrome IPC) | problem evidence; custom mutators; protobuf as IR; stateful traces | include |
| S2 | google/fuzzing, `docs/good-fuzz-target.md` | §§ Seed corpus, Dictionaries, Input size, Determinism, Speed, Coverage discoverability, Large APIs, Splitting inputs | seed-corpus and discoverability rules | include |
| S3 | google/fuzzing, `docs/split-inputs.md` | FuzzedDataProvider, magic separator, hash, TLV | FDP semantics; why TLV is discouraged | include |
| S4 | LLVM libFuzzer docs, `docs/LibFuzzer.rst` (llvm-mirror snapshot 2019; llvm.org blocked) | §§ Corpus, Dictionaries, Options (-minimize_crash, -max_len, -only_ascii, -use_value_profile), Fuzzer-friendly build mode | seed mix "valid and invalid", -merge, build flag | include (version caveat) |
| S5 | fuzzingbook "Fuzzing with Grammars" (`notebooks/Grammars.ipynb`, master) | §§ "Grammars as Mutation Seeds", "Lessons Learned" | CFG strengths and limits | include |
| S6 | fuzzingbook "Fuzzing with Generators" (`notebooks/GeneratorGrammarFuzzer.ipynb`) | §§ intro, "Example: Checksums", "Local Checking and Repairing", "Lessons Learned" | checksums/identifiers via pre/post/order; repair vs reject | include |
| S7 | fuzzingbook "Greybox Fuzzing with Grammars" (`notebooks/GreyboxGrammarFuzzer.ipynb`) | §§ dictionaries, fragments, regions, "Focusing on Valid Seeds", "Mining Seeds", "Lessons Learned" | derivation-tree mutation; LangFuzz; validity schedule; seeds from bug reports | include |
| S8 | fuzzingbook "Parsing Inputs" (`notebooks/Parser.ipynb`) | §§ "Why Parsing for Fuzzing?", Earley complexity, "Lessons Learned" | parse seeds to recombine; O(n³) | include |
| S9 | fuzzingbook "Mining Input Grammars" (`notebooks/GrammarMiner.ipynb`) | §§ intro, "Problems with the Simple Miner", "Lessons Learned", Background (Höschele 2017 AUTOGRAM) | grammar mining validity region | include |
| S10 | fuzzingbook "Probabilistic Grammar Fuzzing" (`docs/code/ProbabilisticGrammarFuzzer.py`; prose stripped) | opts(prob=), ExpansionCountMiner, invert_probs | probabilistic grammars (mechanism only) | include (mechanism; no prose) |
| S11 | fuzzingbook "Grammar Coverage" (`docs/code/GrammarCoverageFuzzer.py`; prose stripped) | GrammarCoverageFuzzer, deep foresight, "Covering Code by Covering Grammars" | seed synthesis by expansion coverage | include (mechanism; numbers not visible) |
| S12 | fuzzingbook "Fuzzing APIs" (`notebooks/APIFuzzer.ipynb`) | "Synthesizing Oracles", "Lessons Learned", Background (Claessen 2000, hypothesis) | API-level generation; false-alarm risk | include |
| S13 | fuzzingbook "Carving Unit Tests" (`notebooks/Carver.ipynb`) | limits of carving; "Mining API Grammars from Carved Calls"; "Lessons Learned"; Elbaum 2006, Kampmann 2018 | seeds from recorded calls | include |
| S14 | fuzzingbook "Testing Web Applications" (`docs/code/WebFuzzer.py`; prose stripped) | HTMLGrammarMiner, ORDER_GRAMMAR + MutationFuzzer | form-grammar mining; valid/invalid split | park (mechanism only) |
| S15 | fuzzingbook "Reducing Failure-Inducing Inputs" (`notebooks/Reducer.ipynb`) | "Lexical Reduction vs. Syntactic Rules", "Comparing Strategies", "Lessons Learned", Background (Zeller 2002, HDD 2006, Perses 2018) | why byte-level reduction breaks structure | include |
| S16 | fuzzingbook "Mutation-Based Fuzzing" (`notebooks/MutationFuzzer.ipynb`) | URL parser odds (1 : 96⁷), "Lessons Learned" | problem evidence | include |
| S17 | rust-fuzz/arbitrary (README; `src/unstructured.rs`; `src/lib.rs`, main) | Unstructured docs (exhaustion → lower bound / first choice / zero padding; lengths taken from end of data; `arbitrary_len` via size_hint), Arbitrary trait docs (dummy values vs error; `try_size_hint` recursion guard; "A Note On Output Distributions"), derive attrs | Rust bytes→value mapping and limits | include |
| S18 | rust-fuzz/book `src/cargo-fuzz/structure-aware-fuzzing.md` (master) | Rgb and `Vec<AllocatorMethod>` examples; `fuzz_mutator!` gzip example; statement that mutation beat arbitrary | Rust generation vs mutator | include |
| S19 | rust-fuzz/libfuzzer `src/lib.rs` (main) | `fuzz_target!` returns -1 (reject) when `arbitrary_take_rest` fails; `fuzz_mutator!` max_size contract; `fuzz_crossover!` | Rust mechanics | include |
| S20 | rust-fuzz/cargo-fuzz README + `src/options/tmin.rs` | `tmin`, `cmin`, `fmt` descriptions | Rust minimisation is byte-level | include |
| S21 | fitzgen/fuzz-experiment README (blog post fitzgen.com 2026-06-01 blocked) | results table: mutate vs arb 1.47 ± 0.02 (5 min), 1.01 ± 0.00 (24 h) | generation vs mutation disagreement | include (README only; author is maintainer of both crates) |
| S22 | bytecodealliance/wasm-tools `crates/wasm-smith` README | "All generated Wasm modules pass validation"; "small changes to the input tend to produce small changes to the output" | exemplar of generator-by-construction | include |
| S23 | proptest book (`book/src/proptest/tutorial/shrinking-basics.md`, `filtering.md`, `vs-quickcheck.md`, `state-machine.md`; master) | ValueTree simplify/complicate; "never shrinks to something outside the range the strategy describes"; filter blocks shrinking; state-machine shrink passes | Rust integrated shrinking; stateful | include |
| S24 | Hypothesis `hypothesis/src/hypothesis/stateful.py` + `hypothesis/docs/stateful.rst` (master) | RuleBasedStateMachine, rule/initialize/precondition/invariant/Bundle/consumes; minimal program output; preconditions cannot read bundles | Python stateful | include |
| S25 | Hypothesis `strategies/_internal/core.py`, `numbers.py` | builds, composite, recursive (max_leaves=100), data, from_regex, sampled_from, lists(unique), dictionaries; "shrinks towards" statements; integers weight bounds | Python strategies | include |
| S26 | Hypothesis `_settings.py` | max_examples=100, stateful_step_count=50, phases incl. shrink, database `.hypothesis/examples`, derandomize | defaults | include |
| S27 | Hypothesis `docs/how-to/external-fuzzers.rst` + `fuzz_one_input` docstring (`core.py`) | bytes→test case; returns None/pruned bytes; database used; deadline/max_examples/phases ignored; health checks not run; byte meaning not stable across versions | Python + Atheris bridge | include |
| S28 | Hypothesis website posts (repo `website/content/`): 2016-12-05 "Integrated vs type based shrinking"; 2016-12-10 "How Hypothesis Works"; 2016-05-11 "Generating the right data"; 2016-08-19 "Recursive data" (all drmaciver) | byte-stream model; shortlex shrinking; invariants preserved; filter→map→builds→composite progression | shrinking theory; what to generate | include |
| S29 | Hypothesis docs `explanation/domain.rst`, `tutorial/adapting-strategies.rst`, `tutorial/custom-strategies.rst` | "most-general strategy"; domain vs distribution; filter vs assume; prefer composite over data | what to generate | include |
| S30 | Hypothesis `extra/lark.py` (`from_lark`) | CFG → strategy; no custom lexing; `%declare` needs `explicit` | Python grammar generation | include |
| S31 | python-jsonschema/hypothesis-jsonschema README | `from_schema`; drafts 04/05/07; non-recursive `$ref` | schema-driven generation | include |
| S32 | schemathesis/schemathesis README | schema-based API fuzzing; stateful via OpenAPI links; sends real requests | API-contract fuzzing | include |
| S33 | Hypothesis website 2025-11-16 "Introducing HypoFuzz" (liam, zac-hd) | coverage-guided execution of existing Hypothesis tests | Python alternative to Atheris | include |
| S34 | MacIver & Donaldson, "Test-Case Reduction via Test-Case Generation: Insights from the Hypothesis Reducer", ECOOP 2020, LIPIcs 166, DOI 10.4230/LIPIcs.ECOOP.2020.13 (abstract via search; PDF host blocked) | internal reduction of the choice sequence; validity problem side-stepped; scaling issue noted | shrinking guarantee | include (abstract-level) |
| S35 | google/atheris README + `example_fuzzers/custom_mutator_example.py` | FuzzedDataProvider API; `custom_mutator=` + `atheris.Mutate`; zlib example | Python FDP and mutator | include |
| S36 | golang/go `src/testing/fuzz.go` doc comments (master) | allowed types list; "fast and deterministic"; seed corpus = `F.Add` + `testdata/fuzz/<Name>` | Go constraints | include |
| S37 | golang/website `_content/doc/security/fuzz/index.md`, `_content/doc/tutorial/fuzz.md` | corpus file format `go test fuzz v1`; `-fuzzminimizetime` (60 s default); 1 s timeout; seeds from unit tests; multi-byte lesson | Go corpus conventions | include |
| S38 | golang/tools `cmd/file2fuzz/main.go` | converts binary files to `go test fuzz v1` + `[]byte(...)` | importing raw corpora into Go | include |
| S39 | golang/go issue #48815 "proposal: testing: custom mutator support for fuzzing" (open; opened 2021-10-06) + golang/proposal `design/48815-custom-fuzz-input-types.md` (2023-06-08) | basic types only; workaround drawbacks (seed-as-PRNG, decode-from-bytes: generator code instrumented, low yield, opaque corpus); proposed Mutate/MarshalBinary | Go tension | include |
| S40 | AdaLogics/go-fuzz-headers README (main) | `NewConsumer(data)`, `GenerateStruct(&p)`, `GetString`, `TarBytes`…; "mostly used in combination with go-fuzz"; std-lib support "will also be supported" | Go struct filling | include |
| S41 | AdamKorcz/go-118-fuzz-build README | compiles native `testing.F` tests to libFuzzer; typed args built from bytes via go-fuzz-headers | how OSS-Fuzz-style Go targets get typed args | include |
| S42 | trailofbits/go-fuzz-utils README | `TypeProvider.Fill` via reflection; nil probability, depth limit; returns error when data too small | Go alternative | include |
| S43 | google/gofuzz README (archived 2024-01-10) | `NewFromGoFuzz(data)` byte-driven mode | historical | park |
| S44 | flyingmutant/rapid README, `engine.go`, `statemachine.go` | `MakeFuzz` for `*testing.F.Fuzz`; no shrink in fuzz mode (`checkFuzz` runs once); `Repeat`/`StateMachineActions`/`Check` | Go idiomatic generator + state machine | include |
| S45 | dvyukov/go-fuzz-corpus | ~90 format directories (json, png, gzip, tls, x509, …); no README guidance | reusable seed corpora for Go formats | include (as a resource) |
| S46 | google/libprotobuf-mutator README | `DEFINE_PROTO_FUZZER`; `PostProcessor` "to keep values that the target needs, such as consistency constraints or checksums"; callbacks must be deterministic | protobuf mutator; repair hook | include |
| S47 | AFL++ `docs/custom_mutators.md` + `custom_mutators/examples/example.py` (stable) | `afl_custom_fuzz`, `post_process` ("format expected by the target"), trim hooks, `AFL_CUSTOM_MUTATOR_ONLY`, Python module support | custom mutator API | include |
| S48 | AFL++ `docs/fuzzing_in_depth.md` (stable) | §2a collect inputs (bug reports, test suites, downloads), §2b `afl-cmin` "highly recommended", §2c `afl-tmin` optional, §3 dictionaries/autodictionary, checksums → remove under `FUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION` or postprocessor | seed and checksum guidance | include |
| S49 | google/AFL README + `docs/technical_details.txt` | "Keep the files small. Under 1 kB is ideal"; functionally different cases; `-x` dictionaries; auto-dictionary from comparisons; "limited coverage if encryption, checksums, cryptographic signatures, or compression … wholly wrap" | seed size; problem evidence | include |
| S50 | AFLplusplus/Grammar-Mutator README | JSON grammars; `grammar_generator` makes seeds + trees; tree mutations and tree trimming; unparseable seed parts kept as terminals | grammar-based AFL++ mutator | include |
| S51 | nautilus-fuzz/nautilus README (NDSS 2019) | coverage-guided derivation-tree mutation; `ctx.script` rules for context-sensitive constraints | grammar + coverage | include |
| S52 | aflsmart/aflsmart README (Pham et al., "Smart Greybox Fuzzing", IEEE TSE 2019) | Peach-pit virtual structure; chunk-level mutations; validity-based power schedule | format-aware greybox | include |
| S53 | aflnet/aflnet README (Pham, Böhme, Roychoudhury, ICST 2020) | seeds = recorded pcap message sequences; state from response codes; `-E` state-aware; nondeterminism caveats | stateful protocol fuzzing | include |
| S54 | rohanpadhye/JQF README + wiki "Fuzzing with Zest" (Padhye et al., ISSTA 2019, DOI 10.1145/3293882.3330576) | parametric generators; validity feedback via assumptions; leap-year 4.6 % vs <0.3 % valid | generator + coverage lineage | include |
| S55 | Herrera et al., "Seed Selection for Successful Fuzzing", ISSTA 2021, DOI 10.1145/3460319.3464795 (abstract via search; PDF host blocked) | minimised corpora beat singleton, empty and thousand-file sets; 33 CPU-years; OptiMin | seed corpus size | include (abstract-level) |
| S56 | Klees et al., "Evaluating Fuzz Testing", CCS 2018 | seed choice changes results; recommend documenting seeds | not fetched | UNVERIFIED (memory) |
| S57 | google/oss-fuzz `docs/getting-started/new_project_guide.md`, `docs/advanced-topics/ideal_integration.md` | `<target>_seed_corpus.zip`, `.dict`, `.options`; "ideal corpus is a minimal set of inputs that provides maximal code coverage"; extend with bug-triggering inputs | corpus conventions | include |
| S58 | camshaft/bolero README | one harness for libfuzzer/afl/honggfuzz + property tests | Rust unifying option | park (README too thin) |

## 3. Claim sheets

### 3.1 Problem evidence: why byte-level mutation fails on structured inputs

| # | Claim | Source | Validity region | Failure modes / caveats | Confidence |
|---|---|---|---|---|---|
| P1 | On structured inputs "any traditional mutation (e.g. bit flipping) leads to an invalid input rejected by the target API" early in parsing; examples: compressed data (uncompress fails), PNG (per-chunk CRC + length + data split across IDAT chunks), protobuf | S1 §§ Compression, PNG, Protocol Buffers | any format with integrity fields, compression, encryption, or strict IDL | the doc also says PNG fuzzes "reasonably" with CRC disabled + comprehensive corpus, but a custom mutator still wins | high |
| P2 | Random text has odds 1 : 96⁷ of producing `http://`; "Randomly generated inputs are frequently invalid – and thus exercise mostly input processing functionality"; mutations of valid seeds "have much higher chances to be valid" | S16 | text protocols with keywords/prefixes | after ~50 stacked mutations the seed is "hardly recognizable" and validity collapses | high |
| P3 | AFL: "limited coverage if encryption, checksums, cryptographic signatures, or compression are used to wholly wrap the actual data format"; remedies: comment out checks or write a postprocessor | S49 README; S48 §4k | all greybox byte fuzzers | – | high |
| P4 | A good target must be able to discover coverage *without* the seed corpus; encrypted/checked inputs are "rejected early as broken"; remedies: split targets, dictionaries, structure-aware fuzzing | S2 §Coverage discoverability | harness design | – | high |
| P5 | Go issue: with a DSL parser "the mutator will generate a large amount of output that cannot pass the syntax or semantic check" | S39 issue | Go native fuzzer, any grammar input | – | high |
| P6 | Fuzzing-build flag `FUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION` to disable CRCs/magic/randomness ("png checks CRC for every chunk"); cargo-fuzz equivalent `--cfg fuzzing` (`#[cfg(not(fuzzing))]` around signature checks) | S4 §Fuzzer-friendly build mode; S48 §3d; rust-fuzz book guide.md (fetched) | targets you can rebuild | the corpus then contains inputs that are invalid for production builds; must not leak into prod; checksum repair is lost for reproduction outside the fuzz build | high |

### 3.2 (a) Grammar-based generation

| # | Claim | Source | Validity region | Failure modes | Confidence |
|---|---|---|---|---|---|
| G1 | Grammars "produce mostly valid inputs" and allow "very systematic and efficient test generation, in particular for complex input formats"; grammar outputs can be used as is or "as seeds for mutation-based fuzzing" | S5 §Grammars as Mutation Seeds, Lessons Learned | textual languages (URLs, expressions, JSON, SQL, JS) with a known CFG | infinite expansion without a cost strategy (simple fuzzer raises `ExpansionError`; GrammarFuzzer uses max/random/min-cost phases) | high |
| G2 | CFGs cannot express semantic constraints: "a complex arithmetic operation like a checksum cannot be expressed in a grammar alone"; matching tags are context-sensitive; port ranges awkward | S6 intro; S5 | – | pure grammar fuzzers produce syntactically valid but semantically rejected inputs (S8 inventory example: "the grammar itself does not capture the complete information about the format") | high |
| G3 | Remedy = functions attached to expansions: `pre` (generate), `post` (check or **repair**), `order`; repair ("each number is generated only once and then repaired") vs filter ("On average, it will still take 10 attempts") for a Luhn digit; local checking on complete subtrees avoids regenerating whole trees | S6 §§ Checksums, Local Checking and Repairing, Lessons Learned | checksums, def-before-use identifiers, numeric ranges, matching tags | restarts are costly when constraints fail late (`replacement_attempts`); `order` needs one entry per child | high |
| G4 | Probabilistic grammars: `opts(prob=)`, probabilities learned from samples by parsing (`ExpansionCountMiner`), inverted to produce *uncommon* inputs | S10 (mechanism) | when a sample corpus exists and you want "typical" vs "rare" inputs | prose/numbers not available in export; UNVERIFIED beyond mechanism | medium |
| G5 | Grammar coverage: choose expansions not yet covered, with look-ahead ("deep foresight"); the chapter's thesis is that covering grammar expansions "also yields higher code coverage" (tested on `cgi_decode`, `urlparse`) | S11 | seed synthesis for a format with a grammar: one input per alternative | export lacks the correlation numbers; equivalent elements and deep data processing listed as cases where it does not help ("Will this always work?" heading) | medium |
| G6 | Derivation-tree mutation of *parsed seeds* (LangFuzz: swap/delete subtrees of same symbol): "requires that the seeds can be parsed successfully"; region-based mutation "is applicable to all seeds" but validity stays low; LangFuzz earned >USD 50 000 in 4 weeks and >2 600 bugs | S7 Lessons Learned, §JavaScript | you have a parser (Earley O(n³) worst case, S8) and real seeds | parsing cost (chapter caps at 0.2 s/seed); unparseable seeds | high |
| G7 | Coverage-guided grammar fuzzers mutate trees (Nautilus; AFL++ Grammar-Mutator with JSON grammars, tree mutations + tree trimming; `grammar_generator` makes seeds and tree files; unparseable seed parts kept as terminal nodes); Nautilus `ctx.script` rules handle context-sensitive constraints (matching tags) | S50, S51 | C/C++ targets under AFL++ (Python targets via Atheris custom mutator could reuse the idea) | Grammar-Mutator: slow startup for big `max_size`, needs `-m 128`; Nautilus regex terminals not mutated after generation | high |
| G8 | Grammar mining from execution (AUTOGRAM lineage): "Simple string inclusion checks are sufficient to obtain reasonably accurate grammars from real world programs"; "can have a multiplier effect on any samples you have" | S9 Lessons Learned | hand-written recursive-descent parsers in an instrumentable language (Python in the book) | assumes variable values are stable; loses fragments across Python/C boundary; fragments shorter than `FRAGMENT_LEN`; implicit flows invisible; names need cleanup | medium |
| G9 | Python grammar generation exists natively: `hypothesis.extra.lark.from_lark(Lark(ebnf))` generates "strings accepted by the given context-free grammar"; no custom lexing; `%declare` terminals need `explicit` strategies | S30 | Python, grammar available as Lark EBNF | same semantic-constraint gap as G2; compose with `.map` to repair | high |

Cost: writing/obtaining the grammar (hours to days per format; S1: structure-aware fuzzing "requires substantial manual work for every input type"). Needs from target: nothing beyond a text/binary input; coverage feedback optional (G7).

### 3.3 (b) Typed / structured generation through libraries

**Rust — `arbitrary` + `cargo fuzz`**

| # | Claim | Source | Validity region | Failure modes | Confidence |
|---|---|---|---|---|---|
| R1 | `fuzz_target!(|input: T|)` accepts any `T: Arbitrary`; the crate "implements Arbitrary for nearly all the types in std"; derive via `arbitrary` feature `derive` or libfuzzer-sys `arbitrary-derive`; field attrs `default`, `value = …`, `with = …` | S18, S17 README | any Rust type whose invariants can be enforced in a constructor or `with` | derive on a type with internal invariants generates invalid values unless `with`/manual impl; recursive types need `try_size_hint`/recursion guard (S17 lib.rs) | high |
| R2 | Byte→value mapping: `Unstructured` is deterministic; on exhaustion `int_in_range` returns `range.start()`, `choose` returns the first choice, `ratio` returns true, `fill_buffer` pads with zeros; collection lengths are taken "from the end" of the data because libFuzzer found this "lets fuzzers more efficiently explore the input space"; distributions "not necessarily uniform" | S17 unstructured.rs | – | empty/short inputs collapse to the "lower-bound" value, so the corpus should contain long enough inputs; an implementation "may return an error if there is not enough data" or fill dummy values (S17 lib.rs) — libfuzzer-sys returns -1 (reject) when `arbitrary_take_rest` fails (S19) | high |
| R3 | Advantage: inputs "avoid uninteresting 'shallow' inputs that will be rejected early" and "go 'deep'"; canonical pattern for stateful APIs is `Vec<Op>` (`enum AllocatorMethod { Malloc{size}, Free{index}, Realloc{..} }`) | S18 | parsers, codecs, stateful APIs | – | high |
| R4 | Generation vs mutation: the book says that if you implement only one, an experiment found "`fuzz_mutator!`-based mutation provides better coverage over time than `arbitrary`-based generation"; the README numbers are 1.47 ± 0.02× at 5 min and 1.01 ± 0.00× at 24 h (mutate vs arb), on a Wasm/Wasmtime target | S18, S21 | – | single target, author maintains both crates; advantage nearly vanishes at 24 h | medium |
| R5 | `arbitrary` has no shrinking; `cargo fuzz tmin` minimises "the failing test case" file (bytes); `cargo fuzz fmt` prints the `Debug` of the decoded input | S17 (no mention), S20 | – | byte-level tmin may change the decoded structure arbitrarily; use proptest/bolero when minimal structured counter-examples matter (§3.6) | high |
| R6 | Exemplar: wasm-smith — "All generated Wasm modules pass validation", "Small changes to the input tend to produce small changes to the output" | S22 | – | – | high |

**Python — Hypothesis, Atheris**

| # | Claim | Source | Validity region | Failure modes | Confidence |
|---|---|---|---|---|---|
| Y1 | Hypothesis strategies: `builds` (callable from strategies; shrinks by shrinking arguments), `composite` (dependent draws; "cannot mix test code and generation code"), `recursive(base, extend, max_leaves=100)`, `deferred` (mutually recursive), `from_regex(…, fullmatch=True)`, `sampled_from`, `lists(unique=)`, `dictionaries`, `from_type`/`register_type_strategy` | S25 | any Python value; JSON via `recursive` (S27 example) | `data()` is more powerful but "prefer st.composite to st.data" — worse reports, incompatible with `@example` (S29 custom-strategies); `filter`/`assume` are rejection sampling | high |
| Y2 | Design guidance: progression filter → map → builds → composite; filter only for conditions "relatively hard to happen by accident"; use "the most-general strategy"; over-constraining "can all too easily exclude the bug-triggering values"; domain is yours, distribution is Hypothesis's | S28 (2016-05-11), S29 domain.rst | – | – | high |
| Y3 | Hypothesis is itself a byte-stream interpreter: Conjecture is "a low level interactive byte stream fuzzer", every strategy is `do_draw(data)`; saved examples are bytes | S28 (2016-12-10) | – | – | high |
| Y4 | Bridge to engines: `test.hypothesis.fuzz_one_input(bytes)` "takes a bytestring, parses it into a test case, and executes the corresponding test once"; returns `None` for invalid, pruned bytes for valid, re-raises on failure and writes the pruned buffer to the database; `database` *is* used; `deadline`, `max_examples`, `phases`, health checks are not; the Atheris JSON example notes FDP-only JSON "would be considerably more difficult"; byte meaning is not stable across Hypothesis versions or strategy edits | S27 | coverage-guided fuzzing of Python with C extensions (docs recommend HypoFuzz for pure Python, S33) | corpus invalidated by Hypothesis upgrade; no shrinking inside the fuzz loop — rerun the test suite to shrink/dedupe; forkserver engines need `database=None` during the run | high |
| Y5 | Atheris `FuzzedDataProvider`: `ConsumeBytes/Unicode/String`, `ConsumeInt/UInt/IntInRange/IntList(InRange)`, `ConsumeFloat/RegularFloat/Probability/FloatInRange`, `PickValueInList`, `ConsumeBool`; "harder for the fuzzer to generate inputs for code that parses complex data types" without it; custom mutators via `custom_mutator=` using `atheris.Mutate` | S35 | flat structs / parameter tuples | FDP corpus files are not valid format files (S3: "you won't be able to simply add image files to your corpus"); integers come "from the last bytes" (S3) | high |
| Y6 | Schema/contract generators: `hypothesis_jsonschema.from_schema` (drafts 04/05/07, non-recursive `$ref`); Schemathesis for OpenAPI/GraphQL incl. stateful chains via links (sends real requests) | S31, S32 | external schema available | recursive refs; custom formats need `custom_formats` | high |

**Go — `testing.F`**

| # | Claim | Source | Validity region | Failure modes | Confidence |
|---|---|---|---|---|---|
| O1 | `F.Fuzz` allows only `[]byte, string, bool, byte, rune, float32, float64, int*, uint*`; "should be fast and deterministic"; seed corpus = `F.Add` + `testdata/fuzz/<FuzzName>`; corpus files `go test fuzz v1` with one typed literal per line; 1 s per-execution timeout; `-fuzzminimizetime` 60 s default | S36, S37 | primitives and flat tuples of primitives | no structs, no custom mutator (proposal #48815 open since 2021, S39) | high |
| O2 | Workarounds and their costs per the Go design doc: seed-as-PRNG → corpus stores the seed not the structure and generator code gets instrumented (slowdown + false positives); decode `[]byte` → "most random bytes don't form a valid structure" | S39 design | – | agent must accept one of these costs or use rapid | high |
| O3 | `rapid.MakeFuzz(func(t *rapid.T){…})` returns `func(*testing.T, []byte)` for `f.Fuzz`; in fuzz mode the property runs once per input (no shrink); invalid data → `SkipNow`; generators (`SliceOf`, `Custom`, …) and state machines (`t.Repeat`, `StateMachineActions`, `Check` invariant) | S44 | Go, typed and stateful inputs | shrinking only under `rapid.Check`, not under `go test -fuzz`; the rapid corpus bytes are generator-version-specific (same caveat as Y4; UNVERIFIED for rapid) | high |
| O4 | go-fuzz-headers `NewConsumer(data).GenerateStruct(&p)` fills nested structs; "most APIs are added as they are needed"; designed for go-fuzz, std-lib "will also be supported"; go-118-fuzz-build uses it to build typed args for OSS-Fuzz-style libFuzzer builds | S40, S41 | Go structs, OSS-Fuzz | unexported fields skipped unless allowed; behaviour on exhaustion undocumented; go-fuzz-utils alternative returns error when data too small (S42) | medium |
| O5 | `file2fuzz` converts raw files to `go test fuzz v1` + `[]byte(...)` corpus entries | S38 | importing upstream corpora (e.g. S45) | – | high |

Cost: lowest of all families (a derive, a strategy, a consumer). Needs from target: a constructor path for the value; deterministic behaviour; for Go, tolerance of instrumented generator code.

### 3.4 (c) Custom mutators

| # | Claim | Source | Validity region | Failure modes | Confidence |
|---|---|---|---|---|---|
| M1 | libFuzzer custom mutator pattern: parse input → mutate representation (optionally with `LLVMFuzzerMutate`) → serialise; on parse failure return a valid dummy input; "every input reaching the target is valid" | S1 §Compression | formats with a reversible parse/serialise pair | mutator bugs become fuzzer bugs; must keep output ≤ max_size (S19) | high |
| M2 | Rust `fuzz_mutator!(|data, size, max_size, seed|)` with `libfuzzer_sys::fuzzer_mutate`; "`max_size < size` is possible when shrinking test cases"; `fuzz_crossover!` optional | S19, S18 | Rust/libFuzzer | – | high |
| M3 | Python: Atheris `custom_mutator=` + `atheris.Mutate` (zlib example) | S35 | Python/libFuzzer | – | high |
| M4 | AFL++: `afl_custom_fuzz`, `post_process` ("write the test case in the format expected by the target" — the AFL docs name checksums as the use case, S48 §4k), `havoc_mutation`, `queue_get`, trim hooks ("Generic trimming can break structured formats"), `AFL_CUSTOM_MUTATOR_ONLY`, Python modules via `AFL_PYTHON_MODULE` | S47, S48 | AFL++-driven targets | if `post_process` is custom you must call it yourself after trimming | high |
| M5 | libprotobuf-mutator: `DEFINE_PROTO_FUZZER(const Msg&)`; "field mutation logic is very basic"; `PostProcessor` "to keep values that the target needs, such as consistency constraints or checksums", callbacks "should be deterministic and avoid modifying good messages"; protobuf as intermediate format for `Foo` ("a subset of a superset of Foo"); reverse converter matters when an existing `Foo` corpus exists | S1 §§ Protocol Buffers, Intermediate Format, SQLite; S46 | C++ targets; any target reachable from a protobuf model | extensions not mutated; UTF-8 differences proto2/proto3 | high |
| M6 | When a mutator beats a generator: (i) an existing real corpus must be reused as-is (seeds stay valid files; S3 FDP caveat inverted); (ii) early-time coverage matters (S21 1.47× at 5 min); (iii) format is binary with integrity fields where repairing is easier than generating. When a generator beats a mutator: (i) no parser/serialiser pair exists; (ii) the type system already encodes validity (R1); (iii) long campaigns (S21 ≈1.01× at 24 h) | S21, S18, S3, S1 | – | fitzgen result is one target | medium |

Cost: a parser + serialiser + mutation logic per format (S1: "substantial manual work"). Needs from target: a reversible representation; engine hook support (libFuzzer/AFL++; **Go has none**, S39).

### 3.5 (d) Format-aware and protocol/stateful fuzzing

| # | Claim | Source | Validity region | Failure modes | Confidence |
|---|---|---|---|---|---|
| F1 | Fix-after-mutate hooks: `post_process` (AFL++), `PostProcessor` (LPM), grammar `post` repair (S6) — recompute checksums/lengths after structural mutation | S47, S46, S6 | checksummed or length-prefixed formats | repair must be deterministic (S46) | high |
| F2 | Chunk-aware greybox (AFLSmart): Peach-pit "virtual file structure", higher-order mutations on chunks, validity-based power schedule; fuzzingbook reproduces the schedule (energy ∝ parsable fraction × log length) | S52, S7 §Focusing on Valid Seeds | binary container formats with a Peach model | Peach dependency; model per format | high |
| F3 | Stateful APIs = traces: byte-per-call (gRPC) "works with any mutation engine" but "not human-readable and brittle"; protobuf action traces (Envoy) "a bit slower and a bit more complicated" but more maintainable; Chrome IPC message design came from manual code review | S1 §Fuzzing Stateful APIs | any API with state | trace ops referencing indices must tolerate invalid indices (S18 allocator example only frees live allocations) | high |
| F4 | Network protocols: AFLNet seeds are recorded pcap exchanges split into messages; state inferred from response codes; without `-E` no state guidance; needs `-K`/cleanup for servers that don't exit; nondeterminism (session IDs) must be patched | S53 | servers with observable response codes | heavy setup; false negatives from early SIGTERM | high |
| F5 | Model-based testing: Hypothesis `RuleBasedStateMachine` (rules with strategies/Bundles, `@precondition`, `@invariant`, prints "a very short program" to reproduce; `stateful_step_count=50`, preconditions can't read bundles); proptest `ReferenceStateMachine`/`StateMachineTest` with three shrink passes (delete tail transitions, shrink each, shrink init state; preconditions re-checked); rapid `Repeat` + `StateMachineActions` with `Check` after every action | S24, S26, S23, S44 | APIs with a cheap reference model | sequential only (proptest); heavier than plain property tests; Go: no shrinking under native fuzzer | high |
| F6 | API-level grammar fuzzing "can be much faster than fuzzing at the system level" but "brings the risk of false alarms by violating implicit preconditions" | S12 Lessons Learned | library APIs | need precondition modelling (preconditions/Bundles) | high |
| F7 | Web/API contracts: form grammars mined from HTML (GET forms only, subset of elements); OpenAPI-driven fuzzing with stateful links | S14, S32 | HTTP services with a schema | real side effects; non-ASCII decoding issue noted in S14 | medium |

### 3.6 (e) Seeds from real data

| # | Claim | Source | Validity region | Failure modes | Confidence |
|---|---|---|---|---|---|
| E1 | Carving: record calls during system tests and replay; "orders of magnitude faster"; from carved calls "one can produce API grammars that arbitrarily combine carved arguments"; hard where functions "heavily interact with their environment and/or access external resources" | S13 | unit-level targets reachable from existing system tests (Python tracing in the book; Elbaum 2006 for Java) | pickling cannot recreate external resources; recombination may violate preconditions → false alarms | high |
| E2 | Seeds from past failures: "inputs that are known to have caused failures before" as seeds; LangFuzz used CVE JavaScript as seeds and still found new bugs | S7 §Mining Seeds | any project with a bug tracker / regression tests | – | high |
| E3 | Where to collect: "reported bugs, test suites, random downloads from the internet, unit test case data"; or patch the target to dump inputs it receives; Go tutorial reuses unit-test inputs via `f.Add` | S48 §2a, S37 tutorial | – | licence hygiene for downloaded corpora (S57: "corpus has an appropriate and consistent license") | high |
| E4 | Upstream corpora: dvyukov/go-fuzz-corpus has ~90 format directories (json, png, gzip, tls, x509, elf, …); OSS-Fuzz ships `<target>_seed_corpus.zip` per target | S45, S57 | Go std-lib-like formats; OSS-Fuzz projects | go-fuzz-corpus has no provenance notes; needs `file2fuzz` for native Go (S38) | medium |
| E5 | Deduplicate/minimise: `afl-cmin` ("highly recommended"), `afl-tmin` (optional, slow), libFuzzer `-merge=1` (only inputs that add coverage), `cargo fuzz cmin`; AFL: "Use multiple test cases only if they are functionally different" | S48 §2b–c, S4 §Corpus, S20, S49 | all engines except Go native (no cmin; UNVERIFIED whether Go dedupes its cached corpus by coverage) | – | high |
| E6 | Synthesise seeds from the grammar when no real data exists: `GrammarCoverageFuzzer` (one per expansion), Grammar-Mutator `grammar_generator <max_num> <max_size>` writes seeds + trees | S11, S50 | grammar available | semantic validity still needs repair hooks (G3) | medium |

### 3.7 Shrinking / minimisation of structured inputs

| # | Claim | Source | Validity region | Failure modes | Confidence |
|---|---|---|---|---|---|
| H1 | Character-level delta debugging on syntactic inputs: "not aware of these constraints" — with a parser-gated runner none of ddmin's reductions produced a valid input; grammar-based reduction needs "a handful of tests" vs "orders of magnitude more"; lineage: Zeller 2002 → HDD 2006 → Perses 2018 | S15 | any grammar input | needs a grammar/parser for the input | high |
| H2 | Engine minimisers are byte-level: libFuzzer `-minimize_crash=1` "minimizes the provided crash input"; `cargo fuzz tmin` minimises the file; `afl-tmin` keeps "exactly the same execution path"; Go `-fuzzminimizetime` | S4, S20, S49, S37 | opaque byte inputs | on `arbitrary`/FDP-decoded inputs the decoded structure changes unpredictably; on checksummed formats almost every candidate is invalid | high |
| H3 | Integrated (generator-internal) shrinking: "You can guarantee that shrinking satisfies the same invariants as generation"; type-based shrinking can turn one failure into another ("shrinkers are fuzzers"); Hypothesis shrinks the byte stream under shortlex ("Shorter is always simpler", then lexicographic) | S28 (2016-12-05, 2016-12-10) | Hypothesis, proptest, rapid, (Zest lineage) | properties that hold only with high probability may not survive shrinking (distribution changes) | high |
| H4 | MacIver & Donaldson 2020: internal reduction of the choice sequence "largely sidesteps the test-case validity problem"; evaluation vs C-Reduce/ddmin; a scaling problem is noted | S34 (abstract) | – | details UNVERIFIED (PDF blocked) | medium |
| H5 | proptest: `ValueTree.simplify/complicate` binary search; "never shrinks a value to something outside the range the strategy describes"; strings still match their regex after shrinking; "Encountering a filter rejection during shrinking prevents shrinking from continuing"; vs QuickCheck type-based: "generation and shrinking may lead to a lot of input rejections"; proptest "up to an order of magnitude slower" | S23 | Rust property tests | `prop_filter` and `prop_flat_map` degrade shrinking; use `prop_map` | high |
| H6 | State-machine shrinking: proptest deletes tail transitions, shrinks each transition, then the initial state, re-checking preconditions; Hypothesis prints the minimal rule program | S23, S24 | stateful tests | – | high |
| H7 | Rust `arbitrary` has no shrinking; Go native has only byte minimisation; rapid shrinks only under `rapid.Check` | S17, S37, S44 | – | mitigation: replay the crashing bytes through a proptest/`rapid.Check`/Hypothesis twin of the same generator to obtain a minimal structured case | high |

### 3.8 Seed-corpus construction guidance (cross-cutting)

| # | Claim | Source | Confidence |
|---|---|---|---|
| C1 | "seeded with a varied collection of valid and invalid inputs"; works without seeds "but will be less efficient" | S4 §Corpus | high (2019 text) |
| C2 | Seeds should "cover large portions of the API under test, ideally achieving 100% coverage"; "Avoid large seed inputs when smaller inputs are sufficient"; no count given; extend when fixing bugs | S2 §Seed corpus | high |
| C3 | "The ideal corpus is a minimal set of inputs that provides maximal code coverage"; "regularly extended with the inputs that (used to) trigger bugs"; dictionaries "can have a dramatic impact" and "should be maintained alongside the fuzz target" | S57 ideal_integration | high |
| C4 | "Keep the files small. Under 1 kB is ideal"; only functionally different files; `afl-cmin` to pick a distinct subset; file size "has a dramatic impact on fuzzing performance" | S49 | high |
| C5 | Minimised corpora outperform singleton, empty and thousand-file corpora (33 CPU-years, 6 selection approaches; OptiMin MaxSAT minimiser now in AFL++ `utils/optimin`) | S55 (abstract) | medium |
| C6 | Dictionaries for keyword formats (`-dict`/`-x`, AFL++ LTO autodictionary, `AFL_LLVM_DICT2FILE`); AFL auto-extracts tokens from comparisons | S4, S48, S49 | high |
| C7 | Boundary values: AFL deterministic stage inserts "known interesting integers (0, 1, INT_MAX, etc)"; Hypothesis `integers()` weights bounds and near-bounds for ranges wider than 127 and shrinks toward zero; `floats()` include NaN/inf/subnormals unless bounded | S49 technical_details, S25 | high |
| C8 | Determinism and speed prerequisites: ~1000 exec/s typical, <10 exec/s "doing something wrong"; no `rand()`; Go 1 s timeout | S2, S36/S37 | high |
| C9 | FDP/arbitrary-encoded corpora "will no longer be valid image files" — so keep two corpora or add a reverse converter when real files must be reused | S3, S1 | high |

## 4. Disagreements and open questions

1. **Generation vs structure-aware mutation.** The rust-fuzz book (S18) and fitzgen's experiment (S21) say mutation wins; but the effect is 1.47× at 5 min and 1.01× at 24 h on one target, measured by the maintainer of both approaches. Zest (S54) and Hypothesis (S28) argue the opposite framing: mutate the *parameters* behind a generator and you get both validity and coverage guidance. The libFuzzer structure-aware doc (S1) treats generation from protobuf + LPM mutation as one combined technique. **Resolution for the agent**: default to generator-over-bytes (cheapest, portable to all three languages, implicit parametric mutation); add a custom mutator only when an existing real corpus must be reused as-is or early coverage matters.
2. **Seed corpus size.** AFL/libFuzzer/OSS-Fuzz say "small, distinct, maximal coverage" without a number; Herrera et al. say minimised corpora beat both empty and large (S55); Klees et al. reportedly found an empty seed sometimes competitive (S56, UNVERIFIED). Nobody gives a count. **Open**: a per-format heuristic (one seed per grammar alternative / format feature, then cmin) is defensible but unmeasured.
3. **Valid vs invalid seeds.** libFuzzer: "valid and invalid" (S4). fuzzingbook: start from valid seeds; invalid ones mostly exercise input handling (S16) — but note the goal: *slightly* invalid inputs probe the parser's error paths (S5). AFLSmart spends energy proportional to validity (S52). **Resolution**: majority valid; include a few minimally invalid variants (one field off) deliberately, not random garbage.
4. **Disable the check vs repair the check.** libFuzzer/AFL++ recommend a fuzz-build flag that skips CRCs (S4, S48); fuzzingbook/LPM recommend repair hooks (S6, S46). Flag is cheaper but the resulting corpus does not reproduce on production builds and may hide bugs in the checksum code itself. **Open**: no source quantifies the coverage lost either way.
5. **Hypothesis `fuzz_one_input` corpus stability.** The byte encoding is version- and strategy-specific (S27); rapid's `MakeFuzz` and `arbitrary`'s derive have the same property in principle (UNVERIFIED for rapid). Corpora built this way are not durable assets the way raw-format corpora are.
6. **Go**: whether `go test -fuzz` deduplicates the cached corpus by coverage, and whether go-fuzz-headers behaves deterministically on data exhaustion, could not be verified from the docs read.
7. **Grammar coverage → code coverage correlation** (S11) and the ddmin-vs-grammar test counts (S15) are asserted in prose but the numeric outputs were not in the sources available.

## 5. Implications for the agent / skills

### 5.1 Decision table by input shape (H1, H3)

| Input shape of the target | Technique | Seed source | Mutation/engine | Shrinking plan |
|---|---|---|---|---|
| Opaque bytes (hash, cipher, decompressor *input*, image decoder with CRC disabled) | plain bytes | real files, upstream corpora (S45), `-merge`/cmin | engine default + dictionary | engine tmin fine |
| Text with keywords (config, SQL, URL, log lines) | grammar or regex strategy + dictionary | grammar-coverage outputs + real samples | engine bytes + dict; or tree mutation (S7/S50) | grammar reducer / Hypothesis |
| Binary format with magic/length/CRC | fuzz-build flag **or** custom mutator with repair (`post_process`/LPM-style) | real files (keep them valid) | custom mutator; otherwise generator (loses real-file corpus, S3) | engine tmin only if repair hook also runs on reproduction |
| Typed value / struct / API argument tuple | `arbitrary` derive / Hypothesis `builds`+`composite` / rapid generators / go-fuzz-headers | `f.Add`/`@example`/seed files produced by the generator | engine bytes through the generator | proptest / Hypothesis / `rapid.Check` twin |
| Sequence of operations (stateful API, protocol client) | `Vec<Op>` / `RuleBasedStateMachine` / `t.Repeat` | one trace per public method + recorded traces (pcap/carving) | parametric; AFLNet for real servers | state-machine shrinking (S23/S24); none in Go fuzz mode |
| External schema (JSON Schema, OpenAPI, protobuf IDL) | `hypothesis-jsonschema`, Schemathesis, LPM/protobuf-as-IR | schema-generated + fixtures | generator | integrated |
| Compressed / encrypted wrapper | custom mutator (decompress → mutate → recompress) or fuzz the inner layer directly | decompressed samples | custom mutator | tmin on inner payload |

Gate (H1): if the target rejects >~90 % of engine mutants at the first check (measure with a counter during a 1-minute dry run) and the shape is one of the last four rows, plain byte fuzzing is the wrong tool; the agent must switch rows, not run longer.

### 5.2 Seed-corpus checklist (H2, H3)

1. Collect: unit-test fixtures, regression inputs for past bugs (S7, S48), upstream corpora (S45, S57 zips), recorded traffic/calls (S53, S13). Record provenance and licence (S57).
2. Synthesise when thin: one input per grammar alternative / enum variant / message type (S11, S50); for typed generators, emit a handful of explicit `f.Add`/`@example` values incl. boundary values (0, 1, max, empty, max-length, NaN/inf where allowed; S25, S49).
3. Mix: mostly valid; add a few *one-field-invalid* variants on purpose (S4, S5); never random garbage as seeds.
4. Size: keep each seed small (AFL "under 1 kB ideal", S49), split big APIs into several targets (S2 >20–30k edges).
5. Dedupe: `afl-cmin` / `-merge=1` / `cargo fuzz cmin`; keep only functionally distinct files (S48, S49). Go: no tool; rely on `go test -fuzz` cache plus manual curation.
6. Check discoverability: the target must gain coverage from an empty corpus too (S2); if not, fix the harness (flag, mutator) rather than piling on seeds.
7. Maintain: add every crash/bug input back to seeds; keep the dictionary next to the target (S57).
8. Stopping input to H2: when `-merge`/cmin adds nothing new from a fresh run and the seed-synthesis list (step 2) is exhausted, the corpus is saturated for this harness; move to another shape row or target.

### 5.3 Per-language mapping (H3, H5)

**Rust** — generator by construction; mutator when a real corpus exists.
```rust
// fuzz/fuzz_targets/ops.rs  (libfuzzer-sys + arbitrary derive, S18/S19)
#![no_main]
use arbitrary::Arbitrary;
#[derive(Arbitrary, Debug)]
enum Op { Insert { k: u16, v: u8 }, Remove { k: u16 }, Clear }
libfuzzer_sys::fuzz_target!(|ops: Vec<Op>| {
    let mut sut = mylib::Map::new();
    let mut model = std::collections::BTreeMap::new();
    for op in ops { match op {
        Op::Insert { k, v } => { sut.insert(k, v); model.insert(k, v); }
        Op::Remove { k }    => { sut.remove(k);    model.remove(&k); }
        Op::Clear           => { sut.clear();      model.clear(); } }
        assert_eq!(sut.len(), model.len()); }
});
```
Limits: no shrinking (R5) — pair with a `proptest` state-machine twin for minimal repros; short inputs collapse to `Vec![]`/lower bounds (R2); derive does not know type invariants (use `#[arbitrary(with=…)]`). Corpus: `fuzz/corpus/<target>`, `cargo fuzz fmt` to read a case (S20). `cargo fuzz cmin` for dedupe; `-- -dict=` for keywords (S4).

**Python** — Hypothesis strategies are the structure; Atheris is the engine.
```python
# fuzz_json.py  (S27 pattern)
import json, sys, atheris
from hypothesis import given, strategies as st
json_val = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False) | st.text(),
    lambda j: st.lists(j) | st.dictionaries(st.text(), j), max_leaves=50)
@given(json_val)
def test_roundtrip(v):
    assert json.loads(json.dumps(v)) == v
atheris.Setup(sys.argv, test_roundtrip.hypothesis.fuzz_one_input)
atheris.Fuzz()
```
Limits: corpus bytes tied to the Hypothesis version/strategy (Y4); no shrinking inside Atheris — run `pytest` afterwards to shrink/dedupe from `.hypothesis/examples` (S26/S27); health checks skipped; pure-Python targets: HypoFuzz (S33) or plain `@given` first. For flat parameter tuples with no invariants, `FuzzedDataProvider` is enough (Y5). Stateful: `RuleBasedStateMachine` (S24).

**Go** — decode bytes through a generator; accept the costs the design doc names.
```go
// map_fuzz_test.go  (rapid.MakeFuzz, S44)
func FuzzMap(f *testing.F) {
    f.Add([]byte{})                       // seeds are raw generator bytes
    f.Fuzz(rapid.MakeFuzz(func(t *rapid.T) {
        m := NewMap(); model := map[uint16]uint8{}
        t.Repeat(map[string]func(*rapid.T){
            "insert": func(t *rapid.T) { k := rapid.Uint16().Draw(t, "k"); v := rapid.Uint8().Draw(t, "v"); m.Insert(k, v); model[k] = v },
            "remove": func(t *rapid.T) { k := rapid.Uint16().Draw(t, "k"); m.Remove(k); delete(model, k) },
            "":       func(t *rapid.T) { if m.Len() != len(model) { t.Fatalf("len %d != %d", m.Len(), len(model)) } },
        })
    }))
}
```
Limits: `testing.F` basic types only (O1); generator code is instrumented and corpus entries are opaque bytes (O2); no shrinking under `-fuzz` — re-run as `rapid.Check` to minimise (O3); 1 s/exec timeout. Alternatives: go-fuzz-headers `GenerateStruct` for plain structs (O4); `file2fuzz` to import raw corpora (O5). For primitive inputs, stay with typed `f.Fuzz(func(t *testing.T, s string, n int))` and `f.Add` boundary values — that is the idiomatic, shrinkable path.

### 5.4 Skills to write (names indicative)

| Skill | Content | Hypotheses |
|---|---|---|
| `input-shape-triage` | the §5.1 table; the 90 %-rejection dry-run gate; "do not byte-fuzz" rule for typed/sequence/schema shapes | H1, H3 |
| `seed-corpus-builder` | §5.2 checklist; per-engine dedupe commands; corpus file conventions (`testdata/fuzz`, `fuzz/corpus`, `_seed_corpus.zip`); licence note | H2, H3, H5 |
| `grammar-and-repair` | CFG + pre/post/order repair pattern (S6); Lark/`from_lark`; grammar-coverage seed synthesis; tree mutation references | H3 |
| `typed-generators-{rust,python,go}` | snippets above; exhaustion semantics; `with=`/`composite`/`Custom`; stateful trace pattern | H3, H5 |
| `custom-mutator` | parse→mutate→serialise template for libFuzzer/Atheris/AFL++; when it beats a generator (M6); `post_process` for checksums; reverse converter for existing corpora | H3 |
| `structured-shrinking` | why tmin breaks structure (H1–H2 rows); twin-test pattern (H7); proptest/Hypothesis shrink caveats (filter) | H5 |

## 6. Candidate eval cases

| # | Input the agent sees | Expected behaviour |
|---|---|---|
| 1 | Rust crate `fn decode(&[u8]) -> Result<Png, E>` with CRC verification; `fuzz/corpus` empty | Pick row 3: add `#[cfg(not(fuzzing))]` around CRC check *or* a `fuzz_mutator!` that recomputes CRCs; seed with ≥1 real PNG per chunk type; add dict of chunk names; justify not using `arbitrary` (would lose the real-file corpus, S3) |
| 2 | Python `parse_config(text: str)` with a documented EBNF | `from_lark` or `from_regex` strategy + `.map` repairs; seeds = one input per rule alternative + fixtures; Atheris via `fuzz_one_input` only if a C extension is involved, else `@given`/HypoFuzz |
| 3 | Go `func Reverse(s string) (string, error)` | **Do not** build structured machinery: typed `f.Fuzz(func(t, s string))`, `f.Add` unit-test strings incl. multi-byte runes (S37); round-trip + UTF-8 property |
| 4 | Go `type Request struct{...}` consumed by a handler; user asks for "fuzzing" | Explain `testing.F` limit (S36/S39); offer `rapid.MakeFuzz` or go-fuzz-headers; state the costs (instrumented generator, opaque corpus, no shrink in fuzz mode); provide `rapid.Check` twin |
| 5 | Rust `struct Session` with `open/write/close` methods | `Vec<Op>` trace target with index-safe ops (S18 allocator pattern) + proptest state machine for shrinking; seeds: one trace per method and the documented happy path |
| 6 | Dry run shows 99.7 % of mutants rejected at `if magic != 0xCAFE` | Stop plain fuzzing; add magic to dictionary and seeds; if still rejected at CRC, move to row 3; do not extend the time budget |
| 7 | Target is a gzip *decompressor*; user asks for a grammar | Opaque-bytes row: real compressed files + engine mutation; no grammar; (for the *compressor* side a custom mutator would be wrong too — plain bytes) |
| 8 | Existing 5 000-file upstream corpus for a JSON parser | Run cmin/`-merge=1` first; expect a far smaller set (S55); keep provenance; add bug-regression inputs |
| 9 | Hypothesis-based Atheris target after a Hypothesis upgrade shows coverage drop | Recognise corpus byte-encoding invalidation (S27); rebuild corpus; keep raw-format seeds separately |
| 10 | Server speaking a request/response protocol over TCP | Prefer in-process API-trace target (row 5) if the handler can be called directly; AFLNet only for black-box binaries, with pcap seeds and nondeterminism patched (S53) |
| 11 | Crash found with `arbitrary` input, user asks for a minimal repro | Do not rely on `cargo fuzz tmin` output as "minimal"; replay through proptest twin or hand-reduce using `cargo fuzz fmt` (S20) |
| 12 | Python function with a `@dataclass` argument that has an invariant `start <= end` | `composite` (draw two, sort) not `builds`+`filter` (S28 2016-05-11); seeds include equal dates; no Atheris unless C code |

## 7. Micro-examples

1. **Generate-then-repair beats generate-then-reject (fuzzingbook, S6 §"Example: Checksums")**: the credit-card grammar attaches `opts(post=lambda cc: fix_luhn_checksum(cc))` to the `<credit-card-number>` expansion; the chapter notes that filtering with `valid_luhn_checksum` costs "on average … 10 attempts" per number while repair means "each number is generated only once and then repaired. This is very efficient." Same pattern: libprotobuf-mutator `PostProcessor` (S46) and AFL++ `post_process` (S47/S48).
2. **Custom mutator for a compressed wrapper (Atheris, S35 `example_fuzzers/custom_mutator_example.py`)**:
   ```python
   def CustomMutator(data, max_size, seed):
       try: dec = zlib.decompress(data)
       except zlib.error: dec = b'Hi'
       else: dec = atheris.Mutate(dec, len(dec))
       return zlib.compress(dec)
   atheris.Setup(sys.argv, TestOneInput, custom_mutator=CustomMutator)
   ```
   This is the Python form of the libFuzzer compression example (S1 §"Example: Compression"); the Rust form is `fuzz_mutator!` with `fuzzer_mutate` over the decompressed buffer (S18).
3. **Typed trace input in Rust (rust-fuzz book, S18)**: `#[derive(Arbitrary, Debug)] enum AllocatorMethod { Malloc{size: usize}, Free{index: usize}, Realloc{index: usize, new_size: usize} }` with `fuzz_target!(|methods: Vec<AllocatorMethod>| …)`; index ops act only on live allocations and all remaining allocations are freed at the end — the recipe for stateful APIs without a protocol parser.
4. **Hypothesis as the structure layer for Atheris (S27)**: a `@given(st.recursive(...))` JSON test registered via `atheris.Setup(sys.argv, test.hypothesis.fuzz_one_input)`; the docs state that producing valid JSON "based only on Atheris' FuzzDataProvider interface would be considerably more difficult" — and that failures are shrunk/deduped later by running the test suite, since `fuzz_one_input` writes failing buffers to the example database.
5. **Why byte-level reduction fails on structure (fuzzingbook, S15)**: with a runner that returns UNRESOLVED for unparseable expressions, delta debugging on `x = 1 + 2 * 3 / 0`-style inputs produced *no* valid reductions ("not aware of these constraints"), while the grammar-based reducer (replace subtree with smaller subtree of the same symbol / alternative expansion) needed "a handful of tests". Hypothesis/proptest avoid the problem by shrinking the choice sequence instead of the output (S28, S23: "never shrinks a value to something outside the range the strategy describes").
