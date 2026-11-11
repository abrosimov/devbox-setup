---
name: go-testing
description: >
  Go testing patterns with testify suites, table-driven tests, and mocking with mockery.
  Use when writing or reviewing Go tests, creating test fixtures, setting up mocks,
  or structuring table-driven test cases.
problem: "Go tests miss error paths, misuse assert instead of require, skip table-driven idioms, or mix literal dates with the real clock and expire as the calendar moves."
related: [go-engineer]
---

# Go Testing Patterns

Write idiomatic Go tests using testify suites, table-driven tests, and mockery mocks. You already know these tools -- this skill defines the agent-system expectations.

## Time: One Clock Per Test

**Every instant in a test derives from one clock.** A test that passes today and fails next week without a code change is a defect in the test, and the Go test cache hides it: a result is replayed while sources, flags, environment and files read stay the same, and the clock is none of them.

Pick one of two modes and keep the whole test, its fixtures and its suite setup in it:

| Mode | How | Literal dates |
|------|-----|---------------|
| All time fake | `testing/synctest` bubble (Go 1.25+), or a clock injected into the code under test | Allowed: nothing reads the real clock |
| All time relative | One anchor read once (`s.now := time.Now().Truncate(...)` in `SetupTest`), every instant an offset from it | Forbidden |

The defect is the **mix**: a literal `time.Date(2026, 11, 2, ...)` or timestamp string next to anything that reads the real clock — a fixture built from `time.Now()`, a TTL or expiry, a retention or "last N days" window, `time.Since`. It passes until the calendar moves the literal outside that window.

- An instant that must sit on a boundary (minute, bucket, day) is the anchor truncated and offset: `s.now.Add(-granularity).Truncate(granularity)`, not a copied wall-clock time. An incident's clock times belong in the comment, not the code.
- Code that reads `time.Now()` directly (TTLs, expiry, "now"-relative windows) is tested inside `synctest.Test`: time there starts at 2000-01-01 00:00 UTC and advances only when every goroutine in the bubble is blocked, so a 5-minute expiry is tested with `time.Sleep(5 * time.Minute)` in microseconds.
  - Build everything that reads the clock inside the bubble. Testify's `SetupTest` runs outside it, so a fixture made there carries real time.
  - Do not call `t.Run` / `s.Run` / `t.Parallel` inside the bubble; open one bubble per subtest instead.
  - Goroutines started in the bubble must exit before it returns.
- Time-relative behaviour gets a boundary case: just inside and just outside the window, the TTL, the retention floor.
- Compare instants with `Equal` on `time.Time` values in one location (`.UTC()`), never on formatted strings that depend on `time.Local`.

Before completion, ask of every test: would it pass unchanged in a month, at 23:59:59, on 31 December, under `TZ=Asia/Tokyo`?

## Validation

```bash
go test -count=1 ./...
go test -count=1 -race ./...
```

`-count=1` because a cached `ok` proves nothing about the tests you just wrote or about the date they run on.

## Checklist Before Completion

- [ ] All public functions have tests
- [ ] All error paths are tested (every `return err`)
- [ ] Table-driven tests used where appropriate
- [ ] Mocks verify call expectations
- [ ] All assertions use `require`, never `assert` — test must stop on first failure
- [ ] Edge cases covered (empty, boundary)
- [ ] Context cancellation tested (if context used)
- [ ] No tests for type system guarantees
- [ ] No nil-argument validation tests for constructors/methods — caller responsibility, not callee
- [ ] Error assertions use `require.ErrorIs`/`require.ErrorAs`, not string comparison
- [ ] One clock per test: no literal date or timestamp next to anything reading the real clock (fixtures, TTLs, windows); clock-reading code tested in `synctest` or against an injected clock
- [ ] Time-relative behaviour has a boundary case (just inside / just outside the window or TTL)
- [ ] Tests pass: `go test -count=1 ./...`
- [ ] Race detector passes: `go test -count=1 -race ./...`
