# Completions for wt (alias for proj wt)
complete -c wt -f

# Reuse helpers from proj completions
complete -c wt -n '__fish_use_subcommand' -a add -d 'Create worktree'
complete -c wt -n '__fish_use_subcommand' -a fork -d 'Fork from current worktree'
complete -c wt -n '__fish_use_subcommand' -a ls -d 'List worktrees'
complete -c wt -n '__fish_use_subcommand' -a rm -d 'Remove worktree'

# Worktree names as cd shortcuts
complete -c wt -n '__fish_use_subcommand' -a '(__proj_worktree_names)'

# wt add: complete with remote branches
complete -c wt -n '__fish_seen_subcommand_from add' -a '(__proj_remote_branches)'
complete -c wt -n '__fish_seen_subcommand_from add' -l from -d 'Base branch'

# wt rm: complete with worktree names
complete -c wt -n '__fish_seen_subcommand_from rm' -a '(__proj_worktree_names)'
