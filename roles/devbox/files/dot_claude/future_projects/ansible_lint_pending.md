# ansible-lint pending cleanup

**Status**: open
**Created**: 2026-06-10
**Repo**: `devbox-setup`

## Context

`make lint-ansible` was enabled via `.ansible-lint` + the dev venv (see commit
log for the vault root-cause fix). Twenty-one `var-naming[no-role-prefix]`
violations were resolved by adding the `devbox_` prefix across `register:`,
`set_fact:`, and `defaults/main/*.yml` keys (including the global `upgrade_mode`
knob, which is also renamed in the Makefile's `upgrade-*` targets and in
`profiles/*.yml` if/when needed).

This document tracks the four remaining items that were deliberately deferred.

## Current state — workarounds in place

To keep `make lint` green, the four remaining violations are currently
suppressed via `.ansible-lint`:

- `no-changed-when` (2 occurrences in `darwin/configure_macos_basics.yml`) — in
  `warn_list`, so they show as warnings but do not fail the run.
- `load-failure` (2 missing `linux/install_from_apt_*.yml` files) — the parent
  `roles/devbox/tasks/main_linux.yml` is in `exclude_paths`, because
  `load-failure` is unskippable and the only escape hatch is to exclude the
  file referencing the missing includes.

This file should be closed when both suppressions are removed and `make lint`
remains clean on its own.

## Remaining violations (4)

### 1. `no-changed-when` (2 occurrences)

| File | Line | Task |
|------|-----:|------|
| `roles/devbox/tasks/darwin/configure_macos_basics.yml` | 66 | Disable sleep when lid is closed (clamshell mode stays awake) |
| `roles/devbox/tasks/darwin/configure_macos_basics.yml` | 83 | Enable developer mode (debugger access without password) |

Both invoke `ansible.builtin.command` against macOS system tooling
(`pmset`, `DevToolsSecurity`) that are inherently mutating. ansible-lint asks
us to declare a `changed_when:` expression so it can model idempotency, even
when the command always changes state.

**Recommended fix**: add `changed_when: true` to both tasks (we genuinely do
change state every time, and we accept that re-runs are no-ops at the OS level
but Ansible reports them as changes). Optionally improve by precomputing the
target state via a `command: ... register:` probe and gating on the diff
(this is already done for the Touch ID PAM block at the top of the file —
mirror that pattern if extra precision is wanted).

### 2. `load-failure[filenotfounderror]` (2 occurrences)

| Path that does not exist | Referenced from |
|------|------|
| `linux/install_from_apt_initial.yml` | `roles/devbox/tasks/main_linux.yml:2` |
| `linux/install_from_apt_secondary.yml` | `roles/devbox/tasks/main_linux.yml:14` |

`main_linux.yml` includes Linux task files that were never created. The
operator-flow does not exercise this path (user is on Darwin only), so the
references have been dormant.

**Resolution options**:

- **(a) Implement Linux support**. Create `linux/install_from_apt_initial.yml`
  and `linux/install_from_apt_secondary.yml` mirroring the Darwin equivalents.
  Largest scope; only worthwhile if the user actually starts using Linux.

- **(b) Delete the Linux path**. Remove `roles/devbox/tasks/main_linux.yml`
  entirely and drop the OS dispatch in `roles/devbox/tasks/main.yml`. Cleanest
  if Linux is permanently out of scope. Restores can be done from git history.

- **(c) Add `linux/` to `.ansible-lint exclude_paths`**. Silences the warning
  without resolving the underlying gap. Lowest cost, but the references in
  `main_linux.yml` are still broken at runtime — anyone running the playbook
  on Linux would discover this.

**Recommended**: (b) until Linux support becomes a real requirement; switch to
(a) if/when it does. (c) is a placeholder, not a solution.

## When this doc can be closed

When `make lint-ansible` exits 0 cleanly on a fresh clone with the dev venv,
and there are no `# noqa` comments or `.ansible-lint skip_list` entries papering
over either category above.
