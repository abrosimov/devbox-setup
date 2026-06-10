function __proj_base_dir
    set -l project (__proj_current_project)
    or return 1
    echo "$PROJECTS_DIR/$project/base"
end
