---
note_id: "202611031507002"
created: 2026-11-03
language: en
type: meta
subtype: open-question
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-OQ-002"]
tags: [fuzzing, design/open-question]
status: open
blocks: ["[[reference-documents]]", "[[automation-scripts]]"]
related: ["[[language-facts-rust]]", "[[language-facts-python]]"]
---
# FTW-OQ-002: libFuzzer status-line legend

**Question.** `ft`, `lim`, `L` and the exact wording of the `pulse` line were read from flag source and the libFuzzer tutorial; the prose manual (`llvm/docs/LibFuzzer.rst`) was unreachable.

**Why it matters.** The engine-output cheatsheet and the campaign script's parser depend on exact column semantics.

**Resolution path.** Verify against `LibFuzzer.rst` before writing `engine-output-cheatsheet.md`; add a parser unit test per column.
