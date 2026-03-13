# Auto-install node_modules for JS/TS projects
# Triggers on directory change — useful for git worktrees and fresh clones

function __npm_autoinstall --on-variable PWD
    # Skip if not a JS project
    if not test -f package.json
        return
    end
    # Skip if node_modules already exists
    if test -d node_modules
        return
    end

    # Detect package manager from lockfile
    if test -f pnpm-lock.yaml
        if type -q pnpm
            echo "Installing dependencies with pnpm..."
            pnpm install --silent
        end
    else if test -f bun.lockb
        if type -q bun
            echo "Installing dependencies with bun..."
            bun install --silent
        end
    else if test -f yarn.lock
        if type -q yarn
            echo "Installing dependencies with yarn..."
            yarn install --silent
        end
    else if test -f package-lock.json
        if type -q npm
            echo "Installing dependencies with npm..."
            npm install --silent
        end
    end
end
