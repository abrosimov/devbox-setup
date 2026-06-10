function __proj_current_project
    set -q PROJECTS_DIR; or return 1
    set -l rel (string replace "$PROJECTS_DIR/" '' -- $PWD)
    test "$rel" = "$PWD"; and return 1
    set -l project (string split '/' -- $rel)[1]
    echo "$project"
end
