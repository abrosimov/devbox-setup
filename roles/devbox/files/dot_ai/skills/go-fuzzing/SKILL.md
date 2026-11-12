---
name: go-fuzzing
description: Build, qualify, run and replay native Go fuzz targets with testing.F, preserving useful corpus inputs and trustworthy failure evidence.
---

# Go fuzzing

Produce a native harness, observed qualification results and replayable inputs for the assigned
Go target. Work within the existing research scope and effort limits. A new corpus may warrant
bounded reconnaissance before a precise hypothesis exists. Keep PBT and mutation analysis out of
this workflow; ordinary fuzz-input mutation remains in scope.

## Establish the local basis

- Read the nearest repository instructions, `go.mod`, toolchain configuration, existing fuzz tests
  and target contract. Use the project's commands and pinned tools; do not replace its Go version.
- Record the actual `go version`, package, target, relevant commit/dirty changes, input selection
  and build settings. Check `go help testflag` when relying on version-specific flags.
- Reuse a qualified existing harness. A missing compiler, dependency or supported execution
  environment is a concrete prerequisite; install or upgrade only with existing authorisation.
- Define the current contribution: inspect a bounded corpus, exercise a named behaviour, or answer
  a formulated question. Include preparation, replay and reduction in its effort accounting.

## Construct and qualify

Use `FuzzXxx(f *testing.F)` in a `_test.go` file, with one `f.Fuzz` call accepting `*testing.T`
followed by supported primitive/string/byte-slice arguments. `f.Add` values and corpus records must
match those arguments in type and order. Use a bounded byte decoder for richer structures, retaining
the raw input and decoder version. Reset target state between calls and avoid cross-input globals.

Choose assertions from the product contract. For a round trip, define semantic equality and any
allowed loss or normalisation. Differential disagreement requires investigation of both sides.
Expected parse errors or contract-permitted panics are not automatically defects. Exercise known
valid and expected-invalid inputs; use an independently expected failing case when one exists.
Never add a false assertion or modify production behaviour merely to make qualification fail.

Replay must reach the intended product call and relevant check. Inspect known-case results and,
where needed, the repository's coverage instrumentation. A successful build or a quiet counter
alone does not establish meaningful execution. Keep an invalid-input route when generating valid
structure. Format changed Go files with the repository's `goimports -local <module-path>` convention.

## Execute and replay

These examples use a hypothetical package `./internal/parser` and target `FuzzDecode`. Substitute
the actual package/target and justified limits; prefer equivalent repository wrappers.

```text
go test ./internal/parser -list '^Fuzz'
go test ./internal/parser -run '^FuzzDecode$' -count=1 -v
go test ./internal/parser -run '^$' -fuzz '^FuzzDecode$' -fuzztime=30s -fuzzminimizetime=2s -parallel=1
go test ./internal/parser -run '^FuzzDecode$/^<saved-case-name>$' -count=1 -v
```

The second command runs seed cases without starting search. Confirm the named saved case actually
ran in the final command; an unmatched filter can exit successfully. `-run '^$'` in the search
example skips ordinary tests, so execute the relevant existing checks separately before relying on
the result. Fuzzing selects one package and one target. `-fuzztime` limits search work;
`-fuzzminimizetime` applies to each reduction attempt. Neither supplies a deadline for all research.

Choose an explicit command/executor limit for the current operation when necessary; do not infer
a product hang from its expiry. Keep raw diagnostics and note whether the engine was searching,
replaying or minimising. A completed no-finding run is a bounded observation, not a safety claim.

## Preserve and continue

- Keep seeds in `f.Add` or native `testdata/fuzz/<FuzzName>/` records, following the repository.
  Generated search-cache entries and failure artefacts have different roles. Inspect the actual
  cache/output locations; copy useful inputs to durable replay storage with compatible native
  encoding and verify replay. A raw byte file is not automatically a Go corpus record.
- Preserve useful coverage, structured and intentionally rejected examples even without a crash.
  Corpus reduction must retain the behaviour and future use for which an input was kept.
- For a failure, retain the original bytes/record and diagnostic before reduction. Accept a smaller
  candidate only after confirming the same relevant symptom; an environment error is unresolved.
  Fix an authored harness error within scope and recheck its evidence; report product defects.
- On interruption, save the question or learning aim, method, last completed operation, original
  and last verified input, pending check, versions and cumulative effort. In the next session,
  inspect relevant changes and perform the unfinished justified operation. A new session or
  unrelated commit does not require replaying or researching everything again.

Return changed harness files, commands and actual exits, qualification evidence, retained corpus
paths and verified replay commands, finding classification and the unfinished operation if any.
Distinguish confirmed product failure, harness/oracle error, environment failure, unconfirmed failure
and no finding. Decide research continuation, pause or closure from its question and evidence;
engine exit alone does not decide it. Retention grants no authority to commit or publish.

## Primary references

Checked 2026-11-12. Recheck against the target toolchain when its behaviour matters:

- [Native Go fuzzing](https://go.dev/doc/security/fuzz/) — signatures, seed types and execution modes.
- [testing fuzzing contract](https://pkg.go.dev/testing#hdr-Fuzzing) — seed records and target API.
- [Go test flags](https://pkg.go.dev/cmd/go#hdr-Testing_flags) — selection, search and reduction limits.
