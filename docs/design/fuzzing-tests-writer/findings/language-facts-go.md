---
note_id: "20261103150301"
created: 2026-11-03
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
toolchain: "go1.27.3 (facts verified on go1.24.7 locally and against go1.27.3 sources)"
decided_by: ["[[FTW-D-007-go-target-version]]"]
related: ["[[language-facts-python]]", "[[language-facts-rust]]"]
opens: ["[[FTW-OQ-003-go-skip-and-minimisation]]", "[[FTW-OQ-004-go-ossfuzz-shim]]"]
---
# Language facts — Go (1.27.3)

Source: [[07-lang-go|R7]]; every fact below is re-verified against the `go1.27.3` sources in R7 §8.

| Topic | Fact |
|---|---|
| Engine and contract | `func FuzzXxx(*testing.F)` in `*_test.go`; exactly one `f.Fuzz(func(t *testing.T, args…))`; argument types limited to `[]byte string bool byte rune float32 float64 int* uint*`; unsupported types panic at run time; no custom mutators (proposal #48815 still open), no dictionaries, no struct arguments. |
| Platforms | `-fuzz` needs coverage instrumentation: amd64/arm64 on linux, darwin, windows, freebsd. |
| Failure = | `t.Fail*`, panic, `os.Exit`, stack overflow, or one input taking > 1 s (`workerTimeoutDuration`). A worker killed by the OOM killer records **no crash**. No sanitizer, no leak check, no allocation cap. |
| Seed corpus | `f.Add(...)` plus files in `testdata/fuzz/<FuzzName>/` (`go test fuzz v1`, one Go literal per line); plain `go test` runs them as subtests, so the seed corpus **is** a regression suite. `file2fuzz` converts raw seeds. |
| Generated corpus | `$GOCACHE/fuzz/<module>/<pkg>/<FuzzName>`; unbounded; `go clean -fuzzcache`; CI runners start empty unless the directory is persisted. |
| Failing input | minimised (string/byte arguments only, best-effort), written to `testdata/fuzz/<FuzzName>/<hash>`, `To re-run: go test -run=FuzzX/<hash>`; until fixed, every later `-fuzz` run fails in the baseline phase — never delete the file to "make fuzzing run again". |
| Invocation that works | `go test -run='^$' -fuzz='^FuzzX$' -fuzztime=10m -parallel=N ./pkg` — one package, one target, anchored, budgeted; `-fuzz` is incompatible with `-coverprofile` and the profiling flags; `-race` works at ≈6× cost. |
| Output for the campaign script | `fuzz: elapsed: …, execs: N (r/sec), new interesting: k (total: T)` every second; under `-json` as `Action:"output"` events (Go 1.27 adds `OutputType`); `GODEBUG=fuzzdebug=1` prints per-input details. |
| Skip-invalid idiom | `t.Skip("reason")` (self-documenting) or `return`; expected errors `return`; unexpected `t.Fatalf`. |
| Property-based twin | `pgregory.net/rapid` v1.3.0 (2026-03): typed generators, shrinking, `T.Repeat` state machines, `rapid.MakeFuzz` bridges a property into `f.Fuzz`; `testing/quick` frozen; gopter dormant; google/gofuzz archived (fork `sigs.k8s.io/randfill`). |
| Structure | go-fuzz-headers `ConsumeFuzzer` / `GenerateStruct`; `rapid.MakeFuzz`; decode inside the target; costs: instrumented decoder, opaque corpus, no structured shrinking. |
| Continuous fuzzing | OSS-Fuzz rebuilds native targets with `go-118-fuzz-build`: `F.Add` is a no-op, named types panic, `t.Skip` panics with a sentinel; seeds must also ship as `seed_corpus.zip`; ClusterFuzzLite same contract, `address` sanitizer only. |
| New since 1.24 | `F.Attr` / `F.Output` (1.25); `F.ArtifactDir` + `go test -artifacts -outputdir` (1.26) — the sanctioned place for campaign artefacts; `OutputType` on `-json` output events, `stdversion` vet by default (1.27). No fuzzing-engine change in 1.25–1.27. |
| Yield evidence | slice-bounds panics dominate; unbounded allocation (archive/tar CVE-2022-2879, x/net/html CVE-2025-58190, debug/gosym #81191), infinite loops (#46288, #56129), round-trip inconsistencies caught by the seed corpus as a unit test (net/netip #67126); one false-positive hang (#56932). |

## Decision rule for typed Go APIs (R7 §5.4)

bytes/strings from a format → native `f.Fuzz` with a round-trip oracle; typed values with algebraic
laws → `rapid.Check` (+ `MakeFuzz` only if a scheduled fuzz job exists); enumerable domain or thin
wrapper over the standard library → table test; typed API fed from bytes → native fuzz on the byte
entry point + rapid on the logic; concurrency-sensitive API → rapid state machine under `-race`.

## Harness skeleton

See R7 §5.2 (round trip, size bound, skip-invalid, three seeds); the ten-point review checklist is
R7 §5.3; CI recipe R7 §5.5 (seed corpus in the normal job, `-fuzz` in a dedicated job with the fuzz
cache persisted).
