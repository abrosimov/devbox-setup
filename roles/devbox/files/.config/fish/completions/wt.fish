# Completions for wt function

# Helper: detect current project from PWD
function __wt_project_dir
    set -q PROJECTS_DIR; or return 1
    set -l rel (string replace "$PROJECTS_DIR/" '' -- $PWD)
    test "$rel" = "$PWD"; and return 1
    set -l project (string split '/' -- $rel)[1]
    echo "$PROJECTS_DIR/$project"
end

function __wt_bare_dir
    set -l pd (__wt_project_dir)
    or return 1
    set -l project (basename $pd)
    echo "$pd/$project.git"
end

# Helper: list worktree directory names (excluding the bare repo)
function __wt_worktree_names
    set -l pd (__wt_project_dir)
    or return
    set -l project (basename $pd)
    for d in $pd/*/
        set -l name (basename $d)
        if test "$name" != "$project.git"
            echo $name
        end
    end
end

# Helper: list remote branch names
function __wt_remote_branches
    set -l bd (__wt_bare_dir)
    or return
    git -C "$bd" branch -r 2>/dev/null | string replace -r '^\s*origin/' '' | string match -rv '^HEAD '
end

complete -c wt -f

# Subcommands
complete -c wt -n '__fish_use_subcommand' -a add -d 'Create worktree'
complete -c wt -n '__fish_use_subcommand' -a ls -d 'List worktrees'
complete -c wt -n '__fish_use_subcommand' -a rm -d 'Remove worktree'

# Worktree names as cd shortcuts
complete -c wt -n '__fish_use_subcommand' -a '(__wt_worktree_names)'

# wt add: complete with remote branches
complete -c wt -n '__fish_seen_subcommand_from add' -a '(__wt_remote_branches)'
complete -c wt -n '__fish_seen_subcommand_from add' -l from -d 'Base branch'

# wt rm: complete with worktree directory names
complete -c wt -n '__fish_seen_subcommand_from rm' -a '(__wt_worktree_names)'
