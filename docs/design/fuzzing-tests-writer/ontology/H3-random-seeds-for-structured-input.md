---
note_id: "20261103150004"
created: 2026-11-03
modified: 2026-11-11
language: en
type: design
subtype: hypothesis
note_role: artifact
artifact_kind: hypothesis
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["H3", "Random seeds for structured input"]
tags: [fuzzing, design/hypothesis, h3]
verdict: "conditional mechanism; not a universal failure"
grounded_in: ["[[03-structure-aware-generation|R3]]", "[[05-fuzzingbook-part2-syntactic|R5]]", "[[04-fuzzingbook-part1-lexical|R4]]"]
addressed_by: ["[[input-shape-triage]]", "[[skill-structured-input-generation]]"]
tested_by: ["[[eval-family-C-structure]]"]
related: ["[[ontology]]"]
---
# H3 — Inputs fail to reach the intended path

**Status:** conditional mechanism; not a universal failure.

Random bytes may repeatedly fail format checks; useful seeds, dictionaries, constructive decoding
or repair can reach deeper paths. R3 and R4–R6 provide examples, not a portable probability or a
universal speed-up. The former numeric examples must not become acceptance thresholds.

[[input-shape-triage]] chooses the smallest justified operation from the actual input contract.
Observe the intended path, retain useful inputs for replay and bound recursion/size. Preserve a
malformed-input path where it is part of the target's contract; grammar validity is not correctness.
Family C checks meaningful execution and defeats over-filtering. Adding grammar machinery does not
justify another experiment or create a requirement to implement PBT.
