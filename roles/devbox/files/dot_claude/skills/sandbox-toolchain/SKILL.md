---
name: sandbox-toolchain
description: >
  How Claude Code's sandbox interacts with language toolchains (Go, Python, Node).
  Covers writable directories, network restrictions, env var configuration,
  and a decision tree for diagnosing tool failures in sandbox.
  Not to be confused with `project-toolchain` (invocation ergonomics) —
  `sandbox-toolchain` covers environment boundaries: what the sandbox allows
  (writable dirs, network allowlist, env vars).
alwaysApply: false
triggers:
  - sandbox
  - GOCACHE
  - GOMODCACHE
  - GOTOOLCHAIN
  - GOFLAGS
  - GOPROXY
  - GOSUMDB
  - GOPRIVATE
  - GOINSECURE
  - GO111MODULE
  - UV_CACHE_DIR
  - UV_TOOL_DIR
  - uvx
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

Go has three sandbox-breaking defaults. `GOTOOLCHAIN=local`, `GOCACHE`, and `GOMODCACHE` are all set in `settings.json` env block at session start, pointing at writable paths under `/tmp/claude/` (`go-build-cache`, `go-mod-cache`).

No manual prefix needed — just run commands directly:
```bash
go build ./...
go test ./...
```

If cache errors occur, verify env is active: `env | grep -E 'GOCACHE|GOMODCACHE'`. On corruption, run `go clean -cache` or `go clean -modcache` — do not override `GOCACHE=…` inline (blocked by `pre_bash_toolchain_guard`).

**Never override Go toolchain or module-resolution env vars.** `pre_bash_toolchain_guard` blocks all three shapes (inline `VAR=… go …`, `export VAR=…`, standalone `VAR=…;`) for the following vars:

| Var | Why blocked |
|-----|-------------|
| `GOTOOLCHAIN` | Pinned to `local` in settings.json. Override forces a toolchain download that fails in sandbox (host allowlist excludes Go download mirrors). |
| `GOSUMDB`, `GOINSECURE` | Bypass checksum verification / allow insecure fetches — security-relevant, never a legitimate workaround. |
| `GOPROXY`, `GOPRIVATE` | Override module source / privacy — usually a workaround for a real module-resolution problem. |
| `GO111MODULE`, `GOWORK`, `GOVCS`, `GOFLAGS`, `GOEXPERIMENT` | Legacy/mode toggles and build-flag overrides — almost always a workaround. |

Cross-compilation (`GOOS`, `GOARCH`) and `CGO_ENABLED` are legitimate build tuners and stay allowed. If the Go build fails, escalate to the user — do not reroute via env vars.

### Python (uv, ruff, mypy)

Python toolchains cache to `~/.cache/` by default, which is outside the sandbox write allowlist. `settings.json` env block sets `UV_CACHE_DIR`, `RUFF_CACHE_DIR`, `MYPY_CACHE_DIR`, `PYTEST_CACHE_DIR` to `/tmp/claude/<tool>-cache/` at session start — inherited by every Bash call without command rewriting.

No manual prefix needed — just run commands directly:
```bash
uv run pytest
ruff check .
mypy src/
```

**Never override cache env vars — in any form.** `pre_bash_toolchain_guard` blocks all three shapes:
- inline env-prefix: `UV_CACHE_DIR=/tmp/x uv sync`
- explicit export: `export UV_CACHE_DIR=/tmp/x; uv sync`
- standalone assignment then chain: `UV_CACHE_DIR=/tmp/x && uv sync`

Watched vars: `UV_CACHE_DIR`, `UV_TOOL_DIR`, `RUFF_CACHE_DIR`, `MYPY_CACHE_DIR`, `PYTEST_CACHE_DIR`, `PIP_CACHE_DIR`, `POETRY_CACHE_DIR` (plus the Go, Node, Cargo siblings — see `CACHE_WORKAROUND_VARS` in the guard). `PYTHONPATH` is treated the same way — never patch `sys.path` at invocation time; configure `src`-layout in `pyproject.toml` or use `uv run`.

If you see a cache-corruption error (`Failed to install … METADATA: No such file`), the fix is:
```bash
uv cache clean          # not `UV_CACHE_DIR=/tmp/x uv sync`
ruff clean              # for ruff
rm -rf "$MYPY_CACHE_DIR"  # mypy has no clean subcommand
```
Then retry the original command.

**Never `uvx <tool>` in a uv project.** `uvx` runs an isolated one-shot install and bypasses the project's uv env and `uv.lock`. In a uv project (detected by `uv.lock` in ancestry), the guard blocks `uvx`. Use `uv add <tool>` (or `uv add --dev`) plus `uv run <tool>` instead. If `uv run <tool>` fails — **escalate to the user; do not work around it with uvx.** `uvx` is fine for genuinely standalone one-shots outside any uv project (e.g. `uvx cookiecutter gh:foo/bar` in an empty scratch dir).

If bare `python`/`pytest`/`mypy` fail, use the `uv run` prefix (enforced by `pre_bash_toolchain_guard` hook). Direct `.venv/bin/<tool>` and `PYTHONPATH=… python …` are also blocked — they bypass uv/poetry env management.

### Node (npm/pnpm)

npm caches to `~/.npm/` by default, which is outside the sandbox write allowlist. `node_modules/` is fine (inside CWD). `NPM_CONFIG_CACHE` is set in `settings.json` env block (`/tmp/claude/npm-cache/`).

No manual prefix needed — just run commands directly:
```bash
npx vitest
npm install
```

If cache errors occur, verify env is active: `env | grep NPM_CONFIG_CACHE`.

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
3. **Never override cache or toolchain env vars — in any form.** `UV_CACHE_DIR=… uv sync`, `export GOTOOLCHAIN=…`, `GOSUMDB=off; go build` and their siblings are workarounds — `pre_bash_toolchain_guard` blocks all three shapes (inline env-prefix, `export`, standalone `VAR=…;`) for cache vars, Go toolchain-override vars, and `PYTHONPATH`. On cache corruption, use the tool's own clean command (`uv cache clean`, `go clean -cache`, `ruff clean`). On toolchain/module-resolution errors, escalate to the user.
4. **Never `uvx <tool>` in a uv project.** `uvx` bypasses the project env and `uv.lock`. Use `uv add <tool>` + `uv run <tool>`. If `uv run` fails, escalate — do not fall back to `uvx`.
5. **Always use `$TMPDIR`, never hardcode `/tmp`.** The sandbox sets `$TMPDIR` to a writable directory. Hardcoded `/tmp` may not be the same path.
6. **Preflight before coding.** Run `go version && go build ./...` (or equivalent) before writing code. If the toolchain is broken, stop immediately.
7. **SKIP ≠ acceptable.** If a verification check is skipped because a tool is missing, that means verification is incomplete. Do not write completion artifacts with unverified code.
