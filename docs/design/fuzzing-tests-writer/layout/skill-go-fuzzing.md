---
note_id: "20261103150405"
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
aliases: ["Skill: go-fuzzing", "go-fuzzing"]
tags: [fuzzing, design/component, design/skill, lang/go, h3, h5]
addresses: ["[[H5-harness-conventions]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]"]
realises: ["[[language-facts-go]]", "[[oracle-ladder]]"]
tested_by: ["[[eval-family-E-conventions]]", "[[eval-family-B-oracle]]"]
decided_by: ["[[FTW-D-007-go-target-version]]", "[[FTW-D-002-six-skills]]"]
target_path: "roles/devbox/files/dot_ai/skills/go-fuzzing/"
codex_shared: true
related: ["[[reference-documents]]"]
opens: ["[[FTW-OQ-003-go-skip-and-minimisation]]", "[[FTW-OQ-004-go-ossfuzz-shim]]"]
---
# Skill `go-fuzzing`

**Problem**: Go harnesses fail for convention reasons — wrong `-fuzz` invocation, unsupported
argument types, seeds that the OSS-Fuzz shim ignores, deleted failing seeds, crash-only targets on
typed APIs.

## Carries (from [[language-facts-go]], Go 1.27.3)

- `testing.F` contract, allowed types, one-`f.Fuzz` rule; platform limits.
- Harness skeleton (R7 §5.2) and the ten-point review checklist (R7 §5.3).
- Native-vs-rapid-vs-table decision (R7 §5.4); `rapid.MakeFuzz` and go-fuzz-headers for structure;
  `file2fuzz` for raw seeds.
- Seed corpus semantics (`f.Add` + `testdata/fuzz/`, baseline failure on committed crashers),
  `$GOCACHE/fuzz` and `go clean -fuzzcache`.
- Invocation template, `-json` parsing incl. `OutputType`, `GODEBUG=fuzzdebug=1`, `-race` cost.
- OSS-Fuzz / ClusterFuzzLite shim differences (`F.Add` no-op, named types panic, seeds as zip).
- CI recipe (R7 §5.5) and `F.ArtifactDir` + `-artifacts` for campaign artefacts.
- Twelve rules R1–R12 of R7 §5.1 tagged by hypothesis.

## Size and shape

≤ 250 lines; pointer paragraph added to the existing `go-testing` skill.

## Evals shipped with the skill

Trigger queries: "write a Go fuzz test for", "testing.F", "go test -fuzz keeps failing",
"fuzz the decoder in pkg/codec"; negatives: "table-driven tests with testify", "benchmark this Go
function". Content evals: R7 §6 E1–E9.

Sources: R7 §5, §8.
