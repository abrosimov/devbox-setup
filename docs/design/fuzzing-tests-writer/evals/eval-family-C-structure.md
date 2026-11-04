---
note_id: "20261103150505"
created: 2026-11-03
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
tests: ["[[input-shape-triage]]", "[[skill-structured-input-generation]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]"]
---
# Eval family C — Structure and seeds

Ten cases. Sources: R3 §6 cases 1/2/4/6/7/12; R5 §6 cases 1/2/4/9.

| Input the agent sees | Expected |
|---|---|
| Rust PNG-like decoder with CRC, empty corpus | `#[cfg(not(fuzzing))]` around CRC or a repairing `fuzz_mutator!`; real seeds per chunk type; chunk-name dictionary; justify not using `arbitrary` |
| Python `parse_config(text)` with a documented EBNF | `from_lark`/`from_regex` strategy with repairs; seeds per rule alternative; HypoFuzz/`@given` unless a C extension is involved |
| Go `Request` struct consumed by a handler; "fuzz this" | explain the `testing.F` limit; offer `rapid.MakeFuzz` or go-fuzz-headers with costs stated; `rapid.Check` twin |
| dry run: 99.7 % of mutants rejected at `magic != 0xCAFE` | stop plain fuzzing; dictionary + seeds; move row if CRC follows; do not extend time |
| gzip decompressor; user asks for a grammar | opaque-bytes row: real compressed files, no grammar |
| Python `@dataclass` with invariant `start <= end` | `composite` (draw two, sort), not `builds` + `filter` |
| Go `.env` parser, 40 lines | native harness with 3–5 seed lines and a small dictionary; no grammar |
| Rust binary frame: 2-byte length, payload, CRC32 | typed generator with computed length and CRC, plus raw-byte target for mismatch paths; no grammar; no filter on CRC validity |
| lenient Markdown converter; draft plan says "full grammar + custom mutator" | reject the plan: seeds from real documents + bytes + dictionary |
| Hypothesis-based Atheris target shows a coverage drop after a Hypothesis upgrade | recognise corpus byte-encoding invalidation; rebuild corpus; keep raw seeds separately |

## Graders

- Seeds present in the ecosystem location; count ≥ 3; no random-byte seeds (regex); dictionary
  file present where the format has tokens; for the CRC case either the fuzzing-build bypass or a
  repair hook.
- LLM judge: technique matches the shape row; construct-not-filter respected; byte-level harness
  kept beside the structured one.
