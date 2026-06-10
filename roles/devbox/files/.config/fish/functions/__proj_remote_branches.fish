function __proj_remote_branches
    set -l bd (__proj_base_dir)
    or return
    git -C "$bd" branch -r 2>/dev/null | string replace -r '^\s*origin/' '' | string match -rv '^HEAD '
end
