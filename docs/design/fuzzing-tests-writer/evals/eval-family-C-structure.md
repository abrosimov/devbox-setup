---
note_id: "20261103150505"
created: 2026-11-03
modified: 2026-11-04
language: en
type: design
subtype: eval
note_role: artifact
artifact_kind: case-family
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Eval family C", "Structure and seeds"]
tags: [fuzzing, design/eval]
addresses: ["[[H3-random-seeds-for-structured-input]]"]
tests: ["[[input-shape-triage]]", "[[fuzzing-vs-pbt-boundary]]", "[[skill-structured-input-generation]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]", "[[fuzzing-vs-pbt-boundary]]"]
---
# Eval family C — Structure and seeds

Ten cases. Sources: R3 §6 cases 1/4/5/6/7/8/9/11; R5 §6 cases 1/3/4; R7 §5.4.

| Input the agent sees | Expected |
|---|---|
| Rust PNG-like decoder with CRC, empty corpus | `#[cfg(not(fuzzing))]` around CRC or a repairing `fuzz_mutator!`; real seeds per chunk type; chunk-name dictionary; justify not using `arbitrary` (would lose the real-file corpus) |
| Python `parse_config(text)` with a documented EBNF, strict parser | Atheris target over `str`; seed corpus generated from the grammar (one input per expansion, bounded) plus fixtures; grammar terminals as dictionary; **no Hypothesis strategy authored**; `fuzz_one_input` only if a `@given` test already exists |
| Go `Request` struct consumed by a handler; "fuzz this" | explain the `testing.F` limit; decode the struct from `[]byte` with go-fuzz-headers (or hand-written decoder) with costs stated; `rapid.MakeFuzz` only if a rapid property already exists; no rapid property written |
| dry run: 99.7 % of mutants rejected at `magic != 0xCAFE` | stop plain fuzzing; dictionary + seeds; move row if CRC follows; do not extend time |
| gzip decompressor; user asks for a grammar | opaque-bytes row: real compressed files, no grammar |
| Rust `struct Session` with `open/write/close` | if the charter names crash/invariant objectives: `Vec<Op>` fuzz target with index-safe ops and `arbitrary`; model-based state machine is `out-of-scope: pbt-track` and is not written |
| Go `.env` parser, 40 lines | native harness with 3–5 seed lines and a small dictionary; no grammar |
| Rust binary frame: 2-byte length, payload, CRC32 | `arbitrary`-decoded payload with computed length and CRC (repair in the target), plus a raw-byte target for mismatch paths; no filter on CRC validity |
| existing 5 000-file upstream JSON corpus | `cmin`/`-merge=1` first; keep provenance; add regression inputs |
| crash found with an `arbitrary` input; user asks for a minimal repro | do not call `cargo fuzz tmin` output minimal; hand-reduce with `cargo fuzz fmt`; note that structured shrinking belongs to the PBT track |

## Graders

- Seeds present in the ecosystem location; count ≥ 3; no random-byte seeds (regex); dictionary
  file present where the format has tokens; for the CRC case either the fuzzing-build bypass or a
  repair hook; no `@given`/`proptest!`/`rapid.Check` in produced files.
- LLM judge: technique matches the shape row; construct-not-filter respected; byte-level harness
  kept beside the structured one.
