function wt --description "Git worktree management for bare-repo projects"
    if not set -q PROJECTS_DIR
        echo "PROJECTS_DIR is not set. Run make work / make personal to configure."
        return 2
    end

    # Detect current project from PWD
    set -l rel (string replace "$PROJECTS_DIR/" '' -- $PWD)
    if test "$rel" = "$PWD"
        echo "Not inside PROJECTS_DIR ($PROJECTS_DIR)"
        return 2
    end
    set -l project (string split '/' -- $rel)[1]
    set -l bare_dir "$PROJECTS_DIR/$project/$project.git"

    if not test -d "$bare_dir"
        echo "Bare repo not found: $bare_dir"
        return 2
    end

    if test (count $argv) -lt 1
        echo "Usage:"
        echo "  wt add <branch> [--from base]  — create worktree (default base: default branch)"
        echo "  wt ls                           — list worktrees"
        echo "  wt rm <name>                    — remove worktree"
        echo "  wt <name>                       — cd to worktree directory"
        return 2
    end

    set -l cmd $argv[1]
    set -e argv[1]

    switch $cmd
        case add
            if test (count $argv) -lt 1
                echo "wt add <branch> [--from base]"
                return 2
            end

            set -l branch $argv[1]
            set -e argv[1]

            # Parse --from
            set -l base
            set -l i 1
            while test $i -le (count $argv)
                switch $argv[$i]
                    case --from
                        set base $argv[(math $i + 1)]
                        set i (math $i + 2)
                        continue
                    case '*'
                        set i (math $i + 1)
                        continue
                end
            end

            # Default base: detect from origin/HEAD
            if not set -q base[1]
                set -l head_ref (git -C "$bare_dir" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null)
                if test -n "$head_ref"
                    set base (string replace 'refs/remotes/origin/' '' -- $head_ref)
                else if git -C "$bare_dir" show-ref --verify --quiet refs/remotes/origin/main
                    set base main
                else if git -C "$bare_dir" show-ref --verify --quiet refs/remotes/origin/master
                    set base master
                else
                    echo "Cannot detect default branch. Use --from <base>."
                    return 2
                end
            end

            # Sanitize branch name for directory: feature/login → feature-login
            set -l dir_name (string replace -a '/' '-' -- $branch)
            set -l wt_path "$PROJECTS_DIR/$project/$dir_name"

            if test -d "$wt_path"
                echo "Directory already exists: $wt_path"
                return 1
            end

            # Check if branch already exists (local or remote tracking)
            if git -C "$bare_dir" show-ref --verify --quiet "refs/heads/$branch"
                git -C "$bare_dir" worktree add "$wt_path" "$branch"
            else
                git -C "$bare_dir" worktree add -b "$branch" "$wt_path" "$base"
            end

            and echo "Ready: $wt_path"
            and cd "$wt_path"

        case ls
            git -C "$bare_dir" worktree list

        case rm
            if test (count $argv) -ne 1
                echo "wt rm <name>"
                return 2
            end

            set -l name $argv[1]
            set -l wt_path "$PROJECTS_DIR/$project/$name"

            if not test -d "$wt_path"
                echo "Worktree directory not found: $wt_path"
                return 1
            end

            # If we're inside the worktree being removed, cd out first
            if string match -q "$wt_path*" -- $PWD
                cd "$PROJECTS_DIR/$project"
            end

            git -C "$bare_dir" worktree remove "$wt_path"

        case '*'
            # Bare name → cd to worktree directory
            set -l target "$PROJECTS_DIR/$project/$cmd"
            if test -d "$target"
                cd "$target"
            else
                echo "Worktree not found: $target"
                return 1
            end
    end
end
