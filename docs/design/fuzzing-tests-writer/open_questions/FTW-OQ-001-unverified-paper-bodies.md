---
note_id: "202611031507001"
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
aliases: ["FTW-OQ-001"]
tags: [fuzzing, design/open-question]
status: nonblocking
blocks: []
related: ["[[research-corpus]]", "[[stopping-algorithm]]"]
---
# FTW-OQ-001: Unverified paper bodies are excluded from current claims

**Disposition (2026-11-10):** nonblocking.

Some historical annexes quote abstract-only figures. Do not use those figures to justify rules or
acceptance thresholds. No current operation requires them. Read a full source only if a later
in-scope decision actually depends on it; this is not a standing research task.
