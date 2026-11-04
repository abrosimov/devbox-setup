---
note_id: "202611031507010"
created: 2026-11-03
language: en
type: meta
subtype: open-question
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-OQ-010"]
tags: [fuzzing, design/open-question]
status: open
blocks: ["[[agent-procedure]]"]
related: ["[[eval-plan]]"]
---
# FTW-OQ-010: Opus for the gate, charter and shape steps raises cost per eval case

**Question.** Is the decision density of the gate, charter and shape steps worth Opus, or does Sonnet with the skills pass family A?

**Why it matters.** Eval budget and day-to-day cost of the agent.

**Resolution path.** Run family A with both models on the non-holdout set; keep the `unit_tests_writer` complexity-escalation block either way.
