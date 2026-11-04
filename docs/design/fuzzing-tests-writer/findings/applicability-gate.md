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
related: ["[[oracle-ladder]]", "[[input-shape-triage]]", "[[fuzzing-vs-pbt-boundary]]", "[[fuzzing-charter]]"]
opens: ["[[FTW-OQ-007-per-language-yield-statistics]]"]
---
# Applicability gate

## What the claim rests on

The gate is built from two kinds of evidence and one inference. **Sourced**: the engine contracts
(determinism, no persistent threads, ≥ ~100–1 000 exec/s, no network/disk/clock, bounded input,
one format per target — google/fuzzing `good-fuzz-target`, libFuzzer manual, AFL++ docs, Go fuzz
docs; R1 §3.2, §5.1) and the Fuzzing Book's lessons that random inputs "exercise mostly input
processing functionality" and that an already-fuzzed target returns nothing (R4 F1, M1, F9).
**Empirical record**: Go issue-tracker finds are almost all in `debug/*`, `archive/*`,
`encoding/*`, `image/*`, `net/*/html`, `regexp` (R7 §3.6); the Rust trophy case is dominated by
parsers, decoders and codecs (R9 §3.7); Python finds are in parsers and C extensions (R8 §3.2).
**Inference**: "fuzzing pays off on a narrow class of code" combines the two; no per-language
yield study exists ([[FTW-OQ-007-per-language-yield-statistics]]), so the gate states the
preconditions and the record, not a yield percentage.

Evaluate top to bottom; the first "do not fuzz" or "out of scope" row that matches wins. Every per-language annex
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

## Fuzz, or out of scope for this agent

Rows marked `out-of-scope: pbt-track` are handed to the property-based-testing track
([[fuzzing-vs-pbt-boundary]], [[FTW-D-008-pbt-out-of-scope]]); the agent records the reason in the
charter and writes nothing for them.

| Target characteristic | Method | Oracles |
|---|---|---|
| Untrusted raw bytes: decoders, decompressors, archive/image/font parsers, wire frames | coverage-guided greybox on bytes; real files as seeds; dictionary for tokens | crash + timeout + allocation bound + round trip where an encoder exists |
| Structured text: JSON-like, YAML/TOML, URLs, regexes, templates, DSLs, headers | greybox + seeds + dictionary; grammar or typed generation only if <50 % of the corpus passes validation after the first run ([[input-shape-triage]]) | round trip, differential versus a reference, "never panics, returns error" |
| Typed API over ints/floats/strings/structs/enums whose risk is a violated law (commutativity, identity, ordering) | `out-of-scope: pbt-track`. Fuzz only when the same API is reachable from untrusted bytes: then the fuzz target decodes the bytes with a fuzzing-side decoder (`arbitrary`, go-fuzz-headers, `FuzzedDataProvider`) and checks round trip or invariants inside the target. | round trip, invariants, resource limits ([[oracle-ladder]]) |
| Numeric or algorithmic code whose only oracle is a metamorphic relation | `out-of-scope: pbt-track`. Fuzz only when a reference implementation exists (differential target) or the input is a byte/text format. | differential; never crash-only |
| Stateful API (containers, caches, protocol state machines, in-memory clients) | Model-based state-machine testing is `out-of-scope: pbt-track`. In scope only as a fuzz target that decodes an operation sequence from bytes (`Vec<Op>` with `arbitrary`, go-fuzz-headers loop, `FuzzedDataProvider` loop) when the charter names crash, invariant or resource objectives and sequences are long enough for coverage guidance to matter. | invariants after every operation, resource limits, crash |
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
output is one line — `fuzz(method, oracle)` / `out-of-scope: pbt-track` / `out-of-scope: unit-tests`
/ `do-not-fuzz` — with the matching row quoted, so [[eval-family-A-gate]] can grade it
deterministically. A `fuzz` outcome is followed by the [[fuzzing-charter]] before any harness.
