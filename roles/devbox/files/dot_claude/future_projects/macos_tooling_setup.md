# macOS Tooling Setup — Awesome-WM Stack & Linux-User Ergonomics

**Created:** 2026-05-28
**Context:** User is a 15+ year Linux veteran (Slackware → Ubuntu, loved
awesome-wm), now on macOS in clamshell mode 90% of the time with a Kinesis
Advantage 360 Pro. Wants config-as-code, keyboard-first workflow, and
Linux-style observability.

## Phase 1 — DONE (installation only, no configuration)

| Tool | Brew name | Permissions needed on first launch |
|------|-----------|-------------------------------------|
| AeroSpace | `nikitabobko/tap/aerospace` (cask) | Accessibility |
| Sketchybar | `FelixKratz/formulae/sketchybar` (formula) | none |
| JankyBorders | `FelixKratz/formulae/borders` (formula) | Accessibility |
| AltTab | `alt-tab` (cask) | Accessibility, Screen Recording |
| Raycast | `raycast` (cask) | Accessibility, Full Disk Access (optional) |
| Hammerspoon | `hammerspoon` (cask) | Accessibility, Screen Recording (optional) |
| Karabiner-Elements | `karabiner-elements` (cask) | System Extension (kernel — manual approval on first run) |
| BetterDisplay | `betterdisplay` (cask) | none for free tier |
| Lima | `lima` (formula) | none |

Profile differentiation:
- `personal.yml` adds `docker-desktop` cask
- `work.yml` adds `orbstack` cask
- `orbstack` removed from base `devbox_brew_secondary`

System tweaks codified in `darwin/configure_macos_basics.yml`:
- Touch ID for sudo via `sudo_local`
- `pmset disablesleep 1` (clamshell stays awake)
- `DevToolsSecurity --enable` (no password on debugger attach)

## Phase 2 — TODO (configuration, one file at a time)

Each item below should become a separate session. Order is suggested by
dependency / blast radius.

### 2.1 AeroSpace baseline (`~/.aerospace.toml`)

**Where it helps:** primary window manager — replaces Mission Control + Cmd-Tab
for window arrangement. Provides i3-style workspaces, tree-tiled layouts,
keyboard-only window movement between displays.

**Repo path:** `roles/devbox/files/.aerospace.toml` (deployed via existing copy
loop in `install_configs.yml`).

**Minimal example to start from:**

```toml
# ~/.aerospace.toml
start-at-login = true
default-root-container-layout = "tiles"
default-root-container-orientation = "horizontal"
accordion-padding = 30

# Mod = Alt (Option) — matches i3 muscle memory.
[mode.main.binding]
alt-h = "focus left"
alt-j = "focus down"
alt-k = "focus up"
alt-l = "focus right"
alt-shift-h = "move left"
alt-shift-j = "move down"
alt-shift-k = "move up"
alt-shift-l = "move right"

# Workspaces 1..9.
alt-1 = "workspace 1"
alt-2 = "workspace 2"
# ...
alt-shift-1 = "move-node-to-workspace 1"
alt-shift-2 = "move-node-to-workspace 2"

# Per-display default workspace assignment.
[workspace-to-monitor-force-assignment]
1 = "main"
2 = "main"
9 = "secondary"   # e.g. Slack always on external monitor

# App-specific rules (auto-place on launch).
[[on-window-detected]]
if.app-id = "com.tinyspeck.slackmacgap"
run = ["move-node-to-workspace 9", "layout floating"]

[[on-window-detected]]
if.app-id = "net.kovidgoyal.kitty"
run = ["layout tiles horizontal"]
```

**Open questions for the config session:**
- Mod key — Alt (default), Cmd, or hyper key from Kinesis?
- Workspace-per-display vs shared workspaces?
- Native macOS fullscreen apps — exclude or treat as floating?

### 2.2 Sketchybar (`~/.config/sketchybar/sketchybarrc` + `plugins/`)

**Where it helps:** replaces native macOS menubar with a customisable status
bar — workspace indicator, CPU/RAM, battery, network, clock, calendar event.
Talks to AeroSpace via events (`aerospace list-workspaces` etc.).

**Repo path:** `roles/devbox/files/.config/sketchybar/`

**Recommended reference configs:**
- [mehd-io/dotfiles](https://github.com/mehd-io/dotfiles) — modern AeroSpace + Sketchybar setup
- [Zack Reed walkthrough](https://zackreed.me/posts/aerospace_and_sketchybar_setup_on_macos/) — top gap for notch, external monitor gaps

**Items to decide:**
- Lua-based config (newer, cleaner) vs bash plugins (more examples online)
- Which widgets — CPU only, full system metrics, or minimal?
- Stick with menubar or full-height bar?

### 2.3 JankyBorders (`~/.config/borders/bordersrc`)

**Where it helps:** thin coloured outline around the focused window — without
it tiled windows are visually indistinguishable on identical-looking apps
(two kitty windows side by side).

**Example:**
```bash
# ~/.config/borders/bordersrc
options=(
  active_color=0xff7aa2f7   # tokyo-night blue
  inactive_color=0xff414868
  width=2.0
  style=round
)
borders "${options[@]}"
```

Started by AeroSpace's `after-startup-command` or a launchd agent.

### 2.4 Raycast (script-commands + extensions)

**Where it helps:** rofi-equivalent — launcher with custom scripts, snippets,
window management commands, calculator, clipboard history, calendar.

**Repo path:** `roles/devbox/files/.config/raycast/script-commands/`

Each script is a shebang file with `@raycast.*` metadata in comments. Raycast
points to a directory of scripts in settings; that directory becomes a symlink
to the repo.

**Example script (`open-project.sh`):**

```bash
#!/usr/bin/env bash
# @raycast.schemaVersion 1
# @raycast.title Open Project
# @raycast.mode silent
# @raycast.packageName Devbox
# @raycast.icon 🚀
# @raycast.argument1 { "type": "text", "placeholder": "project name" }

cd ~/Projects/"$1" && open -a Ghostty .
```

**Items to decide:**
- Free tier (no AI) vs Pro ($10/month — AI commands, Pro extensions)
- Migrate from Spotlight by overriding `Cmd-Space`? Yes — Raycast standard
- Custom hotkeys for top-3 daily apps: kitty, browser, Slack

### 2.5 Hammerspoon (`~/.hammerspoon/init.lua`)

**Where it helps:** Lua scripting bridge to macOS APIs — anything that
AeroSpace/Raycast/Sketchybar can't do (USB device events, custom modal
keybindings à la awesome-wm modes, cursor highlighting on display switch,
audio device routing, calendar reminders).

**Repo path:** `roles/devbox/files/.hammerspoon/init.lua`

**Items to decide:**
- Pure utility (no window mgmt — AeroSpace handles that) or also fallback WM?
- Which spoons to enable from canonical list (SpoonInstall, ReloadConfiguration)
- Modal keymaps (alt+space → modal → "k" for kill app, "f" for finder, etc.)

### 2.6 Karabiner-Elements (`~/.config/karabiner/karabiner.json`)

**Where it helps:** ONLY for the built-in MacBook keyboard. Kinesis Advantage
360 Pro is ZMK-based and handles its own remaps. Keep this config minimal —
basically just Caps Lock → Esc/Ctrl for the rare times the lid is open.

Additionally: solves the Cyrillic + Ctrl shortcuts issue in CLI apps like
Claude Code (terminals send characters, not scancodes, so Ctrl+W maps to
Ctrl+ц on RU layout and the CLI never sees a control event).

**Repo path:** `roles/devbox/files/.config/karabiner/karabiner.json`

The JSON is auto-formatted by the GUI which makes diffs noisy. Use Karabiner's
"complex modifications" feature with a separate file in `assets/complex_modifications/`.

**Prerequisite:** Karabiner's DriverKit system extension must be activated
before any keymap config takes effect. See `karabiner_activation.md` for the
one-time post-install procedure.

**Reference rule library:** [ke-complex-modifications.pqrs.org](https://ke-complex-modifications.pqrs.org/)
— search for "Cyrillic to QWERTY shortcuts" or "Keep modifier shortcuts in
Latin layout".

**Related upstream issue:** [anthropics/claude-code#18221](https://github.com/anthropics/claude-code/issues/18221)
— Alt-shortcuts breaking on international layouts; a Karabiner rule covers
both Ctrl- and Alt-prefixed shortcuts in one configuration.

### 2.7 BetterDisplay config

**Where it helps:** HiDPI for non-Apple external displays (replaces the old
`one-key-hidpi` script note). Custom resolutions, brightness sync across
multiple monitors, per-display colour profiles.

**Repo path:** TBD — BetterDisplay stores prefs in
`~/Library/Application Support/BetterDisplay/`. Need to test which file is
safe to track in git (some contain machine-specific display IDs).

### 2.8 Lima — Linux VM with bpftrace

**Where it helps:** brings back `strace -e trace=open`, `perf record`,
`bpftrace` — the Linux observability stack. Stock VM, full kernel control,
fast on Apple Silicon.

**Repo path:** `roles/devbox/files/.lima/templates/bpftrace.yaml`

**Example use cases:**
- `lima nerdctl run --rm alpine wget ...` for quick Linux container without OrbStack/Docker
- `limactl shell bpftrace -e 'tracepoint:syscalls:sys_enter_open { printf("%s %s\n", comm, str(args->filename)); }'`
- Reproduce Linux-only bugs without rebooting

**Items to decide:**
- Single all-purpose VM or per-task templates?
- Auto-start on login or on-demand?
- Mount setup: 9p (default) vs reverse-sshfs vs virtiofs?

## Phase 3 — Open follow-ups (not yet scoped)

### 3.1 Kinesis Advantage 360 Pro ZMK config
- Standalone repo with keymap (cosmicbuffalo/adv360-zmk-config as reference)
- Possibly a git submodule of devbox-setup
- Decision point — Clique web UI vs GitHub fork build vs Nick Coutsos keymap editor

### 3.2 YubiKey for sudo when in clamshell
- User has a YubiKey somewhere — once located, decide between:
  - YubiKey 5C Nano + `pam_yubico.so` (challenge-response)
  - YubiKey Bio for fingerprint-only authorisation
- Update `configure_macos_basics.yml` to add `pam_yubico` line under `pam_tid`

### 3.3 Full macOS defaults pass (separate session)
- 40+ `defaults write` keys: animation kill, keyboard repeat, Finder, Dock, screenshots, smart quotes, etc.
- Module: `community.general.osx_defaults` (idempotent)
- File: `roles/devbox/tasks/darwin/configure_macos_defaults.yml`
- Variables: `roles/devbox/defaults/main/macos_defaults.yml`
- Reference: mathiasbynens/dotfiles `.macos` script

### 3.4 Eslogger / xctrace ergonomics
- Fish functions: `strace-exec` (eslogger), `strace-files`, `perf-cpu` (xctrace record CPU profile)
- Live in `roles/devbox/files/.config/fish/functions/`

### 3.5 Drift detection
- Extend `make claude-diff` pattern to all managed dotfile dirs
- `make diff-all` showing drift across kitty, fish, nvim, aerospace, sketchybar, etc.

### 3.6 Esc clears Claude Code input — user-reported pain
- Reproducible: typing a long message, accidentally pressing Esc, whole
  input vanishes. Discovered 2026-05-29 during kitty keybinding overhaul.
- Not a kitty-level fix — kitty forwards `\x1b` honestly; Claude Code's
  input handler decides what to do with it.
- First action: run `/keybindings` inside Claude Code and check if Esc is
  rebindable to no-op or require-confirmation.
- If not exposed via `/keybindings`: add to upstream issue
  [anthropics/claude-code#18221](https://github.com/anthropics/claude-code/issues/18221).

### 3.7 Automated keybinding tests
- Manual checklist in `kitty_keybinding_tests.md` is the current bar.
- Upgrade path if churn hurts: `cliclick` + `kitty @ ls` harness (kitty
  bindings), `vhs` (TUI regressions in Claude Code / nvim), `pexpect` (fish
  readline behaviour). Local-only, no CI (kitty GUI required).
- Estimated 2-4h for the kitty test harness; not justified yet.

## Suggested ordering for Phase 2

Greatest day-1 impact first; each item is a separate /full-cycle or focused session.

1. **AeroSpace** (2.1) — without this nothing else makes sense
2. **AltTab** — works out of the box, just open the GUI once to remap Cmd-Tab
3. **Raycast** (2.4) — minimum viable: Cmd-Space override + 2-3 script commands
4. **JankyBorders** (2.3) — 10-line config, immediate visual upgrade
5. **Sketchybar** (2.2) — bigger investment, do once 1-4 are stable
6. **Hammerspoon** (2.5) — only when you need something the above can't do
7. **Karabiner** (2.6) — only when working lid-open
8. **Lima** (2.8) — when next observability need arises
9. **BetterDisplay** (2.7) — only if a new external monitor needs HiDPI

## Reference repos (good full configs to crib from)

- [mehd-io/dotfiles](https://github.com/mehd-io/dotfiles) — AeroSpace + Sketchybar + Atuin + LazyVim
- [falleco/dotfiles](https://github.com/falleco/dotfiles) — AeroSpace + Borders + Sketchybar
- [ashfinal/awesome-hammerspoon](https://github.com/ashfinal/awesome-hammerspoon) — Hammerspoon as awesome-wm
- [Zack Reed walkthrough](https://zackreed.me/posts/aerospace_and_sketchybar_setup_on_macos/) — practical AeroSpace tips
