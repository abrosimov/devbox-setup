function proj --description "Project management: clone bare repos, cd into projects"
    if not set -q PROJECTS_DIR
        echo "PROJECTS_DIR is not set. Run make work / make personal to configure."
        return 2
    end

    if test (count $argv) -lt 1
        echo "Usage:"
        echo "  proj clone <url>   — bare-clone repo, set up default worktree"
        echo "  proj ls            — list projects"
        echo "  proj <name>        — cd into project directory"
        return 2
    end

    set -l cmd $argv[1]
    set -e argv[1]

    switch $cmd
        case clone
            if test (count $argv) -ne 1
                echo "proj clone <url>"
                return 2
            end

            set -l url $argv[1]

            # Parse repo name from URL (HTTPS or SSH)
            set -l name
            if string match -qr '^https?://' -- $url
                # https://github.com/org/repo.git → repo
                set name (string replace -r '\.git$' '' -- (basename $url))
            else if string match -qr '^git@' -- $url
                # git@github.com:org/repo.git → repo
                set name (string replace -r '\.git$' '' -- (string split '/' -- (string split ':' -- $url)[2])[-1])
            else
                echo "Unrecognized URL format: $url"
                return 2
            end

            set -l project_dir "$PROJECTS_DIR/$name"
            set -l bare_dir "$project_dir/$name.git"

            if test -d "$project_dir"
                echo "Project already exists: $project_dir"
                return 1
            end

            mkdir -p "$project_dir"

            echo "Cloning $url → $bare_dir"
            if not git clone --bare "$url" "$bare_dir"
                rm -rf "$project_dir"
                return 1
            end

            # Configure fetch refspec (bare clones don't set this)
            git -C "$bare_dir" config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
            git -C "$bare_dir" fetch origin

            # Detect default branch
            set -l default_branch
            set -l head_ref (git -C "$bare_dir" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null)
            if test -n "$head_ref"
                set default_branch (string replace 'refs/remotes/origin/' '' -- $head_ref)
            else
                # Fallback: try main, then master
                if git -C "$bare_dir" show-ref --verify --quiet refs/remotes/origin/main
                    set default_branch main
                else if git -C "$bare_dir" show-ref --verify --quiet refs/remotes/origin/master
                    set default_branch master
                else
                    echo "Cannot detect default branch. Bare repo ready at $bare_dir"
                    cd "$project_dir"
                    return 0
                end
            end

            # Create worktree for default branch
            git -C "$bare_dir" worktree add "$project_dir/$default_branch" "$default_branch"
            echo "Ready: $project_dir/$default_branch"
            cd "$project_dir/$default_branch"

        case ls
            if not test -d "$PROJECTS_DIR"
                echo "No projects directory: $PROJECTS_DIR"
                return 1
            end
            for dir in $PROJECTS_DIR/*/
                basename $dir
            end

        case '*'
            # Bare name → cd shortcut
            set -l target "$PROJECTS_DIR/$cmd"
            if test -d "$target"
                cd "$target"
            else
                echo "Project not found: $target"
                return 1
            end
    end
end
