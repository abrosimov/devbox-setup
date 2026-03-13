# Auto-create .venv for Python projects (complements fish-autovenv which only activates)
# Triggers on directory change — useful for git worktrees and fresh clones

function __uv_autovenv_create --on-variable PWD
    # Skip if uv not available or not a Python project
    if not type -q uv
        return
    end
    if not test -f pyproject.toml
        return
    end
    # Skip if venv already exists
    if test -d .venv
        return
    end

    echo "Creating venv for Python project..."
    uv venv --quiet && uv sync --quiet
end
