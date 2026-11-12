---
note_id: "202611031507008"
modified: 2026-11-10
created: 2026-11-03
language: en
type: meta
subtype: open-question
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-OQ-008"]
tags: [fuzzing, design/open-question]
status: resolved
blocks: []
related: ["[[corpus-lifecycle]]"]
---
# FTW-OQ-008: Preserve useful inputs using repository conventions

**Disposition (2026-11-10):** resolved.

Retain useful coverage-expanding inputs, useful structured inputs and regression examples for reuse
and replay. Follow repository storage/replay conventions; if none exists, propose a simple scoped
location during authoring and report it. Do not discard an input merely because it has no known bug.
Deduplication/minimisation must preserve its known value. Retention and Git publication are distinct:
this capability does not automatically commit. [[corpus-lifecycle]] owns the rule.
