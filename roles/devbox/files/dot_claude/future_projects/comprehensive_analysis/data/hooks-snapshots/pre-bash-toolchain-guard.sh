#!/bin/sh
# pre-bash-toolchain-guard — PreToolUse hook that blocks wrong toolchain commands.
#
# Unconditional blocks (user preference: always uv for Python):
#   pip install    → uv add
#   python -m venv → uv manages venvs
#
# Context-aware blocks (check marker files):
#   bare pytest/mypy/python <file> in uv project → uv run ...
#   npm install in pnpm project → pnpm install
#   yarn add/install in pnpm project → pnpm
#   go fmt/gofmt → goimports
#
# Env: CC_BASH_COMMAND — the command string being executed.
# Exit 2 to block, 0 to allow.

cmd="$CC_BASH_COMMAND"

# --- Unconditional blocks ---

# Block go fmt / gofmt (always wrong — use goimports)
case "$cmd" in
  *'go fmt'*|*'gofmt'*)
    echo 'BLOCKED: Use `goimports -local <module-name>`, not go fmt/gofmt. Extract module name from go.mod.' >&2
    exit 2
    ;;
esac

# Block pip install (always use uv add or poetry add)
case "$cmd" in
  'pip install'*|'pip3 install'*|'python -m pip'*|'python3 -m pip'*)
    echo 'BLOCKED: Use `uv add <package>` (or `poetry add` in poetry projects). Never use pip install directly.' >&2
    exit 2
    ;;
esac

# Block manual venv creation (uv manages .venv automatically)
case "$cmd" in
  'python -m venv'*|'python3 -m venv'*)
    echo 'BLOCKED: Do not create venvs manually. Use `uv sync` — uv creates and manages .venv automatically.' >&2
    exit 2
    ;;
esac

# --- Helper: walk up to find a marker file ---

find_marker() {
  marker="$1"
  dir="$PWD"
  i=0
  while [ "$i" -lt 20 ]; do
    [ -f "$dir/$marker" ] && return 0
    parent=$(dirname "$dir")
    [ "$parent" = "$dir" ] && return 1
    dir="$parent"
    i=$((i + 1))
  done
  return 1
}

# --- Context-aware: Python uv projects ---

# Block bare pytest, mypy, python <file> when uv.lock exists
case "$cmd" in
  pytest*|'python -m pytest'*)
    if find_marker "uv.lock"; then
      echo 'BLOCKED: This is a uv project. Use `uv run pytest` instead of bare `pytest`.' >&2
      exit 2
    fi
    if find_marker "poetry.lock"; then
      echo 'BLOCKED: This is a poetry project. Use `poetry run pytest` instead of bare `pytest`.' >&2
      exit 2
    fi
    ;;
  mypy\ *)
    if find_marker "uv.lock"; then
      echo 'BLOCKED: This is a uv project. Use `uv run mypy` instead of bare `mypy`.' >&2
      exit 2
    fi
    if find_marker "poetry.lock"; then
      echo 'BLOCKED: This is a poetry project. Use `poetry run mypy` instead of bare `mypy`.' >&2
      exit 2
    fi
    ;;
  pylint\ *)
    if find_marker "uv.lock"; then
      echo 'BLOCKED: This is a uv project. Use `uv run pylint` instead of bare `pylint`.' >&2
      exit 2
    fi
    ;;
  'python '[!-]*|'python3 '[!-]*)
    # Block `python script.py` but NOT `python --version`, `python -c ...`
    if find_marker "uv.lock"; then
      echo 'BLOCKED: This is a uv project. Use `uv run python ...` instead of bare `python`.' >&2
      exit 2
    fi
    if find_marker "poetry.lock"; then
      echo 'BLOCKED: This is a poetry project. Use `poetry run python ...` instead of bare `python`.' >&2
      exit 2
    fi
    ;;
esac

# --- Context-aware: Frontend package manager mismatch ---

case "$cmd" in
  'npm install'*|'npm i '*|'npm i'|'npm add'*|'npm ci'*)
    if find_marker "pnpm-lock.yaml"; then
      echo 'BLOCKED: This is a pnpm project (pnpm-lock.yaml exists). Use `pnpm install` / `pnpm add`.' >&2
      exit 2
    fi
    if find_marker "yarn.lock"; then
      echo 'BLOCKED: This is a yarn project (yarn.lock exists). Use `yarn install` / `yarn add`.' >&2
      exit 2
    fi
    ;;
  'yarn install'*|'yarn add'*)
    if find_marker "pnpm-lock.yaml"; then
      echo 'BLOCKED: This is a pnpm project (pnpm-lock.yaml exists). Use `pnpm install` / `pnpm add`.' >&2
      exit 2
    fi
    if find_marker "package-lock.json"; then
      echo 'BLOCKED: This is an npm project (package-lock.json exists). Use `npm install`.' >&2
      exit 2
    fi
    ;;
  'pnpm install'*|'pnpm add'*)
    if find_marker "package-lock.json"; then
      echo 'BLOCKED: This is an npm project (package-lock.json exists). Use `npm install`.' >&2
      exit 2
    fi
    if find_marker "yarn.lock"; then
      echo 'BLOCKED: This is a yarn project (yarn.lock exists). Use `yarn install` / `yarn add`.' >&2
      exit 2
    fi
    ;;
esac

exit 0
