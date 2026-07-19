# AeroSpace Tier-2 — Dynamic Layouts (`aerospace-layouts`) — Progress & Resume Point

**Created:** 2026-07-19
**Companion to:** `macos_tooling_setup.md` §2.1 (AeroSpace baseline).
**Purpose:** session handoff so setup can continue in a fresh session.

## What this is

An awesome-wm-style **dynamic layout** system layered on AeroSpace's i3 tree.
The direction changed early on: NOT app-pinned fixed-proportion frames (the
Ion/i3 model, initially proposed and rejected), but a library of **named,
app-agnostic geometry algorithms** that re-tile whatever windows currently sit
on the focused workspace — exactly the awesome `Mod+Space` workflow. Window→slot
placement stays the user's job (focus/move/swap).

## What was built — the `aerospace-layouts` uv project

- **Location:** `roles/devbox/files/.config/aerospace/layouts/` (standalone uv
  project; console-script `aerospace-layouts`). Mirrors the `dot_claude/bin/`
  deployed-uv convention: own `uv.lock`/`.venv`, `uv sync --frozen`. It is
  intentionally **not** a repo-root workspace member (an auto-added
  `[tool.uv.workspace]` stanza was reverted).
- **Architecture — one testable seam:** layout functions are pure
  `(windows) -> list[Command]`; a thin executor turns `Command`s into
  `aerospace` calls through a single injected-runner CLI boundary, so every
  layout is unit-tested with no live WM.
  - `model.py` — `Window` (incl. `parent_layout`), `Command`, `MasterSide`,
    pure predicates `tiled_windows()` / `floating_windows()`.
  - `aerospace.py` — the CLI boundary (`AerospaceClient`, injected `runner`,
    `--window-id` addressing, exit-tolerance, `focus_dfs_index`, logging).
  - `ordering.py` — `DfsProbeOrdering` (default; derives true visual order via
    `focus --dfs-index` probe + focus restore). `IdentityOrdering` kept for
    tests only (list-windows array order is NOT dfs order).
  - `layouts/` — `tile.py` (master + stack, 4 sides), `maxx.py` (accordion),
    `columns.py`, `floating.py`.
  - `planner.py` — `plan_layout`, cycle math, `CYCLE` constant, tile master-side
    mapping. Tiling layouts filter to `tiled_windows()` first.
  - `cli.py` — verbs `cycle [--reverse]`, `apply <name>`, `reapply`,
    `adjust-master (+|-)`, `promote`, `diagnose`. `apply_layout` is a live
    two-phase flow: execute `flatten` → probe dfs order on the flattened tree →
    plan joins → execute.
  - `state.py` — `~/.local/state/aerospace-layouts/state.json`, atomic write,
    per-workspace `{layout_index}`.
  - `diagnostics.py` — non-destructive `diagnose` output formatter.
  - `geometry.py` — deliberately empty Phase-2 seam (absolute master sizing).

- **Layout library (MVP):** `floating`, `tile` + `tile.left`/`tile.top`/
  `tile.bottom`, `max` (accordion approximation of monocle), `columns`.
- **Master ratio = Design R** (relative `resize smart` nudge from balanced; no
  persisted factor, no monitor-width math). Design A (absolute via CoreGraphics
  `CGDisplayBounds`) deferred.
- **Reapply = manual** only. `on-window-detected` auto-reapply deferred.

## Live-verified AeroSpace behaviour (probed on the running WM)

- `--window-id` addressing works reliably (focus follows the window across
  workspaces).
- `flatten-workspace-tree` on the wide monitor yields a horizontal ROW.
- `resize smart ±N` moves the ratio of the current split (Design R works).
- `join-with <dir>` is **strict**, operates along the current split axis, and
  needs a neighbour in that direction (else "No windows in the specified
  direction"); accepts only `left|down|up|right`.
- `layout h_tiles` may exit non-zero when already in that state → tolerated.
- **`tile` (master-left) builds a correct master + vertical-stack tree on the
  live WM — live smoke test GREEN.**

## Bring-up fixes (each confirmed by a failing live run then fixed)

1. Ordering must use true dfs order, not `list-windows --json` array order.
2. Ordering must be probed AFTER `flatten` (two-phase live flow), not before —
   stale pre-flatten order mis-slotted the master.
3. **Floating windows are excluded from tiling layouts** (awesome-correct: a
   floating client is skipped by tile/max/columns and left untouched). A
   floating kitty window was the cause of the persistent join failure.

## Test / quality state

72 passed, 1 skipped (live-gated); ruff + ruff format + pyright (strict) clean.
**Not committed yet.**

## RESUME HERE — next session starts with these

1. **Keybinding wiring proposal for `aerospace.toml`** (present to user, await
   approval before editing config):
   - `alt-space` → `exec-and-forget …/aerospace-layouts cycle`
   - `alt-shift-space` → `… cycle --reverse`
   - **Reallocate float-toggle** — currently `alt-shift-space`
     (`layout floating tiling`, `aerospace.toml:60`), which the cycle takes
     over. Needs a new key.
   - Old `alt-space` (`layout tiles accordion`, `aerospace.toml:58`) is now
     subsumed by the layout library — decide whether to drop it.
   - **Cheat-sheet key** — user wants a keybinding that shows available
     bindings. AeroSpace has NO native binding-help overlay. Options: (1)
     generate from `aerospace.toml` and show in a floating window / Quick Look /
     notification (recommended, single source of truth); (2) static
     markdown/image opened via `open`; (3) which-key popup via Sketchybar
     (heavier, defer). **User to choose variant.**
   - Master-adjust keys for Design R (`adjust-master +/-`) — pick a chord that
     does NOT collide with the `alt-shift-{ijlm}` move cluster.
2. **Ansible deploy step** — add a `uv sync --frozen --no-dev` for
   `~/.config/aerospace/layouts/` (mirror `install_configs.yml` Block 1b for
   `bin/`); bindings must point at the absolute built venv console-script
   (`uv`/`exec-and-forget` PATH does not include `uv`). Deploy via
   `make claude-push` equivalent / the aerospace copy-dir block.
3. **Commit** the uv project.
4. **Extend the library + move ergonomics** — implement the three "Confirmed
   new requirements" below (`fair` balanced two-column, and move-between-
   rows/columns key scheme). Can proceed alongside the wiring proposal.

## Deferred / not yet live-verified

- Only `tile` (master-left) verified live. Still unobserved on the live WM:
  `tile.left`/`tile.top`/`tile.bottom`, `max` (accordion), `columns`, the
  merge-vs-nest stack shape for n>3, and `adjust-master`/`promote`.
- Design A (absolute master ratio, `CGDisplayBounds` monitor mapping, gap math).
- `on-window-detected` auto-reapply (debounced, must not disturb the Zen→ws1
  rule).

## Confirmed new requirements (2026-07-19) — user wants ALL of these

1. **`tile` two-column (master + stack)** — already built and live-verified;
   just needs the keybinding wiring to become reachable.
2. **`fair` / balanced two-column** (e.g. 4 windows → 2 left + 2 right, each
   column its own stack) — **now required, no longer deferred.** New pure
   layout function in `layouts/`, added to the library + cycle. Verify live
   like `tile`.
3. **Move windows between rows and columns** — ergonomic bindings/commands to
   relocate a window between the master column and the stack, and to reorder
   within a column (rows). AeroSpace primitives: directional `move`
   (`alt-shift-{ijlm}` already bound), `join-with`, `swap`, and the existing
   `promote` verb. Design a coherent move-ergonomics scheme (awesome parallels:
   swap within stack, promote to/from master) and wire keys. Some pieces exist
   (`promote`, directional `move`); the gap is a clean, documented key scheme
   for moving across the row/column structure.

## Notes / open questions from the user

- Why kitty was floating: a stray float toggle / default; un-float with the
  float-toggle key (`alt-shift-space` today) or `aerospace layout tiling`.

## How to run (manual, from a normal terminal, AeroSpace running)

- Diagnose (non-destructive): `aerospace-layouts diagnose`
  (verbose: `AEROSPACE_LAYOUTS_LOG=debug aerospace-layouts diagnose`)
- Live smoke: `AEROSPACE_LAYOUTS_LIVE=1 uv run pytest -m live -s`
- Unit tests: `uv run pytest` (from the project dir)
