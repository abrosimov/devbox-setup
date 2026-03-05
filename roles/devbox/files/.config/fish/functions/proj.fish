function proj --description "Project management: clone repos, cd into projects"
    if not set -q PROJECTS_DIR
        echo "PROJECTS_DIR is not set. Run make work / make personal to configure."
        return 2
    end

    if test (count $argv) -lt 1
        echo "Usage:"
        echo "  proj clone <url>   — clone repo into base/ directory"
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
