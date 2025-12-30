---
name: python-tooling
description: >
  Python project tooling with uv, poetry, pip. Use when discussing project setup,
  package management, pyproject.toml, virtual environments, or development tools.
  Triggers on: uv, poetry, pip, pyproject.toml, requirements.txt, virtual environment,
  venv, project setup, new project, package manager.
---

# Python Tooling Reference

Project setup and package management for Python projects.

---

## Detect Project Tooling

**Before writing any code**, determine what package manager the project uses:

```bash
# Check for uv
ls uv.lock pyproject.toml 2>/dev/null

# Check for poetry
ls poetry.lock 2>/dev/null

# Check for pip
ls requirements.txt requirements-dev.txt 2>/dev/null
```

| Files Found | Project Uses | Your Commands |
|-------------|--------------|---------------|
| `uv.lock` | uv | `uv add`, `uv run`, `uv sync` |
| `pyproject.toml` with `[tool.uv]` | uv | `uv add`, `uv run`, `uv sync` |
| `poetry.lock` | poetry | `poetry add`, `poetry run` |
| `requirements.txt` only | pip | `pip install`, `python` |
| Nothing (new project) | **uv** | `uv init`, `uv add`, `uv run` |

**Adapt to what the project uses.** Don't mix tools.

---

## New Project Setup (uv)

**ALWAYS use `uv` for new Python projects. No exceptions.**

### FORBIDDEN in uv Projects

| FORBIDDEN | USE INSTEAD |
|-----------|-------------|
| `pip install <package>` | `uv add <package>` |
| `pip install -r requirements.txt` | `uv sync` |
| `python script.py` | `uv run python script.py` |
| `pytest` | `uv run pytest` |
| `black src/` | `uv run black src/` |
| Creating `pyproject.toml` via `cat`/`echo` | `uv init` |
| `python -m venv .venv` | Let uv manage automatically |

**Why:** `uv` ensures reproducible builds via lockfile. Manual pip operations bypass the lockfile.

### Project Initialization

**For libraries** (reusable packages):
```bash
uv init my-library --lib
cd my-library
```

**For applications** (services, CLIs):
```bash
uv init my-service --package
cd my-service
```

Both create a `src/` layout:
```
my-project/
├── src/
│   └── my_project/
│       └── __init__.py
├── pyproject.toml
├── .python-version
└── README.md
```

### Adding Dependencies

**Runtime dependencies:**
```bash
uv add requests pydantic
```

**Dev dependencies** (testing, linting):
```bash
uv add --dev pytest pytest-mock pytest-cov
uv add --group lint ruff pylint mypy
```

### Running Tools

```bash
# Run tests
uv run pytest

# Run linters
uv run --group lint ruff check src/
uv run --group lint pylint src/
uv run --group lint mypy src/

# Format code
uv run --group lint ruff format src/
```

---

## pyproject.toml Template

```toml
[project]
name = "my-project"
version = "0.1.0"
description = "Brief description"
readme = "README.md"
requires-python = ">=3.11"
dependencies = []

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-mock>=3.12",
    "pytest-cov>=4.1",
]
lint = [
    "ruff>=0.8",
    "pylint>=3.0",
    "mypy>=1.13",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# --- Tool Configuration ---

[tool.ruff]
line-length = 88
target-version = "py311"
src = ["src"]

[tool.ruff.lint]
select = ["E", "F", "B", "I", "UP", "C4", "SIM"]
ignore = ["E501"]  # line length handled by formatter

[tool.ruff.format]
quote-style = "double"

[tool.pylint.main]
source-roots = ["src"]
ignore-patterns = ["test_.*\\.py"]

[tool.pylint.messages_control]
disable = ["C0114", "C0115", "C0116"]  # missing docstrings

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
disallow_untyped_defs = true

[[tool.mypy.overrides]]
module = ["tests.*"]
disallow_untyped_defs = false

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --strict-markers"
```

---

## Project Structure

```
project/
├── src/
│   └── mypackage/
│       ├── __init__.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── routes.py
│       ├── services/
│       │   ├── __init__.py
│       │   └── user_service.py
│       └── models/
│           ├── __init__.py
│           └── user.py
├── tests/
│   ├── conftest.py
│   └── test_user_service.py
├── pyproject.toml
└── README.md
```

---

## Poetry Projects

If the project uses Poetry:

```bash
# Add dependencies
poetry add requests

# Add dev dependencies
poetry add --group dev pytest

# Run commands
poetry run pytest
poetry run python script.py

# Install from lockfile
poetry install
```

---

## Pip Projects

If the project uses plain pip:

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run commands
python script.py
pytest
```

---

## Quick Reference: Tooling Violations

| Violation | Fix |
|-----------|-----|
| `pip install` in uv project | Use `uv add` |
| `python script.py` in uv project | Use `uv run python script.py` |
| Creating `pyproject.toml` manually | Use `uv init` |
| Missing `uv.lock` in git | Run `uv sync` and commit lock |
| Mixing package managers | Use only one (prefer uv) |
| `--group` missing for dev deps | Use `uv add --group dev pytest` |
