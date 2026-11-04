---
note_id: "20261103150005"
created: 2026-11-03
language: en
type: design
subtype: hypothesis
note_role: artifact
artifact_kind: hypothesis
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["H4", "Crash as the only oracle"]
tags: [fuzzing, design/hypothesis, h4]
verdict: "confirmed"
grounded_in: ["[[01-methods-and-applicability|R1]]", "[[07-lang-go|R7]]", "[[08-lang-python|R8]]", "[[09-lang-rust|R9]]"]
addressed_by: ["[[oracle-ladder]]", "[[skill-fuzzing-applicability]]"]
tested_by: ["[[eval-family-B-oracle]]"]
related: ["[[ontology]]"]
---
# H4 — Crash as the only oracle

**Hypothesis.** Earlier agents wrote harnesses that only checked "does not panic"; in memory-safe languages that finds almost nothing on typed APIs.

**Verdict.** Confirmed for all three languages with trophy-case and issue-tracker evidence; the Go standard library's own fuzz tests are round-trip properties.

## Evidence

- Rust trophy case ≈367 rows: arithmetic overflow, out-of-range, OOM, stack overflow dominate; 8 security-marked rows, all `unsafe`/FFI; logic bugs appear only through round-trip or reference comparison (rust-url #729) — R9 §3.7, R1 §3.9.
- Go: panics dominate but unbounded allocation (archive/tar CVE-2022-2879, debug/gosym #81191) and round-trip inconsistencies (net/netip #67126) need a property or resource oracle; an OOM-killed worker records no crash — R7 §3.6, §3.1.
- Python: wrong exception types, exponential parsing (CPython #90863), wrong results via differential oracles (ujson #440) — R8 §3.2.
- Hughes ranks model-based and metamorphic properties strongest (partially verified) — R1 §3.4.

## Addressed by

[[oracle-ladder]], carried by [[skill-fuzzing-applicability]] and enforced by the per-language review checklists.

## Tested by

[[eval-family-B-oracle]]: eight cases; a "does not panic" harness on a typed API fails.
