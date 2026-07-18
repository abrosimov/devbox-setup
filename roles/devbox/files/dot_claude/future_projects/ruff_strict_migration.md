# Ruff strict-mode migration

**Status**: done (2026-07) — `ruff check` and `ruff format --check` both exit 0
across the tree, and `--exit-zero` has been removed from `make lint-py`, so CI now
enforces the strict baseline. The deliberate ignores listed in "Progress (2026-07)"
below were accepted as permanent design decisions.
**Created**: 2026-06-10
**Repo**: `devbox-setup`

## Progress (2026-07)

The `bin/` and `skills/*/scripts/` trees were brought to a clean `ruff check` and
`ruff format` on branch `fix_linters`. `ruff check .` now exits 0 and
`ruff format --check .` reports no diffs, so the formatter no longer breaks CI.

Most violations were **fixed in code** (behaviour-preserving), verified green by
`make typecheck`, `make test`, `make test-git-hooks`, and `make test-claude-hooks`:

- `UP017` (`datetime.UTC`), `FURB188` (`str.removeprefix`), `I001`, `RUF100`,
  `SIM114`, `PLC0208`, `RUF021`, `Q003`, `TC005` — ruff safe auto-fixes.
- `PTH111`/`PTH109` — `os.path.expanduser`/`os.getcwd` → `pathlib.Path`.
- `SIM102`/`SIM105`/`SIM110`, `TRY300`, `PERF401`, `PLR1714` — hand refactors in
  `bash_decision_gate.py`.
- `PT018` (split composite asserts), `RUF059`/`ARG001` (drop unused test
  fixtures/unpacks), `N802` (`test_blocks_kill_KILL` → `test_blocks_kill_sigkill`,
  `test_allows_kill_TERM` → `test_allows_kill_sigterm`) — in `test_*` files.
- `TC003` — `Iterator` moved under `TYPE_CHECKING` in `scan_transcripts.py`.

The following are **resolved via deliberate, scoped ignores** — each is a permanent
design decision, not a punt. They mirror the existing `validate_skill_evals.py`
precedent and were accepted as permanent, so `--exit-zero` was removed:

| Rule(s) | Where | Mechanism | Reason |
|---------|-------|-----------|--------|
| `RUF001` | `bash_decision_gate.py`, `proposal_discipline.py`, `test_proposal_discipline.py` | per-file-ignore (former) + inline `# noqa` (latter two) | Intentional Cyrillic in Russian-language deny messages / feedback regex / test fixtures — the characters are meaningful, not accidental homoglyphs, so they must not be "corrected". |
| `C901`, `PLR0911`, `PLR0912` | `bash_decision_gate.py` | per-file-ignore | Security-critical Bash gate; the command-shape dispatchers are branchy by nature (one branch per shell command / redirect shape). Splitting them would fragment the safety logic and reduce reviewability. Behaviour is pinned by `test_bash_decision_gate.py`. |
| `S105` | `bash_decision_gate.py` `_SECRET_DENY_REASON` | inline `# noqa` | False positive — the constant is a deny-reason message template, not a credential. |
| `S110` | `bash_decision_gate.py` `log_miss` | inline `# noqa` | Telemetry write is best-effort and MUST NOT break the hook. |

Migration complete: `--exit-zero` was removed from the `lint-py` target and the
explanatory comment block updated, so `make lint` now fails on any new `ruff check`
violation under `roles/devbox/files/dot_claude/`.

## Context (historical)

`pyproject.toml` enables `ruff check select = ["ALL"]` with a curated `ignore`
list (see the comment block in `pyproject.toml`). This catches modern Python
hygiene problems strictly.

The existing Python scripts under `roles/devbox/files/dot_claude/bin/` and a
handful in `scripts/` predated this strict baseline and, at the June 2026
baseline, produced **~644 violations** after `ruff format` and `ruff check --fix`.

To unblock the rest of the dev tooling (`make lint-yaml`, `make typecheck`,
`make test`, and `ruff format --check`), `make lint-py` ran `ruff check
--exit-zero` — reporting issues without failing — while the formatter stayed
strict. That advisory mode has since been removed (see "Flip the switch" above).

This task captured the work to bring the existing code up to strict and then
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

## Flip the switch (done)

The `Makefile` `lint-py` target was flipped to strict:

```diff
 lint-py: $(DEV_SENTINEL)
-	@$(DEV_BIN)/ruff check --exit-zero roles/devbox/files/dot_claude/
+	@$(DEV_BIN)/ruff check roles/devbox/files/dot_claude/
 	@$(DEV_BIN)/ruff format --check roles/devbox/files/dot_claude/
```

The explanatory comment block above the target was updated to describe strict
enforcement. The `per-file-ignores` in `pyproject.toml` were kept deliberately —
see the table under "Progress (2026-07)" for why each is permanent.

## Related

- `pyproject.toml` — current ruff config (look for the `[tool.ruff.lint]` block).
- `Makefile` — `lint-py`, `typecheck`, `test` targets.
- `.yamllint.yml` — companion YAML linter config.
