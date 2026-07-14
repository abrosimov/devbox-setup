# macOS Tooling Deployment — Follow-ups

**Created:** 2026-07-14
**Context:** Companion to `macos_tooling_setup.md`. That doc covers per-tool
*content* (AeroSpace bindings, Sketchybar widgets, Karabiner rules, etc.).
This doc covers *deployment lifecycle* — how configs move between the repo
and the live system, and how macOS privacy gates get granted.

Scaffolding session on 2026-07-14 landed Karabiner + Hammerspoon under
`roles/devbox/files/.config/karabiner/` and `roles/devbox/files/.hammerspoon/`,
registered them in `install_configs.yml` Block 3, and added a `jq-sort`
clean-filter for `karabiner.json` (defined in `roles/devbox/files/.config/git/config.j2`,
attributed via top-level `.gitattributes`). The three items below were
deferred from that session.

## 1. `karabiner-pull` make-target — back-propagation from live

**Problem.** Karabiner's GUI writes to `~/.config/karabiner/karabiner.json` on
every rule edit. The repo is source of truth; on next `make personal`/`make
work` the repo copy overwrites live. So GUI edits are lost unless pulled back
into the repo first.

**Prior art.** `make claude-pull` (`Makefile:claude-pull`) already implements
this pattern for `~/.claude/` root files — see `scripts/claude-pull.sh` (or
inline in the Makefile, whichever it is).

**Design.**
- New target `make karabiner-pull` runs
  `jq --sort-keys . ~/.config/karabiner/karabiner.json > roles/devbox/files/.config/karabiner/karabiner.json`
  and the same for each `assets/complex_modifications/*.json`.
- `make karabiner-diff` shows `git diff` on those files after a hypothetical
  pull, so the user can preview before committing.
- Optional: extend the umbrella `make claude-diff` pattern into `make
  dotfiles-diff` covering *all* managed dirs (see `macos_tooling_setup.md`
  §3.5 "Drift detection"). That subsumes karabiner-diff and would also cover
  Hammerspoon (`~/.hammerspoon/`) once its modules stabilise.

**Not urgent** while rule set is tiny — hand-edit repo directly and let
Karabiner reload. Becomes urgent once complex modifications multiply and
GUI-driven authoring is easier than editing JSON by hand.

## 2. `configure_macos_permissions.yml` — deep-link helper

**Problem.** Karabiner, Hammerspoon, AeroSpace, AltTab, Raycast, JankyBorders
all need TCC permissions (Accessibility / Input Monitoring / Screen
Recording) granted through System Settings. Apple deliberately requires human
approval — no supported programmatic grant without MDM. See
`karabiner_activation.md` for the Karabiner-specific case (System Extension
+ Input Monitoring, requires reboot).

**Design — declarative permission manifest.**

Add `roles/devbox/defaults/main/macos_apps.yml`:

```yaml
devbox_macos_apps:
  - id: com.knollsoft.AeroSpace
    name: AeroSpace
    permissions: [accessibility]
  - id: com.hammerspoon.Hammerspoon
    name: Hammerspoon
    permissions: [accessibility, screen_recording]
  - id: org.pqrs.Karabiner-Elements
    name: Karabiner-Elements
    permissions: [input_monitoring]
    system_extension: pqrs.org.Karabiner-VirtualHIDDevice
  # ... AltTab, Raycast, JankyBorders, BetterDisplay
```

Add `roles/devbox/tasks/darwin/configure_macos_permissions.yml`:

- **Query** current grants — read `~/Library/Application Support/com.apple.TCC/TCC.db`
  via `sqlite3` (works read-only without Full Disk Access on the *user*
  database; the *system* database at `/Library/…` requires FDA on the terminal
  and is out of scope).
- **Diff** against the manifest — list which permissions are missing per app.
- **Print** a checklist with `x-apple.systempreferences:` deep-link URLs
  per pane (`…?Privacy_Accessibility`, `…?Privacy_ListenEvent`,
  `…?Privacy_ScreenCapture`). The user runs `open <url>` from the terminal
  and ticks the box — one round-trip per missing grant.
- **Re-query** to confirm at the end (optional).

**Helper form — split.** Ansible task orchestrates and prints; heavy lifting
lives in `scripts/macos_grant_permissions.sh` (or `.py`) so it can run
outside the playbook too (`make grant-permissions`).

**System Extension (Karabiner DriverKit).** Separate code path — read
`systemextensionsctl list`, and if the Karabiner extension isn't
`activated enabled`, print the sequence from `karabiner_activation.md`. Do
not try to automate — password prompt + reboot are non-negotiable.

**MDM sidenote.** If the work machine ever gets enrolled into an MDM with
PPPCP support, permissions can be granted via configuration profile — no
manual UI. Not applicable to the current personal + work setup (both are
unmanaged), but worth documenting once/if it changes.

## 3. Skeletons for remaining macOS tools

**Deferred** from the 2026-07-14 scaffolding session because empty
scaffolds bring no value — they'd just add `.gitkeep` markers and force
early decisions on `install_configs.yml` wiring. Materialise each in the
same session that writes its first working config.

Anchored plans already exist in `macos_tooling_setup.md`:
- §2.1 AeroSpace → `roles/devbox/files/.aerospace.toml` (single-file, no dir)
- §2.2 Sketchybar → `roles/devbox/files/.config/sketchybar/` (dir + plugins/)
- §2.3 JankyBorders → `roles/devbox/files/.config/borders/bordersrc`
- §2.4 Raycast → `roles/devbox/files/.config/raycast/script-commands/` (dir of shebang scripts)

For each: add repo path, extend `install_configs.yml` Block 3 loop (or
Block 4 for single-file cases like `.aerospace.toml` and `bordersrc`), and
add per-tool config-reload hook to `apply_configs.yml` if needed
(AeroSpace picks up `~/.aerospace.toml` changes on reload; Sketchybar
needs `sketchybar --reload`; Borders is restarted by AeroSpace
`after-startup-command`).

## Suggested ordering

1. **Follow-up 3** — comes for free with any tool-config session; no
   dedicated work.
2. **Follow-up 2** — do once several tools are installed and permission
   friction becomes noticeable during setup of a fresh machine.
3. **Follow-up 1** — only when Karabiner rule set has grown enough that
   GUI-driven authoring beats direct JSON editing.
