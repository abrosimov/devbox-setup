---
note_id: "202611031507003"
modified: 2026-11-11
created: 2026-11-03
language: en
type: meta
subtype: open-question
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-OQ-003"]
tags: [fuzzing, design/open-question]
status: deferred-to-authoring
blocks: ["[[skill-go-fuzzing]]"]
related: ["[[language-facts-go]]"]
---
# FTW-OQ-003: Go skip and minimisation behaviour need runtime qualification

**Disposition (2026-11-10):** deferred-to-authoring.

Qualify skipped-input retention, reproducer location and minimisation against the target repository's
selected Go toolchain during authoring. The historical R7 question remains version-specific.
Minimisation is best-effort within an admitted experiment; retain the original useful/failing input if a
smaller equivalent input is not established. Save interrupted reduction and its context. Another
minimisation attempt needs a justified contribution; a new session does not itself justify a retry.
