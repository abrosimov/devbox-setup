---
note_id: "20261103150907"
created: 2026-11-03
language: en
type: research
subtype: annex
note_role: artifact
artifact_kind: research-report
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["R7"]
tags: [fuzzing, design/research, h3, h4, h5]
topic: "Go native fuzzing ecosystem (verified against go1.27.3 sources in section 8)"
addresses: ["[[H3-random-seeds-for-structured-input]]", "[[H4-crash-only-oracle]]", "[[H5-harness-conventions]]"]
related: ["[[research-index]]", "[[research-corpus]]"]
---
# Go fuzzing ecosystem — what a Go fuzz-test-writing agent must know

Research date: 2026-11-03. Local toolchain used for confirmation: `go1.24.7 linux/amd64` (`go help testflag`, `go doc testing.F`, source of `internal/fuzz`, and three throw-away fuzz runs under `scratchpad/research/exp*`). `go.dev` and `google.github.io` were not reachable from this session; their content was read from the upstream Markdown in `golang/website` and `google/oss-fuzz` on raw.githubusercontent.com, which is the same source the sites render.

## 0. Summary for the design doc

1. **One engine, one contract.** Since Go 1.18 fuzzing is built into `go test`: `func FuzzXxx(*testing.F)` in a `*_test.go` file, exactly one `f.Fuzz(func(t *testing.T, args...))`, arguments restricted to `[]byte`, `string`, `bool`, the int/uint family, `float32/64` [S1, S4]. There is no custom mutator, no struct argument, no dictionary; proposal #48815 is still "Incoming" after five years [S9]. Structure must be built *inside* the target from bytes (go-fuzz-headers `ConsumeFuzzer`, or hand-written decoding) — this is the Go answer to H3.
2. **Seed corpus is dual and is a regression suite.** `f.Add(...)` plus files in `testdata/fuzz/<FuzzName>/` (format: first line `go test fuzz v1`, one Go literal per line). Plain `go test` runs *only* the seed corpus as subtests; `-fuzz` additionally loads the generated corpus from `$GOCACHE/fuzz/<module>/<pkg>/<FuzzName>` [S1, S4, S6, S34]. A failing input is minimised and written to `testdata/fuzz/<FuzzName>/<hash>` and reproduced with `go test -run=FuzzName/<hash>` — it is a unit test from then on, and until it is fixed every later `-fuzz` run **fails during baseline** ("failure while testing seed corpus entry") [S34]. Agents must commit it, and must not re-fuzz over an unfixed crasher.
3. **Oracles are ordinary test assertions.** Failure = `t.Fail*`/`t.Error*`/`t.Fatal*`, a panic, `os.Exit`, stack overflow, or one input taking > 1 s [S1, S6]. Nothing else is detected: no sanitiser, no leak check, no allocation cap (OOM kills the worker without recording a crash [S6]). The Go team's own examples are all **round-trip** properties (hex encode/decode [S4], `url.ParseQuery` re-encode [S3], `Reverse(Reverse(s))==s` + UTF-8 validity [S2]). This is H4: an agent that writes only "does not panic" targets finds mostly index-out-of-range panics in parsers and nothing in typed APIs.
4. **The engine never stops by itself** unless `-fuzztime` is set; the docs say the user decides when to stop and describe the expected `new interesting` curve (spike, taper, occasional bursts) [S1]. Stopping rule input for H2: parse `fuzz: elapsed: …, execs: N (r/sec), new interesting: k (total: T)` lines (available as `Action:"output"` events under `-json` [S34]); stop a target when `k` has been flat for a chosen window or when `-fuzztime` expires; the only persistent progress signal is the growth of `$GOCACHE/fuzz/.../<FuzzName>`.
5. **Platform and scope limits:** `-fuzz` needs coverage instrumentation (`-d=libfuzzer`, 8-bit edge counters) which exists only on amd64/arm64 for linux/darwin/windows/freebsd; one package and exactly one fuzz test per `-fuzz` invocation; incompatible with `-coverprofile`/profiling flags; `-cpu` ignored; `-parallel` = worker processes [S5, S6, S34].
6. **Conventions that make harnesses compile and stay maintainable (H5):** thin deterministic target, no shared state, no retention of input slices, `t.Skip` (or `return`) for invalid input shapes, expected errors are `return`, `-run='^$' -fuzz=X -fuzztime=…` in a dedicated job, `go test ./...` (seed corpus only) in the normal CI job, `go vet` checks `FuzzXxx` signatures [S1, S4, S35].
7. **Alternatives, ranked for today:** `pgregory.net/rapid` (v1.3.0, Mar 2026; typed generators, automatic shrinking, state-machine tests, `rapid.MakeFuzz` bridges a property into `f.Fuzz`) is the recommended tool for typed APIs; `gopter` is dormant (v0.2.11 Apr 2024, 49 importers); `testing/quick` is frozen and has no shrinking; `google/gofuzz` archived Jan 2024 (fork `sigs.k8s.io/randfill`); `dvyukov/go-fuzz` is legacy but still the only route to libFuzzer dictionaries and is what OSS-Fuzz/ClusterFuzzLite actually run (native targets are rebuilt as libFuzzer binaries by `go-118-fuzz-build`, where `F.Add` is a no-op) [S11–S21].
8. **Decision rule (H1):** native fuzz for byte/string-consuming parsers, decoders, protocol/format readers and anything reachable from untrusted input; rapid/gopter property tests for typed APIs with algebraic laws; table tests when the input domain is enumerable or the function is a thin wrapper over the standard library.
9. Evidence of what Go fuzzing finds in practice: panics (slice bounds) dominate, but a steady stream of **unbounded allocation / OOM / apparent hangs** (archive/tar CVE-2022-2879, regexp/syntax, x/net/html CVE-2025-58190, debug/gosym #81191) and **round-trip inconsistencies** (net/netip #67126) exist — all require a memory- or property-aware oracle to be caught locally [S23–S30].

## 1. Scope and question answered

What an agent that writes and runs Go fuzz tests must know about: the native engine's API, flags, corpus formats and locations, output and failure handling, limitations; the older/alternative tooling and whether it is still relevant; concrete bugs found by Go fuzzing; conventions; interactions with `-race`, `-short`, build tags and generics. Out of scope: generic fuzzing theory (covered by the sibling reports), Rust/Python.

## 2. Corpus ledger

| id | source + edition/date | locator | used for | status |
|---|---|---|---|---|
| S1 | Go Fuzzing landing page, golang/website `_content/doc/security/fuzz/index.md` (master, read 2026-11-03; renders at go.dev/doc/security/fuzz) | sections Overview, Requirements, Suggestions, Running, Command line output, Failing input, Custom settings, Corpus file format, Glossary | requirements, output semantics, failure handling, limits | include |
| S2 | Tutorial "Getting started with fuzzing", `_content/doc/tutorial/fuzz.md` (same repo) | final `FuzzReverse`, sample output, "To re-run" | round-trip pattern, Skip vs return | include |
| S3 | Blog "Fuzzing is Beta Ready", Hockman & Conrod, 2021-06-03, `_content/blog/fuzz-beta.md` | `FuzzParseQuery` example; cache warning | oracle pattern, memory/cache caveats | include |
| S4 | `testing` package doc, Go 1.24.7, `go doc testing.F`, `go doc testing.F.Fuzz`, `go doc -all testing` § Fuzzing (matches pkg.go.dev/testing#hdr-Fuzzing) | type F, F.Add, F.Fuzz, Fuzzing section | API contract | include |
| S5 | `go help testflag`, Go 1.24.7 | `-fuzz`, `-fuzztime`, `-fuzzminimizetime`, `-parallel`, `-run`, `-json` | flags | include |
| S6 | Go 1.24.7 source: `src/internal/fuzz/{encoding.go,fuzz.go,worker.go,minimize.go,coverage.go,counters_*.go}`, `src/internal/platform/supported.go`, `src/cmd/go/internal/test/test.go`, `src/cmd/go/internal/work/init.go`, `src/testing/fuzz.go` | encVersion1; log format strings; `workerTimeoutDuration = 1s`; `isMinimizable`; `FuzzInstrumented`; `-d=libfuzzer`; cmd/go fatal messages | mechanics, exact limits | include |
| S7 | Go 1.18 release notes, `_content/doc/go1.18.md` § Fuzzing | memory warning, unlimited `$GOCACHE/fuzz`, `go clean -fuzzcache` | caveats | include |
| S8 | Design draft "Design Draft: First Class Fuzzing", Hockman, golang/proposal `design/draft-fuzzing.md` (undated; proposal accepted as #44551) | types, corpus encoding, seed-as-test rationale, limitations | rationale | include |
| S9 | golang/go #48815 "proposal: testing: custom mutator support for fuzzing" (opened 2021-10-06; status Incoming, last comment 2025-05-12) + `design/48815-custom-fuzz-input-types.md` | status, proposed interface | limitation: no custom mutators | include |
| S10 | golang/go #50192 "cmd/go: support continuously running fuzzing with OSS-Fuzz" (2021-12-15, closed 2024-03-21) | how OSS-Fuzz runs native targets | OSS-Fuzz | include |
| S11 | OSS-Fuzz docs `docs/getting-started/new-project-guide/go_lang.md` (master) | project.yaml, `compile_go_fuzzer`, `compile_native_go_fuzzer`, F.Add note | OSS-Fuzz | include |
| S12 | OSS-Fuzz `infra/base-images/base-builder/compile_native_go_fuzzer` + `go_utils.sh` (master) | `build_native_go_fuzzer[_legacy]`, `go-118-fuzz-build[_v2]`, coverage mode | OSS-Fuzz mechanics | include |
| S13 | AdamKorcz/go-118-fuzz-build README + `testing/f.go` (main) | shim semantics: `Add` no-op, type switch, `Skip` panics with sentinel | OSS-Fuzz limits | include |
| S14 | ClusterFuzzLite docs `docs/build-integration/go_lang.md` (main) | Go steps, sanitizer `address` only | CFL | include |
| S15 | dvyukov/go-fuzz README (master, 4.8k stars; pkg.go.dev pseudo-version 2024-09-24) | `Fuzz(data []byte) int`, return values, workdir layout, `-libfuzzer`, Trophies | legacy tooling | include |
| S16 | dvyukov/go-fuzz-corpus (GitHub page, 209 stars, ~90 dirs) | seed corpora per format | seeds | include |
| S17 | AdaLogics/go-fuzz-headers README + pkg.go.dev (pseudo-version 2024-08-06, 36 importers) | `NewConsumer([]byte)`, `GenerateStruct`, `GetString`, … | structure-aware inputs | include |
| S18 | google/gofuzz README; GitHub "archived 2024-01-10"; pkg.go.dev/sigs.k8s.io/randfill ("fork of github.com/google/gofuzz, which was archived", v1.0.0 2025-03-04) | status | alternatives | include |
| S19 | pkg.go.dev/testing/quick | "frozen and is not accepting new features", `Check`, `CheckEqual`, `Config` | alternatives | include |
| S20 | pgregory.net/rapid: pkg.go.dev (v1.3.0, 2026-03-30), README, `engine.go` flags | `MakeFuzz`, `Check`, `T.Repeat`, flags/defaults, failfile replay | PBT | include |
| S21 | leanovate/gopter README + pkg.go.dev versions (v0.2.11 2024-04-03; v0.2.9 2020-11-09; 49 importers; 639 stars) | features, status | PBT | include |
| S22 | pkg.go.dev/golang.org/x/tools/cmd/file2fuzz | binary → corpus file conversion | seeds | include |
| S23 | golang/go #67126 "net/netip: FuzzParse failures" (2024-05-01) | round-trip identity failure on seed `[::ffff:192.0.2.128%eth0]:1` | bug class: inconsistency | include |
| S24 | golang/go #53350 encoding/xml reflect panic (2022-06-13, fixed) | "Found by ngolo-fuzzing on oss-fuzz" | bug class: panic | include |
| S25 | golang/go #63337 debug/buildinfo, internal/xcoff OOM (2023-10-02, fixed 2024-02) | endless zero reader → OOM; found by ngolo-fuzzing/OSS-Fuzz | bug class: OOM/hang | include |
| S26 | golang/go #81191 debug/gosym multi-GB allocation on 90-byte input (2026-08-28, fixed 2026-09) | "first surfaced as an apparent hang under `go test -fuzz`" | bug class: allocation | include |
| S27 | golang/go #70179 x/net/html ParseFragment OOM, CVE-2025-58190 (2024-11-04, fixed 2025-10) | maintainer fuzzed `html.Parse` | bug class: OOM | include |
| S28 | golang/go #54853 archive/tar unbounded memory, CVE-2022-2879 (2022-09-03) | credited to Adam Korczynski (ADA Logics) and OSS-Fuzz | bug class: memory | include |
| S29 | golang/go #56932 x/image/webp "infinite loop" (2022-11-24, closed WAI) | 28-byte input → 12043×4098 image; false positive | false-positive class | include |
| S30 | api.github.com search `repo:golang/go "found by fuzzing"` (84 results) and `"OSS-Fuzz" label:Security` (11), read 2026-11-03 | #75516, #70584, #64446, #59810 (slice bounds); #55949 regexp memory; #46288 x/net/html infinite loop; #46242 archive/zip; #55338 gob preallocation; #56129 debug/elf loop; #43786 P-224 incorrect ops | bug class distribution | include |
| S31 | Go vuln DB GO-2022-0972 / CVE-2022-41719 (shamaton/msgpack/v2 `Unmarshal` panic; credit Red Canary) | third-party example | include |
| S32 | `go help clean` (1.24.7) | `-fuzzcache` semantics | cache | include |
| S33 | `src/cmd/go/testdata/script/test_fuzz_test_race.txt` (1.24.7) | `-fuzz -race` supported; no false race on seeds | interactions | include |
| S34 | Local experiments 2026-11-03, go1.24.7 linux/amd64 (`scratchpad/research/exp`, `exp2`, `exp3`) | outputs quoted in §3 | confirmation | include |
| S35 | `go tool vet help tests` (1.24.7) | vet checks Fuzz names/signatures | conventions | include |
| S36 | golang/go #48820 (minimisation hang, 2021; workaround `-fuzzminimizetime=0x`) — from search snippet only | not verified in detail | park |
| S37 | Red Canary msgpack blog, free5GC CVE-2022-43677 blog | hosts unreachable from session | park (UNVERIFIED beyond S31) |

## 3. Claim sheets

### 3.1 Native engine mechanics (coverage-guided greybox, libFuzzer lineage)

| claim | source | validity region | failure modes | confidence |
|---|---|---|---|---|
| Fuzz test = `func FuzzXxx(*testing.F)` in `*_test.go`; target = the one `f.Fuzz(func(*testing.T, args...))`; allowed arg types: `[]byte string bool byte rune float32 float64 int int8 int16 int32 int64 uint uint8 uint16 uint32 uint64`; "More types may be supported in the future" | S1 Requirements; S4 F.Fuzz | all Go ≥1.18 | named types (`type ID string`), structs, pointers, slices other than `[]byte` are rejected at run time (`go test` panics in `F.Fuzz`) | high |
| `F.Fuzz` must be called exactly once (unless `F.Skip`/`F.Fail` first); returning without calling it is an error; inside the target only `*T` methods plus `F.Failed`/`F.Name` are allowed | S4; S6 `testing/fuzz.go:636-663` | all | `f.Log`/`f.Skip` inside target → panic | high |
| Coverage: `go test -fuzz` compiles with `-d=libfuzzer`, producing 8-bit edge counters between `_counters`/`_ecounters`; an input is "interesting" when it sets counter bits not in the corpus mask | S6 `work/init.go:95-99`, `counters_supported.go`, `coverage.go`; S1 Command line output | linux/darwin/windows/freebsd × amd64/arm64 (`FuzzInstrumented`) | elsewhere `-fuzz` is refused: `-fuzz flag is not supported on GOOS/GOARCH` (`test.go:715`); without counters the engine warns "fuzzing will run without coverage guidance" | high |
| Workers: `-parallel` = number of worker *processes* while fuzzing (default GOMAXPROCS); `-cpu` ignored; each worker runs inputs in 100 ms batches and is killed if one input exceeds 1 s (`workerTimeoutDuration`) | S5; S6 `worker.go:24-30` | all | a slow-but-legitimate input (large image decode) is reported as a hang; see S29 | high |
| Worker killed by a non-crash signal (e.g. Linux OOM killer `SIGKILL`) → "fuzzing process terminated by unexpected signal; no crash will be recorded" | S6 `worker.go:170-176` | Linux/macOS | **memory blow-ups are invisible** unless the target bounds them itself | high |
| Mutation + minimisation: only `string`/`[]byte` arguments are minimised (`isMinimizable`); a minimised candidate is accepted if the target returns *any* error (message need not match) or preserves coverage; interesting inputs are also minimised; `-fuzzminimizetime` default 60 s, `0` disables | S6 `minimize.go:11`, `worker.go:876-920`; S1 Custom settings | all | integer-only targets are never minimised; in one of three local runs the crasher was written unminimised (10 filler bytes + rune) with no `fuzz: minimizing` line — cause not established (UNVERIFIED) | high / medium for the anomaly |
| Order: all other tests, benchmarks, examples and *other fuzz tests' seed corpora* run before fuzzing begins; `-run='^$' -fuzz=X` skips them | S5 `-fuzz`; S1 Running | all | forgetting `-run` makes a fuzz job pay for the full unit suite first | high |
| `-fuzz` regexp must match exactly one fuzz test and the package argument exactly one package in the main module; otherwise `testing: will not fuzz, -fuzz matches more than one fuzz test: [FuzzReverse FuzzMax FuzzShortGate]` + FAIL, or `cannot use -fuzz flag with multiple packages`, or `cannot use -fuzz flag on package outside the main module` | S5; S6 `test.go:718,735`; S34 | all | agents that pass `./...` or `-fuzz=Fuzz` get a non-zero exit with no fuzzing done | high (observed) |
| `-fuzz` is incompatible with `-coverprofile` and the profiling flags (`cannot use -coverprofile flag with -fuzz flag`) | S6 `test.go:721-724`; S34 | all | coverage of a fuzz *session* cannot be measured with `-cover`; use the seed corpus under `go test -cover -run=FuzzX` instead | high (observed) |
| `-fuzztime` accepts a duration or `Nx` executions; default "run forever"; `F.Fuzz` returns only on failure, time-out or signal | S5; S4 | all | no built-in saturation stop | high |

### 3.2 Corpus: seed vs generated, file format, failure handling

| claim | source | validity region | failure modes | confidence |
|---|---|---|---|---|
| Seed corpus = `f.Add` entries + files in `testdata/fuzz/<FuzzName>/`; it runs under plain `go test` as subtests named `FuzzX/seed#N` (for `f.Add`) and `FuzzX/<filename>` (for files); it is "optional, but the fuzzing engine may find bugs more efficiently when provided with a set of small seed inputs with good code coverage" and "can also serve as regression tests" | S4 Fuzzing section; S34 (`--- PASS: FuzzReverse/seed#0`) | all | `f.Add` with wrong types/arity panics at run time | high |
| Generated corpus lives in `$GOCACHE/fuzz/<module path>/<pkg>/<FuzzName>/<hash>` in the same text format; used only while fuzzing; unbounded in size; removed by `go clean -fuzzcache` (not by `go clean -cache`) | S1 Glossary; S7; S32; S34 (`$GOCACHE/fuzz/example.com/fuzzexp/FuzzReverse` held 6 files) | all | CI runners start with an empty cache every time → every job re-discovers the same coverage unless the cache dir is persisted | high |
| File format: line 1 `go test fuzz v1`; one value per line as a Go literal: `string("…")`, `[]byte("…")`, `int64(572293)`, `byte('x')`, `rune('x')`, `float64(1.5)`, `math.Float64frombits(0x…)` for unusual NaNs, `int32(n)` for invalid runes; parsed with `go/parser` as a one-argument call expression; CRLF tolerated on the version line | S6 `encoding.go`; S1 Corpus file format; S34 (file content `go test fuzz v1\nstring("ɰ")`) | all | a Windows checkout with `autocrlf` once produced "unknown encoding version" (search snippet, UNVERIFIED) | high |
| `file2fuzz [-o dir] files…` converts raw binary seeds (e.g. go-fuzz-corpus) into `[]byte(...)` corpus files named by SHA-256 | S22 | single-`[]byte` targets | multi-argument targets need hand-written lines | high |
| On failure: input minimised, written to `testdata/fuzz/<FuzzName>/<hash>`, log prints `Failing input written to …` and `To re-run:\ngo test -run=FuzzX/<hash>`; if the directory is read-only it goes to the fuzz cache instead | S1 Failing input; S6 `testing/fuzz.go:373-375`; S34 | all | the file is a **regression test immediately**: a subsequent `-fuzz` run fails in the baseline phase with `failure while testing seed corpus entry: FuzzReverse/<hash>` (observed) — the agent must fix the bug (or deliberately delete the file) before fuzzing that target again | high (observed) |
| `go-fuzz` corpora are raw files under `workdir/corpus`, crashers under `workdir/crashers` (`<hash>`, `.quoted`, `.output`); not readable by the native engine without `file2fuzz` | S15 | legacy | mixing layouts | high |

### 3.3 Output, observability and stopping (H2)

| claim | source | validity region | failure modes | confidence |
|---|---|---|---|---|
| Progress lines (stderr of the test binary, every second): `fuzz: elapsed: 0s, gathering baseline coverage: 3/3 completed, now fuzzing with 2 workers` → `fuzz: elapsed: 3s, execs: 86342 (28778/sec), new interesting: 2 (total: 35)`; when a crasher is found: `fuzz: minimizing N-byte failing input file`; `total` = seed+cache entries + new interesting | S6 `fuzz.go:304,374,729-741`; S1 Command line output; S34 | all | "new interesting" counts entries added *this run*; a warm cache makes a fresh run look saturated from the start | high |
| Expected trend per Go docs: new interesting "typically spike early, taper off as coverage grows, and occasionally burst when new code paths are found"; "Fuzzing has no fixed end. The user decides how long to run it" | S1 | all | nothing in the engine implements a saturation stop | high |
| `-json` emits the same lines as `{"Action":"output","Test":"FuzzMax","Output":"fuzz: elapsed: …"}` events followed by `pass`/`fail` for the test and the package — machine-parseable with one regex | S5 `-json`; S34 (full event stream captured) | all | no structured coverage field; `GODEBUG=fuzzdebug=1` adds `DEBUG new interesting input, id, parent, gen, new bits, total bits, size, exec time` lines (observed) | high |
| Baseline phase runs seed + cache entries first; failing there is reported as a seed-corpus failure, not a new finding | S6 `fuzz.go:245-250`; S34 | all | — | high |

### 3.4 Limitations the agent must not fight

| claim | source | validity region | failure modes | confidence |
|---|---|---|---|---|
| No custom mutators / structured input types: #48815 open since 2021, status Incoming (2023), last design iteration 2025 | S9 | — | workarounds: decode bytes inside the target (go-fuzz-headers), or `rapid.MakeFuzz` | high |
| No dictionaries, no `-max_len`, no ASan/MSan/UBSan equivalent (Go is memory-safe; cgo bugs are not caught); no leak/alloc cap; the only resource oracle is the 1 s per-input timeout | S1, S6, S8 (dictionaries "future work") | — | OOM = silent worker death; CPU blow-up < 1 s invisible | high |
| Only module mode; package must be in the main module | S6 `test.go:735`; S8 | — | fuzzing a dependency requires a wrapper package in your module | high |
| Running the generated corpus is not possible under plain `go test`; there is no `-fuzzdir`; corpus minimisation across the cache (#49290) not implemented | S8; S10 | — | cache grows forever (S7) | high |
| Fuzzing "can consume a lot of memory and may impact your machine's performance"; lower `-parallel` | S7, S3 | — | — | high |

### 3.5 Alternative and complementary tooling

| tool | what it is | state (date) | relation to native fuzzing | recommend? | source |
|---|---|---|---|---|---|
| dvyukov/go-fuzz | AFL-style engine; target `func Fuzz(data []byte) int` returning 1 (prioritise) / 0 / −1 (drop); `go-fuzz-build` + `go-fuzz`; `-libfuzzer` mode emits an archive for `clang -fsanitize=fuzzer` (Linux); modules support "preliminary", vendoring unsupported, final build in GOPATH mode | last pseudo-version 2024-09-24; README does not mention native fuzzing | pre-dates native; its trophy list (cmd/compile, net/http, encoding/gob, image/*, archive/*, regexp, html/template, vitess, hcl …) is the historical evidence base for "what Go fuzzing finds" | only when libFuzzer features (dictionaries, `-max_len`, OSS-Fuzz legacy targets) are needed | S15 |
| go-fuzz-corpus | ~90 directories of seed files per format (png, gif, jpeg, gob, json, xml, tar, zip, asn1, bzip2, tls, x509, …) | 231 commits, date not shown | reusable seeds; convert with `file2fuzz` | yes, as seeds | S16, S22 |
| AdaLogics/go-fuzz-headers | `ConsumeFuzzer` over `[]byte`: `GetString/GetInt/GetUint64/GetFloat32/GetBytes/GetNBytes/GetStringFrom(chars,n)/GetBool/GetRune/GenerateStruct(&v)/FuzzMap/AddFuncs/TarBytes/CreateFiles`; "mostly used in combination with go-fuzz", any engine giving a byte slice works | pseudo-version 2024-08-06; 36 importers; used by runC, Istio, Vitess, containerd | the structure-aware layer for native `[]byte` targets; also what `go-118-fuzz-build` uses to split one buffer into typed args | yes, for structs/maps | S17, S13 |
| google/gofuzz | random struct population (`fuzz.New().NilChance().NumElements().Funcs()`), `NewFromGoFuzz(data)` bridge | archived 2024-01-10; fork `sigs.k8s.io/randfill` v1.0.0 (2025-03) | generation-based, not coverage-guided; no shrinking | prefer randfill or rapid | S18 |
| testing/quick | `Check(f, cfg)`, `CheckEqual(f, g, cfg)`, default 100 iterations, `Generator` interface | "frozen and is not accepting new features" | no shrinking, no coverage | no (legacy only) | S19 |
| pgregory.net/rapid | PBT with typed generators (`Int`, `String`, `SliceOf`, `Custom`, `Just`, `OneOf`, `Map`, `Filter`), automatic shrinking "without any user code", `T.Repeat`/`StateMachine` for model-based tests, failfile persistence and replay; flags `-rapid.checks` (100), `-rapid.steps` (30), `-rapid.shrinktime` (30 s), `-rapid.seed`, `-rapid.failfile`, `-rapid.nofailfile`, env `RAPID_*`; `rapid.MakeFuzz(prop) func(*testing.T, []byte)` plugs a property into `f.Fuzz`, reading the bytes as a little-endian `[]uint64` bit stream; README: "stronger at generating complex structured data" but "lacks coverage-guided feedback and mutations" | v1.3.0 2026-03-30 (v1.2.0 2025-02, v1.1.0 2023-08); MPL-2.0; stdlib-only deps | complementary; `MakeFuzz` gives native coverage guidance to a rapid property | **yes** — default for typed APIs | S20 |
| leanovate/gopter | ScalaCheck port: `gen`, `prop`, `arbitrary`, `commands` (stateful), regex generator, shrinkers built into generators | v0.2.11 2024-04-03 after v0.2.9 2020-11; 49 importers | same role as rapid, older API | acceptable if already in the repo; rapid otherwise | S21 |
| OSS-Fuzz (Go) | `project.yaml: language: go`, `fuzzing_engines: [libfuzzer]`, `sanitizers: [address]` only; base image `gcr.io/oss-fuzz-base/base-builder-go`; `compile_go_fuzzer <pkg> <Func> <out> [tag]` for go-fuzz-style targets (`-tags gofuzz`); `compile_native_go_fuzzer` for `FuzzXxx` → `go-118-fuzz-build[_v2] -o x.a -func FuzzX` + `$CXX … $LIB_FUZZING_ENGINE`; coverage builds use `go test -c -cover`. In the shim **`F.Add` is a no-op**, only `F.Fuzz` is supported, `_test.go` files are excluded from the build (rename e.g. `*_fuzz_test.go` → `*_test_fuzz.go`), `t.Skip` panics with a sentinel, unsupported types panic | docs master 2026-11 | native targets run **under libFuzzer**, with libFuzzer's corpus/dictionary handling; seeds come from `<fuzzer>_seed_corpus.zip`, not `f.Add` | yes for continuous fuzzing; write targets so both engines accept them | S11, S12, S13, S10 |
| ClusterFuzzLite (Go) | same build contract as OSS-Fuzz in-repo (`.clusterfuzzlite/project.yaml`, Dockerfile, `build.sh` with `compile_go_fuzzer`); sanitizer `address` only | docs main | PR-time fuzzing via GitHub Actions | yes for PR gating when a project already has OSS-Fuzz-style targets | S14 |

### 3.6 Bugs found by Go fuzzing (bug-class evidence for the oracle design)

| class | examples (issue · package · how found) | note | source |
|---|---|---|---|
| Panic (slice/index bounds, nil deref) | #75516, #75130, #70584, #64446, #63610, #62649 debug/elf; #59810 archive/zip; #69066 debug/buildinfo; #57946 math/big; #53350 encoding/xml (nil pointer → reflect panic, "Found by ngolo-fuzzing on oss-fuzz"); GO-2022-0972 msgpack `Unmarshal` | the dominant class; crash oracle suffices; mostly binary-format parsers | S30, S24, S31 |
| Unbounded / excessive allocation | #54853 archive/tar headers (CVE-2022-2879, credit ADA Logics + OSS-Fuzz, fix: 1 MiB cap); #55949 regexp/syntax; #55338 gob `decodeSlice` preallocation (~4 GB); #58755/#58754/#58603/#59817/#58886 debug/{macho,buildinfo} over-allocation (3–7 GB); #81191 debug/gosym `make([]Func, 3256877056)` from a 90-byte input, "first surfaced as an apparent hang under `go test -fuzz`"; #70179 x/net/html ParseFragment OOM (CVE-2025-58190) | native engine sees these only as a 1 s timeout or a silently killed worker; needs an allocation-bounded oracle or `debug.SetMemoryLimit`/`ulimit` discipline (agent design question) | S28, S30, S26, S27 |
| Infinite loop / hang | #46288 x/net/html ParseFragment infinite loop (Security); #56129 debug/elf `NewFile` loop (regression); #63337 internal/xcoff endless zero reader → OOM | timeout oracle catches these | S30, S25 |
| Round-trip / consistency | #67126 net/netip `FuzzParse`: `netip.AddrPort round trip identity failure: s="[::ffff:192.0.2.128%eth0]:1"` — found by running the *seed corpus* on a builder, the property being an identity check in the stdlib's own fuzz test | shows (a) property oracles find non-crash bugs, (b) seed corpora run as unit tests catch regressions | S23 |
| Incorrect computation | #43786 crypto/elliptic P-224 incorrect operations (OSS-Fuzz, Security) | differential oracle needed (reference implementation) | S30 |
| False positive | #56932 x/image/webp "infinite loop": a 28-byte header declaring 12043×4098 decoded correctly in ~2.5 s locally; closed working-as-designed | the agent must triage "hang" reports against the 1 s budget before filing | S29 |

Pattern across S30: almost everything is a **binary/text format reader in `debug/*`, `archive/*`, `encoding/*`, `image/*`, `net/*/html`, `regexp`** — direct evidence for the H1 applicability gate.

### 3.7 Interactions

| topic | claim | source | confidence |
|---|---|---|---|
| `-race` | Supported together with `-fuzz`; the toolchain's own script asserts no false race on seed execution even with `t.Parallel` in the target. Throughput cost in the local run: 34 266 execs/s → 5 208 execs/s (~6.5×) on the same trivial target | S33; S34 | high (observed); cost figure is one measurement |
| `-short` | No special semantics; `testing.Short()` is readable in the fuzz test body before `f.Fuzz`, so `if testing.Short() { f.Skip() }` works (`--- SKIP: FuzzShortGate`) | S34 | high (observed) |
| build tags | `-tags` is an ordinary build flag; OSS-Fuzz builds with `-tags gofuzz`, go-fuzz's libFuzzer mode adds `gofuzz_libfuzzer`; a native target that must also compile under `go-118-fuzz-build` should avoid `_test.go`-only helpers | S11, S12, S15, S13 | high |
| generics | Target may call generic code (`Max[T]` fuzzed via `int64` args, observed); fuzz tests themselves are plain functions (vet enforces `func FuzzXxx(*testing.F)`), so type parameters are instantiated *inside* the target, one instantiation per fuzz test or per subtest | S34; S35; S4 | high for the observation, medium for the "cannot be generic" reading (follows from the signature rule, not stated verbatim) |
| `t.Skip` vs `return` | Both leave the input un-failed; the package doc explicitly offers `T.Skip` for invalid input; the tutorial uses `return`. Under `go-118-fuzz-build` `Skip` panics with a sentinel the shim handles | S4 (pkg.go.dev summary); S2; S13 | high |
| `t.Parallel()` | Applies to the seed-corpus run only; while fuzzing, parallelism is process-level | S5 `-parallel` | high |
| vet | `go vet` "walks Test, Benchmark, Fuzzing and Example functions checking malformed names, wrong signatures" | S35 | high |

## 4. Disagreements and open questions

1. **Skip vs return for invalid inputs.** Tutorial returns, package doc suggests `t.Skip`. Functionally equivalent for pass/fail; whether a skipped input is still eligible as "interesting" for the corpus was not determined from source (UNVERIFIED). Recommendation: `t.Skip` with a reason — it is self-documenting and shows up in `-v` output.
2. **Minimisation reliability.** Two of three local crashers were minimised to one rune, one was not, without a log line. Issue #48820 (2021) reports minimisation hanging. The agent should treat minimisation as best-effort and check the committed file's size (S34, S36 — cause UNVERIFIED).
3. **OSS-Fuzz vs local semantics diverge** on `F.Add` (ignored upstream), on `t.Error` (shim ends the run immediately), and on allowed types (named types panic in the shim). A target that is "correct" locally can be silently seed-less in OSS-Fuzz (S11, S13).
4. **Memory oracle gap.** Go docs list timeout, panic, `os.Exit`, stack overflow as failure causes; the worker code explicitly declines to record OOM-killed inputs (S6). The real-world evidence (S3.6) says allocation bugs are the second most common class. Open design question for the agent: run workers under `GOMEMLIMIT`/`ulimit -v` and treat worker death as a finding to triage, or add explicit size assertions in targets (e.g. `if len(out) > 64*len(in) { t.Fatal }`).
5. **Is PBT or native fuzz better for typed APIs?** rapid's README claims better structured generation but no coverage feedback; the Go docs claim coverage guidance "reaches edge cases humans often miss". Both are right for different input shapes; `rapid.MakeFuzz` composes them, at the cost of libFuzzer-style bit-stream mutations having little semantic locality (own assessment, not sourced).
6. **No official "what to fuzz" list.** The Go docs never say "parsers"; the guidance is by example (hex, url, Reverse) plus the design draft's "programs working with arbitrary user input" (S8). The empirical answer (S3.6) is unambiguous.

## 5. Implications for the agent / skills

### 5.1 Rules (hypothesis addressed in brackets)

| # | rule | H | source |
|---|---|---|---|
| R1 | Gate: write a native fuzz target only if the function consumes `[]byte`/`string` (or ints that select a code path) from an untrusted or format-defined source; otherwise choose PBT or table tests (§5.4) | H1 | S3.6, S8 |
| R2 | Every target carries ≥3 meaningful `f.Add` seeds (valid minimal, valid typical, edge) **and** a `testdata/fuzz/<FuzzName>/` directory for binary or long seeds (via `file2fuzz`); no random-byte seeds | H3 | S4, S22, S16 |
| R3 | Assert at least one property beyond "no panic": round trip, idempotence, parse(format(x))==x, equivalence with a reference, monotone bounds on output size/time | H4 | S2, S3, S4, S23 |
| R4 | Structure for typed inputs: decode inside the target with go-fuzz-headers or a hand-written reader, or wrap a `rapid` property with `rapid.MakeFuzz`; never emulate structs with many primitive args when the relation between them matters | H3 | S17, S20 |
| R5 | Target hygiene: deterministic, no globals, no retained input slices, no `os`/network/time/randomness, `t.Skip` for out-of-shape input, `return` for documented error paths, `t.Fatalf` for unexpected errors | H5 | S4, S1 Suggestions |
| R6 | Always `go vet ./...` and `go test -run='^Fuzz' ./...` before any `-fuzz` run; seed subtests must pass | H5 | S35, S4 |
| R7 | Fuzz invocation template: `go test -run='^$' -fuzz='^FuzzX$' -fuzztime=<budget> -parallel=<n> ./pkg` — one package, anchored regexp, explicit budget | H2, H5 | S5, S34 |
| R8 | Stopping: parse `new interesting: k (total: T)`; stop when `k` unchanged for a window (e.g. 5 min or 25 % of budget) or budget expires; record `T`, execs/s and the corpus directory size as the saturation evidence; on a second run start from the same `$GOCACHE` or the run is not comparable | H2 | S1, S6, S34 |
| R9 | On failure: keep the written `testdata/fuzz/<FuzzName>/<hash>` file, reproduce with `go test -run=FuzzX/<hash>`, fix or document, then resume; never delete the file to "make fuzzing run again" | H5 | S1, S34 |
| R10 | Triage every "hang" against the 1 s budget and every worker death against memory before filing (S29 false positive; S6 OOM policy) | H4 | S6, S29 |
| R11 | If the repo is or will be on OSS-Fuzz/ClusterFuzzLite: keep seeds in `testdata/fuzz` *and* a seed zip; avoid named-type args; expect `F.Add` to be ignored there | H5 | S11, S13 |
| R12 | Budget guidance (own synthesis from S1 trend statement): 30–60 s smoke locally, 10–15 min per target in a scheduled job, hours only on dedicated infrastructure; `-race` runs at ~6× cost, so give them 3–6× the time or a separate job | H2 | S1, S34 |

### 5.2 Harness template skeleton (≤ 15 lines)

```go
func FuzzDecode(f *testing.F) {
	f.Add([]byte{})                 // empty
	f.Add(mustRead("testdata/min.bin")) // smallest valid
	f.Fuzz(func(t *testing.T, in []byte) {
		if len(in) > 1<<16 { t.Skip("out of shape") }
		v, err := Decode(in)
		if err != nil { return }               // documented error path
		out := Encode(v)                       // round trip
		v2, err := Decode(out)
		if err != nil { t.Fatalf("re-decode: %v", err) }
		if !reflect.DeepEqual(v, v2) { t.Fatalf("round trip: %#v != %#v", v, v2) }
		if len(out) > 4*len(in)+64 { t.Fatalf("output blow-up %d→%d", len(in), len(out)) }
	})
}
```

### 5.3 Review checklist for a Go fuzz target

- [ ] `FuzzXxx(f *testing.F)` in `*_test.go`, `go vet` clean, exactly one `f.Fuzz`, args from the allowed list (S1, S4, S35)
- [ ] `f.Add` seeds: ≥3, meaningful, types match exactly; binary seeds in `testdata/fuzz/<FuzzName>/` (S4, S22)
- [ ] `go test -run='^FuzzXxx$' -v` passes on seeds; no committed `<hash>` file fails (S34)
- [ ] At least one property assertion; "no panic" alone is rejected unless the function is a pure byte parser with no inverse (S2–S4)
- [ ] Invalid shapes → `t.Skip`; expected errors → `return`; unexpected → `t.Fatalf` (S4)
- [ ] No `*F` methods inside the target; no globals/retained slices; no I/O, clock, randomness, goroutine leaks (S4)
- [ ] Per-input work well under 1 s and bounded memory; if the API can allocate proportionally to a header field, cap it in the target or assert on it (S6, S26)
- [ ] Invocation uses `-run='^$'`, anchored `-fuzz`, one package, explicit `-fuzztime` (S5)
- [ ] CI: seed corpus in the normal job; `-fuzz` in a dedicated job with persisted `$GOCACHE/fuzz` (S1, S7)
- [ ] If OSS-Fuzz/CFL targeted: no named-type args, seeds also as zip, helpers not in other `_test.go` files (S11, S13)

### 5.4 Decision rule for typed Go APIs

| input shape of the unit under test | choose | why | source |
|---|---|---|---|
| `[]byte`/`string`/`io.Reader` from a format (parser, decoder, tokenizer, protocol frame, URL, path, regexp) | native `f.Fuzz` with round-trip/consistency oracle; seeds from fixtures/go-fuzz-corpus | coverage guidance is what finds deep parser states; evidence S3.6 | S1, S16 |
| typed struct/values with algebraic laws (serialiser pairs, containers, arithmetic, state machines) | `rapid.Check` (or gopter if present); add `rapid.MakeFuzz` wrapper only if a scheduled fuzz job exists | typed generators + shrinking; coverage feedback adds little when the generator already enumerates the shape | S20 |
| small enumerable domain, or a thin wrapper over stdlib/third-party code already fuzzed upstream | table test | fuzzing cannot find anything the table does not already express; cost not justified | S8, own |
| typed API but values are decoded from bytes anyway (e.g. `Unmarshal` then business logic) | native fuzz on the byte entry point + rapid on the logic | separates format bugs from logic bugs | S17, S20 |
| concurrency-sensitive API | rapid `StateMachine` or table test under `-race`; fuzzing with `-race` only for byte parsers with internal goroutines | fuzzing explores inputs, not schedules | S20, S33 |

### 5.5 CI recipe sketch

```yaml
# job 1 (every PR): seed corpora are unit tests
- run: go vet ./... && go test -race ./...          # runs FuzzXxx/seed#N and testdata entries
# job 2 (nightly or label-triggered): one target per step, cache persisted
- uses: actions/cache@v4
  with: { path: ~/.cache/go-build/fuzz, key: fuzz-${{ github.ref_name }} }
- run: go test -run='^$' -fuzz='^FuzzDecode$' -fuzztime=10m -parallel=4 ./pkg/codec
- if: failure()
  uses: actions/upload-artifact@v4
  with: { path: pkg/codec/testdata/fuzz }           # the new <hash> file is the bug report
```
Notes: `-fuzztime` must be set or the job never ends; one `-fuzz` per `go test`; the fuzz cache path is `$(go env GOCACHE)/fuzz` (S1, S5, S7).

### 5.6 Skills this suggests

`go-fuzz-target-authoring` (R2–R6, template, checklist), `go-fuzz-run-and-stop` (R7–R10, output parsing, JSON), `go-structured-inputs` (go-fuzz-headers, rapid.MakeFuzz, seeds via file2fuzz), `go-fuzz-ci-and-ossfuzz` (R11, 5.5, shim differences), `go-fuzz-applicability` (5.4 decision table, S3.6 evidence).

## 6. Candidate eval cases

| # | input the agent sees | expected behaviour | H |
|---|---|---|---|
| E1 | `func ParseHeader(b []byte) (Header, error)` + `func (h Header) Marshal() []byte` in a wire-protocol package, fixtures in `testdata/*.bin` | Native target; seeds via `f.Add` of each fixture (or `file2fuzz` into `testdata/fuzz/FuzzParseHeader/`); oracle: `Marshal(Parse(b))` re-parses to equal `Header`, output length bounded; `-fuzztime` set; run `go test -run=FuzzParseHeader` first | H3, H4 |
| E2 | `func Add(a, b Money) Money` with `Money{Amount int64, Currency string}` and documented laws (commutative, zero identity, currency mismatch → panic documented) | **Do not write a fuzz target**; write `rapid.Check` with a `Money` generator (`rapid.Custom`) asserting the laws; table test for the mismatch panic | H1 |
| E3 | A function `func IsWeekend(t time.Time) bool` | **Do not fuzz**; enumerate seven weekdays and DST/zone edge cases in a table test; fuzzing offers nothing beyond enumeration | H1 |
| E4 | Existing `FuzzReverse` with seeds; previous run left `testdata/fuzz/FuzzReverse/00063af5…` failing | Agent recognises `failure while testing seed corpus entry`, reproduces with `-run=FuzzReverse/00063af5…`, fixes `Reverse` (or reports), does **not** delete the file, re-runs seeds, then fuzzes | H5 |
| E5 | 20-minute log where `new interesting` is `(total: 212)` for the last 12 minutes, execs ~30 k/s | Agent stops the target, records totals and cache size, moves to the next target or proposes a new seed family / a different oracle; does not restart the same run | H2 |
| E6 | `go test -fuzz=Fuzz ./...` proposed by the agent | Must be rejected/corrected: `./...` with multiple packages and an unanchored pattern matching several targets both fail with no fuzzing done; correct form `-run='^$' -fuzz='^FuzzX$' ./pkg` | H5 |
| E7 | `func Decode(r io.Reader) (*Image, error)` where the header declares width×height; a fuzz run prints a "hang" after 1 s on a 28-byte input | Agent triages: measures the input standalone; if legitimate large allocation, proposes an input-size guard in the target or a decoder limit (API-level fix), does not file "infinite loop" (cf. #56932); if allocation is unbounded (cf. #81191) files it as a bug with the 90-byte reproducer | H4 |
| E8 | Repo has `.clusterfuzzlite/` and a target `func FuzzParse(f *testing.F)` with `f.Fuzz(func(t *testing.T, id UserID, b []byte))` where `type UserID string` | Agent flags that `UserID` fails both engines (native: unsupported type; shim: panics), rewrites to `string` + conversion, moves seeds to `testdata/fuzz` + zip because `F.Add` is ignored under go-118-fuzz-build | H5 |
| E9 | Request: "fuzz our HTTP handler end-to-end" (spins up server, DB) | Agent declines a native target on the handler (network, state, speed, non-determinism); proposes fuzzing the request parsing/validation function in isolation | H1, H5 |

## 7. Micro-examples

**M1 — The tutorial's round-trip oracle finds two distinct bugs (S2, reproduced locally S34).** Target: `Reverse` reversing bytes. Seeds `"Hello, world"`, `" "`, `"!12345"`. Properties: `Reverse(Reverse(s)) == s` and `utf8.ValidString(rev)` when `s` is valid. Local run (`go test -run='^$' -fuzz=FuzzReverse -fuzztime=10s -parallel=2`): baseline `3/3`, `execs: 502`, `new interesting: 2 (total: 5)`, failure after 0.03 s: `Before: "0000000000͡", after: "\xa1\xcd0000000000"`, `Failing input written to testdata/fuzz/FuzzReverse/942bcf3022d240f5`, file content `go test fuzz v1` / `string("0000000000͡")`. In a second clean run the crasher was minimised to `string("Ѐ")`. The tutorial's second bug — invalid UTF-8 input such as `"\x91"` making the double reverse differ — is why the final target skips invalid UTF-8 and `Reverse` returns an error for it. A crash-only oracle would have found neither.

**M2 — A seed corpus as regression test catches a stdlib inconsistency (S23).** `net/netip`'s own `FuzzParse` asserts a round-trip identity for `AddrPort`. On 2024-04-30 the seed `[::ffff:192.0.2.128%eth0]:1` (seed #53) failed on a builder with `netip.AddrPort round trip identity failure` — the two values had equal address and port but different zone-handle pointers. No fuzzing session was involved; `go test` ran the seed corpus. This is the designed behaviour from S4: seeds "can also serve as regression tests for bugs identified through fuzzing".

**M3 — What the engine cannot see (S6, S26).** `debug/gosym` #81191: a 90-byte malformed table made `NewTable` call `make([]Func, 3256877056)`; the reporter saw it only as "an apparent hang under `go test -fuzz`". Per `internal/fuzz/worker.go`, a worker killed by the OOM killer records **no crash**; the 1 s `workerTimeoutDuration` is the only reason it surfaced. The fix bounded the allocation (`saferio`). An agent's target for such parsers should add an explicit size oracle or run with a memory limit so the finding is deterministic rather than timing-dependent.

**M4 — OSS-Fuzz shim semantics (S13).** In `go-118-fuzz-build/testing/f.go`, `func (c *F) Add(args ...any) {}` is empty; `F.Fuzz` builds each argument from a `go-fuzz-headers` consumer (`GetBytes` for `[]byte`, `GetString` for `string`, 64-bit read for `int`, …), calls the target once, and panics `unsupported type: <T>` for anything else. A locally fine `f.Add(validFrame)` therefore contributes nothing upstream; the seeds must be shipped as the libFuzzer seed-corpus zip.

## 8. Addendum — verification against Go 1.27.3 (2026-11-03)

The target toolchain for the agent is Go 1.27.3, not the 1.24.7 used for the local runs above.
`dl.google.com` is not reachable from the research session, so the 1.27.3 binary could not be
installed; instead the relevant sources were read at tag `go1.27.3` on GitHub and the release notes
for 1.25, 1.26 and 1.27 were checked (`golang/website` `_content/doc/go1.2{5,6,7}.md`).

| Fact relied on above | State at `go1.27.3` | Locator |
|---|---|---|
| Allowed `f.Fuzz` argument types (`[]byte string bool byte rune float32 float64 int* uint*`); unsupported type panics `testing: unsupported type for fuzzing` | unchanged | `src/testing/fuzz.go` `supportedTypes` |
| `F.Fuzz` once only; no `*F` methods inside the target; `Failing input written to …` / `To re-run: go test -run=…` | unchanged | `src/testing/fuzz.go` |
| `workerTimeoutDuration = 1 s`; worker killed by a non-crash signal (OOM killer) records no crash; minimisation accepts any error, not the same error; `workerSharedMemSize = 100 MB` caps input size | unchanged | `src/internal/fuzz/worker.go` |
| `-fuzz` one package, one target, main module only; incompatible with `-coverprofile` and profiling flags; `-fuzztime`, `-fuzzminimizetime` (default 60 s), `-parallel` semantics | unchanged | `src/cmd/go/internal/test/test.go` |
| No custom mutators, no dictionaries, no struct arguments | unchanged (no release note 1.25–1.27 mentions fuzzing) | release notes |

New since 1.24 that a Go skill should know:

- **Go 1.25**: `F.Attr` / `T.Attr` emit attributes to the test log (an `attr` action under `-json`); `F.Output` gives an `io.Writer` into the test log; `testing/synctest` is stable (irrelevant to fuzz targets, which must be single-threaded anyway).
- **Go 1.26**: `F.ArtifactDir` / `T.ArtifactDir` plus the `go test -artifacts -outputdir DIR` flags give a sanctioned place for campaign artefacts (coverage dumps, corpus snapshots) instead of ad-hoc temp files.
- **Go 1.27**: `go test -json` annotates `"Action":"output"` events with an `"OutputType"` field, which makes the `fuzz: elapsed: …` progress lines easier to separate from test output when the campaign runner parses JSON; `go test` runs the `stdversion` vet check by default.

Conclusion: every claim in §§3–5 holds for 1.27.3; the harness skeleton, flags and stopping inputs need no change. The 1.24.7 throughput numbers in §3.7 are machine-specific either way.

### 8.1 Run on the actual go1.27.3 binary (2026-11-04)

The toolchain was obtained without `dl.google.com`: `GOTOOLCHAIN=go1.27.3` with
`GOPROXY=https://proxy.golang.org,direct` fetches it as the module
`golang.org/toolchain@v0.0.1-go1.27.3.linux-amd64`. A throw-away module with the tutorial's
byte-reversing `FuzzReverse` (round-trip + UTF-8 oracle, three `f.Add` seeds) confirmed:

| Check | Observed on go1.27.3 |
|---|---|
| `go doc testing.F.Fuzz` allowed types | `[]byte, string, bool, byte, rune, float32, float64, int, int8, int16, int32, int64, uint, uint8, uint16, uint32, uint64. More types may be supported in the future.` |
| `go help testflag` | `-fuzz` (one package in the main module, one fuzz test), `-fuzztime` (default forever, `Nx`), `-fuzzminimizetime` (default 60 s), `-artifacts` ("Save test artifacts in the directory specified by -outputdir. See 'go doc testing.T.ArtifactDir'") — texts identical to the 1.24.7 reading plus the new flag |
| `go doc testing.F` | methods declared on `*F`: `Add`, `Fail`, `Fuzz`, `Helper`, `Skipped`; `Attr`, `Output`, `ArtifactDir` are promoted from the embedded `common` (not listed by `go doc testing.F`, reachable as `f.ArtifactDir()`) |
| Seed corpus as unit tests | `go test -run='^FuzzReverse$' -v` → `--- PASS: FuzzReverse/seed#0..2` |
| Fuzz run, `-json` | progress line `fuzz: elapsed: 0s, execs: 545 (22473/sec), new interesting: 3 (total: 6)` arrives as an `Action:"output"` event **without** `OutputType`; framing lines (`=== RUN`, `--- FAIL`, `FAIL`) carry `"OutputType":"frame"`. A parser can therefore select progress lines as `output` events lacking `OutputType` and matching `^fuzz: ` |
| Failing input | `Failing input written to testdata/fuzz/FuzzReverse/3c46e12e595642de`; file content `go test fuzz v1` / `string("̓0")` (two runes — minimisation is best-effort, consistent with §4.2) |
| Baseline failure on re-run | `failure while testing seed corpus entry: FuzzReverse/3c46e12e595642de` on the next `-fuzz` run and on `go test -fuzz=Fuzz ./...`; the committed crasher pre-empts fuzzing until fixed |
| Generated corpus | `$GOCACHE/fuzz/example.com/…` created |

All §§3–5 claims stand on 1.27.3; the local throughput figure (22 473 exec/s on a trivial target,
two workers) is machine-specific.
