---
note_id: "20261103150408"
created: 2026-11-03
modified: 2026-11-04
language: en
type: design
subtype: component
note_role: artifact
artifact_kind: reference-set
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Reference documents"]
tags: [fuzzing, design/component]
addresses: ["[[H2-no-stopping-rule]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]"]
decided_by: ["[[FTW-D-006-references-beside-skills]]"]
related: ["[[research-index]]", "[[repository-placement]]"]
---
# Reference documents

Reference files live in `<skill>/references/`, so Codex and Gemini receive them with the skill
([[FTW-D-006-references-beside-skills]]); `dot_claude/docs/` gets only an index. The research
annexes stay in this vault and are cited by file and section.

| Document | Lives in | Derived from | Content |
|---|---|---|---|
| `fuzzingbook-map.md` | `fuzzing-applicability/references/` | [[04-fuzzingbook-part1-lexical\|R4]], [[05-fuzzingbook-part2-syntactic\|R5]], [[06-fuzzingbook-parts3-5\|R6]] | one paragraph per chapter: lesson, when it applies, what the agent should and should not attempt; the "too academic" list |
| `bug-class-evidence.md` | `fuzzing-applicability/references/` | R7 §3.6, R9 §3.7, R8 §3.2 | the Go, Rust and Python bug-class tables with issue links — the argument for the [[oracle-ladder]] |
| `engine-output-cheatsheet.md` | `fuzzing-campaign/references/` | R2 §3.2, R7 §3.3, R8 §3.1, R9 §3.1 | Go, libFuzzer, AFL++, honggfuzz, Hypothesis output lines and flags with meaning and the stop-relevant fields; `ft`/`lim`/`L` pending [[FTW-OQ-002-libfuzzer-legend]] |
| `stopping-theory.md` | `fuzzing-campaign/references/` | R2 §3.1, R6 §3 | Good–Turing, Chao1, extrapolation formulas; Enigma and HTMLParser figures; the adaptivity caveat |
| `grammar-and-repair.md` | `structured-input-generation/references/` | R5 | derivation trees, expansion coverage, pre/post repair, structured reduction, with the book's numbers as illustrations only |
