---
name: project-toolchain
description: >
  Project toolchain detection and correct command prefixes per language.
  Prevents failures from bare tool invocations outside virtual environments.
alwaysApply: true
---

# Project Toolchain Rules

Claude Code runs every Bash command in a fresh shell — no venv is activated.
You MUST detect the project toolchain and use the correct prefix for ALL commands.

## Detection Table

Check marker files in the working directory before running any tool:

| Marker | Stack | Run Prefix | Add Dependency | Install |
|--------|-------|-----------|----------------|---------|
| `uv.lock` | Python (uv) | `uv run` | `uv add` / `uv add --dev` | `uv sync` |
| `poetry.lock` | Python (poetry) | `poetry run` | `poetry add` / `poetry add --group dev` | `poetry install` |
| `requirements.txt` only | Python (pip) | `.venv/bin/python` | `pip install` | `pip install -r requirements.txt` |
| `go.mod` | Go | *(none)* | `go get` | `go mod download` |
| `pnpm-lock.yaml` | Frontend (pnpm) | `pnpm` | `pnpm add` / `pnpm add -D` | `pnpm install` |
| `package-lock.json` | Frontend (npm) | `npx` | `npm install` | `npm install` |
| `yarn.lock` | Frontend (yarn) | `yarn` | `yarn add` / `yarn add -D` | `yarn install` |
| `bun.lockb` | Frontend (bun) | `bunx` | `bun add` / `bun add -D` | `bun install` |
| New Python project | Python (uv) | `uv run` | `uv add` | `uv init` |

## Python — FORBIDDEN bare commands

In uv/poetry projects, these will FAIL (tool not on system PATH):

| FORBIDDEN | Use Instead (uv) | Use Instead (poetry) |
|-----------|-------------------|----------------------|
| `pytest` | `uv run pytest` | `poetry run pytest` |
| `mypy src/` | `uv run mypy src/` | `poetry run mypy src/` |
| `python script.py` | `uv run python script.py` | `poetry run python script.py` |
| `ruff check .` | `uv run ruff check .` | `poetry run ruff check .` |
| `pip install X` | `uv add X` | `poetry add X` |
| `python -m venv` | *(uv manages .venv automatically)* | — |

## Go — System toolchain, no prefix needed

- Build: `go build ./...`
- Test: `go test ./... -count=1`
- Format: `goimports -local <module> -w .` (NEVER `go fmt`)
- Lint: `golangci-lint run ./...`
- Module name: first line of `go.mod`

## Frontend — Match the lock file

| FORBIDDEN | When | Use Instead |
|-----------|------|-------------|
| `npm install` | `pnpm-lock.yaml` exists | `pnpm install` |
| `yarn add` | `pnpm-lock.yaml` exists | `pnpm add` |
| `pnpm add` | `package-lock.json` exists | `npm install` |

Never create a second lock file. Use the package manager that owns the existing one.
