---
note_id: "20261103150006"
created: 2026-11-03
modified: 2026-11-04
language: en
type: design
subtype: hypothesis
note_role: artifact
artifact_kind: hypothesis
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["H5", "Harnesses that do not compile or follow conventions"]
tags: [fuzzing, design/hypothesis, h5]
verdict: "confirmed"
grounded_in: ["[[07-lang-go|R7]]", "[[08-lang-python|R8]]", "[[09-lang-rust|R9]]"]
addressed_by: ["[[language-facts-go]]", "[[language-facts-python]]", "[[language-facts-rust]]", "[[skill-go-fuzzing]]", "[[skill-python-fuzzing]]", "[[skill-rust-fuzzing]]"]
tested_by: ["[[eval-family-E-conventions]]"]
related: ["[[ontology]]"]
---
# H5 — Harnesses that do not compile or follow conventions

**Hypothesis.** Earlier harnesses did not compile, did not use the ecosystem's corpus location or CI split, or were not reproducible.

**Verdict.** Confirmed as a convention problem rather than a coding problem: each ecosystem has three or four non-obvious rules, carried by the `language-facts-*` notes. The seed corpus passes as unit tests at the harness step of [[agent-procedure]] (step 4), before any campaign.

## Evidence

- Go: `-fuzz` needs one package, one target, anchored regexp and a budget or it fails with no fuzzing done; the OSS-Fuzz shim ignores `f.Add` and panics on named types; a committed failing seed fails every later baseline until fixed — R7 §3.1, §3.5, §3.2.
- Rust: `#![no_main]`, nightly, `-O` drops overflow checks unless `--debug-assertions`; corpus and artifacts are git-ignored by default — R9 §3.1 C5, C7, D5.
- Python: `@reproduce_failure` blobs are version-specific; `.hypothesis/` stays out of VCS; Atheris never stops without `-atheris_runs`; pure-Python targets must not preload ASan — R8 §3.1, §3.2.
