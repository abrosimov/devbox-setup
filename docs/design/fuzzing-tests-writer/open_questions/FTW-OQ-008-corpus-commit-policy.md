---
note_id: "202611031507008"
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
status: open
blocks: ["[[skill-fuzzing-campaign]]"]
related: ["[[corpus-lifecycle]]"]
---
# FTW-OQ-008: Generated-corpus commit policy differs per ecosystem

**Question.** Go writes regression inputs into the repository; cargo-fuzz git-ignores corpus and artifacts; proptest commits seeds; bolero commits `__fuzz__`; ClusterFuzzLite uses a storage repository. Which policy does the agent apply when a repository mixes tools?

**Why it matters.** Copying one ecosystem's habit to another creates noise or loses regressions.

**Resolution path.** Per-tool rule in each language skill, graded in family E; a repository-level override documented in the campaign report.
