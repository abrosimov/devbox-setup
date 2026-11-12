---
note_id: "202611031507005"
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
aliases: ["FTW-OQ-005"]
tags: [fuzzing, design/open-question]
status: deferred-to-authoring
blocks: ["[[skill-rust-fuzzing]]"]
related: ["[[language-facts-rust]]"]
---
# FTW-OQ-005: Selected Rust engine/toolchain combination needs verification

**Disposition (2026-11-10):** deferred-to-authoring.

Verify cargo-fuzz, compiler channel, target and sanitizer combination using current primary docs
and an actual fixture build/run when authoring. Historical claims about stable or nightly are not
current execution evidence. Do not silently substitute a PBT runner or install a toolchain in this
document pass. Report unsupported environments explicitly.
