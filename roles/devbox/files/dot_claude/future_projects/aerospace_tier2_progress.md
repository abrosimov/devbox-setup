# AeroSpace Tier-2 — Dynamic Layouts (`aerospace-layouts`) — Progress & Resume Point

**Created:** 2026-07-19
**Companion to:** `macos_tooling_setup.md` §2.1 (AeroSpace baseline).
**Purpose:** session handoff so setup can continue in a fresh session.

---

## SESSION 2 (2026-07-22) — RESUME HERE

The Session-1 "RESUME HERE" block further down is **all DONE** (keybindings,
`fair`, `demote`, deploy step, tap hygiene). Start the next session from here.

### Deployed / current state
- **AeroSpace upgraded 0.20.3-Beta → 0.21.3-Beta** (brew cask). `aerospace eval`
  confirmed working (`aerospace eval 'balance-sizes'` → exit 0). `eval` semantics:
  shell-like string, separators `; || && |` + parens, `&&` binds tighter than `||`,
  pipe = pipefail.
- **`config-version = 2`** added to `aerospace.toml` (v1 was warned as outdated;
  only behavioural change is `persistent-workspaces` now defaults to empty — benign
  for the current keybinding-driven use).
- **eval-phase implemented & deployed** (SE agent, 120 passed / 1 skipped, ruff +
  pyright strict clean):
  - `executor.py`: whole mutation batch → ONE `aerospace eval 'cmd ; cmd ; …'`
    (double-buffered); non-zero → WARNING, never raises; empty → no call.
  - `geometry.py` (Design A): absolute 50 % master via `resize width|height <pts>`
    from `NSScreen.visibleFrame` (pyobjc-framework-cocoa added to pyproject+lock);
    monitor id via `list-monitors --focused` `%{monitor-appkit-nsscreen-screens-id}`;
    degrades to None (no resize) if unavailable.
  - `CYCLE` trimmed to `(tile, tile.left, tile.top, tile.bottom, max)`; `columns`
    and `fair` removed from the cycle but still `apply`-able.
  - `promote`/`demote` append the absolute master-resize (pull-to-half in one gesture).
- Keybindings (deployed `aerospace.toml`): cycle `alt-space`/`alt-shift-space`;
  focus clusters right `i/j/l/,` + left `e/s/f/c`; move `alt-shift-*`; join
  `alt-ctrl-*`; `promote alt-enter` / `demote alt-shift-enter`; adjust-master
  `alt-shift--`/`alt-shift-=`; fullscreen `alt-z`; float `alt-t` / unfloat `alt-shift-t`.

### THE OPEN PROBLEM (why a fresh session is needed)
**Even AFTER deploying the eval code + `reload-config`, `alt-space` still freezes
and behaves unpredictably.** So `eval` batching did NOT solve the jank as the deep
research predicted. Evidence: `~/Documents/freezes_and_unpredictable_behaviour.mov`
(30 s, recorded on the deployed eval build). Frame analysis showed:
- A **floating Finder file-picker panel** present throughout — excluded from tiling
  (awesome-correct), sits on top, tiled windows reflow around it → looks chaotic.
- **`max`/monocle** makes one window near-fullscreen with thin slivers — reads as
  the "terminal maximizes" bug; likely just `v_accordion` doing its job.
- **Narrow vertical columns** as the pre-layout default (AeroSpace native tiling).
- Freezes are temporal (not visible in stills).

### Hypotheses to test next session (START WITH A PROFILER — user's idea)
- eval may NOT actually be collapsing the work: verify a real cycle emits ONE
  `aerospace eval` call at runtime (log `AEROSPACE_LAYOUTS_LOG=info` and count
  `aerospace` process spawns during one `alt-space`). If it's still N spawns, the
  wiring didn't take (or the flatten+probe phase — which is NOT in the eval batch —
  dominates).
- The **dfs-probe (J2)** was never eval-able (needs read-back). It is `2N` focus
  round-trips per apply and is the prime remaining latency/flicker suspect. Measure
  its share. Deep-research option 5 (persistent socket helper over
  `/tmp/bobko.aerospace-$USER.sock`) and **exotic A** (probe-free focus-walk INSIDE
  one eval) target exactly this — reconsider them.
- Confirm `geometry` isn't silently degrading to None (no 50 % master) or, worse,
  throwing per-apply.
- **Add a profiler / timing harness** to the CLI (per-phase timing: list → flatten →
  probe → eval) so the freeze is measured, not guessed. This is the user's proposed
  starting point.

### Design items surfaced by the video (after the jank is measured/fixed)
1. **Per-workspace default layout** (user's #1 ask): AeroSpace has NO native
   per-workspace default. Needs `on-window-detected` / `exec-on-workspace-change`
   callback → `aerospace-layouts apply <ws-default>` + a `ws→layout` config
   (mostly `tile.left`/`tile.right`). This IS the deferred debounced auto-reapply,
   and pairs with the **named-workspace scheme** (parked to its own session).
2. **Drop `max` from the cycle** — the monocle reads as breakage; leave the pure
   `tile` family (user wants "mostly tile left/right").
3. **Auto-reapply after a floating dialog closes** so the layout re-collapses.

### Other parked items
- **Named-workspace scheme** (names instead of 1-9; `workspace <name>` +
  force-assignment + Zen→ws1) — user wants it, its own session.
- **`start-at-login = true`** — flip only once the environment satisfies the user
  on all layouts (Kinesis at home, laptop screen). Currently `false`.
- **Profiler + related ideas** — user has more; fresh session.

### Uncommitted changeset (NOT committed — user commits manually)
All on `master`, accumulated this session:
- `roles/devbox/files/.config/aerospace/layouts/` — full uv project incl. `fair`,
  `demote`, eval executor, `geometry.py` (Design A), trimmed cycle, tests.
- `roles/devbox/files/.config/aerospace/aerospace.toml` — clusters, cycle/engine
  binds, float/unfloat, `config-version = 2`.
- `roles/devbox/tasks/install_configs.yml` — Block 3c (aerospace rsync + uv sync).
- `CLAUDE.md` (project) — Block 3c doc.
- `roles/devbox/defaults/main/packages.yml` — declared `abrosimov/otelbox` tap +
  `otelbox-edge`.
- `Makefile` — `STALE_TAPS` (+`mongodb/brew`, `homebrew/brew-vulns`); `audit-brew`
  fixed for the deprecated `brew-vulns` tap (built-in `brew vulns`).

### Machine follow-ups (operator, not repo)
- `make untap-stale && make audit-taps` (remove `hudochenkov/sshpass`,
  `jakehilborn/jakehilborn` after `brew uninstall sshpass displayplacer`, +
  `homebrew/brew-vulns`) — confirm clean.
- AeroSpace tray icon hidden behind the notch after the upgrade (menu-bar overflow).

---

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
