function _tide_item_proj_pwd
    # Custom pwd for Tide prompt with:
    # - Project-aware display for PROJECTS_DIR
    # - Ellipsis pattern for deep paths: first/.../last

    set -l pwd_display

    if test "$PWD" = "$HOME"
        set pwd_display "~"
    else if set -q PROJECTS_DIR; and string match -q "$PROJECTS_DIR/*" -- $PWD
        # Inside PROJECTS_DIR — project-aware display
        set -l rel (string replace "$PROJECTS_DIR/" '' -- $PWD)
        set -l parts (string split '/' -- $rel)
        set -l project $parts[1]

        if test (count $parts) -le 2
            # At project root or base/worktree level
            set pwd_display $project
        else
            # Deep inside project — show project/.../last
            set pwd_display "$project/.../$parts[-1]"
        end
    else
        # Outside PROJECTS_DIR — use ellipsis pattern
        set -l path (string replace "$HOME" "~" -- $PWD)
        set -l parts (string split '/' -- $path)

        if test (count $parts) -le 2
            set pwd_display $path
        else
            # first/.../last pattern
            set pwd_display "$parts[1]/.../$parts[-1]"
        end
    end

    # Output with Tide styling
    _tide_print_item proj_pwd $tide_proj_pwd_icon' ' $pwd_display
end
