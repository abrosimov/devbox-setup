# Kitty Terminal — Keybindings & Behaviour

All custom shortcuts bind on **macOS native virtual key codes** (`0x##`) rather
than on character literals. This makes every binding **layout-independent**:
they work identically on English, Russian, or any other input source. Without
this, Cyrillic-active `Cmd+T` would not match `cmd+t` because the OS produces
`е` not `t`.

The clipboard keys and the macOS window basics are
the exception: they are mapped by character with
`--allow-fallback=shifted,ascii`, which falls back to the physical key on a
non-Latin layout and so is layout-independent too. Those actions also appear
in kitty's macOS menu bar, and kitty gives the menu item the map's key as a
character: a native code such as `0x32` becomes the character `2`, so
`cmd+0x32` would put `Cmd+2` on "Cycle Through OS Windows" and AppKit would
take `Cmd+2` away from the tab switch.

Where a binding is referenced by character below (e.g. `Cmd+C`), it is the
**physical** key on the US-QWERTY position. On Russian, that's `С` on physical
C, `В` on physical D, etc — same physical key.

`clear_all_shortcuts yes` drops every kitty default shortcut: only the keys
listed here exist. The intended feel is a Linux terminal — Cmd only for the
clipboard and the tab/split basics — so none of kitty's macOS defaults
(Cmd+Enter new window, Cmd+Opt+, debug screen, Cmd+K clear, …) are kept.
Clear the screen with `Ctrl+L`.

After editing `kitty.conf`, run through
[`kitty_keybinding_tests.md`](../../../.claude/future_projects/kitty_keybinding_tests.md)
to verify nothing regressed.

## Tabs

| Key | Action |
|-----|--------|
| `Cmd+T` | New tab at `$HOME` |
| `Cmd+Shift+T` | New tab at current `cwd` |
| `Cmd+1` … `Cmd+9` | Jump to tab N |
| `Ctrl+Tab` / `Ctrl+Shift+Tab` | Next / previous tab |
| `Ctrl+Shift+→` / `Ctrl+Shift+←` | Next / previous tab |
| `Ctrl+Shift+.` / `Ctrl+Shift+,` | Move the tab right / left |
| `Cmd+Shift+I` | Rename the tab |
| `Cmd+W` | **Disabled** (no-op) to prevent browser-muscle-memory accidents |

## Splits

| Key | Action |
|-----|--------|
| `Cmd+S` | Vertical split (side by side) |
| `Cmd+Shift+S` | Horizontal split (top/bottom) |
| `Ctrl+Shift+R` | Resize the active split |
| `Cmd+Opt+←/→/↑/↓` | Move focus between splits |
| `Cmd+Shift+Enter` | Zoom active split fullscreen (toggle layout stack); press again to revert |

## Clipboard

| Key | Action |
|-----|--------|
| `Cmd+C` | Copy kitty's selection to clipboard; with none, pass the key to the application (Claude Code copies its own selection) |
| `Cmd+V` | Paste from clipboard |
| `Cmd+X` | Cut selection |
| `Ctrl+Shift+C` / `Ctrl+Shift+V` | Copy / paste (Linux terminal habit) |

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
| `Ctrl+Shift+E` / `Ctrl+Shift+U` | URL hints (URLs written out in the text) — open in browser |
| `Ctrl+Shift+L` | Hyperlink hints (OSC 8 links such as Claude Code's `#113`) — open |
| `Cmd+Shift+P` | File-path hints — paste into command line |
| `Cmd+Shift+G` | `file:line` hints — open in editor at that line |
| `Cmd+Shift+H` | Git SHA / hash hints — copy to clipboard |
| `Cmd+Shift+O` | Fuzzy file picker — paste path |

## Scrollback & shell integration

**Cyrillic-fixed via scancode remaps** — same pattern as `Ctrl+letter` above.
Kitty's shell-integration defaults match by character and break on non-Latin
input sources; the maps in `kitty.conf` under "Keybindings — Scrollback /
prompts" restore them at the physical-key layer.

| Key | Action |
|-----|--------|
| `Ctrl+Shift+H` | Full scrollback in `bat` with its built-in pager |
| `Ctrl+Shift+G` | Last command's output in a writable Neovim buffer (`:w path` to save) |
| `Ctrl+Shift+Z` | Jump to previous shell prompt |
| `Ctrl+Shift+X` | Jump to next shell prompt |
| `Ctrl+Shift+F` | Search the scrollback |
| `Shift+PgUp` / `Shift+PgDn` | Scroll a page |
| `Cmd+Home` / `Cmd+End` | Top / bottom of the scrollback |
| `Cmd+↑` / `Cmd+↓` | Scroll a line |
| `Cmd+PgUp` / `Cmd+PgDn` | Scroll a page |
| `Cmd+L` | Erase the last command's output |
| `Cmd+Opt+K` | Clear the scrollback |
| `Ctrl+Cmd+L` | Clear the screen up to the cursor, moving it into the scrollback |
| `Ctrl+Shift+↑` / `Ctrl+Shift+↓` | Scroll a line |

`shell_integration` is set to `no-cursor` — all features enabled except
cursor-shape reset, so vim/nvim manage their own cursor.

> These remaps are **kept permanently** (decision 2026-07-19): kitty is a
> cross-OS terminal, so the scancode blocks help on Linux too. A Karabiner rule
> will additionally cover the wider Cyrillic + Ctrl/Alt problem for non-kitty
> apps (Claude Code, VS Code, etc.) — it is additive, not a replacement, so
> this block stays. See `~/.claude/future_projects/keyboard_project.md`.

## Font size

| Key | Action |
|-----|--------|
| `Cmd+=` | Larger |
| `Cmd+-` | Smaller |
| `Cmd+0` | Reset |

## macOS window basics

kitty's own macOS defaults, restored by character (with the ASCII fallback)
after `clear_all_shortcuts`, because they also sit in the macOS menu bar.

| Key | Action |
|-----|--------|
| `Cmd+H` / `Cmd+Opt+H` | Hide kitty / hide the other apps |
| `Cmd+M` | Minimise the window |
| `Cmd+N` | New kitty window |
| `` Cmd+` `` / `` Cmd+Shift+` `` | Cycle through kitty windows |
| `Ctrl+Cmd+F` | Toggle fullscreen |
| `Ctrl+Cmd+,` | Reload `kitty.conf` |
| `Ctrl+Cmd+Space` | Unicode character input |

## Close & quit policy

The terminal is treated as **always-on**. Two principles:

1. **`Cmd+W` is disabled.** Browser muscle memory cannot kill a tab with a
   running process.
2. **`Cmd+Q` runs a custom kitten** (`quit_confirm.py`) which inspects the
   focused OS window. If every tab is just an idle shell (`fish`, `bash`,
   `zsh`, `sh`, `dash`, `ksh`), the window closes silently. If any tab has a
   non-shell foreground process (claude, vim, htop, …), a confirmation
   prompt lists the busy tabs and asks `[y/N]`. `y` closes; any other key,
   `Esc` or `Ctrl+C` cancels. Left unanswered, the prompt counts down from
   5 minutes and then closes the window as if confirmed (snapshot included),
   so an unattended quit is never blocked.

Scope of `Cmd+Q` is **the current OS window only** — other kitty OS windows
are untouched.

`Cmd+,` (kitty's macOS default `edit_config_file`) is also disabled — it opens
an editor in a new OS window, and the config is owned by this repo, so editing
the deployed copy is a dead end.

kitty's own close confirmation is switched off (`confirm_os_window_close 0`).
Its prompt has no timeout, so when macOS asks kitty to quit (system update,
restart, logout) it waited for an answer and blocked the update. The red close
button, Dock → Quit, system quit and remote-control `close-window` therefore
close without asking, and without taking a session snapshot; only `Cmd+Q`
confirms.

## Session save / restore

The focused OS window is snapshotted to `~/.config/kitty/last-session.conf`
by `kitty_session.py`, which runs under kitty's own interpreter:

| Trigger | Effect |
|---------|--------|
| `kitty-save-session` (abbr `kss`) | Snapshot now, e.g. before a planned reboot |
| `Cmd+Q` | Snapshot just before the window closes (after confirmation, if one was asked). A failed snapshot never stops the window closing |
| (automatic on next launch) | `startup_session ~/.config/kitty/last-session.conf` restores the snapshot |

What a snapshot keeps:

- every tab, with its title and layout, and every split in it;
- each split's working directory, taken from its foreground process, so a split
  running a program comes back where that program was, not where its shell started;
- Claude Code conversations: a split that was running Claude Code reopens fish in
  the conversation's directory and runs `claude --resume <session id>` there;
  quitting Claude leaves you in that fish.

Other programs (vim, htop, …) are **not** relaunched: their split reopens as fish
in the program's directory. Split sizes, OS window geometry and other OS windows
are not saved. For full per-process restore (tmux/zellij + resurrect), see
`macos_tooling_setup.md` Phase 3.

Claude Code is recognised through the record it keeps for each running
interactive session in `~/.claude/sessions/<pid>.json`. That file is Claude
Code's undocumented internal state: if it is missing or its shape changes, the
split is restored as a plain fish in its directory.

A snapshot is written atomically, and a failed `kitty @ ls` (for instance without
`allow_remote_control yes`) leaves the previous snapshot in place.

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
| /   | 0x2C | ,   | 0x2B | .   | 0x2F |
| [   | 0x21 | ]   | 0x1E | `   | 0x32 |
| Space | 0x31 | |   | |     | |
