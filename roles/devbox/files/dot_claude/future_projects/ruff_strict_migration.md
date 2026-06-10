# Ruff strict-mode migration

**Status**: open
**Created**: 2026-06-10
**Repo**: `devbox-setup`

## Context

`pyproject.toml` enables `ruff check select = ["ALL"]` with a curated `ignore`
list (see the comment block in `pyproject.toml`). This catches modern Python
hygiene problems strictly.

The existing Python scripts under `roles/devbox/files/dot_claude/bin/` and a
handful in `scripts/` predate this strict baseline and currently produce
**~644 violations** after `ruff format` and `ruff check --fix` have been applied.

To unblock the rest of the dev tooling (`make lint-yaml`, `make typecheck-py`,
`make test-py`, and `ruff format --check`), `make lint-py` runs
`ruff check --exit-zero` — it reports issues but does not fail. The formatter
remains strict (it is deterministic and auto-fixable).

This task captures the work to bring the existing code up to strict and then
flip `--exit-zero` off.

## Violation inventory (baseline, June 2026)

Top categories produced by `ruff check . --statistics`:

| Count | Rule | Description |
|------:|------|-------------|
| 247 | `PT009` | `unittest.assertX` instead of plain `assert` (pytest style) |
| 201 | `ANN201` | Missing return-type annotation on public functions |
| 38 | `PTH118` | `os.path.join(...)` should be `Path / "..."` |
| 32 | `UP045` | `Optional[X]` should be `X | None` (PEP 604) |
| 26 | `SIM117` | Combine nested `with` statements |
| 24 | `SLF001` | Access to private member from outside the class |
| 20 | `UP006` | `List[X]` should be `list[X]` (PEP 585) |
| 19 | `PTH108` | `os.unlink` should be `Path.unlink` |
| 18 | `ANN001` | Missing argument-type annotations |
| 10 | `ANN202` | Missing return-type annotation on private functions |
| 8 | `UP035` | Deprecated import (e.g. `typing.List` over `list`) |
| 7 | `PLC0415` | Import not at top of file |
| 6 | `PERF401` | Manual list comprehension instead of `list.extend` |
| 6 | `SIM102` | Collapsible `if` |
| <5 | various | `PTH*`, `E741`, `S108`, `C901`, `FBT*`, `RET*`, etc. |

Run `make lint-py` (or `.venv/bin/ruff check . --statistics`) for the current
breakdown.

## Migration plan

One commit per logical category. Easiest first (modernisations) → semantic last.

1. **Auto-modernisations** (`UP006`, `UP035`, `UP045`):
   ```bash
   .venv/bin/ruff check --select UP --fix --unsafe-fixes .
   ```
   Diff is mechanical (rewrites `List[X]` → `list[X]`, `Optional[X]` → `X | None`).
   Verify by re-running tests.

2. **`PTH*` migrations** (`os.path.*` → `pathlib.Path`): ~70 violations across
   a handful of files. Some are safe auto-fixes (`PTH118` join), others need
   manual judgement (`PTH123` open, where the calling convention may differ).

3. **Annotation coverage** (`ANN001`, `ANN201`, `ANN202`, `ANN003`, `ANN204`):
   ~230 violations. Largest chunk of the work. Best done file-by-file, hand in
   hand with `pyrefly check` to validate the added types.

4. **Pytest style** (`PT009`): the 247 `unittest.assertEqual(a, b)` calls become
   `assert a == b`. Affects `*_test.py` files in `bin/`. Mostly mechanical
   rewrite, but the migration also lets us drop the `import unittest` boilerplate
   and any `class FooTest(unittest.TestCase)` wrappers in favour of plain
   functions — that part is judgement.

5. **Encapsulation and structural** (`SLF001`, `SIM117`, `SIM102`, `C901`,
   `PLC0415`, `PERF401`): one-by-one review. Some may be legitimate `noqa`
   exceptions; most should be cleaned.

6. **Long tail** (`E741`, `S108`, `FBT*`, `RET*`, `TC003`, `PIE810`, `N802`,
   `PLR0912`, `TRY300`, etc.): one-shot pass.

## Flip the switch

When `make lint-py` is clean (no violations from `ruff check`), edit `Makefile`:

```diff
 lint-py: $(DEV_SENTINEL)
-	@$(DEV_BIN)/ruff check --exit-zero .
+	@$(DEV_BIN)/ruff check .
 	@$(DEV_BIN)/ruff format --check .
```

…and remove the explanatory comment block above the target. Update
`pyproject.toml` to remove any per-file `ignore` rules that are no longer needed.

## Related

- `pyproject.toml` — current ruff config (look for the `[tool.ruff.lint]` block).
- `Makefile` — `lint-py`, `typecheck-py`, `test-py` targets.
- `.yamllint.yml` — companion YAML linter config.
