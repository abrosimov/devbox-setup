---
name: go-testing
description: >
  Go testing patterns with testify suites, table-driven tests, mocking with mockery.
  Triggers on: test, testing, testify, mock, table-driven, suite, fixture, assertion.
---

# Go Testing Patterns

Write idiomatic Go tests using testify suites, table-driven tests, and mockery mocks. You already know these tools -- this skill defines the agent-system expectations.

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
- [ ] Tests pass: `go test ./...`
- [ ] Race detector passes: `go test -race ./...`
