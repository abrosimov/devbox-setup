---
note_id: "20261103150203"
created: 2026-11-03
modified: 2026-11-11
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
related: ["[[corpus-lifecycle]]", "[[applicability-gate]]", "[[fuzzing-vs-pbt-boundary]]"]
---
# Input shape triage — structure and bytes

Choose input construction from the target contract and available material. Reuse representative
seeds and supported dictionaries when sufficient. For an unfamiliar corpus or direction, a bounded
reconnaissance pass may establish the obstacle or useful question. Name the material, feasible
operation, possible knowledge contribution and effort limit; its exact discovery need not be known.
A grammar, decoder or repair step can be examined before its benefit is established. Retain its
claimed benefit only after relevant observations; no rejection percentage prescribes escalation.

| Observed input shape or obstacle | Bounded operation | Check and limitation |
|---|---|---|
| Opaque bytes or a lenient format | Use representative seeds and engine byte mutation | Include boundary and intentional rejection cases |
| Keywords or delimiters | Add a supported dictionary or targeted seeds | Verify that the engine actually consumes them |
| Recursive syntax with an existing grammar | Produce bounded representative seeds | Bound recursion, size and generation work; record grammar alternatives separately from code coverage |
| Length/checksum dependencies | Construct or repair dependent fields in an authorised harness/generator | Replay must use the same transformation; retain an invalid-input route |
| Typed or encoded values | Decode engine bytes with a fuzzing-side decoder | Account for decoder coverage, version dependence and input exhaustion |
| Operation sequence | Decode a bounded sequence and reset target state per input | Use existing contract checks; no separate PBT/model-testing project |
| Compressed wrapper | Target the authorised inner layer or use bounded repair/recompression | Name which wrapper behaviour is no longer exercised |

Do not modify production validation or add a fuzzing-only bypass merely because valid inputs are
hard to reach. Such a change alters the experiment and needs its own scope decision. This pass
specifies input construction and harness operations only.

## Concrete operation

1. Read the format/entry contract and inspect or replay representative inputs. Identify which
   checks reject them and whether deeper product behaviour is reached; keep unknowns explicit.
2. Choose a small feasible construction that can reveal or resolve a useful distinction. Reuse
   saved attempts and state the comparison or observation to obtain. Initial reconnaissance may
   compare an unfamiliar construct with an existing seed without predicting the resulting question.
3. Bound generated depth, size, operation count and repair cost. Construct dependent fields
   directly where practical rather than rely on repeated rejection.
4. Preserve successful generated inputs as seeds, with raw bytes and decoder/grammar provenance.
   Maintain intentionally invalid examples alongside valid structure.
5. Measure the relevant distinction: acceptance, grammar alternatives and product coverage are
   different observations. Verify replay and report uncovered or unverified behaviour.
6. Use the observed difference to answer the current question, form a new in-scope question, choose
   a further bounded examination, or close the line. Compare the next attainable contribution with
   its burden under [[stopping-algorithm]]. Save useful inputs, governing assumptions and unfinished
   operations for later work. An imagined better generator alone does not justify continuing.

For example, replay unfamiliar nested constructs beside existing flat seeds. Reaching a different
parser path can support a new question about nesting behaviour; early rejection instead identifies
what the current sample cannot exercise. Neither outcome requires a promised bug or a new grammar
project. Preserve useful inputs from either case, including intentionally rejected examples.

The [Fuzzing Book grammar coverage chapter](https://www.fuzzingbook.org/html/GrammarCoverageFuzzer.html)
provides a concrete way to cover grammar expansions; that is not a guarantee of program coverage.
Its construction and reduction lessons are transferred into bounded operations here and in
[[corpus-lifecycle]], rather than an obligation to implement every technique in the book.

PBT generator bridges are excluded by [[fuzzing-vs-pbt-boundary]]. No new inputs after a merge
means that operation added none under its criterion; it does not establish a saturated corpus.
