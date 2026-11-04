---
note_id: "202611031507007"
created: 2026-11-03
language: en
type: meta
subtype: open-question
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-OQ-007"]
tags: [fuzzing, design/open-question]
status: open
blocks: []
related: ["[[applicability-gate]]", "[[oracle-ladder]]"]
---
# FTW-OQ-007: No per-language OSS-Fuzz yield statistics

**Question.** The argument for what fuzzing finds in memory-safe code rests on trophy lists and issue trackers; the OSS-Fuzz headline numbers are dominated by C/C++.

**Why it matters.** Only affects how strongly the gate's "unit tests suffice" row is worded.

**Resolution path.** Acceptable for a gate; revisit if a per-language study appears.
