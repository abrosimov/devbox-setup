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
