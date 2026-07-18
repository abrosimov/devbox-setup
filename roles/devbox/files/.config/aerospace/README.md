# AeroSpace — Tiling WM Keybindings & Behaviour

i3-style tiling window manager. Config: `aerospace.toml` (deployed to
`~/.config/aerospace/aerospace.toml`). Mod key = **Alt (Option)**.

Docs: <https://nikitabobko.github.io/AeroSpace/guide>

## Launch

`start-at-login = false` — launch manually while the config is being dialled in:

```bash
open -a AeroSpace          # grant Accessibility on first run; it restarts itself
pkill AeroSpace            # quit — windows return to their normal (floating) state
```

Nothing is destructive: quitting AeroSpace restores all windows to the visible
area. After editing `aerospace.toml`, reload live with `Alt+Shift+;` then `Esc`
(or `aerospace reload-config`).

## Keybindings

| Key | Action |
|-----|--------|
| `Alt+J / I / L / M` | Focus left / up / right / down |
| `Alt+Shift+J / I / L / M` | Move focused window left / up / right / down |
| `Alt+Ctrl+J / I / L / M` | `join-with` — pull neighbour into a shared container (builds nested columns/rows) |
| `Alt+1..9` | Switch to workspace 1..9 |
| `Alt+Shift+1..9` | Move focused window to workspace 1..9 |
| `Alt+Space` | Toggle layout tiles ⇄ accordion |
| `Alt+Shift+Space` | Toggle floating ⇄ tiling |
| `Alt+F` | Fullscreen (zoom within workspace — **not** macOS native fullscreen) |
| `Alt+Minus` / `Alt+=` | Resize focused window smaller / larger |
| `Alt+0` | Balance all sibling sizes |
| `Alt+Tab` | Switch to previous workspace (back-and-forth) |
| `Alt+Shift+Tab` | Move current workspace to the next monitor |
| `Alt+Shift+;` | Enter **service mode** (see below) |

The focus/move/join clusters use the right-hand **ijlm** keys (`j`=left,
`i`=up, `l`=right, `m`=down). A left-hand alternate cluster can be added later
as extra bindings to the same commands.

### Service mode (`Alt+Shift+;`, exit `Esc`)

| Key | Action |
|-----|--------|
| `Esc` | Reload config, back to main mode |
| `R` | Flatten workspace tree (reset to a flat layout) |
| `F` | Toggle floating/tiling for the workspace |
| `Backspace` | Close all windows but the focused one |

## Workspace → monitor assignment

`ws 1-5 → main`, `ws 6-9 → secondary` (falls back to main when no secondary is
attached). AeroSpace re-applies this on every monitor connect/disconnect, so
workspaces **snap back automatically** when an external display is plugged in —
no manual redistribution.

## Window placement rules

- **Zen browser** (`app.zen-browser.zen`) → always workspace 1
  (`on-window-detected`).

## On "does a single window get maximised?"

No. AeroSpace **tiles**; it never triggers macOS native fullscreen. A *single*
window on a workspace fills the whole screen because tiling gives the only
window the entire area — that is normal, not a maximise. Add a second window
and they split. On first launch AeroSpace pulls all existing windows into the
current workspace's tree; redistribute them with `Alt+Shift+1..9`, tidy with
`Alt+0`, or reset with service-mode `R`.

## Limitation — no persisted layouts

AeroSpace does **not** save window tree/proportions across restart, and
`on-window-detected.run` only allows `layout floating|tiling` and
`move-node-to-workspace`. Precise per-workspace layouts (e.g. browser at 70% +
two stacked terminals) are therefore built at runtime with the `join-with`
(`Alt+Ctrl+*`) and `resize` (`Alt+Minus`/`Alt+=`) bindings. A future Tier-2
`aerospace` CLI script can rebuild a saved layout on demand once the exact
proportions have settled — see
`~/.claude/future_projects/macos_tooling_setup.md` §2.1.
