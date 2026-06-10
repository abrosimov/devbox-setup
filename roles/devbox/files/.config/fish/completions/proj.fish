# Completions for proj function.
# Helper functions live in functions/__proj_*.fish so fish autoload picks them up
# regardless of whether `proj` or `wt` is being completed first.
complete -c proj -f

# Subcommands
complete -c proj -n '__fish_use_subcommand' -a clone -d 'Clone a repo into base/'
complete -c proj -n '__fish_use_subcommand' -a new -d 'Create empty project with git init'
complete -c proj -n '__fish_use_subcommand' -a convert -d 'Convert old-style to base/ layout'
complete -c proj -n '__fish_use_subcommand' -a hooks -d 'Install git hooks to current project'
complete -c proj -n '__fish_use_subcommand' -a ls -d 'List projects'
complete -c proj -n '__fish_use_subcommand' -a wt -d 'Worktree management'

# Project names as cd shortcuts
complete -c proj -n '__fish_use_subcommand' -a '(set -q AION_AUTOPOIESEON; and test -d "$AION_AUTOPOIESEON"; and for d in $AION_AUTOPOIESEON/*/; basename $d; end)'

# proj wt subcommands
complete -c proj -n '__proj_seen_wt; and not __proj_seen_wt_subcommand' -a add -d 'Create worktree (tracks remote if exists)'
complete -c proj -n '__proj_seen_wt; and not __proj_seen_wt_subcommand' -a fork -d 'Fork from current worktree'
complete -c proj -n '__proj_seen_wt; and not __proj_seen_wt_subcommand' -a sync -d 'Merge upstream into current worktree'
complete -c proj -n '__proj_seen_wt; and not __proj_seen_wt_subcommand' -a push -d 'Push current branch to origin'
complete -c proj -n '__proj_seen_wt; and not __proj_seen_wt_subcommand' -a ls -d 'List worktrees'
complete -c proj -n '__proj_seen_wt; and not __proj_seen_wt_subcommand' -a rm -d 'Remove worktree'

# proj wt <name> — worktree names as cd shortcuts
complete -c proj -n '__proj_seen_wt; and not __proj_seen_wt_subcommand' -a '(__proj_worktree_names)'

# proj wt add: complete with remote branches
complete -c proj -n '__proj_seen_wt_add' -a '(__proj_remote_branches)'
complete -c proj -n '__proj_seen_wt_add' -l from -d 'Base branch'

# proj wt fork: no special completions (new branch name is user-provided)

# proj wt rm: complete with worktree names and -f flag
complete -c proj -n '__proj_seen_wt_rm' -a '(__proj_worktree_names)'
complete -c proj -n '__proj_seen_wt_rm' -s f -l force -d 'Force remove worktree and delete unmerged branch'
