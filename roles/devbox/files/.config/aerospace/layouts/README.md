# aerospace-layouts

awesome-wm-style **dynamic tiling layouts** scripted on top of the
[AeroSpace](https://nikitabobko.github.io/AeroSpace/) CLI.

AeroSpace natively offers only `tiles` / `accordion` / `floating` plus manual tree
building (`join-with` / `split`). It has no dynamic master-stack / fair layouts. This
tool fills that gap: a library of **named, app-agnostic geometry functions** that
re-tile whatever windows currently sit on the focused workspace, cycled by a
keybinding. It is geometry-only reflow -- it never pins apps to slots. Deciding which
window goes where stays the user's job.

## Layout library

All layouts operate on the **focused workspace** and are app-agnostic.

| Name | Behaviour |
|------|-----------|
| `floating` | Float every window (`layout floating` per window). |
| `tile` | Master column on the **left**, vertical stack on the right. |
| `tile.left` | Master column on the **right**, vertical stack on the left. |
| `tile.top` | Master row on the **bottom**, horizontal stack on top. |
| `tile.bottom` | Master row on the **top**, horizontal stack on the bottom. |
| `fair` | Balanced two vertical columns; split `k = (n + 1) // 2`, the odd extra goes **left**. |
| `max` | `v_accordion` -- an *approximation* of awesome's monocle (not "only focused visible"). |
| `columns` | Flatten + even `h_tiles` row + balance. Zero nesting; the robust fallback. |

The master is always the window at tree position 0 (dfs-index 0). The order
`aerospace list-windows --json` returns is **not** dfs/visual order, so the default
`DfsProbeOrdering` resolves each dfs position by probing `focus --dfs-index i` and reading
back which window landed there (focus is captured beforehand and restored afterwards).
`IdentityOrdering` (trust the array order) is kept only for tests / a future CLI that
guarantees dfs array order.

### awesome naming

awesome-wm names its `tile` variants by the side the **stack** occupies, not the
master: `tile` (== `tile.right`) is master-left, `tile.left` mirrors it (master-right),
`tile.bottom` is master-top, `tile.top` is master-bottom. Those names are kept here and
translated to the master side in `planner._TILE_MASTER_SIDE` -- a single dict to edit if
you would rather the name refer to the master side.

## CLI

The console-script `aerospace-layouts` exposes:

| Verb | Action |
|------|--------|
| `cycle [--reverse]` | Advance the focused workspace's stored index mod the cycle list, persist, apply. |
| `apply <name>` | Apply a named layout (records its cycle index if it is in the cycle). |
| `reapply` | Re-apply the current stored layout without advancing. |
| `adjust-master (+ \| -)` | Nudge the master larger / smaller by a fraction of the monitor width (`resize smart ± --window-id <master>`, step ≈ `0.05 × usable width`). |
| `promote` | Swap the focused window into the master slot (dfs-index 0) and re-assert its 50% master proportion. |
| `demote` | Swap the focused window toward the tail (inverse of `promote`); re-assert 50% on the new master. |
| `diagnose [name]` | Non-destructive: print the window list, dfs-index->id map and planned commands. Runs `list-windows` + `flatten` + the dfs probe (restoring focus) but executes NO `join-with`/`resize`. Defaults to `tile`. |

The cycle list is a single constant `planner.CYCLE`:
`tile, tile.left, tile.top, tile.bottom, max`. `columns` (even row) and `fair` (two stacks)
are deliberately **out of the cycle** -- the workflow is master+stack halves, which they do
not serve -- but both stay valid `apply columns` / `apply fair` targets. `floating` is also
**not** in the cycle -- per-window float is a manual toggle (`apply floating`), not a cycle
step; a floating-all step would trap the tiling layouts, which exclude floating windows.

### Mutation batching (AeroSpace >= 0.21.0-Beta)

The flatten + dfs probe read-back phase runs as individual calls (each needs the prior
result), but the arrange/mutation sequence ships as **one** `aerospace eval '<cmd> ; <cmd> ;
...>'` request. `;` runs each sub-command sequentially regardless of exit, so a
`tolerate_nonzero` no-op `layout` never aborts the batch. The single round-trip is
double-buffered by AeroSpace -- no intermediate-state flashes while cycling. A non-zero eval
exit is logged at WARNING and never raised: intermediate layout no-ops legitimately make eval
non-zero, and best-effort is correct for a keybinding.

Environment:

- `AEROSPACE_BIN` -- path to the `aerospace` binary (default: `aerospace` on `PATH`).
- `AEROSPACE_LAYOUTS_LOG` -- log level (default `WARNING`; set `INFO` for the full per-command trace, `DEBUG` for every query).
- `XDG_STATE_HOME` -- overrides the state directory.

### Move ergonomics

Four complementary ways to rearrange windows within a layout:

- **Directional move** (`alt-shift` cluster, native AeroSpace `move`) -- reorders a window
  within its column or moves it across columns.
- **`promote`** -- swap the focused window to `master` (dfs-index 0).
- **`demote`** -- swap the focused window to the tail (last dfs slot); the inverse of
  `promote`.
- **`join-with`** (native AeroSpace) -- manually nest windows into a shared container.

## Diagnosing

`list-windows` requests `%{window-parent-container-layout}`, so a **floating** window
(`layout=floating`) is visible in the output. Floating windows are NOT in the tiling tree,
so `join-with` has no neighbour for them. As in awesome, the tiling layouts (`tile` family,
`max`, `columns`) **exclude floating windows** -- the master is the leftmost *tiled* window
and no `join-with`/`resize`/`layout` targets a floating window. Floating windows are left
untouched (their float state is respected). The `floating` layout still floats everything.
`diagnose` prints the excluded floating windows and the tiled-only ordered set.

```bash
# AeroSpace running, on the target workspace:
aerospace-layouts diagnose            # prints windows (+layout), dfs map, planned commands
AEROSPACE_LAYOUTS_LOG=info aerospace-layouts apply tile   # full per-command trace on stderr
```

State lives at `~/.local/state/aerospace-layouts/state.json` (per-workspace layout
index, atomic write). Missing or corrupt state resets to index 0 -- harmless, because
AeroSpace rebuilds window trees from scratch on restart.

## How the tile master+stack tree is built

`max` and `columns` are **order-agnostic**: they only ever touch `windows[0]` (root
`set_layout` + balance), so they flatten but **skip** the dfs probe. This lets them cycle
without the 2N-subprocess focus-flicker. Only the `tile` family and `fair` are
**order-sensitive** (`planner.ORDER_SENSITIVE_LAYOUTS`) -- they need the true dfs order for
master identity and the join sequence, so they run the probe below. `floating` skips the
flatten entirely.

Applying an order-sensitive reflow layout is a **two-phase** live sequence
(`cli.apply_layout`), because `flatten` linearises the tree and thus changes which window
sits where -- the join order can only be read *after* the flatten:

1. `flatten-workspace-tree --workspace <ws>` executes live.
2. The dfs order is probed on the freshly-flattened tree (`focus --dfs-index`), giving the
   true left-to-right `w0..w_{n-1}`.
3. The pure layout function builds the arrange commands from that order.
4. The arrange commands execute.

The pure `tile_layout` therefore emits only the post-flatten arrange sequence (master-left).
The CLI batches these into one `aerospace eval` call:

```
layout h_tiles --window-id w0               # force root horizontal (tolerates no-op)
join-with left --window-id w2               # collapse the stack into one container,
join-with left --window-id w3               #   anchored on w1, one window at a time
...                                         #   (join count == n-2)
layout v_tiles --window-id w1               # force the stack container vertical
balance-sizes --workspace <ws>
resize width <points> --window-id w0        # Design A: absolute 50% master (see below)
```

**Design A -- absolute master sizing.** The master is pinned to ~50% of the focused
monitor's usable area via a single absolute `resize width <points>` (LEFT/RIGHT master) or
`resize height <points>` (TOP/BOTTOM master), replacing the earlier relative
`resize smart +50` nudges. The extent is `round(0.5 × usable_dimension)` where the usable
width/height comes from AppKit `NSScreen.visibleFrame` (menu bar / Dock excluded).
AeroSpace's `%{monitor-appkit-nsscreen-screens-id}` is a 1-based index into
`NSScreen.screens()`; the CLI reads it via `aerospace list-monitors --focused`. The tile gap
is not subtracted -- the half is an accepted approximation (live-verify per monitor). When
the monitor cannot be read the resize is simply skipped (best-effort). `promote` re-asserts
this half on the pulled window and `demote` on the new master, so a pull lands as a true
half in one gesture.

Key constraints handled:

- **Flatten before ordering.** The dfs probe MUST read the flattened tree, not whatever
  nested/partial tree a previous run left behind, or the join sequence targets the wrong
  window. `apply_layout` enforces the flatten -> probe -> build -> execute order.
- **Join axis / neighbour.** `join-with <dir>` needs a neighbour along the current split
  axis. Post-flatten the stack windows are all siblings, so each is joined *towards the
  anchor* (`left` under a horizontal root, `up` under a vertical root) -- a neighbour always
  exists there, and the anchor `w1` is never joined, so the master `w0` is never pulled in.
- **`layout` non-zero exit.** `layout` can exit non-zero when the requested layout is
  already in effect. Those commands carry `tolerate_nonzero=True`; the executor treats a
  non-zero exit as "already in the desired state" and continues the sequence.
- **master-right / master-bottom** relocate the master past the stack with a single
  `move right` / `move down` after the stack is built.
- **n == 1** emits only the root-orientation force (no joins).

## Validating against the live WM

The unit tests never touch the real WM. One `@pytest.mark.live` smoke test drives it, to
pin the exact `join-with` behaviour on your machine (whether the third stack window
merges into the growing stack container or nests beside it). It is skipped unless
`AEROSPACE_LAYOUTS_LIVE=1`:

```bash
# AeroSpace running, three windows open on the focused workspace:
AEROSPACE_LAYOUTS_LIVE=1 uv run pytest -m live -s
```

Read the docstring in `tests/test_live_smoke.py` -- it lists exactly what to observe and
how each possible mis-tiling maps back to a fix in `layouts/tile.py`.

## Development

```bash
uv sync --all-groups
uv run pytest
uv run ruff check .
uv run pyright
```

Standalone uv project (own `uv.lock` / `.venv`), mirroring
`roles/devbox/files/dot_claude/bin/`. Deployed to `~/.config/aerospace/layouts/` and
materialised with `uv sync --frozen`; AeroSpace invokes the built console-script from the
deployed `.venv`.
