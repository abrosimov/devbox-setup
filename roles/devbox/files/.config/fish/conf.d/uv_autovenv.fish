# Auto-activate, auto-deactivate, and auto-create .venv for Python projects.
# Replaces aohorodnyk/fish-autovenv fisher plugin.
#
# On every cd:
#   1. Walk up the directory tree looking for .venv/bin/activate.fish
#   2. If found and different from current $VIRTUAL_ENV — switch
#   3. If not found and $VIRTUAL_ENV is set — deactivate
#   4. If pyproject.toml exists in cwd but no .venv — create with uv, then activate

function __uv_autovenv --on-variable PWD
    if not status is-interactive
        return
    end

    # Walk up to find nearest .venv
    set -l dir (pwd)
    set -l venv_path ""
    while test "$dir" != "/"
        if test -f "$dir/.venv/bin/activate.fish"
            set venv_path "$dir/.venv"
            break
        end
        set dir (dirname "$dir")
    end

    # Activate / switch / deactivate
    if test -n "$venv_path"
        if test "$venv_path" != "$VIRTUAL_ENV"
            if test -n "$VIRTUAL_ENV"
                deactivate
            end
            source "$venv_path/bin/activate.fish"
            echo "Activated venv ($venv_path)"
        end
        return
    end

    # No .venv found — deactivate if active
    if test -n "$VIRTUAL_ENV"
        set -l old "$VIRTUAL_ENV"
        deactivate
        echo "Deactivated venv ($old)"
    end

    # Auto-create: pyproject.toml exists but no .venv
    if test -f pyproject.toml; and type -q uv
        echo "Creating venv for Python project..."
        if uv venv --quiet && uv sync --quiet
            source .venv/bin/activate.fish
            echo "Activated venv (.venv)"
        end
    end
end

# Run once on first prompt (handles: open terminal already inside a venv directory)
function __uv_autovenv_init --on-event fish_prompt
    functions -e __uv_autovenv_init
    __uv_autovenv
end
