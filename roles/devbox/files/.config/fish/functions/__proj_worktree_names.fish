function __proj_worktree_names
    set -l project (__proj_current_project)
    or return
    for d in $AION_AUTOPOIESEON/$project/*/
        set -l name (basename $d)
        if test "$name" != base
            echo $name
        end
    end
end
