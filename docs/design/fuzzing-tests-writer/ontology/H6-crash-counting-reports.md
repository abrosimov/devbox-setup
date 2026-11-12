---
note_id: "20261103150007"
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
aliases: ["H6", "Reports that count crashes instead of bugs"]
tags: [fuzzing, design/hypothesis, h6]
verdict: "design risk supported by counterexamples"
grounded_in: ["[[02-stopping-and-corpus-lifecycle|R2]]", "[[06-fuzzingbook-parts3-5|R6]]", "[[01-methods-and-applicability|R1]]"]
addressed_by: ["[[reporting-and-claim-hygiene]]", "[[skill-fuzzing-campaign]]"]
tested_by: ["[[eval-family-F-reporting]]", "[[eval-family-G-triage]]"]
related: ["[[ontology]]"]
---
# H6 — Crash counts are mistaken for product findings

**Status:** design risk supported by counterexamples.

A signature count is not a unique-bug count. A failing process may reflect the environment, harness,
or an unconfirmed product symptom. Abstract-only percentages in R2 do not calibrate this agent.

[[reporting-and-claim-hygiene]] separates research states, experiment statuses and findings and bounds each claim by
its evidence. Families F/G check false oracles, environment failures, duplicate symptoms and
unreproduced failures. [[methodology-review]] records the local negative examples. A confirmed
product finding needs a contract violation and reproducible evidence; a no-finding result does not
establish correctness or saturation.
