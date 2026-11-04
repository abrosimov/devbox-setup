---
note_id: "20261103150201"
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
aliases: ["Applicability gate"]
tags: [fuzzing, design/finding, h1]
addresses: ["[[H1-no-applicability-gate]]"]
grounded_in: ["[[01-methods-and-applicability|R1]]", "[[04-fuzzingbook-part1-lexical|R4]]", "[[06-fuzzingbook-parts3-5|R6]]", "[[07-lang-go|R7]]", "[[08-lang-python|R8]]", "[[09-lang-rust|R9]]"]
realised_by: ["[[skill-fuzzing-applicability]]", "[[agent-procedure]]"]
tested_by: ["[[eval-family-A-gate]]"]
decided_by: ["[[FTW-D-001-gate-is-first-step]]"]
related: ["[[oracle-ladder]]", "[[input-shape-triage]]"]
opens: ["[[FTW-OQ-007-per-language-yield-statistics]]"]
---
# Applicability gate

Evaluate top to bottom; the first "do not fuzz" row that matches wins. Every per-language annex
agrees on every row (R1 §5.1; R4 §5.1; R6 §5.4; R7 §5.4; R8 §5.1; R9 §5.3).

## Hard stops

| Target characteristic | Recommendation | Evidence |
|---|---|---|
| Behaviour depends on network, database, external process, wall clock, unseeded randomness, environment, or writes to disk | **Do not fuzz as is.** Extract the pure core (parser, validator, state machine) and gate again. | determinism contract (R1 S1, S7); OSS-Fuzz runtime (R1 S27f); AFL++ "no direct support for network services" (R1 S30) |
| Persistent threads or goroutines outliving one call; mutable global state the target cannot reset | **Do not fuzz** until refactored. | "results will be unreliable" (R1 S7); stability < 90 % (R2 P11) |
| One execution slower than ≈100 ms after hoisting setup | **Do not fuzz**; property test with a small budget if a property exists. | <10 exec/s "probably doing something wrong" (R1 S1); Go kills at 1 s (R7 §3.1) |
| GUI/CLI glue, orchestration, configuration wiring, developer-constant inputs | **Do not fuzz.** Pairwise option testing for flag sets (`C(n,2)`), unit tests otherwise. | R1 S30b; R6 §5.4 (30 options → 435 pairs) |
| Thin wrapper over an upstream-fuzzed library (stdlib JSON/XML/URL/regexp, `serde` derive, `json.loads`) with no own transformation | **Do not fuzz the wrapper**; property-test the mapping if it has one. | "all errors found are already fixed" (R4 §5.1); shallow target (R1 S1) |
| Contract permits panics (`Must*`, `unwrap` on programmer error, precondition asserts) | **Do not fuzz that entry**; fuzz the non-panicking variant or encode the precondition in the generator. | ngolo-fuzzing had to exclude `regexp.MustCompile` (R1 S17) |
| Memory-safe total function, no resource amplification, no oracle beyond crash | **Unit tests suffice.** | crash-oracle bug set is empty for such code (R1 §3.9, inference) |
| Finite enumerable domain (three enum arguments, seven weekdays) | **Exhaustive table test.** | R6 §5.4; R7 E3 |

## Fuzz or property-test

| Target characteristic | Method | Oracles |
|---|---|---|
| Untrusted raw bytes: decoders, decompressors, archive/image/font parsers, wire frames | coverage-guided greybox on bytes; real files as seeds; dictionary for tokens | crash + timeout + allocation bound + round trip where an encoder exists |
| Structured text: JSON-like, YAML/TOML, URLs, regexes, templates, DSLs, headers | greybox + seeds + dictionary; grammar or typed generation only if <50 % of the corpus passes validation after the first run ([[input-shape-triage]]) | round trip, differential versus a reference, "never panics, returns error" |
| Typed API over ints/floats/strings/structs/enums | property-based test first (Hypothesis, proptest, rapid); bridge into the engine only on hot untrusted paths | invariant, postcondition, metamorphic, model-based ([[oracle-ladder]]) |
| Numeric or algorithmic code | property test with metamorphic and differential oracles | never crash-only |
| Stateful API (containers, caches, protocol state machines, in-memory clients) | model-based state machine (`proptest-state-machine`, `RuleBasedStateMachine`, rapid `T.Repeat`), or an enum-of-operations trace under the coverage engine for long sequences | model equality + invariants after every transition |
| `unsafe`, cgo/FFI, C extensions | greybox with ASan (UBSan too for Python native); the harness touches every returned reference | sanitizer + crash |
| Two implementations of one specification | differential fuzzing; confirm the spec defines all behaviours first | normalised equality |

## Preconditions every "fuzz" row assumes

1. Determinism (RNG and clock injectable). 2. Speed ≥ ~100 exec/s after init hoisting. 3. Isolation
(no network/DB/FS writes; reads only in one-time init). 4. An oracle named from the
[[oracle-ladder]]. 5. A contract statement: "never panics; returns error on invalid input" or "may
panic on precondition X". 6. Seeds that pass validation; dictionary if the format has tokens. 7. One
format or API family per target; split above 20–30 k reachable edges (R1 S1).

## Design consequence

The gate is step 1 of [[agent-procedure]] and the body of [[skill-fuzzing-applicability]]. Its
output is one line — `fuzz(method, oracle)` / `property-test` / `unit-test` / `do-not-fuzz` — with
the matching row quoted, so [[eval-family-A-gate]] can grade it deterministically.
