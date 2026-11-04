---
note_id: "20261103150403"
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
aliases: ["Skill: fuzzing-campaign", "fuzzing-campaign"]
tags: [fuzzing, design/component, design/skill, h2, h5, h6]
addresses: ["[[H2-no-stopping-rule]]", "[[H5-harness-conventions]]", "[[H6-crash-counting-reports]]"]
realises: ["[[stopping-algorithm]]", "[[corpus-lifecycle]]", "[[reporting-and-claim-hygiene]]"]
tested_by: ["[[eval-family-D-stopping]]", "[[eval-family-F-reporting]]", "[[eval-family-G-triage]]"]
decided_by: ["[[FTW-D-003-thresholds-as-flags]]", "[[FTW-D-002-six-skills]]"]
target_path: "roles/devbox/files/dot_ai/skills/fuzzing-campaign/"
codex_shared: true
related: ["[[reference-documents]]"]
---
# Skill `fuzzing-campaign`

**Problem**: no engine stops by itself and no document gives a threshold, so agents run until
interrupted, declare "saturated" on a quiet quarter-hour, or report crash counts as bugs.

## Carries

- Budget classes and the nine-step procedure of [[stopping-algorithm]], with the per-engine
  observable/threshold table marked ✓ sourced / ◇ proposed (R2 §5.1).
- The escalation ladder and the attention rule across targets.
- The [[corpus-lifecycle]] checklist (before / during / after) with per-engine commands and the
  commit policy per ecosystem.
- Crash minimisation and deduplication policy; the ≤10 % triage budget.
- The campaign report template and the claim-hygiene rules of [[reporting-and-claim-hygiene]].
- How to call `fuzz_campaign.py` and `fuzz_corpus.py` ([[automation-scripts]]) and read their JSON.

## Size and shape

≤ 300 lines plus `references/engine-output-cheatsheet.md` and `references/stopping-theory.md`
([[reference-documents]]).

## Evals shipped with the skill

Trigger queries around "how long should we fuzz", "is the corpus saturated", "what do these
libFuzzer lines mean", "write up the fuzzing results"; negatives about benchmark timing and
flaky-test retries. Content evals from [[eval-family-D-stopping]] and [[eval-family-F-reporting]].

Sources: R2 §5, R6 §5.2–5.3, R1 §5.4.
