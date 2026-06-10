# Karabiner-Elements — Post-Reboot Activation Checklist

**Why this file exists:** brew installs the .app bundle but does NOT register
the DriverKit system extension. Activation is a one-time multi-step process
involving a reboot. Run through it once after the first `make personal` that
installs `karabiner-elements`.

## Quick state check (before doing anything)

```bash
brew list --cask | grep karabiner          # expect: karabiner-elements
ls -ld /Applications/Karabiner-Elements.app # expect: present, root:wheel
pgrep -lf karabiner_grabber                 # if running → already activated
systemextensionsctl list | grep karabiner   # if "activated enabled" → done
```

If both `pgrep` and `systemextensionsctl` show Karabiner active — nothing to do.
Skip to "Configure the keymap" below.

## Activation sequence

1. `open -a Karabiner-Elements`
2. macOS shows "System Extension Blocked" dialog → **Open System Settings**
   - If the dialog was dismissed: System Settings → Privacy & Security → scroll
     to **Login Items & Extensions** → **Driver Extensions**
3. Toggle the `pqrs.org / Karabiner-VirtualHIDDevice` switch ON
4. Authenticate with **password** (Touch ID is not accepted for driver extensions)
5. macOS asks to **reboot** → reboot now
6. After reboot, launch Karabiner-Elements again
7. It now requests **Input Monitoring** — approve in System Settings →
   Privacy & Security → Input Monitoring (toggle Karabiner ON)

## Post-activation verification

```bash
pgrep -lf karabiner_grabber                 # one or more processes running
systemextensionsctl list | grep karabiner   # "activated enabled"
```

If either is missing, the activation didn't take — start again from step 1.

## Configure the keymap (after activation works)

Next step lives in the `macos_tooling_setup.md` plan, section 2.6. Two things
to set up:

1. **Caps Lock → Esc/Ctrl** (for the rare times the laptop lid is open and the
   Kinesis isn't connected)
2. **Cyrillic + Ctrl/Alt → Latin layout** complex modification (so Ctrl+W works
   in Claude Code, vim, tmux regardless of active input source)

Both live in `~/.config/karabiner/karabiner.json` (or a complex modification
JSON under `~/.config/karabiner/assets/complex_modifications/`). The repo will
deploy these as dotfiles once the JSON is dialled in.

## Why we can't automate steps 1-7

System Extension approval, password authentication, and Input Monitoring grant
all live behind macOS Privacy & Security UI gates that have no programmable
equivalent. Apple deliberately requires a human to click them. The best we can
do is document the sequence.
