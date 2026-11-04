---
note_id: "20261103150402"
created: 2026-11-03
language: en
type: design
subtype: component
note_role: artifact
artifact_kind: skill
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Skill: fuzzing-applicability", "fuzzing-applicability"]
tags: [fuzzing, design/component, design/skill, h1, h4]
addresses: ["[[H1-no-applicability-gate]]", "[[H4-crash-only-oracle]]"]
realises: ["[[applicability-gate]]", "[[oracle-ladder]]"]
tested_by: ["[[eval-family-A-gate]]", "[[eval-family-B-oracle]]"]
decided_by: ["[[FTW-D-001-gate-is-first-step]]", "[[FTW-D-002-six-skills]]"]
target_path: "roles/devbox/files/dot_ai/skills/fuzzing-applicability/"
codex_shared: true
related: ["[[reference-documents]]"]
---
# Skill `fuzzing-applicability`

**Problem** (frontmatter `problem:`): agents fuzz everything they are pointed at and accept "does
not crash" as the oracle, so campaigns cost time and find nothing in memory-safe code.

## Carries

- The gate table of [[applicability-gate]] with the seven preconditions and the one-line output
  format (`fuzz(method, oracle)` / `property-test` / `unit-test` / `do-not-fuzz` + quoted row).
- The [[oracle-ladder]], the contract-statement header, templates for round-trip, differential and
  metamorphic properties, the property catalogue and the triage rubric reused from the Hypothesis
  and `agentic-pbt` prompts (R8 §3.5).
- The anti-pattern list with the evidence behind each entry (R1 §3.12): fuzzing a forwarder to
  `json.Unmarshal`, unit-test inputs as the only seeds, asserting on internal state, one monolithic
  target, time/RNG/network in the target, `os.Exit` in the path, treating a `Must*` panic as a
  bug, `--release` without debug assertions, "N unique crashes", corpus size as progress.
- Pairwise option testing as the answer for flag spaces (R6 §5.4).

## Size and shape

≤ 250 lines; decision tables, no narrative; `references/bug-class-evidence.md`
([[reference-documents]]) holds the per-language trophy tables the gate cites.

## Evals shipped with the skill

`evals/trigger_evals.json` (~20 queries; positives: "should we fuzz this parser", "add a fuzz
target for the decoder", "is fuzzing worth it here"; near-miss negatives: "add table-driven tests
for the parser", "fuzzy-match these strings", "speed up the CI test job") and `evals/evals.json`
with the gate cases of [[eval-family-A-gate]].

Sources: R1 §5.1–5.5, R4 §5.1/5.4, R6 §5.4, R8 §3.5.
