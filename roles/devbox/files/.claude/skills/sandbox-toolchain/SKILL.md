---
name: sandbox-toolchain
description: >
  How Claude Code's sandbox interacts with language toolchains (Go, Python, Node).
  Covers writable directories, network restrictions, env var configuration,
  and a decision tree for diagnosing tool failures in sandbox.
alwaysApply: false
triggers:
  - sandbox
  - GOCACHE
  - GOMODCACHE
  - GOTOOLCHAIN
  - toolchain
  - "permission denied"
  - "operation not permitted"
  - "sandbox blocks"
---

# Sandbox Toolchain Compatibility

Claude Code's sandbox enforces filesystem and network isolation at the OS level. Language toolchains need specific configuration to work within these boundaries.

## How the Sandbox Works

**Filesystem writes** are restricted to:
- The current working directory and subdirectories
- `$TMPDIR` (set by sandbox to a writable temp directory, e.g. `/private/tmp/claude-<uid>/`)

**Filesystem reads** are allowed everywhere except denied paths (`.ssh`, `.aws`, `.gnupg`, secrets).

**Network** is restricted to domains listed in `settings.json` → `sandbox.network.allowedDomains`.

## Language-Specific Configuration

### Go

Go has three sandbox-breaking defaults:

| Default Behaviour | Problem | Fix |
|---|---|---|
| `GOTOOLCHAIN=auto` | Downloads newer Go binary — fails (network/filesystem) | `GOTOOLCHAIN=local` |
| `GOCACHE=~/Library/Caches/go-build` | Outside sandbox write allowlist | `GOCACHE="$TMPDIR/go-build-cache"` |
| `GOMODCACHE=~/go/pkg/mod` | Outside sandbox write allowlist | `GOMODCACHE="$TMPDIR/go-mod-cache"` |

**Standard prefix for all Go commands:**
```bash
GOTOOLCHAIN=local GOCACHE="${TMPDIR:-/tmp}/go-build-cache" GOMODCACHE="${TMPDIR:-/tmp}/go-mod-cache" go build ./...
```

These env vars are also set automatically by `~/.claude/bin/env-setup.js` for hook scripts.

### Python (uv, ruff, mypy)

Python toolchains cache to `~/.cache/` by default, which is outside the sandbox write allowlist.

| Default Behaviour | Problem | Fix |
|---|---|---|
| `UV_CACHE_DIR=~/.cache/uv` | Outside sandbox write allowlist | `UV_CACHE_DIR="$TMPDIR/uv-cache"` |
| `RUFF_CACHE_DIR=~/.cache/ruff` | Outside sandbox write allowlist | `RUFF_CACHE_DIR="$TMPDIR/ruff-cache"` |
| `MYPY_CACHE_DIR=.mypy_cache` | Usually fine (CWD), but set explicitly for consistency | `MYPY_CACHE_DIR="$TMPDIR/mypy-cache"` |

**Standard prefix for Python commands:**
```bash
UV_CACHE_DIR="${TMPDIR:-/tmp}/uv-cache" uv run pytest
UV_CACHE_DIR="${TMPDIR:-/tmp}/uv-cache" uv run mypy --strict src/
RUFF_CACHE_DIR="${TMPDIR:-/tmp}/ruff-cache" ruff check .
```

If bare `python`/`pytest`/`mypy` fail, use the `uv run` prefix (enforced by `pre-bash-toolchain-guard` hook).

### Node (npm/pnpm)

npm caches to `~/.npm/` by default, which is outside the sandbox write allowlist. `node_modules/` is fine (inside CWD).

| Default Behaviour | Problem | Fix |
|---|---|---|
| `NPM_CONFIG_CACHE=~/.npm` | Outside sandbox write allowlist | `NPM_CONFIG_CACHE="$TMPDIR/npm-cache"` |

**Standard prefix for Node commands:**
```bash
NPM_CONFIG_CACHE="${TMPDIR:-/tmp}/npm-cache" npx vitest
NPM_CONFIG_CACHE="${TMPDIR:-/tmp}/npm-cache" npm install
```

If `npx`/`pnpm exec` fail with network errors, check that `registry.npmjs.org` is in `allowedDomains`.

## Decision Tree: Tool Fails in Sandbox

```
Tool command fails
├── "Operation not permitted" / "Permission denied"
│   ├── Writing to a path outside $CWD or $TMPDIR?
│   │   └── Redirect output to $TMPDIR or project directory
│   └── Reading a denied path (.ssh, .env, secrets)?
│       └── You should not be reading this file — check your approach
├── "TLS handshake failure" / "network unreachable" / "connection refused"
│   ├── Is the target domain in settings.json allowedDomains?
│   │   ├── No → Report to user: "Domain X needs to be added to allowedDomains"
│   │   └── Yes → Report exact error to user — may be a proxy/cert issue
│   └── Is it GOTOOLCHAIN trying to download Go?
│       └── Set GOTOOLCHAIN=local — use the locally installed version
├── "go: toolchain go1.X.Y required"
│   └── Local Go is too old for this module. Report version mismatch to user.
│       Do NOT attempt to download. Do NOT retry.
└── Other error
    └── This is likely a real code/config bug. Fix it normally.
```

## Critical Rules

1. **Never write "sandbox blocks this" and continue.** Either fix the sandbox configuration or STOP and report to the user.
2. **Never retry a failing command hoping it will work.** Sandbox restrictions are deterministic — if it fails once, it fails every time.
3. **Always use `$TMPDIR`, never hardcode `/tmp`.** The sandbox sets `$TMPDIR` to a writable directory. Hardcoded `/tmp` may not be the same path.
4. **Preflight before coding.** Run `go version && go build ./...` (or equivalent) before writing code. If the toolchain is broken, stop immediately.
5. **SKIP ≠ acceptable.** If a verification check is skipped because a tool is missing, that means verification is incomplete. Do not write completion artifacts with unverified code.
