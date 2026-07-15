# Ubuntu: GUI-config deploy is not OS-gated (latent bug)

Status: NOT STARTED — parked 2026-07-16. Ubuntu is not an active target yet;
fix when Linux support becomes real.

## Problem

`main.yml:14-19` gates only the *system* layer by `os_family` (Darwin → brew +
macOS tasks; Linux → apt). But `main_linux.yml` also calls the shared
`install_configs.yml`, and **Block 3 (`install_configs.yml:142-154`) copies
`.config/kitty`, `.config/karabiner`, `.hammerspoon` with no OS gate.** The only
per-OS dotfile is the git config template (`install_configs.yml:237-240`,
`config-{darwin,linux}`). Consequences on Ubuntu:

1. **kitty.conf ships as-is and its keybindings misfire.** The whole
   layout-independence scheme uses macOS native key codes (`map ctrl+0x02`, …).
   Those numbers are platform-specific — the README's own discovery method
   (`kitty --debug-input`) returns different codes on Linux (X11/evdev), so the
   macOS codes point at different physical keys. Plus `cmd+*` (no Cmd on Linux),
   `macos_*` options, and the `quit_confirm.py` / Cmd+Q kitten are macOS-only.
2. **karabiner + hammerspoon are macOS-only apps** — on Ubuntu the deployed
   `~/.config/karabiner` and `~/.hammerspoon` are dead files (harmless clutter).
   The Cyrillic-Ctrl scheme (native scancodes + Karabiner) has no Linux analog;
   on Linux this is an XKB-level concern.

## What is already clean

- apt vs brew system layer is OS-gated (`main.yml:14-19`).
- macOS-only tasks (defaults, pmset, DevToolsSecurity, login items, ssh-keychain
  via `security(1)`, Night Shift) live in `main_darwin.yml` and never run on
  Linux.

## To do when Linux support is real

- Gate karabiner/hammerspoon deploy to Darwin (add `when: os_family == 'Darwin'`
  to those loop items, or split the loop).
- Per-OS kitty config, mirroring the git `config-{darwin,linux}` pattern — a
  Linux kitty.conf with X11/evdev key codes (or char-based bindings) and
  `super`/no-Cmd shortcuts.
- Decide the Linux-native Cyrillic-Ctrl approach (XKB options), separate from the
  macOS native-scancode workaround.

## Refs

- `roles/devbox/tasks/install_configs.yml:142-154` (ungated Block 3)
- `roles/devbox/tasks/install_configs.yml:237-240` (the one OS-gated dotfile)
- `roles/devbox/tasks/main.yml:14-19` (system-layer OS dispatch)
- `roles/devbox/files/.config/kitty/README.md` (native-scancode scheme, macOS-only)
