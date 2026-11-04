---
note_id: "20261104100011"
created: 2026-11-04
language: en
type: meta
subtype: open-question
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-OQ-011"]
tags: [fuzzing, design/open-question]
status: open
blocks: []
related: ["[[pbt-agent-prompts]]", "[[FTW-OQ-001-unverified-paper-bodies]]"]
---
# FTW-OQ-011: Validity figures of agent-found bugs in agentic-pbt

**Question.** The 56 % valid / 32 % worth-reporting figures (and a competing "≈81 % of
high-priority reports") come from search snippets of arXiv 2510.09907 and a blog; which subset each
measures is unknown.

**Why it matters.** Only as a calibration point for the fuzzing agent's own triage rubric and for
the eval's "valid" versus "worth reporting" split; nothing in scope depends on the exact number.

**Resolution path.** Read the paper when the host is reachable; record the measured subsets in
[[pbt-agent-prompts]].
