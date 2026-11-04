---
note_id: "20261103150406"
created: 2026-11-03
modified: 2026-11-04
language: en
type: design
subtype: skill
note_role: artifact
artifact_kind: skill
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Skill: python-fuzzing", "python-fuzzing"]
tags: [fuzzing, design/component, design/skill, lang/python, h3, h4, h5]
addresses: ["[[H5-harness-conventions]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]"]
realises: ["[[language-facts-python]]", "[[oracle-ladder]]", "[[fuzzing-vs-pbt-boundary]]"]
tested_by: ["[[eval-family-E-conventions]]", "[[eval-family-B-oracle]]"]
decided_by: ["[[FTW-D-002-six-skills]]", "[[FTW-D-008-pbt-out-of-scope]]"]
opens: ["[[FTW-OQ-006-hypofuzz-licence]]"]
target_path: "roles/devbox/files/dot_ai/skills/python-fuzzing/"
codex_shared: true
related: ["[[reference-documents]]", "[[pbt-agent-prompts]]"]
---
# Skill `python-fuzzing`

**Problem**: agents reach for Hypothesis when asked to fuzz (and the reverse), write Atheris
harnesses that never stop or instrument nothing, preload ASan on pure-Python targets, and treat an
uncaught `ValueError` as a finding.

## Carries (from [[language-facts-python]])

- The decision rule (Atheris, HypoFuzz, `fuzz_one_input`, `out-of-scope: pbt-track` hand-offs),
  with the HypoFuzz licence stated first and the `fuzz_one_input` condition of
  [[fuzzing-vs-pbt-boundary]].
- Atheris harness skeleton (R8 §5.3), the `tests/fuzz/` layout, instrumentation and its cost,
  `-atheris_runs=N`, the "No interesting inputs" diagnostic, `FuzzedDataProvider` idioms for
  structured knobs, custom mutators for compressed input, expected-exception classification, crash
  files as regression seeds.
- Oracles in the target: round trip, differential against a second implementation, timeouts as
  findings, resource limits.
- Native extensions: sanitizer build, ASan preload and `ASAN_OPTIONS`, `enable_python_coverage`;
  pure-Python targets run without a preload.
- HypoFuzz operation and what it does and does not report; no plateau logic for plain Hypothesis
  runs.
- OSS-Fuzz Python integration and CI recipe (R8 §5.6, fuzz rows only).
- Review checklist (R8 §5.5, fuzz items).

≤ 250 lines.

## Evals shipped with the skill

Trigger queries: "fuzz this parser with Atheris", "libFuzzer for Python", "our C extension
decoder", "fuzz_one_input under Atheris"; negatives: "property-based test with Hypothesis",
"pytest fixtures for the database". Content evals: R8 §6 cases 4, 5, 7, 8, 11 (fuzz-side) plus
hand-off cases.
