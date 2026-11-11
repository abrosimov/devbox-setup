---
note_id: "20261103150301"
created: 2026-11-03
modified: 2026-11-11
language: en
type: design
subtype: finding
note_role: artifact
artifact_kind: finding
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Language facts — Go"]
tags: [fuzzing, design/finding, lang/go, h5, h3, h4]
addresses: ["[[H5-harness-conventions]]", "[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]"]
grounded_in: ["[[07-lang-go|R7]]"]
realised_by: ["[[skill-go-fuzzing]]"]
tested_by: ["[[eval-family-E-conventions]]"]
decided_by: ["[[FTW-D-007-go-target-version]]"]
related: ["[[language-facts-python]]", "[[language-facts-rust]]"]
opens: ["[[FTW-OQ-003-go-skip-and-minimisation]]", "[[FTW-OQ-004-go-ossfuzz-shim]]"]
---
# Language facts — Go

[[07-lang-go|R7]] is a historical research snapshot, including its recorded Go 1.27.3 source and
binary checks. This methodology pass does not rerun that toolchain or establish those details
for another installed version. [[FTW-D-007-go-target-version]] must not silently become a
permanent latest-version claim.

## Operations to specify at authoring

| Operation | Go-specific contract | Required evidence |
|---|---|---|
| Discover and build | Follow native `testing.F` naming/signature and supported input types for the selected toolchain | Actual target discovery and compilation; `go vet` alone is not a compile/replay check |
| Replay seeds | Use `f.Add` and/or native `testdata/fuzz/<FuzzName>/` records following repository conventions | Ordinary test replay with observed exit and per-case results |
| Search | Select the intended package and target; use supported limits for the admitted experiment | Actual command, toolchain, engine output and observed run status |
| Reject invalid input | Handle expected errors/skip according to the target contract | Known accepted/rejected examples exercise the intended product calls |
| Preserve useful input | Export useful generated inputs from transient cache to a durable replay location | Native corpus encoding, input provenance and successful replay |
| Triage and reduce | Preserve original input, verify the symptom and allow only bounded reduction/reproduction | Raw diagnostic and independent replay, with unfinished reduction explicit |
| Decode structure | Use native primitive arguments or an existing justified fuzzing-side decoder | Bounds, decoder version and raw engine input retained |

Record investigation, compilation and automatic minimisation as part of the experiment effort.
Save interrupted work and corpus context for the research checkpoint. A local engine limit is not
an answer to the research question or a reason to reopen it on the next agent invocation.
Native cache location, output fields, skip handling, timeout behaviour, minimisation defaults and
platform support must be verified against the version actually used. Do not infer product OOM
or hang classification solely from worker exit or zero progress.

## Verification sources and boundaries

Use the official [Go fuzzing documentation](https://go.dev/doc/security/fuzz/) and the matching
[`testing` package documentation](https://pkg.go.dev/testing), then the selected toolchain's
sources for behaviour not documented there. Record source date/version and a small relevant
local check when authoring. [[FTW-OQ-003-go-skip-and-minimisation]] tracks unresolved detail.

PBT and hybrid PBT bridges, including `rapid.MakeFuzz`, are excluded by
[[fuzzing-vs-pbt-boundary]]. OSS-Fuzz shims and continuous-fuzzing infrastructure are not implied
by a local harness request; [[FTW-OQ-004-go-ossfuzz-shim]] is relevant only if that infrastructure
is separately in scope. This note supplies a Go adapter specification, not executed assurance.
