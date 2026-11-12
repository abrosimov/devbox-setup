---
note_id: "202611031507004"
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
aliases: ["FTW-OQ-004"]
tags: [fuzzing, design/open-question]
status: conditional
blocks: []
related: ["[[language-facts-go]]"]
---
# FTW-OQ-004: Existing OSS-Fuzz integration requires its own compatibility check

**Disposition (2026-11-10):** conditional.

Only if an authorised target already uses such integration, inspect its adapter, seed format and
build/replay contract before claiming compatibility. Do not create infrastructure or always generate
a second corpus archive. Native local target qualification can proceed without this conditional
claim; new integration work is outside this methodology pass.
