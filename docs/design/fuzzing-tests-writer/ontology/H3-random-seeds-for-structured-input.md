---
note_id: "20261103150004"
created: 2026-11-03
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
verdict: "confirmed"
grounded_in: ["[[03-structure-aware-generation|R3]]", "[[05-fuzzingbook-part2-syntactic|R5]]", "[[04-fuzzingbook-part1-lexical|R4]]"]
addressed_by: ["[[input-shape-triage]]", "[[skill-structured-input-generation]]"]
tested_by: ["[[eval-family-C-structure]]"]
related: ["[[ontology]]"]
---
# H3 — Random seeds for structured input

**Hypothesis.** Earlier agents seeded with random bytes or with the unit-test inputs only; structured inputs (parsers, protocols, typed APIs) never got past validation and coverage stayed shallow.

**Verdict.** Confirmed with mechanism and numbers.

## Evidence

- Prefix probability: a random `http://` prefix has odds 1/96⁷; one valid seed plus 2–10 stacked mutations keeps ~80 % of candidates valid versus ~0 % for random bytes — R4 §0, §5.3.
- Checksums gate everything: the first CRC, magic, length field or parse step rejects almost every mutant — R3 §0 (libFuzzer structure-aware doc, good-fuzz-target).
- Generate-then-repair beats generate-then-reject ≈10× (Luhn example); Hypothesis `filter_too_much` fires at 50 rejected draws — R5 §0, R8 §3.1.
- Go cannot take structured arguments at all; structure must be decoded inside the target — R7 §3.4, R3 §5.3.

## Addressed by

[[input-shape-triage]] (shape table, seed checklist, construct-not-filter), carried by [[skill-structured-input-generation]] and the per-language skills.

## Tested by

[[eval-family-C-structure]]: ten cases including the CRC frame, the lenient parser where a grammar is overkill, and the dry-run rejection gate.
