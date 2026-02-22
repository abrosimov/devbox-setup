---
description: Run pre-PR quality gate — build, typecheck, lint, test, debug scan
---

You are running a lightweight, deterministic quality gate before code review or PR creation.

Unlike `/review` (which spawns a code reviewer agent for deep analysis), `/verify` runs automated checks only. Use it as a fast sanity check.

## Parse Arguments

- `/verify` or `/verify full` → run all checks (default)
- `/verify quick` → build + typecheck only
- `/verify pre-pr` → all checks + secret scan

## Steps

### 1. Detect Project Stack AND Toolchain

Check for project markers (check ALL — a project may have multiple):

```bash
ls go.mod pyproject.toml uv.lock poetry.lock requirements.txt package.json pnpm-lock.yaml package-lock.json yarn.lock tsconfig.json next.config.* Dockerfile docker-compose.yml compose.yml 2>/dev/null
```

Classify stack AND toolchain:

| Markers | Stack | Toolchain | Run Prefix |
|---------|-------|-----------|------------|
| `go.mod` | Go | system go | *(none)* |
| `uv.lock` | Python | uv | `uv run` |
| `poetry.lock` | Python | poetry | `poetry run` |
| `pyproject.toml` only | Python | uv (default) | `uv run` |
| `requirements.txt` only | Python | pip | `python -m` |
| `pnpm-lock.yaml` | Frontend | pnpm | `pnpm` / `pnpm exec` |
| `package-lock.json` | Frontend | npm | `npm run` / `npx` |
| `yarn.lock` | Frontend | yarn | `yarn` |

Store the detected `RUN_PREFIX` — use it for ALL subsequent commands. **Never guess or use fallback chains.**

Multiple stacks → run checks for **all detected stacks**.

### 2. Run Checks (in order — stop on critical failure)

Run each check and record PASS/FAIL. If build fails, stop entirely (nothing else is meaningful).

#### Check 1: Build

**Go:**
```bash
go build ./...
```

**Python (uv):**
```bash
uv run python -m py_compile $(git diff --name-only --diff-filter=d HEAD -- '*.py' | head -20) 2>&1
```

**Python (poetry):**
```bash
poetry run python -m py_compile $(git diff --name-only --diff-filter=d HEAD -- '*.py' | head -20) 2>&1
```

**Frontend (pnpm):**
```bash
pnpm run build 2>&1
```

**Frontend (npm):**
```bash
npm run build 2>&1
```

**If build fails → report FAIL and stop. Nothing else is meaningful.**

#### Check 2: Type Check

**Go:**
```bash
go vet ./...
```

**Python (uv):**
```bash
uv run mypy --ignore-missing-imports $(git diff --name-only --diff-filter=d HEAD -- '*.py' | head -20) 2>&1
```

**Python (poetry):**
```bash
poetry run mypy --ignore-missing-imports $(git diff --name-only --diff-filter=d HEAD -- '*.py' | head -20) 2>&1
```

**Frontend (pnpm):**
```bash
pnpm exec tsc --noEmit 2>&1
```

**Frontend (npm):**
```bash
npx tsc --noEmit 2>&1
```

#### Check 3: Lint (skip if `/verify quick`)

**Go:**
```bash
# Extract module name from go.mod for goimports
MODULE=$(head -1 go.mod | awk '{print $2}')
goimports -local "$MODULE" -l $(git diff --name-only --diff-filter=d HEAD -- '*.go') 2>&1
golangci-lint run ./... 2>&1 || echo "SKIP: golangci-lint not installed"
```

**Python (uv):**
```bash
uv run ruff check $(git diff --name-only --diff-filter=d HEAD -- '*.py') 2>&1
```

**Python (poetry):**
```bash
poetry run ruff check $(git diff --name-only --diff-filter=d HEAD -- '*.py') 2>&1
```

**Frontend (pnpm):**
```bash
pnpm run lint 2>&1
```

**Frontend (npm):**
```bash
npm run lint 2>&1
```

#### Check 3b: Docker Lint (skip if `/verify quick` or no Docker files)

Only run if Dockerfiles or compose files were detected in Step 1.

**Dockerfiles (hadolint):**
```bash
# Find and lint all Dockerfiles (maxdepth 3)
find . -maxdepth 3 \( -name 'Dockerfile' -o -name 'Dockerfile.*' -o -name '*.dockerfile' \) -exec hadolint {} + 2>&1
```

**Compose files (dclint):**
```bash
dclint . 2>&1
```

Skip gracefully if hadolint or dclint are not installed.

#### Check 4: Test Suite (skip if `/verify quick`)

**Go:**
```bash
go test ./... -count=1 -timeout 120s 2>&1
```

**Python (uv):**
```bash
uv run pytest --tb=short -q 2>&1
```

**Python (poetry):**
```bash
poetry run pytest --tb=short -q 2>&1
```

**Frontend (pnpm):**
```bash
pnpm test 2>&1
```

**Frontend (npm):**
```bash
npm test -- --watchAll=false 2>&1
```

#### Check 4b: Smoke Test (skip if `/verify quick`)

Run if a smoke test convention is detected:

| Convention | Detection | Command |
|------------|-----------|---------|
| Makefile target | `make -qn smoke` succeeds | `make smoke` |
| Script | `scripts/smoke-test.sh` is executable | `./scripts/smoke-test.sh` |

Skip if neither convention found (not an error).

#### Check 5: Debug Statement Scan (skip if `/verify quick`)

Scan for debug statements that should not be committed:

```bash
# Go
grep -rn 'fmt\.Println\|fmt\.Printf\|log\.Print' --include='*.go' --exclude='*_test.go' . 2>/dev/null | head -10

# Python
grep -rn 'print(\|breakpoint(\|pdb\.set_trace\|import pdb' --include='*.py' --exclude='test_*' --exclude='*_test.py' . 2>/dev/null | head -10

# TypeScript/JavaScript
grep -rn 'console\.log\|console\.debug\|debugger' --include='*.ts' --include='*.tsx' --exclude='*.test.*' --exclude='*.spec.*' . 2>/dev/null | head -10
```

#### Check 6: Secret Scan (only for `/verify pre-pr`)

```bash
# Check for common secret patterns
grep -rn 'PRIVATE.KEY\|SECRET_KEY\|password\s*=\s*["\x27][^"\x27]\+["\x27]\|api_key\s*=\s*["\x27]' --include='*.go' --include='*.py' --include='*.ts' --include='*.tsx' --include='*.env' . 2>/dev/null | grep -v '_test\.\|test_\|\.spec\.\|mock\|fixture\|example' | head -10

# Check for .env files being committed
git diff --cached --name-only 2>/dev/null | grep -i '\.env\|credentials\|\.pem\|\.key' || true
```

#### Check 7: Git Status

```bash
git status --short
git diff --stat HEAD
```

### 3. Report Results

Present a clear PASS/FAIL report:

```markdown
## Verification Report

| Check | Result |
|-------|--------|
| Build | PASS / FAIL |
| Types | PASS / X errors / SKIP |
| Lint | PASS / X issues / SKIP |
| Docker Lint | PASS / X issues / SKIP |
| Tests | X/Y passed, Z% coverage / SKIP |
| Smoke Test | PASS / FAIL / SKIP |
| Debug statements | Clean / X found |
| Secrets | Clean / X found (pre-pr only) |

**Verdict: READY FOR REVIEW** or **NOT READY — fix N issues**
```

If all checks pass:

> Verification passed. Ready for `/review` or PR.

If issues found:

> Verification found N issue(s). Fix and re-run `/verify`.

### 4. Suggest Next Step

Based on result:

| Result | Suggestion |
|--------|------------|
| All pass | "Run `/review` for code review, or `/checkpoint` to save progress." |
| Minor issues | "Fix the issues above and re-run `/verify`." |
| Build fails | "Build is broken. Fix compilation errors first." |
