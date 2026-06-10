# Workbench decomposition — work in progress (paused 2026-06-10)

## Goal

Split the growing `devbox-setup` monolith into independently-versioned pieces, and formalise the user's workspace as a first-class contract. The monolith mixes three change cadences (machine bootstrap, dotfiles/shell tooling, Claude Code config); the user is worried it will become a SPOF.

Target shape:

| Repository | Contents | Audience |
|---|---|---|
| `fish-weft` | `proj`, `wt`, `k`, `kpf`, `kms`, `klocal-use`, completions, tide pwd item | Public |
| `workbench-spec` *(optional)* | Document the workspace-root contract; possibly a shell-agnostic helper | Public |
| `devbox-setup` *(slimmed)* | Ansible only: bootstrap, packages, macOS prefs. Installs `fish-weft` via fisher. | Personal |
| `claude-config` | Everything under `roles/devbox/files/dot_claude/`. Own evals, validators, CI. | Public (eventually) |

## Workspace contract

Implicit directory layout the user already follows. To make it explicit:

```
$AION_AUTOPOIESEON/
├── <project>/base/        # the git repository
├── <project>/<branch>/    # worktree, sibling of base/
├── .kubeconfigs/          # per-cluster KUBECONFIG files
├── .local-tools/          # generated wrappers/shims
└── .wtfiles               # default seed manifest for new worktrees
```

**Naming note:** the workspace-root env var is `AION_AUTOPOIESEON` (Greek mythology — Aion = eternity/lifetime, "autopoieseon" = self-making). This is already in place in `devbox-setup` shell templates, and the user has applied it to the fish-weft helpers via post-extraction edits. `PROJECTS_DIR` survives as a transitional alias. The companion file `problem_statement.md` in this repo was written before this naming was settled and uses `WORKBENCH_ROOT` — supersede that name when reading.

## Naming for the plugin

Chosen name: **`weft`**.

Rationale (for both today's fisher plugin and a possible future Go binary):
- 4 chars, easy to type, easy to brand.
- No active CLI conflict in dev tooling.
- Ties into the user's existing `warp-and-weft` project — weaving as a metaphor for worktrees (threads being interlaced).
- Considered alternatives that were eliminated:
  - `loom` — soft conflict with OpenJDK Project Loom (concurrency).
  - `smithy` — hard conflict with AWS Smithy.
  - `forge` — overcrowded namespace.
  - `fleet` — JetBrains Fleet.
  - `wharf` — clean alternative if `weft` ever turns out to be too obscure.

## Progress so far

| Item | State |
|---|---|
| Architecture analysis written | DONE — `problem_statement.md` in this repo (uses the old `WORKBENCH_ROOT` name; supersede before further discussion) |
| Fish helpers copied to plugin layout | DONE — `/Users/kirillabrosimov/Projects/fish-weft/base/{functions,completions}/` |
| Files copied (functions): `proj`, `wt`, `k`, `kpf`, `kms`, `klocal-use`, `_kpf_registry.fish.example`, `_tide_item_proj_pwd` | DONE |
| Files copied (completions): `proj`, `wt`, `k`, `kpf`, `kms` | DONE |
| Source files in `devbox-setup` removed | NOT DONE — copies, not moves; originals still active |
| Fish-weft refactored to use `AION_AUTOPOIESEON` (via `__fish_weft_workspace_root` helper) | IN PROGRESS — user has done this in `proj.fish`, `_tide_item_proj_pwd.fish`, `completions/proj.fish` |
| Plugin scaffolding (README, LICENSE, fisher install hooks, `conf.d/`) | DEFERRED — user is doing it in a separate session |
| `kx` (kube-switch reading `$AION_AUTOPOIESEON/.kubeconfigs/`) | NOT STARTED |
| `devbox-setup` updated to install fish-weft via fisher | NOT STARTED |
| `claude-config` extraction | NOT STARTED |

## Known cleanup items in the extracted fish-weft

- `klocal-use.fish` has `~/Work/mlops-be` hardcoded — work-specific. Options: generalise via config list, push into a private overlay, or split into a separate addon.
- `_tide_item_proj_pwd.fish` depends on tide. Options: keep in core but guard with `functions -q _tide_print_item`, or move to an opt-in subplugin.

## Open questions to pick up next time

1. Should `workbench-spec` exist as its own repo, or is documenting the contract inside `fish-weft`'s README enough?
2. `.kubeconfigs/` location: `$AION_AUTOPOIESEON/.kubeconfigs/` (workspace-scoped, auto separates personal vs work) or `~/.kube/` (kubectl convention, user-scoped)?
3. Migration for `klocal-use`'s work hardcode (see above).
4. Order of operations: `claude-config` extraction first (frees the most context) or last (lets the bootstrap split stabilise first)?

## How to resume

Read these in order:
1. This file (status snapshot).
2. `problem_statement.md` in this repo (full architecture rationale — adjust env var name from `WORKBENCH_ROOT` to `AION_AUTOPOIESEON` mentally).
3. `/Users/kirillabrosimov/Projects/fish-weft/base/` (the current state of the extracted plugin).

Then pick one open question or one item from "Progress so far" to advance.
