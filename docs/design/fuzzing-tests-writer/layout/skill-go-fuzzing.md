---
note_id: "20261103150405"
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
aliases: ["Skill: go-fuzzing", "go-fuzzing"]
tags: [fuzzing, design/component, design/skill, lang/go, h3, h5]
addresses: ["[[H5-harness-conventions]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]"]
realises: ["[[language-facts-go]]", "[[oracle-ladder]]", "[[fuzzing-vs-pbt-boundary]]"]
tested_by: ["[[eval-family-E-conventions]]", "[[eval-family-B-oracle]]"]
decided_by: ["[[FTW-D-007-go-target-version]]", "[[FTW-D-002-six-skills]]", "[[FTW-D-008-pbt-out-of-scope]]"]
opens: ["[[FTW-OQ-003-go-skip-and-minimisation]]", "[[FTW-OQ-004-go-ossfuzz-shim]]"]
target_path: "roles/devbox/files/dot_ai/skills/go-fuzzing/"
codex_shared: true
related: ["[[reference-documents]]"]
---
# Skill `go-fuzzing`

**Problem**: Go harnesses fail for convention reasons — wrong `-fuzz` invocation, unsupported
argument types, seeds that the OSS-Fuzz shim ignores, deleted failing seeds, crash-only targets on
format readers that have an encoder, and rapid property tests written where a fuzz target was asked
for (or the reverse).

## Carries (from [[language-facts-go]], Go 1.27.3)

- `testing.F` contract, allowed types, one-`f.Fuzz` rule; platform limits; what the engine counts
  as a failure and what it cannot see (OOM-killed worker).
- Harness skeleton (R7 §5.2) and the ten-point review checklist (R7 §5.3).
- Scope rule: native `f.Fuzz` for bytes/strings from a format; `out-of-scope: pbt-track` for typed
  laws (rapid is PBT); `out-of-scope: unit-tests` for enumerable domains and thin wrappers. The
  `rapid.MakeFuzz` bridge only when a rapid property already exists and the charter names coverage
  guidance ([[fuzzing-vs-pbt-boundary]]).
- Structure from bytes: typed `f.Fuzz` arguments, go-fuzz-headers `ConsumeFuzzer`/`GenerateStruct`,
  hand-written decoders; `file2fuzz` for raw seeds; costs stated (instrumented decoder, opaque
  corpus, no structured shrinking).
- Seed corpus semantics (`f.Add` + `testdata/fuzz/`, baseline failure on committed crashers),
  `$GOCACHE/fuzz` and `go clean -fuzzcache`.
- Invocation template, `-json` parsing incl. `OutputType`, `GODEBUG=fuzzdebug=1`, `-race` cost.
- OSS-Fuzz / ClusterFuzzLite shim differences (`F.Add` no-op, named types panic, seeds as zip).
- CI recipe (R7 §5.5) and `F.ArtifactDir` + `-artifacts` for campaign artefacts.
- Toolchain: `GOTOOLCHAIN=go1.27.3` with `GOPROXY=https://proxy.golang.org,direct`.
- Twelve rules R1–R12 of R7 §5.1 tagged by hypothesis.

## Size and shape

≤ 250 lines; pointer paragraph added to the existing `go-testing` skill.

## Evals shipped with the skill

Trigger queries: "write a Go fuzz test for", "testing.F", "go test -fuzz keeps failing", "fuzz the
decoder in pkg/codec"; negatives: "table-driven tests with testify", "rapid property test for
Money", "benchmark this Go function". Content evals: R7 §6 E1–E9 with E2 restated as a hand-off.

Sources: R7 §5, §8.
