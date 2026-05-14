---
name: project-preferences
alwaysApply: true
description: >
  Project-specific conventions and opinionated choices. Library selections,
  tooling mandates, coding rules that differ from community defaults.
  Single source of truth — never duplicate these in other skills.
---

# Project Preferences

Opinionated choices that differ from community defaults. These are NOT standard practices — they are this project's specific conventions.

---

## Language & Style

**British English** in all **written artifacts**: behaviour, colour, organise, analyse, serialise, initialise, optimise, defence, centre, licence (noun). Applies to file contents, code, comments, docstrings, commit messages, PR titles/descriptions, plans, designs, JSON outputs, and persisted memory files.

**Conversational responses** to the user (chat, AskUserQuestion, TaskCreate subjects, other non-persisted UI output) match the user's language. Persisted artifacts stay British English regardless of conversation language.

Enforcement: non-blocking PostToolUse hook `bin/post-edit-cyrillic-guard` warns on Cyrillic in edited content; allowlist for `testdata/`, `fixtures/`, `memory/`.

---

## Go

### Libraries

| Purpose | Use | Not |
|---------|-----|-----|
| Logging | `github.com/rs/zerolog` (injected, never global) | slog, zap, logrus, stdlib `log` |
| Testing | `github.com/stretchr/testify` (suites, require, assert) | stdlib testing only |
| CLI | `github.com/alecthomas/kong` | cobra, urfave/cli |
| Stack traces | `github.com/pkg/errors` at error origin | — |

### Tooling

| Action | Command | Never |
|--------|---------|-------|
| Format | `goimports -local <module-name> -w .` | `go fmt`, `gofmt` |
| Lint | `golangci-lint run ./...` | — |
| Test | `go test -race -count=1 ./...` | — |

### Rules (Stricter Than Community)

- **No runtime panics** — `panic()` and `Must*()` ONLY in `init()`, `main()` before server starts, or test helpers. FORBIDDEN in handlers, methods, any runtime code
- **No `log.Fatal`** — return error instead
- **No `interfaces.go` files** — define interfaces where consumed
- **No split test files** — no `*_internal_test.go`
- **No doc comments on unexported** symbols
- **No nil checks on pointer arguments** — caller responsibility, not callee. Especially for long-lived objects created at init
- **Constructor order**: config first, dependencies middle, logger last
- **Testing: `require` only** — never `testify/assert`. First failure stops the test
- **Constructor returns** `(*T, error)` for services
- **Error wrapping**: always `%w` in `fmt.Errorf`
- **No `fmt.Print*` in production** — use zerolog

---

## Python

### Libraries

| Purpose | Use | Not |
|---------|-----|-----|
| Logging | `structlog` | stdlib `logging`, loguru |
| Validation | `pydantic` for DTOs | — |

### Tooling

| Action | Command | Never |
|--------|---------|-------|
| Package manager | `uv` | pip directly, poetry, conda |
| Format | `ruff format` | black, autopep8 |
| Lint | `ruff check` + `pylint` + `mypy` | flake8 |
| New project | `uv init` | `python -m venv` |

---

## Frontend

### Tooling

| Action | Tool |
|--------|------|
| Format | Prettier |
| Lint | ESLint |
| Package manager | Match lock file (pnpm preferred for new) |

---

## All Languages

- **Immutability preferred** — return new instances, don't mutate. Exception: measured hot paths
- **DTO vs Domain Object**: public fields if no invariants; private fields if methods depend on field validity
- **Interfaces**: create only when needed (2+ implementations or mocking). Consumer-side definition
- **Error detection**: compile-time > startup-time > runtime error > runtime panic (NEVER)
- **Backward compatibility**: never break existing consumers
