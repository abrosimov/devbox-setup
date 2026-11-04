---
note_id: "20261103150203"
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
aliases: ["Input shape triage", "Structure versus bytes"]
tags: [fuzzing, design/finding, h3]
addresses: ["[[H3-random-seeds-for-structured-input]]"]
grounded_in: ["[[03-structure-aware-generation|R3]]", "[[05-fuzzingbook-part2-syntactic|R5]]", "[[04-fuzzingbook-part1-lexical|R4]]", "[[07-lang-go|R7]]"]
realised_by: ["[[skill-structured-input-generation]]", "[[skill-go-fuzzing]]", "[[skill-python-fuzzing]]", "[[skill-rust-fuzzing]]"]
tested_by: ["[[eval-family-C-structure]]"]
related: ["[[corpus-lifecycle]]", "[[applicability-gate]]"]
---
# Input shape triage — structure versus bytes

Byte mutation fails on structured input for a mechanical reason: the first checksum, magic
number, length field or parse step rejects almost every mutant, so coverage stops at the validation
layer (R3 §0; R4 §0: random `http://` prefix odds 1/96⁷). Three mechanically different remedies
exist; the agent must choose one explicitly (R3 §0).

## Decision table by input shape (R3 §5.1, R5 §5.i)

| Input shape | Technique | Seeds | Shrinking |
|---|---|---|---|
| Opaque bytes (hash, cipher, decompressor input) | plain bytes + dictionary | real files, upstream corpora, `cmin` | engine minimiser |
| Text with keywords; lenient parser; flat format | seeds + bytes + dictionary; **no grammar** | real samples | engine minimiser |
| Recursive text, strict parser, a grammar exists in the repo or spec | grammar-generated seed corpus (bounded, coverage-driven) handed to the engine; terminals as dictionary | one input per expansion | grammar reducer or generator shrinker |
| Binary format with magic, length, CRC | fuzzing-build flag that skips the check **or** custom mutator with repair | real valid files | engine minimiser only if the repair hook also runs on reproduction |
| Typed value, struct, argument tuple | `arbitrary` derive / Hypothesis `builds` + `composite` / rapid generators / go-fuzz-headers | explicit `f.Add` / `@example` boundary values | generator shrinker (proptest, Hypothesis, rapid twin) |
| Sequence of operations | `Vec<Op>` / `RuleBasedStateMachine` / rapid `T.Repeat` | one trace per public method + recorded traces | state-machine shrinking; none under `go test -fuzz` |
| External schema (JSON Schema, OpenAPI, protobuf) | `hypothesis-jsonschema`, schemathesis, libprotobuf-mutator | schema-generated + fixtures | integrated |
| Compressed or encrypted wrapper | custom mutator (decompress → mutate → recompress) or fuzz the inner layer directly | decompressed samples | minimise the inner payload |

**Dry-run gate**: if >~90 % of engine mutants are rejected at the first check during a one-minute
dry run and the shape is one of the last five rows, plain byte fuzzing is the wrong tool; change
rows, do not run longer (R3 §5.1).

## Rules of thumb with their evidence

- *Construct, do not filter*: Luhn filter ≈10 attempts per valid number, repair 1 (R5 §0);
  Hypothesis `filter_too_much` fires at 50 rejected draws (R8 §3.1 claim 10).
- *Bound size explicitly* (`max_nonterminals`, `max_size`/`max_leaves`, `size_hint`) or recursive
  generators recreate the simple-fuzzer hang (R5 §5.i).
- *Keep the byte-level harness beside the structured one*, or the parser's error paths are never
  fuzzed (R5 §5.i).
- *Structure at seed-generation time, not per candidate* when throughput matters: fragment
  mutation on a lenient HTML parser cost 94.9 s for 300 inputs against 0.1 s for bytes and reached
  less coverage; a keyword dictionary alone lifted coverage 79→108 statements (R5 §0).
- Generator versus custom mutator: the one controlled comparison found a mutator 1.47× ahead at
  5 minutes and 1.01× at 24 hours; default to the generator, escalate to a mutator for
  compressed/checksummed containers (R3 §4.1, R9 §4 D3).
- Go is the outlier: `testing.F` accepts only basic types and custom mutators are an open
  proposal since 2021, so structure is decoded inside the target at the cost of instrumented
  decoder code, opaque corpus files and no structured shrinking (R7 §3.4; R3 §5.3).

## Seed-corpus checklist (R3 §5.2)

1. Collect: unit-test fixtures, regression inputs, upstream corpora, recorded traffic or carved
   calls; record provenance and licence. 2. Synthesise when thin: one input per grammar alternative,
   enum variant or message type; explicit boundary values. 3. Mix: mostly valid, a few
   one-field-invalid variants, never random garbage. 4. Keep each seed small; split large APIs.
5. Dedupe with `afl-cmin` / `-merge=1` / `cargo fuzz cmin` (Go: no tool, rely on the fuzz cache and
curation). 6. Discoverability: the target must gain coverage from an empty corpus too. 7. Maintain:
every bug input goes back into the seeds; dictionary lives next to the target. 8. Input to
[[stopping-algorithm]]: when merge adds nothing from a fresh run and the synthesis list is exhausted,
the corpus is saturated for this harness.

## Design consequence

[[skill-structured-input-generation]] carries the table, the checklist, the rules and one snippet
per language; the per-language skills fill in the idioms; [[eval-family-C-structure]] grades it.
