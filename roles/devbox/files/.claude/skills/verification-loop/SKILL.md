---
name: verification-loop
description: >
  6-phase continuous verification methodology. Triggers on: verify, validation loop, pre-commit checks, quality assurance.
---

# Verification Loop

## 6-Phase Methodology

Continuous verification across the development lifecycle.

```
Build → Type Check → Lint → Test → Security → Diff Review
```

Each phase builds on the previous (no point linting if build fails).

## Phase 1: Build

Compile/transpile passes without errors.

### Go
```bash
go build ./...
```

**Failures**: syntax errors, import cycles, missing dependencies.

### TypeScript
```bash
tsc --noEmit  # Type check only (no emit)
# or
npm run build  # Full build (transpile + bundle)
```

### Python
```bash
python -m py_compile src/**/*.py  # Syntax check
# or
uv build  # Build wheel/sdist
```

**When to run**: After any code change, before commit.

## Phase 2: Type Check

Static type verification.

### TypeScript
```bash
tsc --noEmit
```

**Failures**: type mismatches, missing properties, incompatible types.

### Python (mypy)
```bash
mypy src/
```

**Configuration** (`pyproject.toml`):
```toml
[tool.mypy]
python_version = "3.13"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### Go
```bash
go vet ./...
```

**Checks**: unreachable code, printf format errors, mutex misuse.

**When to run**: After build passes, before lint.

## Phase 3: Lint

Style and correctness rules.

### Go
```bash
golangci-lint run
```

**Checks**: deadcode, errcheck, ineffassign, staticcheck, unused.

**Configuration** (`.golangci.yml`):
```yaml
linters:
  enable:
    - errcheck
    - gosimple
    - govet
    - ineffassign
    - staticcheck
    - unused
```

### Python
```bash
ruff check .
```

**Checks**: unused imports, undefined variables, style violations (PEP 8).

**Configuration** (`pyproject.toml`):
```toml
[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]
```

### TypeScript
```bash
eslint .
```

**Configuration** (`.eslintrc.json`):
```json
{
  "extends": ["eslint:recommended", "plugin:@typescript-eslint/recommended"],
  "rules": {
    "no-unused-vars": "error",
    "no-console": "warn"
  }
}
```

**When to run**: After type check passes, before tests.

## Phase 4: Test

All tests pass with coverage.

### Go
```bash
go test -v -race -coverprofile=coverage.out ./...
go tool cover -html=coverage.out
```

**Flags**:
- `-v`: verbose output
- `-race`: race condition detector
- `-coverprofile`: coverage report

### Python
```bash
pytest --cov=src --cov-report=html
```

**Configuration** (`pyproject.toml`):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "--strict-markers --cov=src --cov-report=term-missing"
```

### TypeScript
```bash
npm test  # Jest/Vitest
```

**Coverage threshold** (`jest.config.js`):
```javascript
module.exports = {
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
};
```

**When to run**: After lint passes, before security check.

## Phase 5: Security

No secrets, no injection patterns, no vulnerable dependencies.

### Secret Detection

**git-secrets** (prevent committing secrets):
```bash
git secrets --scan
```

**truffleHog** (scan git history):
```bash
trufflehog git file://. --only-verified
```

**Patterns to catch**:
- AWS keys: `AKIA[0-9A-Z]{16}`
- GitHub tokens: `ghp_[a-zA-Z0-9]{36}`
- Private keys: `-----BEGIN PRIVATE KEY-----`

### Dependency Vulnerabilities

**Go**:
```bash
go list -json -m all | nancy sleuth
# or
govulncheck ./...
```

**Python**:
```bash
pip-audit
# or
safety check
```

**TypeScript**:
```bash
npm audit
# or
pnpm audit
```

**Fix strategy**:
- Update vulnerable dependency to patched version
- If no patch: find alternative, or accept risk (document justification)

### Code Injection Patterns

**SQL injection** (static analysis):
```bash
# Go
gosec ./...

# Python
bandit -r src/

# TypeScript
eslint --plugin security
```

**Common patterns**:
- SQL: string concatenation in queries
- Shell: `os.system()` with user input
- Path traversal: `open(user_input)`

**When to run**: After tests pass, before diff review.

## Phase 6: Diff Review

Changes match intent, no unintended modifications.

### Manual Review

```bash
# View staged changes
git diff --staged

# View unstaged changes
git diff
```

**Check for**:
- Unintended file changes (lock files, generated code)
- Debug code left in (console.log, print statements)
- Commented-out code
- Large diffs (should be in separate commits)

### Automated Checks

**File size limits**:
```bash
# Prevent committing large files (>5MB)
find . -type f -size +5M
```

**Generated files** (should be in `.gitignore`):
```bash
# Check for accidentally committed generated files
git ls-files | grep -E '\.pyc$|node_modules|\.DS_Store|coverage|dist'
```

**Formatting** (auto-fix):
```bash
# Go
goimports -local $(head -1 go.mod | awk '{print $2}') -w .

# Python
ruff format .

# TypeScript
prettier --write .
```

**When to run**: Before commit, before PR.

## When to Run

### After Major Changes

Full 6-phase check after:
- Merging feature branch
- Refactoring
- Dependency updates
- Build configuration changes

```bash
# Manual trigger
/verify
```

### Before PR

```bash
# CI pipeline
name: Verify
on: [pull_request]
jobs:
  verify:
    steps:
      - run: make build
      - run: make typecheck
      - run: make lint
      - run: make test
      - run: make security-scan
```

### After Merge Conflicts

```bash
# After resolving conflicts
git diff --check  # Check for conflict markers
make verify       # Full verification
```

## Integration with Hooks

### PostToolUse Triggers

Hooks run automatically after Edit/Write tools.

**hooks.json**:
```json
{
  "postToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "command": "post-edit-format",
          "async": true
        },
        {
          "command": "post-edit-typecheck",
          "async": true
        },
        {
          "command": "post-edit-lint",
          "async": true
        }
      ]
    }
  ]
}
```

**Phase sequence**:
1. Format → fix style issues automatically
2. Type check → surface type errors immediately
3. Lint → surface correctness issues

**Async**: Runs in background (doesn't block next tool call).

### Manual Trigger

`/verify` command runs full 6-phase check.

**Implementation** (`commands/verify.md`):
```markdown
Run verification loop:
1. Build (fail fast on syntax errors)
2. Type check (fail on type errors)
3. Lint (fail on style/correctness issues)
4. Test (fail on test failures)
5. Security (warn on secrets/vulnerabilities)
6. Diff review (manual inspection)
```

## Failure Handling

### Fix in Phase Order

**Don't skip phases**:
- Build fails → fix syntax before linting
- Lint fails → fix style before running tests
- Tests fail → fix tests before security scan

**Rationale**: Later phases assume earlier phases pass (e.g., tests won't run if build fails).

### Categorise Failures

| Phase | Failure Type | Action |
|-------|--------------|--------|
| Build | Syntax error | Fix immediately (blocks everything) |
| Type Check | Type mismatch | Fix immediately (blocks runtime safety) |
| Lint | Style violation | Fix or suppress (with justification) |
| Test | Test failure | Fix or update test (if behaviour intentional) |
| Security | Secret detected | Remove secret, rotate credentials |
| Diff Review | Unintended change | Revert or split into separate commit |

### Suppression

**Lint suppression** (use sparingly):
```go
// nolint:errcheck
result, _ := someFunction()  // Error intentionally ignored
```

```python
# ruff: noqa: F401
import unused_module  # Imported for side effects
```

**Test skip** (document reason):
```python
@pytest.mark.skip(reason="Flaky test, tracked in issue #123")
def test_flaky():
    ...
```

## Best Practises

1. **Fail fast**: Run build before expensive tests
2. **Automate**: Use hooks for format/lint/typecheck after edits
3. **Fast feedback**: Run phases locally before pushing (CI is backup)
4. **Fix immediately**: Don't accumulate lint/test failures
5. **Document suppressions**: Explain why rule is disabled
6. **Track coverage**: Ensure coverage doesn't decrease over time
7. **Review diffs**: Always review changes before committing (catch unintended edits)
