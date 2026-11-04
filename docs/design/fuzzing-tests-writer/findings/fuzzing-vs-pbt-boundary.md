---
note_id: "20261104100003"
created: 2026-11-04
language: en
type: design
subtype: finding
note_role: artifact
artifact_kind: finding
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Fuzzing versus PBT boundary", "Fuzzing vs property-based testing"]
tags: [fuzzing, design/finding, h1, h3, lang/go, lang/python, lang/rust]
addresses: ["[[H1-no-applicability-gate]]", "[[H3-random-seeds-for-structured-input]]"]
grounded_in: ["[[01-methods-and-applicability|R1]]", "[[03-structure-aware-generation|R3]]", "[[07-lang-go|R7]]", "[[08-lang-python|R8]]", "[[09-lang-rust|R9]]"]
realised_by: ["[[skill-fuzzing-applicability]]", "[[skill-go-fuzzing]]", "[[skill-python-fuzzing]]", "[[skill-rust-fuzzing]]"]
tested_by: ["[[eval-family-A-gate]]", "[[eval-family-C-structure]]"]
decided_by: ["[[FTW-D-008-pbt-out-of-scope]]"]
related: ["[[applicability-gate]]", "[[input-shape-triage]]", "[[pbt-agent-prompts]]"]
---
# Fuzzing versus property-based testing — the boundary this agent keeps

The two approaches overlap in tooling and are routinely conflated. This agent does **fuzzing**;
property-based testing (PBT) is a separate track with its own agent and skills
([[FTW-D-008-pbt-out-of-scope]]). The boundary below says what each is, where they share
mechanisms, and which parts of which tools this agent may use.

## Definitions the agent works with

| | Fuzzing (this agent) | Property-based testing (other track) |
|---|---|---|
| Search space | a byte string (or a small tuple of primitives) that the engine **mutates** | a typed domain described by a **generator/strategy**; values are drawn, not mutated |
| Feedback | coverage instrumentation decides which inputs are kept (greybox); the corpus grows | none by default; each example is independent; budget is a count (`max_examples`, `cases`, `checks`) |
| Termination | never by itself; a cap or a stopping decision ([[stopping-algorithm]]) | at the example count, at domain exhaustion, or on the first failure |
| Minimisation | engine minimiser on bytes (lexical) | integrated shrinking inside the generator (structure-preserving) |
| Regression form | corpus files replayed by the engine or the test runner | explicit examples (`@example`, `proptest-regressions` seeds, rapid failfile) |
| Typical oracle | crash, timeout, resource limit, plus round-trip/differential checks written in the target | a property stated over typed values (invariant, metamorphic, model-based) |
| Lives in | `testdata/fuzz`, `fuzz/`, `tests/fuzz/*_fuzzer.py`, CI fuzz job | the ordinary unit-test suite |
| Primary evidence | R1 §3.2, R2 §3.2, R7 §3.1, R9 §3.1 | R1 §3.4, R8 §3.1, R9 §3.4, R7 §3.5 (rapid) |

The gate therefore returns `out-of-scope: pbt-track` for typed APIs with algebraic laws, numeric
code with metamorphic relations, and stateful APIs needing a model — with the reason recorded in
the charter ([[fuzzing-charter]]) — instead of writing a property test. rapid's state machines,
`proptest-state-machine` and `RuleBasedStateMachine` are PBT and out of scope here, even though
they are excellent tools (R7 §3.5, R9 §3.4, R8 §3.1).

## Where the tools overlap, and what this agent may use

| Mechanism | Tradition it belongs to | In scope for this agent? | Why |
|---|---|---|---|
| **Go** `testing.F` / `go test -fuzz`, `f.Add`, `testdata/fuzz` | fuzzing | yes — the engine | R7 §3.1 |
| Go typed `f.Fuzz(func(t, s string, n int))` arguments | fuzzing (the engine still mutates a byte encoding of the tuple) | yes | R7 §3.1 |
| Go go-fuzz-headers `ConsumeFuzzer` / `GenerateStruct` | fuzzing-side decoder (built for go-fuzz/libFuzzer bytes) | yes, for structs from bytes | R7 §3.5 |
| Go `pgregory.net/rapid` generators, `rapid.Check`, `T.Repeat` state machines | PBT | **no** — PBT track | R7 §3.5; README: "lacks coverage-guided feedback and mutations" |
| Go `rapid.MakeFuzz(prop)` inside `f.Fuzz` | hybrid: PBT generator driven by the fuzz engine's bytes | only when a rapid property **already exists** in the repository and the charter names the fuzz engine's coverage guidance as the objective; the agent never writes the rapid property itself; corpus entries are opaque generator bytes and shrinking does not work under `-fuzz` | R7 §3.5, R3 §5.3 |
| Go `file2fuzz`, `go-fuzz-corpus` | fuzzing | yes (seeds) | R7 §3.5 |
| **Rust** `cargo fuzz`, `libfuzzer-sys`, `fuzz_target!`, `fuzz_mutator!`, `cmin`/`tmin`/`coverage` | fuzzing | yes | R9 §3.1 |
| Rust `arbitrary` crate (`#[derive(Arbitrary)]`, `Unstructured`) | fuzzing-side decoder ("produce well-typed, structured values from raw byte buffers", built for AFL/libFuzzer) | yes | R9 §3.2 A1 |
| Rust `proptest`, `proptest-state-machine`, `quickcheck` | PBT | **no** — PBT track | R9 §3.4 |
| Rust `proptest-arbitrary-interop` | bridge PBT ← fuzzing types | no (PBT side consumes it) | R9 P9 |
| Rust `bolero` | hybrid harness (runs one target as `#[test]` with 1 s random **and** under libFuzzer/AFL/honggfuzz) | yes, as a fuzz harness front-end when the repository already uses it or wants committed `__fuzz__` corpora; `with_type`/`TypeGenerator` properties as PBT are not written by this agent | R9 §3.3 |
| **Python** Atheris, `FuzzedDataProvider`, custom mutators, `-atheris_runs` | fuzzing | yes | R8 §3.2 |
| Python Hypothesis `@given`, strategies, `RuleBasedStateMachine`, `target()`, Ghostwriter | PBT | **no** — PBT track | R8 §3.1 |
| Python `test.hypothesis.fuzz_one_input` under Atheris | hybrid: existing Hypothesis test driven by libFuzzer bytes | only when the Hypothesis test already exists; the agent does not author strategies; corpus bytes are tied to the Hypothesis version; shrinking/dedup happen later in `pytest` | R8 §3.1 claim 22, R3 §5.3 |
| Python HypoFuzz | a coverage-guided **fuzzer** over existing Hypothesis tests | yes as an engine, with the precondition that the tests exist and the licence note; the agent does not write the tests | R8 §3.3 |
| Python schemathesis | PBT over an API schema | no — PBT/API-testing track | R8 §3.4 |
| libFuzzer / AFL++ / honggfuzz flags, dictionaries, `-merge`, `-minimize_crash` | fuzzing | yes | R2 §3.2 |

## Consequences for the other notes

- [[applicability-gate]]: the rows that used to say "property-based test first" now say
  `out-of-scope: pbt-track`; the agent hands off and records the reason.
- [[input-shape-triage]]: "generators over the byte stream" means **fuzzing-side decoders**
  (`arbitrary`, go-fuzz-headers, `FuzzedDataProvider`); PBT generators (Hypothesis strategies,
  rapid, proptest) are not a seed-construction technique for this agent except through the hybrid
  bridges above, under their stated conditions.
- [[oracle-ladder]]: round-trip, differential and invariant checks written *inside a fuzz target*
  are fuzzing; the same relations stated as a PBT property are not this agent's deliverable.
- Per-language skills carry only the fuzzing-side column plus the boundary table; the
  "property-based twin" material moves to the PBT track.
