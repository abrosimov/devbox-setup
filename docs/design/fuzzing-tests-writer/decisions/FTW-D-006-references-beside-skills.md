---
note_id: "202611031506006"
created: 2026-11-03
language: en
type: meta
subtype: decision
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-D-006"]
tags: [fuzzing, design/decision]
status: accepted
supersedes: []
superseded_by: []
related: ["[[reference-documents]]", "[[research-index]]"]
---
# FTW-D-006: Reference documents live beside the skill that cites them; the research annexes stay in docs/design

## Decision

Each reference file (`fuzzingbook-map`, `bug-class-evidence`, `engine-output-cheatsheet`, `stopping-theory`, `grammar-and-repair`) is placed under `<skill>/references/`; the ten annexes remain in this vault and are cited by file and section.

## Context

Codex and Gemini receive skills as directories; a reference outside the skill would not deploy with it. The annexes are an audit trail with corpus ledgers, too long and too source-heavy to ship as skill context.

## Alternatives considered

(a) All references in `dot_claude/docs/` — Claude-only. (b) Copy annex prose into skills — size and drift.

## Consequences

Skills cite annex sections in a trailing Sources list; a refresh of an annex is a vault change, not a deploy.

## Reopen when

a reference is needed by more than one skill in full (then a shared skill or `shared-utils` placement is reconsidered).
