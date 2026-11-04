---
note_id: "202611031506007"
created: 2026-11-03
language: en
type: meta
subtype: decision
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-D-007"]
tags: [fuzzing, design/decision]
status: accepted
supersedes: []
superseded_by: []
related: ["[[language-facts-go]]", "[[skill-go-fuzzing]]"]
---
# FTW-D-007: Go facts target 1.27.3 and are verified against sources when the binary is unavailable

## Decision

The Go skill states Go 1.27.3 as its toolchain and `GOTOOLCHAIN=go1.27.3` + `GOPROXY=https://proxy.golang.org,direct` as the way to obtain it. Facts researched on go1.24.7 were re-verified against the `go1.27.3` sources (`testing/fuzz.go`, `internal/fuzz/worker.go`, `cmd/go/internal/test/test.go`), the 1.25–1.27 release notes (R7 §8) and a run on the real go1.27.3 binary (R7 §8.1).

## Context

The user set 1.27.3 as the target; `dl.google.com` is blocked from the research session, so the first verification was against the `go1.27.3` sources. The user then pointed at `proxy.golang.org`: `GOTOOLCHAIN=go1.27.3` with `GOPROXY=https://proxy.golang.org,direct` fetches the toolchain as the module `golang.org/toolchain@v0.0.1-go1.27.3.linux-amd64`, and the facts were re-run on the real binary (R7 §8.1). The repository itself does not pin Go (brew formula).

## Alternatives considered

(a) Keep 1.24.7 facts unqualified — stale. (b) Wait for the binary — blocks the design.

## Consequences

No fuzzing-engine change in 1.25–1.27; the skill gains `F.ArtifactDir`/`-artifacts` for campaign artefacts and `OutputType` in `-json` parsing; throughput numbers are marked machine-specific.

## Reopen when

Go 1.28 release notes mention fuzzing, or the local toolchain can be upgraded and the three throw-away runs repeated.
