function fish_title
    # Home
    if test "$PWD" = "$HOME"
        echo "~"
        return
    end

    # Inside PROJECTS_DIR — show project name (and JIRA key for worktrees)
    if set -q PROJECTS_DIR; and string match -q "$PROJECTS_DIR/*" -- $PWD
        set -l rel (string replace "$PROJECTS_DIR/" '' -- $PWD)
        set -l parts (string split '/' -- $rel)
        set -l project $parts[1]

        if test (count $parts) -ge 2
            set -l location $parts[2]
            if test "$location" = "base"
                # In base — just project name
                echo $project
            else
                # In worktree — extract JIRA key if present
                set -l jira_key (string match -r '[A-Z]{2,}-[0-9]+' -- $location)
                if test -n "$jira_key"
                    echo "$project:$jira_key"
                else
                    echo "$project:$location"
                end
            end
        else
            echo $project
        end
        return
    end

    # Default: basename
    basename "$PWD"
end
