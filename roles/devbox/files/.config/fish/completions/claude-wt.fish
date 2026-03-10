# Completions for claude-wt (Claude Code worktree manager)
complete -c claude-wt -f

# Helper: list existing worktree branch names (excluding main worktree)
function __claude_wt_branches
    set -l main_wt (git rev-parse --show-toplevel 2>/dev/null)
    or return
    git worktree list 2>/dev/null | while read -l line
        set -l parts (string split ' ' -- $line)
        set -l wt $parts[1]
        test "$wt" = "$main_wt"; and continue
        basename $wt
    end
end

# Helper: list git branch names for --from
function __claude_wt_git_branches
    git branch -a 2>/dev/null | string replace -r '^\*?\s+' '' | string replace -r '^remotes/origin/' '' | string match -rv '^HEAD ' | sort -u
end

# Subcommands
complete -c claude-wt -n '__fish_use_subcommand' -a new -d 'Create worktree + branch'
complete -c claude-wt -n '__fish_use_subcommand' -a list -d 'List worktrees'
complete -c claude-wt -n '__fish_use_subcommand' -a status -d 'Show worktrees with PR status'
complete -c claude-wt -n '__fish_use_subcommand' -a rm -d 'Remove worktree + delete merged branch'
complete -c claude-wt -n '__fish_use_subcommand' -a clean -d 'Remove all fully-merged worktrees'

# new: --from flag with branch completion
complete -c claude-wt -n '__fish_seen_subcommand_from new' -l from -d 'Base branch' -xa '(__claude_wt_git_branches)'

# list: --ticket flag
complete -c claude-wt -n '__fish_seen_subcommand_from list' -l ticket -d 'Filter by ticket ID'

# rm: complete with existing worktree names
complete -c claude-wt -n '__fish_seen_subcommand_from rm' -a '(__claude_wt_branches)'
