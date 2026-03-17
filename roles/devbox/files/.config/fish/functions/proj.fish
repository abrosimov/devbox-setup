# Helper: install git hooks to a repository
function __proj_install_hooks --argument-names repo_dir
    set -l hooks_src "$HOME/.local/share/proj/hooks"
    set -l hooks_dst "$repo_dir/.git/hooks"

    if not test -d "$hooks_src"
        return 0
    end

    for hook in $hooks_src/*
        set -l hook_name (basename $hook)
        cp "$hook" "$hooks_dst/$hook_name"
        chmod +x "$hooks_dst/$hook_name"
    end
    git -C "$repo_dir" config core.hooksPath "$hooks_dst"
    echo "Installed git hooks"
end

function proj --description "Project management: clone repos, cd into projects"
    if not set -q PROJECTS_DIR
        echo "PROJECTS_DIR is not set. Run make work / make personal to configure."
        return 2
    end

    if test (count $argv) -lt 1
        echo "Usage:"
        echo "  proj clone <url>   — clone repo into base/ directory"
        echo "  proj new <name>    — create empty project with git init"
        echo "  proj convert <name>— convert old-style layout to base/ structure"
        echo "  proj hooks         — install git hooks to current project"
        echo "  proj ls            — list projects"
        echo "  proj <name>        — cd into project directory"
        echo ""
        echo "  proj wt add <branch> [--from base] — create worktree"
        echo "  proj wt sync                       — merge upstream into current worktree"
        echo "  proj wt push                       — push current branch to origin"
        echo "  proj wt ls                         — list worktrees"
        echo "  proj wt status                     — show worktrees with PR status"
        echo "  proj wt rm <name>                  — remove worktree"
        echo "  proj wt clean                      — remove all fully-merged worktrees"
        echo "  proj wt <name>                     — cd to worktree"
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
                set name (string replace -r '\.git$' '' -- (basename $url))
            else if string match -qr '^git@' -- $url
                set name (string replace -r '\.git$' '' -- (string split '/' -- (string split ':' -- $url)[2])[-1])
            else
                echo "Unrecognized URL format: $url"
                return 2
            end

            set -l project_dir "$PROJECTS_DIR/$name"
            set -l base_dir "$project_dir/base"

            if test -d "$project_dir"
                echo "Project already exists: $project_dir"
                return 1
            end

            echo "Cloning $url → $base_dir"
            if not git clone "$url" "$base_dir"
                rm -rf "$project_dir"
                return 1
            end

            # Install git hooks
            __proj_install_hooks "$base_dir"

            echo "Ready: $base_dir"
            cd "$base_dir"

        case ls
            if not test -d "$PROJECTS_DIR"
                echo "No projects directory: $PROJECTS_DIR"
                return 1
            end
            for dir in $PROJECTS_DIR/*/
                basename $dir
            end

        case new
            if test (count $argv) -ne 1
                echo "proj new <name>"
                return 2
            end
            set -l name $argv[1]
            set -l project_dir "$PROJECTS_DIR/$name"
            set -l base_dir "$project_dir/base"

            if test -d "$project_dir"
                echo "Project already exists: $project_dir"
                return 1
            end

            mkdir -p "$base_dir"
            git init "$base_dir"

            # Install git hooks
            __proj_install_hooks "$base_dir"

            echo "Created: $base_dir"
            cd "$base_dir"

        case convert
            if test (count $argv) -ne 1
                echo "proj convert <name>"
                return 2
            end
            set -l name $argv[1]
            set -l project_dir "$PROJECTS_DIR/$name"

            # Check project exists
            if not test -d "$project_dir"
                echo "Project not found: $project_dir"
                return 1
            end

            # Check it's old-style (has .git at root, no base/ subdir)
            if not test -d "$project_dir/.git"
                echo "Not a git repository: $project_dir"
                return 1
            end
            if test -d "$project_dir/base"
                echo "Already new-style layout (base/ exists): $project_dir"
                return 1
            end

            # Check for uncommitted staged changes
            if not git -C "$project_dir" diff --cached --quiet
                echo "Uncommitted staged changes detected. Commit or reset before converting."
                return 1
            end

            # Collect untracked project files to preserve at wrapper level
            set -l preserve_files
            for f in CLAUDE.md .claude
                if test -e "$project_dir/$f"
                    if not git -C "$project_dir" ls-files --error-unmatch "$f" >/dev/null 2>&1
                        set -a preserve_files $f
                    end
                end
            end

            # Move preserved files to temp location
            set -l tmp_preserve (mktemp -d)
            for f in $preserve_files
                mv "$project_dir/$f" "$tmp_preserve/"
            end

            # Do the conversion: rename → mkdir → move back as base/
            set -l tmp_dir "$project_dir.converting"
            mv "$project_dir" "$tmp_dir"
            mkdir -p "$project_dir"
            mv "$tmp_dir" "$project_dir/base"

            # Restore preserved files at wrapper level
            for f in $preserve_files
                mv "$tmp_preserve/$f" "$project_dir/"
            end
            rmdir "$tmp_preserve" 2>/dev/null

            echo "Converted to new layout:"
            echo "  $project_dir/base/ — repository"
            if test (count $preserve_files) -gt 0
                echo "  $project_dir/{$preserve_files} — preserved at project level"
            end
            cd "$project_dir/base"

        case hooks
            # Install hooks to current project — detect from PWD
            set -l rel (string replace "$PROJECTS_DIR/" '' -- $PWD)
            if test "$rel" = "$PWD"
                echo "Not inside PROJECTS_DIR ($PROJECTS_DIR)"
                return 2
            end
            set -l project (string split '/' -- $rel)[1]
            set -l project_dir "$PROJECTS_DIR/$project"
            set -l base_dir "$project_dir/base"

            if not test -d "$base_dir/.git"
                echo "Base repo not found: $base_dir"
                return 2
            end

            __proj_install_hooks "$base_dir"

        case wt
            # Worktree management — detect project from PWD
            set -l rel (string replace "$PROJECTS_DIR/" '' -- $PWD)
            if test "$rel" = "$PWD"
                echo "Not inside PROJECTS_DIR ($PROJECTS_DIR)"
                return 2
            end
            set -l project (string split '/' -- $rel)[1]
            set -l project_dir "$PROJECTS_DIR/$project"
            set -l base_dir "$project_dir/base"

            if not test -d "$base_dir/.git"
                echo "Base repo not found: $base_dir"
                echo "Run 'proj convert $project' to migrate to new layout first."
                return 2
            end

            if test (count $argv) -lt 1
                echo "Usage:"
                echo "  proj wt add <branch> [--from base] — create worktree (tracks remote if exists)"
                echo "  proj wt sync                       — merge upstream into current worktree"
                echo "  proj wt push                       — push current branch to origin"
                echo "  proj wt ls                         — list worktrees"
                echo "  proj wt status                     — show worktrees with PR status"
                echo "  proj wt rm <name>                  — remove worktree"
                echo "  proj wt clean                      — remove all fully-merged worktrees"
                echo "  proj wt <name>                     — cd to worktree"
                return 2
            end

            set -l wt_cmd $argv[1]
            set -e argv[1]

            switch $wt_cmd
                case add
                    if test (count $argv) -lt 1
                        echo "proj wt add <branch> [--from base]"
                        return 2
                    end

                    set -l branch $argv[1]
                    set -e argv[1]

                    # Parse --from
                    set -l base_branch
                    set -l i 1
                    while test $i -le (count $argv)
                        switch $argv[$i]
                            case --from
                                set base_branch $argv[(math $i + 1)]
                                set i (math $i + 2)
                                continue
                            case '*'
                                set i (math $i + 1)
                                continue
                        end
                    end

                    # Default base: detect from origin/HEAD
                    if not set -q base_branch[1]
                        set -l head_ref (git -C "$base_dir" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null)
                        if test -n "$head_ref"
                            set base_branch (string replace 'refs/remotes/origin/' '' -- $head_ref)
                        else if git -C "$base_dir" show-ref --verify --quiet refs/remotes/origin/main
                            set base_branch main
                        else if git -C "$base_dir" show-ref --verify --quiet refs/remotes/origin/master
                            set base_branch master
                        else
                            echo "Cannot detect default branch. Use --from <base>."
                            return 2
                        end
                    end

                    # Sanitize branch name for directory: feature/login → feature-login
                    set -l dir_name (string replace -a '/' '-' -- $branch)
                    set -l wt_path "$project_dir/$dir_name"

                    if test -d "$wt_path"
                        echo "Directory already exists: $wt_path"
                        return 1
                    end

                    # Check if branch already exists (local, remote, or create new)
                    if git -C "$base_dir" show-ref --verify --quiet "refs/heads/$branch"
                        # Local branch exists
                        git -C "$base_dir" worktree add "$wt_path" "$branch"
                    else if git -C "$base_dir" show-ref --verify --quiet "refs/remotes/origin/$branch"
                        # Remote branch exists — create tracking branch
                        git -C "$base_dir" fetch origin "$branch"
                        git -C "$base_dir" worktree add --track -b "$branch" "$wt_path" "origin/$branch"
                    else
                        # Neither exists — create new branch from base
                        git -C "$base_dir" worktree add -b "$branch" "$wt_path" "$base_branch"
                    end

                    and echo "Ready: $wt_path"
                    # Claude Code extras (settings.local.json + memory symlink)
                    if test -d "$base_dir/.claude"
                        if test -f "$base_dir/.claude/settings.local.json"
                            mkdir -p "$wt_path/.claude"
                            cp "$base_dir/.claude/settings.local.json" "$wt_path/.claude/"
                            echo "Copied .claude/settings.local.json"
                        end
                        if test -d "$base_dir/.claude/memory"
                            mkdir -p "$wt_path/.claude"
                            ln -sf (realpath "$base_dir/.claude/memory") "$wt_path/.claude/memory"
                            echo "Linked .claude/memory"
                        end
                    end
                    and cd "$wt_path"

                case sync
                    # Must be inside a worktree (not base/)
                    set -l current_rel (string replace "$project_dir/" '' -- $PWD)
                    if test "$current_rel" = "base" -o "$current_rel" = "$PWD"
                        echo "Run this from inside a worktree, not base/"
                        return 2
                    end

                    # Detect upstream from base's current branch
                    set -l upstream (git -C "$base_dir" branch --show-current)
                    if test -z "$upstream"
                        echo "Cannot detect upstream branch (base/ is in detached HEAD?)"
                        return 1
                    end

                    # Fetch and merge
                    echo "Fetching origin/$upstream..."
                    if not git -C "$base_dir" fetch origin "$upstream"
                        echo "Fetch failed"
                        return 1
                    end

                    echo "Merging origin/$upstream into current branch..."
                    git merge "origin/$upstream" --no-edit
                    # Let git merge report success/conflict

                case push
                    # Must be inside a worktree (not base/)
                    set -l current_rel (string replace "$project_dir/" '' -- $PWD)
                    if test "$current_rel" = "base" -o "$current_rel" = "$PWD"
                        echo "Run this from inside a worktree, not base/"
                        return 2
                    end

                    set -l current_branch (git branch --show-current)
                    if test -z "$current_branch"
                        echo "Not on a branch (detached HEAD?)"
                        return 1
                    end

                    echo "Pushing $current_branch to origin..."
                    git push -u origin "$current_branch"

                case ls
                    git -C "$base_dir" worktree list

                case rm
                    if test (count $argv) -ne 1
                        echo "proj wt rm <name>"
                        return 2
                    end

                    set -l wt_name $argv[1]
                    set -l wt_path "$project_dir/$wt_name"

                    if not test -d "$wt_path"
                        echo "Worktree directory not found: $wt_path"
                        return 1
                    end

                    # If we're inside the worktree being removed, cd out first
                    if string match -q "$wt_path*" -- $PWD
                        cd "$project_dir"
                    end

                    git -C "$base_dir" worktree remove "$wt_path"

                case status
                    set -l default_branch
                    set -l head_ref (git -C "$base_dir" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null)
                    if test -n "$head_ref"
                        set default_branch (string replace 'refs/remotes/origin/' '' -- $head_ref)
                    else if git -C "$base_dir" show-ref --verify --quiet refs/remotes/origin/main
                        set default_branch main
                    else if git -C "$base_dir" show-ref --verify --quiet refs/remotes/origin/master
                        set default_branch master
                    else
                        set default_branch (git -C "$base_dir" branch --show-current)
                    end

                    printf "%-50s %-30s %s\n" "WORKTREE" "BRANCH" "STATUS"
                    printf "%-50s %-30s %s\n" "--------" "------" "------"

                    for line in (git -C "$base_dir" worktree list)
                        set -l wt (echo $line | awk '{print $1}')
                        set -l br (git -C "$wt" branch --show-current 2>/dev/null; or echo "(detached)")
                        set -l label

                        if test "$wt" = "$base_dir"
                            set label "(base)"
                        else
                            set -l ahead (git -C "$base_dir" rev-list --count "$default_branch".."$br" 2>/dev/null; or echo "?")
                            set -l pr_state (gh pr view "$br" --json state --jq .state 2>/dev/null; or echo "no PR")
                            set label "+$ahead commits | PR: $pr_state"
                        end

                        printf "%-50s %-30s %s\n" "$wt" "$br" "$label"
                    end

                case clean
                    echo "Cleaning merged worktrees..."
                    set -l removed 0

                    for line in (git -C "$base_dir" worktree list | tail -n +2)
                        set -l wt (echo $line | awk '{print $1}')
                        test "$wt" = "$base_dir"; and continue

                        set -l br (git -C "$wt" branch --show-current 2>/dev/null)
                        test -z "$br"; and continue

                        if git -C "$base_dir" branch --merged 2>/dev/null | grep -q "^[[:space:]]*$br\$"
                            echo "  Removing: $wt ($br)"
                            git -C "$base_dir" worktree remove "$wt" 2>/dev/null; or true
                            git -C "$base_dir" branch -d "$br" 2>/dev/null; or true
                            set removed (math $removed + 1)
                        end
                    end

                    git -C "$base_dir" worktree prune
                    echo "Done. Removed $removed worktree(s)."

                case '*'
                    # Bare name → cd to worktree directory
                    set -l wt_path "$project_dir/$wt_cmd"
                    if test -d "$wt_path"
                        cd "$wt_path"
                    else
                        echo "Worktree not found: $wt_path"
                        return 1
                    end
            end

        case '*'
            # Bare name → cd shortcut
            set -l target "$PROJECTS_DIR/$cmd"
            if not test -d "$target"
                echo "Project not found: $target"
                return 1
            end

            # Detect old-style layout and warn
            if test -d "$target/.git"; and not test -d "$target/base"
                echo "⚠ Old-style layout. Run 'proj convert $cmd' to migrate."
            end

            # For new-style, cd into base/ if it exists
            if test -d "$target/base"
                cd "$target/base"
            else
                cd "$target"
            end
    end
end
