# devbox-setup
- [x] change paths to j2 and use variables there.
- [x] Then test it on local laptop
- [ ] Set `devbox_paths.dotfiles_root_dir` to valid path, e.g. `~`.
- [ ] Linux should be supported too.
- [x] Dev-mode with `devbox_paths.dotfiles_root_dir` set to some dir, useful in local development and tests
- [ ] Partially applying tasks. We don't need to rune all operations if dotfiles have changed, or new software for brew, etc.
- [ ] Write Makefile for creating and encrypting vault file with ssh password.
- [ ] Move `prepare_user` and `install_configs` tasks to common directory.
- [ ] Then ensure .gitconfig, etc.
- [ ] Write tests
- [ ] Write CI for GH Actions.
- [ ] Install `sudo softwareupdate --install-rosetta`

# Additional packages
- jq
- yq
- perf
- pprof

# Supported OS
- macOS (Darwin)
- Ubuntu (Linux) — current Linux support is Ubuntu-only.

## Quick start
- `make run` - full run
- `make dev` - run in dev_mode (useful for local testing with overridden dotfiles path)
- `make run V=2` - increase verbosity (use V=1..4)

## Partial runs via tags (Makefile)
- `make packages` - run only package installation phases
- `make configs` - apply configuration files only
- `make user` - user setup and shell polishing only
- `make dev-packages` - packages phase in dev_mode
- `make dev-configs` - configs phase in dev_mode
- `make dev-user` - user phase in dev_mode
- `make run TAGS="packages,configs"` - custom set of tags
- `make dev TAGS="configs"` - run only configs in dev_mode

## Local overlay

Laptop-only files that should not be committed to the repository go into `roles/devbox/local/`. This directory is gitignored and mirrors the same structure as `roles/devbox/files/`. Files placed there are deployed **after** the main `files/` pass, so they can add new files or override repo-managed ones.

Example: a fish function with a private path
```
roles/devbox/local/.config/fish/functions/kstg.fish
```
gets deployed to `~/.config/fish/functions/kstg.fish` without ever appearing in git.
