---
note_id: "202611031507005"
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
status: open
blocks: ["[[skill-rust-fuzzing]]"]
related: ["[[language-facts-rust]]"]
---
# FTW-OQ-005: cargo-fuzz on stable with --sanitizer none

**Question.** Whether `cargo fuzz build -s none` builds on stable is unverified; sanitizer stabilisation (rust-lang/rust#123617) is open and cargo-fuzz carries a placeholder version for it.

**Why it matters.** Decides the CI recipe (pinned nightly versus stable) and whether bolero is recommended for stable-only projects.

**Resolution path.** Keep "nightly, pinned date" as the rule with a dated re-check note; test `-s none` on stable when the Rust toolchain is available in the authoring session.
