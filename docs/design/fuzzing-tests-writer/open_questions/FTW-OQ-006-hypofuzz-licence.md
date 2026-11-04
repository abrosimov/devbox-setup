---
note_id: "202611031507006"
created: 2026-11-03
language: en
type: meta
subtype: open-question
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-OQ-006"]
tags: [fuzzing, design/open-question]
status: open
blocks: ["[[skill-python-fuzzing]]"]
related: ["[[language-facts-python]]"]
---
# FTW-OQ-006: HypoFuzz is free only for non-commercial use

**Question.** How should the agent handle HypoFuzz on the `work` profile?

**Why it matters.** Adding it to a commercial CI without a licence is a compliance problem the agent must not create silently.

**Resolution path.** The Python skill states the licence before recommending it; optionally gate the recommendation on the active profile via a skill variable.
