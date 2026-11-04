---
note_id: "20261103150406"
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
aliases: ["Skill: python-fuzzing", "python-fuzzing"]
tags: [fuzzing, design/component, design/skill, lang/python, h3, h4, h5]
addresses: ["[[H5-harness-conventions]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]"]
realises: ["[[language-facts-python]]", "[[oracle-ladder]]"]
tested_by: ["[[eval-family-E-conventions]]", "[[eval-family-B-oracle]]"]
decided_by: ["[[FTW-D-002-six-skills]]"]
target_path: "roles/devbox/files/dot_ai/skills/python-fuzzing/"
codex_shared: true
related: ["[[reference-documents]]"]
---
# Skill `python-fuzzing`

**Problem**: agents confuse Hypothesis, Atheris and HypoFuzz, over-constrain strategies, suppress
health checks, commit version-specific reproduction blobs, and write Atheris harnesses that never
stop.

## Carries (from [[language-facts-python]])

- Hypothesis-vs-Atheris-vs-parametrised decision (R8 §5.1) and schemathesis for HTTP APIs.
- Skeletons for a Hypothesis property test and an Atheris harness (R8 §5.2–5.3).
- Settings and profiles (`ci`, nightly, smoke `phases`), stop reasons and what each implies,
  `deadline`, `max_examples` budgeting, `target()` thresholds.
- Health checks that are never suppressed; `.filter` > `assume` > early return.
- Strategies for structure; `RuleBasedStateMachine`; `fuzz_one_input` bridge and its corpus caveat.
- Atheris layout, `-atheris_runs`, `FuzzedDataProvider` idioms, native-extension ASan recipe.
- Reproduction (`@example`, never `@reproduce_failure` in the tree; database policy).
- HypoFuzz operation and the licence note ([[FTW-OQ-006-hypofuzz-licence]]).
- Ten-point review checklist (R8 §5.5) and CI recipe (R8 §5.6).

## Size and shape

≤ 300 lines; pointer paragraph added to the existing `python-testing` skill.

## Evals shipped with the skill

Trigger queries: "property-based test with Hypothesis", "fuzz this parser with Atheris",
"Hypothesis says filter_too_much", "fuzz_one_input"; negatives: "pytest fixtures for the
database", "mock requests in this test". Content evals: R8 §6 cases 1–13.

Sources: R8 §5.
