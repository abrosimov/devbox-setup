---
note_id: "202611031507001"
created: 2026-11-03
language: en
type: meta
subtype: open-question
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-OQ-001"]
tags: [fuzzing, design/open-question]
status: open
blocks: ["[[skill-fuzzing-campaign]]", "[[reference-documents]]"]
related: ["[[research-corpus]]", "[[stopping-algorithm]]"]
---
# FTW-OQ-001: Paper bodies cited at abstract level

**Question.** Klees et al. 2018 figures (trials, 57 142 crashes → 9 bugs), Böhme 2020/2021 magnitudes, Mañes et al. taxonomy, Hughes' property ranking were read from abstracts or search snippets only.

**Why it matters.** Skills must not quote numbers from them until read; the stopping algorithm's adaptivity caveat and the claim-hygiene rules currently rest on the Fuzzing Book chapter and the fuzz-evaluator guidelines, which were read.

**Resolution path.** Re-fetch when `arxiv.org` and the ACM/IEEE hosts are reachable; until then skills cite the Fuzzing Book chapter and engine docs.
