---
note_id: "202611031507003"
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
status: open
blocks: ["[[skill-go-fuzzing]]"]
related: ["[[language-facts-go]]"]
---
# FTW-OQ-003: Go: skipped inputs and minimisation reliability

**Question.** Whether a `t.Skip`-ped input can still be kept as interesting was not determined from source; one of three local crashers was written unminimised with no log line (issue #48820 reports minimisation hangs).

**Why it matters.** Decides the wording of the skip idiom and what the checklist promises about committed crasher size.

**Resolution path.** Read the `internal/fuzz/worker.go` paths for skipped results at go1.27.3; keep minimisation as best-effort in the checklist until then.
