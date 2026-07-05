# Keyboard & macOS Diet — Project Index

**Created:** 2026-07-05
**Status:** parked, awaiting standalone session
**Context:** consolidates three intertwined threads that share hardware,
input-source, and per-machine dimensions. Doing them piecemeal creates
conflicts (Karabiner CapsLock remap vs Kinesis firmware CapsLock remap —
one has to yield).

## Related files in this directory

- `karabiner_activation.md` — post-reboot activation checklist (must run
  once before any Karabiner-based rule takes effect).
- `macos_tooling_setup.md` — full Phase 2 plan for the awesome-WM-style
  stack: AeroSpace (§2.1), Sketchybar (§2.2), JankyBorders (§2.3), Raycast
  (§2.4), Hammerspoon (§2.5), Karabiner (§2.6), BetterDisplay (§2.7),
  Lima (§2.8). Kinesis is Phase 3 §3.1.
- `kitty_keybinding_tests.md` — manual test harness for the kitty layer;
  will grow to cover Karabiner regressions once the rule ships.

## Scope

### 1. Cross-layout normalisation (immediate motivation)

- Karabiner complex modification: `ctrl / cmd / alt (+ shift) + cyrillic → latin`
  at the HID layer. Fixes kitty, Claude Code, VS Code, Slack, any app in one
  shot. Also lays the ground for the Alt-shortcut regression tracked in
  [claude-code#18221](https://github.com/anthropics/claude-code/issues/18221).
- Delivery path: versioned JSON in
  `roles/devbox/files/.config/karabiner/assets/complex_modifications/*.json`,
  deployed via `install_configs.yml` Block 3 (copy dir).
- Reference library: [ke-complex-modifications.pqrs.org](https://ke-complex-modifications.pqrs.org/).
- **Interim in place:** kitty scancode remaps for Ctrl+letter and
  Ctrl+Shift+{Z,X,G,H} in
  `roles/devbox/files/.config/kitty/kitty.conf`. Retire once the Karabiner
  rule lands.

### 2. Kinesis Advantage 360 Pro — ZMK keymap

- Kinesis handles remaps in firmware. Karabiner only owns the built-in
  MacBook keyboard (clamshell-open scenario).
- Standalone repo: `kinesis-adv360-config` (or submodule of `devbox-setup`).
- Reference keymap: [cosmicbuffalo/adv360-zmk-config](https://github.com/cosmicbuffalo/adv360-zmk-config).
- Tooling options: Clique web UI (easy, opaque), GitHub fork build
  (reproducible, versioned), Nick Coutsos keymap editor (visual + JSON).
- **User is currently adapting to the split keyboard.** Layer plan open —
  vanilla QWERTY overlay first, evaluate Colemak-DH once base-layer muscle
  memory is stable.

### 3. Awesome-WM-style stack (macOS diet)

- AeroSpace (i3-like tiling), Sketchybar (custom menubar), JankyBorders
  (focus outline), Raycast (rofi-equivalent launcher), Hammerspoon (Lua
  bridge for anything the above cannot do).
- Full plan lives in `macos_tooling_setup.md` §§ 2.1-2.5; that file is
  authoritative for the WM stack, this file only cross-references.
- Also 2.7 BetterDisplay, 2.8 Lima for Linux observability parity.

## Home vs Work profile split

`personal` = `~/Projects` workspace, `work` = `~/Work` workspace (Ansible
profiles already exist — see `profiles/personal.yml`, `profiles/work.yml`).
The keyboard project inherits this split.

| Layer | Home (`personal`) | Work (`work`) | Delivery mechanism |
|-------|-------------------|---------------|--------------------|
| Kinesis firmware keymap | Personal daily-driver keymap | Work keymap — chat/meeting oriented, maybe corp-shortcut overrides | Two firmware profiles side by side (Kinesis supports layer switching) or two separate builds flashed on demand |
| Karabiner (built-in kbd) | Same Cyrillic-fix rule set | Same + potential per-app rules for corp tools (Zoom, Teams) | Shared JSON + `frontmost_application_if` conditions for corp-specific rules |
| AeroSpace | Full 9-workspace layout | 3-4 workspace subset, Slack pinned to workspace 9 | Two `.aerospace.toml` files behind Ansible profile toggle |
| Sketchybar | Full metrics widget bar, calendar integration | Minimal, no personal calendar | Shared plugins, profile-conditional widget list |
| Raycast | Personal script commands | Corp script commands (Jira ops, VPN toggle) | Shared script dir, per-profile symlink overlay |

Kinesis and app-level tools differ by machine. The Karabiner rule for
Cyrillic normalisation is universal — the machine-specific parts are the
per-app overlays layered on top.

## Execution order (when this project starts)

1. **Karabiner activation** (`karabiner_activation.md`) — one-time human
   prerequisite (system extension approval + reboot + Input Monitoring).
2. **Karabiner Cyrillic → Latin rule**, versioned in repo, deployed on both
   profiles.
3. **Verify kitty Cyrillic works via Karabiner alone**, then delete the
   kitty scancode blocks (`Ctrl+letter` + `Ctrl+Shift+{Z,X,G,H}`) from
   `kitty.conf` and update the kitty `README.md`.
4. **AeroSpace baseline** (`macos_tooling_setup.md` §2.1) — dominant WM.
5. **JankyBorders** (§2.3) and **Raycast** (§2.4) — quick visual and
   launcher wins.
6. **Sketchybar** (§2.2) — bigger investment, do once 1-5 are stable.
7. **Hammerspoon** (§2.5) — only if the above leaves gaps.
8. **Kinesis keymap** (§3.1) — parallel track, own repo, own iteration
   rhythm.

## Open decisions

- Kinesis flashing workflow: Clique UI vs GitHub fork build vs Nick Coutsos
  editor?
- Kinesis home vs work: two firmware profiles vs two flashed builds?
- Karabiner: single `karabiner.json` shared across profiles, or one per
  profile? Prefer shared + `device_if` (built-in vs Kinesis) + Ansible-
  templated per-profile block.
- Base layout on Kinesis: stay on QWERTY or migrate to Colemak-DH?
- CapsLock ownership: Karabiner (for built-in only) vs Kinesis firmware (for
  the split). Both need CapsLock → Esc/Hyper; who wins when both keyboards
  are connected?
- Deferred: Esc-clears-Claude-Code-input pain (see `macos_tooling_setup.md`
  §3.6) — not a keyboard-project blocker but lives in the same input
  handling neighbourhood.

## Handoff notes

When this project starts, expect to touch:

- `roles/devbox/files/.config/karabiner/` (new directory)
- `roles/devbox/files/.aerospace.toml` (new file, per-profile)
- `roles/devbox/files/.config/sketchybar/` (new directory)
- `roles/devbox/files/.config/borders/bordersrc` (new file)
- `roles/devbox/files/.config/raycast/script-commands/` (new directory)
- `roles/devbox/tasks/install_configs.yml` — Block 3 (copy dir) extensions
- `roles/devbox/defaults/main/packages.yml` — already has the brew packages
- `profiles/personal.yml` / `profiles/work.yml` — profile-conditional overrides
- `roles/devbox/files/.config/kitty/kitty.conf` — DELETE Ctrl+letter block
  and Ctrl+Shift+{Z,X,G,H} block once Karabiner rule is verified
- `roles/devbox/files/.config/kitty/README.md` — sync with kitty.conf
