# Completions for proj function
complete -c proj -f

# Helper: detect current project from PWD
function __proj_current_project
    set -q PROJECTS_DIR; or return 1
    set -l rel (string replace "$PROJECTS_DIR/" '' -- $PWD)
    test "$rel" = "$PWD"; and return 1
    set -l project (string split '/' -- $rel)[1]
    echo "$project"
end

function __proj_base_dir
    set -l project (__proj_current_project)
    or return 1
    echo "$PROJECTS_DIR/$project/base"
end

# Helper: list worktree directory names (excluding base)
function __proj_worktree_names
    set -l project (__proj_current_project)
    or return
    for d in $PROJECTS_DIR/$project/*/
        set -l name (basename $d)
        if test "$name" != base
            echo $name
        end
    end
end

# Helper: list remote branch names
function __proj_remote_branches
    set -l bd (__proj_base_dir)
    or return
    git -C "$bd" branch -r 2>/dev/null | string replace -r '^\s*origin/' '' | string match -rv '^HEAD '
end

# Helper: check if we're completing after "proj wt"
function __proj_seen_wt
    set -l cmd (commandline -opc)
    test (count $cmd) -ge 2; and test "$cmd[2]" = wt
end

# Helper: check if we're completing after "proj wt add/rm/ls"
function __proj_seen_wt_subcommand
    set -l cmd (commandline -opc)
    test (count $cmd) -ge 3; and test "$cmd[2]" = wt; and contains -- "$cmd[3]" add rm ls
end

# Subcommands
complete -c proj -n '__fish_use_subcommand' -a clone -d 'Clone a repo into base/'
complete -c proj -n '__fish_use_subcommand' -a new -d 'Create empty project with git init'
complete -c proj -n '__fish_use_subcommand' -a convert -d 'Convert old-style to base/ layout'
complete -c proj -n '__fish_use_subcommand' -a ls -d 'List projects'
complete -c proj -n '__fish_use_subcommand' -a wt -d 'Worktree management'

# Project names as cd shortcuts
complete -c proj -n '__fish_use_subcommand' -a '(set -q PROJECTS_DIR; and test -d "$PROJECTS_DIR"; and for d in $PROJECTS_DIR/*/; basename $d; end)'

# proj wt subcommands
complete -c proj -n '__proj_seen_wt; and not __proj_seen_wt_subcommand' -a add -d 'Create worktree'
complete -c proj -n '__proj_seen_wt; and not __proj_seen_wt_subcommand' -a ls -d 'List worktrees'
complete -c proj -n '__proj_seen_wt; and not __proj_seen_wt_subcommand' -a rm -d 'Remove worktree'

# proj wt <name> — worktree names as cd shortcuts
complete -c proj -n '__proj_seen_wt; and not __proj_seen_wt_subcommand' -a '(__proj_worktree_names)'

# proj wt add: complete with remote branches
complete -c proj -n '__proj_seen_wt; and string match -q "* wt add*" -- (commandline -cp)' -a '(__proj_remote_branches)'
complete -c proj -n '__proj_seen_wt; and string match -q "* wt add*" -- (commandline -cp)' -l from -d 'Base branch'

# proj wt rm: complete with worktree names
complete -c proj -n '__proj_seen_wt; and string match -q "* wt rm*" -- (commandline -cp)' -a '(__proj_worktree_names)'
