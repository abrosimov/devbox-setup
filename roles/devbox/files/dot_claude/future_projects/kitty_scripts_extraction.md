# Extract kitty scripts to a separate repo/project?

**Purpose:** decide whether the kitty terminal configuration and helper
scripts currently living under `roles/devbox/files/.config/kitty/` should
move out of `devbox-setup` into their own repository (or be folded into an
existing one).

**Status:** open question — not started, just noting the trigger and the
trade-offs while context is fresh.

**Trigger.** Surfaced 2026-06-12 during a repo-wide lint cleanup. The kitty
helper `quit_confirm.py` imports `kittens.tui.handler` and `kittens.tui.loop`,
which are only resolvable inside kitty's embedded interpreter. Static
checkers (pyright, pyrefly) cannot see them; this forced a path-scoped
`reportMissingImports = "none"` override in `[tool.pyright]` and a
`[[tool.pyrefly.sub-config]]` entry pointed at the kitty dir. The override
is correct and minimal, but it is a smell: the kitty subtree obeys a
different type-checking contract from the rest of the repo because it
runs on a different runtime.

## What lives there today

```
roles/devbox/files/.config/kitty/
├── kitty.conf
├── quit_confirm.py        # kittens.tui-based confirmation helper
└── …
```

Deployed by Ansible (`install_configs.yml` block 3 — copy dir).

## Reasons to extract

- **Different runtime.** Kittens run inside the kitty embedded interpreter,
  not the system Python. Type-checker config has to carve out an exception.
- **Different audience.** Useful to other kitty users, regardless of whether
  they use the rest of devbox-setup.
- **Cleaner repo.** Removes a stylistic outlier from a primarily
  Ansible-orchestration project.
- **Independent versioning.** Kitty release cadence has nothing to do with
  the devbox provisioning cadence.

## Reasons to keep in place

- **Single-repo deployment story.** Today `make personal` puts everything
  on disk in one shot. Splitting means a second clone, second submodule, or
  a second `make` invocation.
- **Tight integration with shell env.** `kitty.conf` references env vars
  (`AION_AUTOPOIESEON`, `MNEMOSYNE_PERISTASEOS`) and PATH entries owned by
  this repo's shell defaults.
- **Tiny size.** A separate repo for ~2 files is bureaucratic.

## Possible end states

1. **Status quo + accept the type-checker carve-out.** No further work.
2. **Move to a sibling project** (e.g. `~/Projects/kitty-config`) and pull
   it back in at deploy time via Ansible or `git submodule`. Ansible task
   becomes `git_repo` + `copy`.
3. **Fold into an existing personal-dotfiles repo** if one ever materialises.
   The "obsidian plugins" workspace is the closest analogue today.

## Decision criteria — revisit when

- The kitty subtree grows past ~5 helper scripts (current bar is 1).
- A second person/machine wants the kitty config without the rest of
  devbox-setup.
- The pyright/pyrefly carve-out leaks (e.g. blocks a legitimate type error
  elsewhere).

Until one of those triggers fires, **option 1 is the right answer.**
