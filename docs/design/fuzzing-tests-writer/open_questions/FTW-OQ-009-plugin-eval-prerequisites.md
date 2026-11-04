---
note_id: "202611031507009"
created: 2026-11-03
language: en
type: meta
subtype: open-question
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-OQ-009"]
tags: [fuzzing, design/open-question]
status: open
blocks: ["[[eval-tooling]]"]
related: ["[[FTW-D-004-evals-as-plugin]]"]
---
# FTW-OQ-009: claude plugin eval prerequisites in CI

**Question.** The tool requires Claude Code ≥ 2.1.269 and, for granted Bash on Linux, bubblewrap and socat; cost per case is not documented.

**Why it matters.** Decides the CI image and the `--max-cost-usd` ceiling for the behavioural eval job.

**Resolution path.** Add the packages to the eval job image; measure cost on the first non-holdout run; the trigger evals need neither.
