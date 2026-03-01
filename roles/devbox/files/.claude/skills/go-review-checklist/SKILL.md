---
name: go-review-checklist
description: >
  Go code review checklist, verification checkpoints, and review patterns.
  Used by code-reviewer-go agent. Covers enumeration, verification, counter-evidence,
  backward compatibility, and domain compliance checks.
  Triggers on: go review, code review go, review checklist, verification checkpoint.
---

# Go Review Checklist

## Step 3: Exhaustive Enumeration (NO EVALUATION YET)

**This phase is about LISTING, not JUDGING. Do not skip items. Do not optimise.**

### 3-Pre: Lint Suppression Audit

**Before any other enumeration**, scan for newly added suppression directives:
```bash
git diff $DEFAULT_BRANCH...HEAD -U0 -- '*.go' | grep -n '^\+.*nolint'
```

**Every new suppression is a finding.** For each one:
- Does it have a specific linter name? (`//nolint:errcheck` not `//nolint`)
- Does it have a justification comment?
- Was the user asked before adding it?
- Can the underlying issue be fixed instead?

Flag unjustified suppressions as **HIGH severity**.

### 3A: Error Handling Inventory

```bash
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "return.*err\|if err != nil\|errors\.\|fmt\.Errorf"
```

```
| Line | File | Pattern | Has Context Wrapping? | Verified? |
|------|------|---------|----------------------|-----------|
Total error handling sites found: ___
```

### 3B: Identifier Inventory

```
| Identifier | Type | Location | What It Represents | Ambiguous? |
|------------|------|----------|-------------------|------------|
Total new identifiers: ___
```

### 3C: Public Function Inventory

```bash
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | grep -v _test.go | xargs grep -n "^func [A-Z]\|^func (.*) [A-Z]"
```

```
| Function | File:Line | Test Exists? | Test Location | Error Paths Tested? |
|----------|-----------|--------------|---------------|-------------------|
Total public functions: ___
Functions without tests: ___
```

### 3D: Skipped Test Inventory

```bash
grep -rn "t\.Skip\|s\.T()\.Skip\|suite\.T()\.Skip" *_test.go
```

```
Skipped tests found: ___
List: ___
```

## Step 4: Individual Verification

**Now evaluate EACH enumerated item. Do NOT batch. Do NOT assume consistency.**

For EACH error handling site: checked? context added? sentinel handling correct?

**Ultrathink trigger**: If you have >5 error handling sites, pause and think harder about each one individually.

For EACH type with methods: verify receiver consistency (all pointer or all value, never mixed).

```bash
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | grep -v _test.go | xargs grep "^func (" | awk -F'[()]' '{print $2}' | sort | uniq -c
```

## Step 5: Formal Logic Validation

For each changed function/method, verify:
- Boolean logic: conditions inverted? `&&`/`||` correct? comparison operators correct?
- State checks: right states checked? missing states?
- Boundary conditions: off-by-one? empty slice/map? integer overflow?
- Control flow: early returns cover all cases? switch default handled? type assertions use comma-ok?

## Step 6: Verification Checkpoints

**DO NOT proceed to final report until ALL checkpoints are complete.**

### Checkpoint A: Error Handling
```
Total error returns found: ___
Error returns WITH context wrapping: ___
Error returns WITHOUT context: ___
Errors ignored with `_`: ___
VERDICT: [ ] PASS  [ ] FAIL
```

### Checkpoint B: Test Coverage
```
Public functions in changed files: ___
Functions with dedicated tests: ___
Functions with ZERO test coverage: ___
Skipped tests found: ___
VERDICT: [ ] PASS  [ ] FAIL
```

### Checkpoint C: Naming Clarity
```
New identifiers introduced: ___
Identifiers with potential ambiguity: ___
VERDICT: [ ] PASS  [ ] FAIL
```

### Checkpoint D: Nil Safety
```
Methods with nil receiver checks (anti-pattern — flag for removal): ___
Constructors with nil-argument validation (anti-pattern — caller responsibility): ___
VERDICT: [ ] PASS  [ ] FAIL
```

### Checkpoint E: Architecture
```
Project structure follows existing codebase patterns: YES/NO
Imposes new architectural pattern unnecessarily: ___
Constructor argument order correct (config, deps, logger): ___
Dependencies passed as pointers: ___
Receiver consistency (no mixed pointer/value): ___
VERDICT: [ ] PASS  [ ] FAIL
```

### Checkpoint F: API Surface (Minimal Export)

```bash
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | grep -v _test.go | xargs grep -n "^type [A-Z]\|^func [A-Z]\|^func (.*) [A-Z]\|^const [A-Z]\|^var [A-Z]"
```

For EACH exported identifier: will code outside this package use it? Is it intended public API or implementation detail?

```
Over-exported (should be unexported): ___
VERDICT: [ ] PASS  [ ] FAIL
```

### Checkpoint G: Test Quality --- Error Assertions

```bash
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*_test.go' | xargs grep -n "err\.Error()\|Contains.*err\|Equal.*err.*Error\|strings\.Contains.*err"
```

```
String-based error checks (MUST FIX): ___
Correct ErrorIs/ErrorAs usage: ___
Missing sentinel errors in production code: ___
VERDICT: [ ] PASS  [ ] FAIL
```

### Checkpoint H: Export-for-Testing Anti-patterns

```bash
git diff $DEFAULT_BRANCH...HEAD --name-only | grep "export_test.go"
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | grep -v _test.go | xargs grep -n "TestHelper\|ForTest\|// exported for test"
```

```
export_test.go files found: ___
Split test files (*_internal_test.go --- FORBIDDEN): ___
VERDICT: [ ] PASS  [ ] FAIL
```

### Checkpoint I: Security

> Three-tier severity: **CRITICAL** (never acceptable), **GUARDED** (dev OK with guards), **CONTEXT** (needs judgment).

Search for security-sensitive patterns in changed files:
```bash
# CRITICAL patterns
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "fmt.Sprintf.*SELECT\|fmt.Sprintf.*INSERT\|exec.Command\|== .*token\|== .*secret\|\"math/rand\"\|log.*password\|log.*token\|password.*=.*\"\|\"crypto/md5\"\|\"crypto/sha1\""

# GUARDED patterns
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "InsecureSkipVerify\|WithInsecure\|reflection.Register\|\"text/template\""

# CONTEXT patterns
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "filepath.Join.*\+\|http.Redirect\|status.Errorf.*%v"
```

```
CRITICAL findings: ___
GUARDED findings (check for build tag/config/env guard): ___
CONTEXT findings (needs judgment): ___
VERDICT: [ ] PASS  [ ] FAIL
```

### Checkpoint J: No Runtime Panics

```bash
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "panic(\|Must[A-Z]"
```

`panic()`/`Must*()` acceptable ONLY in package-level `var` or `init()`. Forbidden in runtime code.

```
Runtime panics found: ___
VERDICT: [ ] PASS  [ ] FAIL
```

### Checkpoint K: Scope Verification (Plan Contracts)

**If plan.md exists**, verify:

1. **Review Contract**: For each row, does implementation satisfy pass criteria?
2. **SE Verification Contract**: All rows marked verified?
3. **Assumption Register**: Any unresolved assumptions?
4. **Test Mandate**: Each mandatory scenario has a test?
5. **Scope Check**: Features implemented NOT in plan? Features in plan NOT implemented?

Classification: production necessity (OK) vs product feature (FLAG).

```
VERDICT: [ ] PASS  [ ] FAIL
```

### Checkpoint L: AC Technical Feasibility

For each AC that claims a failure mode exists, trace the code path and verify the failure is realistic. Flag ACs that describe impossible failure modes.

```
ACs verified as realistic: ___
ACs identified as unrealistic/theoretical: ___
VERDICT: [ ] PASS  [ ] FAIL
```

### Checkpoint M: Test Scenario Completeness

For each function with tests, enumerate the problem domain scenarios BEFORE looking at existing tests, then check coverage.

```
Functions with test coverage gaps: ___
VERDICT: [ ] PASS  [ ] FAIL
```

### Checkpoint N: Comment Quality (BLOCKING)

```bash
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n "// [A-Z][a-z].*the\|// Check\|// Verify\|// Create\|// Start\|// Get\|// Set"
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | xargs grep -n -B1 "^func [a-z]\|^func (.*) [a-z]" | grep "//"
```

Flag: narration comments, doc comments on unexported functions, doc comments on business logic.

```
VERDICT: [ ] PASS  [ ] FAIL
```

### Checkpoint O: Complexity Review

Apply Occam's Razor: unnecessary abstractions? premature generalisation? Could anything be removed to improve the system?

```
VERDICT: [ ] PASS  [ ] FAIL
```

### Checkpoint P: Log Message Quality

```bash
git diff $DEFAULT_BRANCH...HEAD --name-only -- '*.go' | grep -v _test.go | xargs grep -n "\.Info()\|\.Error()\|\.Warn()\|\.Debug()"
```

Each log must have: `.Err(err)` on errors, entity IDs, specific message, lowercase start.

```
VERDICT: [ ] PASS  [ ] FAIL
```

### Checkpoint Q: SE Self-Review Verification

Check if SE completed pre-handoff self-review. If SE consistently misses self-review items, flag the pattern.

```
VERDICT: [ ] PASS  [ ] FAIL
```

---

## Go-Specific Issues (Report Template)

```
## Go-Specific Issues
### Error Handling
- [ ] file.go:42 - Error ignored on line X
- [ ] file.go:87 - Missing error context

### Concurrency
- [ ] worker.go:23 - Possible goroutine leak

### Nil Safety
- [ ] service.go:15 - Unnecessary nil check on argument (caller responsibility)

### Architecture
- [ ] service/interfaces.go - Interfaces in separate file (move to consumer)
- [ ] service.go:40 - Constructor arg order wrong (logger before deps)

### API Surface (Over-exported)
- [ ] client.go:15 - Struct fields exported (should be unexported)
- [ ] utils.go:30 - Helper function exported unnecessarily

### Test Error Assertions
- [ ] user_test.go:45 - String comparison: use ErrorIs instead

### Export-for-Testing
- [ ] export_test.go - Unjustified export (test via public API instead)

### Security
- [ ] handler.go:45 - SQL injection: string concatenation in query

### Distributed Systems
- [ ] client.go:30 - HTTP call without timeout

## Test Review
### Coverage Gaps
- [ ] handler.go:GetUser - No test for empty ID

### Test Quality Issues
- [ ] handler_test.go:45 - Weak assertion (NotNil instead of Equal)

## Logic Review
### <function name>
- **Intent**: <what it should do per ticket>
- **Implementation**: <what it actually does>
- **Issues**: <any logical errors found>

## Backward Compatibility
### Breaking Changes
- [ ] api.go:GetUser - Signature changed without wrapper migration

## Formatting Issues
- [ ] file.go - Not formatted with goimports

## Questions for Developer
1. <specific question about ambiguous logic>
```
