# Kitty Keybinding Test Checklist

**Purpose:** Manual smoke test for every keybinding in `kitty.conf` after any
change. Walk through this once per config edit. If something regresses, the
diff is small enough to bisect.

**Scope:** kitty.conf only. Claude Code's own `/keybindings` is separate.

**Prerequisite:** start a fresh kitty window so background state doesn't
pollute observations.

---

## A. Layout-independent test (run on both EN and RU input source)

For each binding below, switch input source to Russian, repeat. Both must
behave identically. That is the whole point of the scancode-based mapping.

## B. Readline / Ctrl+letter (the cyrillic fix)

Open a fresh `fish` prompt for each test.

| Test | Steps | Expected |
|---|---|---|
| Ctrl+A | Type "hello world", `Ctrl+A` | Cursor jumps to start |
| Ctrl+E | From start, `Ctrl+E` | Cursor jumps to end |
| Ctrl+W | Type "hello world", `Ctrl+W` | Removes "world" |
| Ctrl+U | Type text, `Ctrl+U` | Whole line cleared |
| Ctrl+Y | After Ctrl+U or Ctrl+W, `Ctrl+Y` | Killed text restored |
| Ctrl+K | Cursor mid-line, `Ctrl+K` | Right side of cursor cleared |
| Ctrl+R | `Ctrl+R`, type partial of previous command | Reverse history search activates |
| Ctrl+L | `Ctrl+L` | Screen clears, prompt at top |
| Ctrl+P / Ctrl+N | Cycle history | Up/down through history |
| Ctrl+B / Ctrl+F | Move cursor char-by-char | Same as ← / → |
| Ctrl+T | Type "ab", cursor between, `Ctrl+T` | Becomes "ba" |
| Ctrl+H | Identical to Backspace | Char before cursor removed |
| Ctrl+D | On empty line, `Ctrl+D` | Shell exits (fish closes). With text: deletes char under cursor |
| Ctrl+G | During incomplete command/search, `Ctrl+G` | Cancel without execution |
| Ctrl+Z | Run `htop`, `Ctrl+Z` | htop suspends, returns to shell. `fg` resumes |
| Ctrl+/ | Type, kill with Ctrl+W, then `Ctrl+/` | Undo: text restored |

**Same set in Claude Code:** open Claude Code in a separate tab, run the same
tests. Specifically — `Ctrl+W` (kill word), `Ctrl+A` (line start), `Ctrl+E`
(line end), `Ctrl+/` (undo) — these are the user-reported pain points.

## C. Cmd+letter (clipboard + tabs + splits)

| Test | Steps | Expected |
|---|---|---|
| Cmd+C | Select text, Cmd+C | Copies to clipboard. Verify via `pbpaste` in another tab |
| Cmd+V | Cmd+V in prompt | Pastes clipboard |
| Cmd+X | Select text in input, Cmd+X | (Where applicable — terminal usually no-ops cut) |
| Cmd+T | `Cmd+T` | New tab opens at HOME |
| Cmd+Shift+T | `Cmd+Shift+T` | New tab opens at current cwd |
| Cmd+1..9 | `Cmd+5` | Switches to tab 5 if exists |
| Cmd+D | `Cmd+D` | Vertical split — current window splits left/right |
| Cmd+Shift+D | `Cmd+Shift+D` | Horizontal split — top/bottom |
| Cmd+Opt+arrows | `Cmd+Opt+←/→/↑/↓` | Focus moves between splits in that direction |
| Cmd+Shift+Enter | In a tab with 2+ splits, `Cmd+Shift+Enter` | Active split goes fullscreen ("zoom"). Press again to revert |
| Cmd+= / Cmd+- / Cmd+0 | Font size | Larger / smaller / reset |
| Cmd+W | `Cmd+W` while typing | **NOTHING** — disabled by `no_op` |
| Cmd+Q | `Cmd+Q` with no busy tabs | Closes OS window. With busy tabs — custom prompt with list of active processes |

## D. Hints kittens (Cmd+Shift+letter)

These rely on `kitten hints` and overlay clickable labels on terminal output.

### Ctrl+Shift+E — URL hints

1. Run: `echo "Visit https://github.com/anthropics and https://kitty.app"`
2. Press `Ctrl+Shift+E`
3. **Expected:** each URL gets a 1-2 letter label overlay
4. Press the label of a URL → opens in default browser
5. **If regex error appears:** record the exact text — newer kitty may require explicit `--regex` arg

### Cmd+Shift+P — paste path

1. Run: `ls -la /etc/hosts /etc/shells`
2. Press `Cmd+Shift+P`
3. **Expected:** labels on `/etc/hosts` and `/etc/shells`
4. Press label → path is pasted into current command line

### Cmd+Shift+G — jump to file:line

1. In a Go project (or any with file:line errors), run something that errors:
   ```fish
   echo "main.go:42: error: example"
   ```
2. Press `Cmd+Shift+G`
3. **Expected:** label on `main.go:42`
4. Press label → opens in editor at line 42

### Cmd+Shift+H — copy git hash

1. In a git repo: `git log --oneline -5`
2. Press `Cmd+Shift+H`
3. **Expected:** label on each SHA
4. Press label → SHA copied to clipboard. Verify with `pbpaste`

### Cmd+Shift+O — file picker

1. `cd ~/Projects/<any>`
2. Press `Cmd+Shift+O`
3. **Expected:** fuzzy file picker TUI opens
4. Select a file → path pasted into command line

## E. Cmd+Q custom kitten (after implementation)

| Test | Steps | Expected |
|---|---|---|
| Idle close | No tab has running process, `Cmd+Q` | OS window closes immediately (no prompt) |
| Busy single | One tab running `htop`, `Cmd+Q` | Prompt lists tab N: htop. y → close, n/Esc → cancel |
| Busy multiple | Tab 2: claude, Tab 5: vim main.go, `Cmd+Q` | Prompt lists both with their commands |
| Scope check | Two OS windows open, both with busy tabs | Only **current** OS window is affected. Other window untouched |

## F. Session restore (after R1 implementation)

| Test | Steps | Expected |
|---|---|---|
| Save | 3 tabs at different pwd, run `kitty-save-session` | `~/.config/kitty/last-session.conf` updated, contains 3 launch entries |
| Restore | Quit kitty (`kitty @ quit`), launch kitty again | Tabs reappear at their pwd. Commands not re-launched (best-effort R1) |

---

## Open follow-ups for automated testing

Manual checklist is fine for now. If regressions become frequent, build:

1. **`cliclick` + `kitty @ ls` harness** — sends real keystrokes via macOS
   Accessibility, queries kitty state via remote-control. Local-only
   (no CI), but reliable. Estimated effort: 2-4 hours for ~15 tests.

2. **`vhs` for TUI regression of Claude Code / nvim** — Charm's tool records
   declarative `.tape` files and produces GIF/screenshot diffs. Cannot test
   kitty-level bindings (vhs runs its own pty), but useful for "does
   Ctrl+A move cursor to line start in Claude Code" type tests.

3. **`pexpect` for shell-level keybinding behaviour** — tests that fish
   readline binds (Ctrl+W kills word) survive shell config edits.

Decision deferred — see `macos_tooling_setup.md` Phase 3.

## Esc clearing input in Claude Code

Separate concern, not solvable in kitty (kitty just forwards `\x1b`).
Follow-ups:

1. Run `/keybindings` inside Claude Code and check if Esc can be rebound to
   "no-op" or "require confirmation"
2. If `/keybindings` doesn't cover Esc handling — file feature request /
   add to Anthropic GitHub issue [#18221](https://github.com/anthropics/claude-code/issues/18221)

The cyrillic Ctrl+W fix (this file) does NOT solve the Esc-clears-input
problem. Those are unrelated.
