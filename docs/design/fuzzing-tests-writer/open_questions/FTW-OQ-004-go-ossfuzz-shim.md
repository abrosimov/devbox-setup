---
note_id: "202611031507004"
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
status: open
blocks: ["[[skill-go-fuzzing]]"]
related: ["[[language-facts-go]]"]
---
# FTW-OQ-004: Go: OSS-Fuzz shim ignores f.Add and panics on named types

**Question.** Should the agent always generate both `testdata/fuzz` seeds and a `seed_corpus.zip` when a repository is or will be on OSS-Fuzz/ClusterFuzzLite?

**Why it matters.** A locally correct target is silently seed-less upstream.

**Resolution path.** Rule in the Go skill: when `.clusterfuzzlite/` or an OSS-Fuzz project exists, ship both and avoid named-type arguments; eval case in family E.
