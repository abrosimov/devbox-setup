---
note_id: "20261103150404"
created: 2026-11-03
modified: 2026-11-04
language: en
type: design
subtype: component
note_role: artifact
artifact_kind: skill
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Skill: structured-input-generation", "structured-input-generation"]
tags: [fuzzing, design/component, design/skill, h3, h5]
addresses: ["[[H3-random-seeds-for-structured-input]]", "[[H5-harness-conventions]]"]
realises: ["[[input-shape-triage]]", "[[corpus-lifecycle]]"]
tested_by: ["[[eval-family-C-structure]]"]
decided_by: ["[[FTW-D-002-six-skills]]"]
target_path: "roles/devbox/files/dot_ai/skills/structured-input-generation/"
codex_shared: true
related: ["[[reference-documents]]"]
---
# Skill `structured-input-generation`

**Problem**: random bytes or unit-test inputs as seeds leave structured targets stuck at the first
validation step; agents then extend the budget instead of changing technique.

## Carries

- The shape table of [[input-shape-triage]] and the dry-run rejection gate.
- The seed-corpus checklist and the four rules of thumb (construct not filter; bound size; keep the
  byte path; structure at seed time).
- Grammar coverage as a corpus-adequacy criterion and a stop signal for *seed construction* only
  (R5 §5.ii); generate-then-repair pattern (R5 §0); custom-mutator template
  (decompress → mutate → recompress) for libFuzzer, Atheris and AFL++ (R3 §7).
- Structured reduction checklist: same-symptom runner, determinism, reducer by structure, keep
  candidates valid, report minimal input plus original (R5 §5.iii).
- One fuzzing-side decoder snippet per language (R3 §5.3), each with its limits: Rust `Vec<Op>`
  with `Arbitrary`, Go go-fuzz-headers loop, Python `FuzzedDataProvider` loop. The `fuzz_one_input`
  and `rapid.MakeFuzz` bridges appear only under the conditions in [[fuzzing-vs-pbt-boundary]].

≤ 300 lines plus `references/grammar-and-repair.md` ([[reference-documents]]).

## Evals shipped with the skill

Trigger queries around "seeds for the parser", "the fuzzer never gets past the CRC", "generate
valid inputs for", "write a grammar for fuzzing"; negatives about test data factories and fixture
cleanup. Content evals from [[eval-family-C-structure]].
