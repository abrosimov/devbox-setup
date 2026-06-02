# Kitty Terminal — Keybindings & Behaviour

All custom shortcuts bind on **macOS native virtual key codes** (`0x##`) rather
than on character literals. This makes every binding **layout-independent**:
they work identically on English, Russian, or any other input source. Without
this, Cyrillic-active `Cmd+T` would not match `cmd+t` because the OS produces
`е` not `t`.

Where a binding is referenced by character below (e.g. `Cmd+C`), it is the
**physical** key on the US-QWERTY position. On Russian, that's `С` on physical
C, `В` on physical D, etc — same physical key.

After editing `kitty.conf`, run through
[`kitty_keybinding_tests.md`](../../../.claude/future_projects/kitty_keybinding_tests.md)
to verify nothing regressed.

## Tabs

| Key | Action |
|-----|--------|
| `Cmd+T` | New tab at `$HOME` |
| `Cmd+Shift+T` | New tab at current `cwd` |
| `Cmd+1` … `Cmd+9` | Jump to tab N |
| `Cmd+W` | **Disabled** (no-op). Replaces kitty's default tab-close to prevent browser-muscle-memory accidents |

## Splits

| Key | Action |
|-----|--------|
| `Cmd+D` | Vertical split (side by side) |
| `Cmd+Shift+D` | Horizontal split (top/bottom) — overrides kitty's macOS default that bound this to `close_window` |
| `Cmd+Opt+←/→/↑/↓` | Move focus between splits |
| `Cmd+Shift+Enter` | Zoom active split fullscreen (toggle layout stack); press again to revert |

## Clipboard

| Key | Action |
|-----|--------|
| `Cmd+C` | Copy selection to clipboard |
| `Cmd+V` | Paste from clipboard |
| `Cmd+X` | Cut selection |

Auto-copy on selection is enabled (`copy_on_select clipboard`).

## Readline / Ctrl+letter (cyrillic-fixed)

These exist because **terminals translate `Ctrl+ASCII-letter` to a single
control byte** (Ctrl+A → `\x01`, Ctrl+W → `\x17`, etc), but macOS only
performs that translation when the active input source produces a Latin
letter. On Cyrillic, `Ctrl+W` becomes `Ctrl+ц`, has no control-byte
equivalent, and Claude Code / fish / vim never see the readline command.

Each binding below intercepts at the **physical key** level and emits the
correct control byte regardless of active input source. Behaviour on EN
layout is unchanged.

| Key | Sends | What it does |
|-----|-------|--------------|
| `Ctrl+A` | `\x01` | Move cursor to start of line |
| `Ctrl+B` | `\x02` | Move cursor back one character |
| `Ctrl+C` | `\x03` | SIGINT / interrupt foreground process |
| `Ctrl+D` | `\x04` | EOF (closes shell on empty line); delete-forward otherwise |
| `Ctrl+E` | `\x05` | Move cursor to end of line |
| `Ctrl+F` | `\x06` | Move cursor forward one character |
| `Ctrl+G` | `\x07` | Bell / cancel partial input |
| `Ctrl+H` | `\x08` | Backspace |
| `Ctrl+K` | `\x0b` | Kill text from cursor to end of line |
| `Ctrl+L` | `\x0c` | Clear screen |
| `Ctrl+N` | `\x0e` | Next history entry |
| `Ctrl+P` | `\x10` | Previous history entry |
| `Ctrl+R` | `\x12` | Reverse history search |
| `Ctrl+T` | `\x14` | Transpose two characters around cursor |
| `Ctrl+U` | `\x15` | Kill text from start of line to cursor |
| `Ctrl+W` | `\x17` | Kill word backwards |
| `Ctrl+Y` | `\x19` | Yank — restore last killed text |
| `Ctrl+Z` | `\x1a` | SIGTSTP — suspend foreground process (`fg` to resume) |
| `Ctrl+/` | `\x1f` | Readline undo (revert last edit) |

Intentionally not remapped:
- `Ctrl+I` = Tab (do not break completion)
- `Ctrl+J` / `Ctrl+M` = Enter variants
- `Ctrl+S` / `Ctrl+Q` = XOFF / XON terminal flow control (can hang shells)
- `Ctrl+O` / `Ctrl+V` / `Ctrl+X` = mode-specific readline behaviour

## Hints (select text patterns from terminal output)

| Key | Action |
|-----|--------|
| `Ctrl+Shift+E` | URL hints — open in browser |
| `Cmd+Shift+P` | File-path hints — paste into command line |
| `Cmd+Shift+G` | `file:line` hints — open in editor at that line |
| `Cmd+Shift+H` | Git SHA / hash hints — copy to clipboard |
| `Cmd+Shift+O` | Fuzzy file picker — paste path |

## Scrollback & shell integration

Built into kitty's shell-integration layer, not custom-bound:

| Key | Action |
|-----|--------|
| `Ctrl+Shift+H` | Full scrollback in `bat` pager |
| `Ctrl+Shift+G` | Last command's output in pager |
| `Ctrl+Shift+Z` | Jump to previous shell prompt |
| `Ctrl+Shift+X` | Jump to next shell prompt |

`shell_integration` is set to `no-cursor` — all features enabled except
cursor-shape reset, so vim/nvim manage their own cursor.

## Font size

| Key | Action |
|-----|--------|
| `Cmd+=` | Larger |
| `Cmd+-` | Smaller |
| `Cmd+0` | Reset |

## Close & quit policy

The terminal is treated as **always-on**. Two principles:

1. **`Cmd+W` is disabled.** Browser muscle memory cannot kill a tab with a
   running process.
2. **`Cmd+Q` runs a custom kitten** (`quit_confirm.py`) which inspects the
   focused OS window. If every tab is just an idle shell (`fish`, `bash`,
   `zsh`, `sh`, `dash`, `ksh`), the window closes silently. If any tab has a
   non-shell foreground process (claude, vim, htop, …), a confirmation
   prompt lists the busy tabs and asks `[y/N]`.

Scope of `Cmd+Q` is **the current OS window only** — other kitty OS windows
are untouched.

As a defence-in-depth, `confirm_os_window_close -1` is set, which makes
kitty's built-in close paths (window-manager close button, remote-control
`close-window`) also confirm when active processes are present.

## Session save / restore

R1 — minimal layout snapshot, no per-process persistence:

| Command | Effect |
|---------|--------|
| `kitty-save-session` (abbr `kss`) | Snapshot the focused OS window's tabs + per-tab `cwd` to `~/.config/kitty/last-session.conf` |
| (automatic on next launch) | `startup_session ~/.config/kitty/last-session.conf` restores the tabs at their saved `cwd`. Commands are **not** re-launched |

Run `kss` before a planned reboot. To upgrade to full per-process restore
(tmux/zellij + resurrect), see `macos_tooling_setup.md` Phase 3.

## Layout-independent scancode reference

Custom shortcuts use macOS virtual key codes for physical key mapping. To
discover a code for a key, run `kitty --debug-input` and press the key.

| Key | Code | Key | Code | Key | Code |
|-----|------|-----|------|-----|------|
| A   | 0x00 | J   | 0x26 | S   | 0x01 |
| B   | 0x0B | K   | 0x28 | T   | 0x11 |
| C   | 0x08 | L   | 0x25 | U   | 0x20 |
| D   | 0x02 | M   | 0x2E | V   | 0x09 |
| E   | 0x0E | N   | 0x2D | W   | 0x0D |
| F   | 0x03 | O   | 0x1F | X   | 0x07 |
| G   | 0x05 | P   | 0x23 | Y   | 0x10 |
| H   | 0x04 | Q   | 0x0C | Z   | 0x06 |
| I   | 0x22 | R   | 0x0F | Enter | 0x24 |
| /   | 0x2C | |   | |     | |
