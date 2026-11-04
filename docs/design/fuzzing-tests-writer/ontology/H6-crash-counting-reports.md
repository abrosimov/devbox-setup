---
note_id: "20261103150007"
created: 2026-11-03
modified: 2026-11-04
language: en
type: design
subtype: hypothesis
note_role: artifact
artifact_kind: hypothesis
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["H6", "Reports that count crashes instead of bugs"]
tags: [fuzzing, design/hypothesis, h6]
verdict: "emerged-from-research"
grounded_in: ["[[02-stopping-and-corpus-lifecycle|R2]]", "[[06-fuzzingbook-parts3-5|R6]]", "[[01-methods-and-applicability|R1]]"]
addressed_by: ["[[reporting-and-claim-hygiene]]", "[[skill-fuzzing-campaign]]"]
tested_by: ["[[eval-family-F-reporting]]", "[[eval-family-G-triage]]"]
related: ["[[ontology]]"]
---
# H6 — Reports that count crashes instead of bugs

**Hypothesis.** A campaign report that counts "N unique crashes", and files contract panics or sub-second hangs as bugs, misstates what the campaign found.

**Verdict.** Emerged from R2, R6 and R1 rather than from the original list; the practice those sources document is bucket-level reporting with reproducers, which [[reporting-and-claim-hygiene]] fixes as the report form.

## Evidence

- Klees et al.: one bug maps to ~46 stack hashes on average and ~16 % of hashes collide (abstract level); OSS-Fuzz reports one timeout and one OOM per target because they cannot be deduplicated — R2 §3.3 C8.
- FuzzingInTheLarge's data model: product id, reproduce steps, stack, coverage; crashes grouped into buckets by signature — R6 §5.3.
- False positives exist: x/image/webp "infinite loop" was a 2.5 s legitimate decode; `regexp.MustCompile` panics by contract — R7 §3.6, R1 §3.8.
