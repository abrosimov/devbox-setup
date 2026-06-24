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

# Helper: read the `claude` action from .wtfiles, returning "link" (default) or "copy".
# Recognised manifest entries (any of these forms):
#   claude            → link
#   claude link       → link
#   claude copy       → copy
# Returns the action string on stdout.
function __proj_wt_claude_action --argument-names base_dir
    set -l manifest "$base_dir/.wtfiles"
    set -l action link

    if not test -f "$manifest"
        echo $action
        return 0
    end

    while read -l line
        string match -qr '^\s*(#|$)' -- "$line"; and continue
        set line (string trim -- "$line")
        if string match -qr '^claude(\s+(link|copy))?\s*$' -- "$line"
            set -l rest (string replace -r '^claude\s*' '' -- "$line")
            set rest (string trim -- "$rest")
            if test "$rest" = copy
                set action copy
            else
                set action link
            end
        end
    end <"$manifest"

    echo $action
end

# Helper: list paths inside a worktree considered "ours" — wrapper-level
# injections (`.claude`, `CLAUDE.md`) and every entry from `base/.wtfiles`
# (with optional `link`/`copy` verb stripped, `claude` pseudo-entry skipped).
# Used by `wt rm` to distinguish managed artefacts from user work.
function __proj_wt_collect_ours --argument-names base_dir
    echo .claude
    echo CLAUDE.md

    set -l manifest "$base_dir/.wtfiles"
    test -f "$manifest"; or return 0

    while read -l line
        string match -qr '^\s*(#|$)' -- "$line"; and continue
        set line (string trim -- "$line")

        if string match -qr '^claude(\s+(link|copy))?\s*$' -- "$line"
            continue
        end

        set -l fpath $line
        if string match -qr '^(copy|link)\s+' -- "$line"
            set fpath (string replace -r '^(copy|link)\s+' '' -- "$line")
        end

        echo $fpath
    end <"$manifest"
end

# Helper: inject wrapper-level .claude/ and CLAUDE.md into a new worktree.
# Defaults to relative symlinks (portable across machines). Respects the
# `claude link`/`claude copy` directive in .wtfiles (read from base/, the
# repo root) for per-worktree divergence. Skips silently when the source is
# missing; warns when the target already exists.
function __proj_wt_link_claude --argument-names project_dir base_dir wt_path
    set -l action (__proj_wt_claude_action "$base_dir")

    for item in .claude CLAUDE.md
        set -l src "$project_dir/$item"
        set -l dst "$wt_path/$item"

        if not test -e "$src"
            continue
        end

        if test -e "$dst" -o -L "$dst"
            echo "  claude: $item already exists in worktree, skipping"
            continue
        end

        switch $action
            case copy
                cp -R "$src" "$dst"
                echo "  copied: $item"
            case '*'
                # Relative target: parent dir of wt_path is the wrapper.
                ln -s "../$item" "$dst"
                echo "  linked: $item"
        end
    end
end

# Helper: seed a new worktree with gitignored files shared from base
# Uses .wtfiles manifest if present, otherwise prompts interactively.
# Default verb is `link` (symlink); explicit `copy` is the escape hatch
# for entries that must diverge per worktree.
function __proj_wt_copy_shared --argument-names base_dir wt_path
    set -l manifest "$base_dir/.wtfiles"

    if test -f "$manifest"
        while read -l line
            string match -qr '^\s*(#|$)' -- "$line"; and continue
            set line (string trim -- "$line")

            # The `claude` pseudo-entry is handled by __proj_wt_link_claude;
            # skip it here so it is not treated as a real path.
            if string match -qr '^claude(\s+(link|copy))?\s*$' -- "$line"
                continue
            end

            set -l verb link
            set -l fpath
            if string match -qr '^(copy|link)\s+' -- "$line"
                set verb (string match -r '^(copy|link)' -- "$line")[1]
                set fpath (string replace -r '^(copy|link)\s+' '' -- "$line")
            else
                set fpath "$line"
            end

            if not test -e "$base_dir/$fpath"
                echo "  .wtfiles: skip $fpath (not found)"
                continue
            end

            mkdir -p (dirname "$wt_path/$fpath")

            switch $verb
                case copy
                    cp -r "$base_dir/$fpath" "$wt_path/$fpath"
                    echo "  Copied $fpath"
                case link
                    ln -sf (realpath "$base_dir/$fpath") "$wt_path/$fpath"
                    echo "  Linked $fpath"
            end
        end <"$manifest"
        return 0
    end

    # Fallback: scan for ignored files and prompt
    set -l ignored (git -C "$base_dir" ls-files --others --ignored --exclude-standard 2>/dev/null)
    test (count $ignored) -eq 0; and return 0

    # Filter noise: build artifacts, caches, OS junk
    set -l candidates
    for f in $ignored
        string match -qr '^(node_modules|vendor|dist|build|__pycache__|\.cache|target|\.next|\.nuxt|\.turbo|coverage)/' -- "$f"; and continue
        string match -qr '\.(pyc|pyo|class|o|so|dylib)$' -- "$f"; and continue
        string match -qr '(\.DS_Store|Thumbs\.db)$' -- "$f"; and continue
        string match -qr '\.log$' -- "$f"; and continue
        set -a candidates "$f"
    end

    test (count $candidates) -eq 0; and return 0

    echo ""
    echo "Git-ignored files in base/ that may be needed:"
    for i in (seq (count $candidates))
        printf "  %d. %s\n" $i "$candidates[$i]"
    end
    echo ""
    read -P "Link into worktree? [a=all / n=none / 1,3,...]: " answer

    switch "$answer"
        case '' n N no
            return 0
        case a A all
            for f in $candidates
                mkdir -p (dirname "$wt_path/$f")
                ln -sf (realpath "$base_dir/$f") "$wt_path/$f"
                echo "  Linked $f"
            end
        case '*'
            for idx in (string split ',' -- "$answer")
                set idx (string trim -- "$idx")
                if string match -qr '^\d+$' -- "$idx"; and test "$idx" -ge 1 -a "$idx" -le (count $candidates)
                    set -l f "$candidates[$idx]"
                    mkdir -p (dirname "$wt_path/$f")
                    ln -sf (realpath "$base_dir/$f") "$wt_path/$f"
                    echo "  Linked $f"
                end
            end
    end
end

# Helper: classify a worktree-local .claude/ directory for migration.
# Prints one of: empty | only-settings-local | has-unexpected:<list>
function __proj_wt_classify_claude_dir --argument-names dir
    set -l entries
    for e in $dir/* $dir/.*
        set -l name (basename $e)
        test "$name" = .; or test "$name" = ..; and continue
        test -e "$e" -o -L "$e"; or continue
        set -a entries $name
    end

    if test (count $entries) -eq 0
        echo empty
        return 0
    end

    set -l unexpected
    for e in $entries
        if test "$e" != settings.local.json
            set -a unexpected $e
        end
    end

    if test (count $unexpected) -eq 0
        echo only-settings-local
    else
        echo "has-unexpected:"(string join ',' -- $unexpected)
    end
end

# Helper: compare two settings.local.json files. Prints "subset" if `a` has no
# top-level keys missing from `b`, otherwise "diverged:<unique-keys>".
# Falls back to "diverged:unknown" if jq is unavailable or files unparseable.
function __proj_wt_settings_subset --argument-names a b
    if not type -q jq
        echo "diverged:unknown(jq missing)"
        return 0
    end
    set -l unique (jq -r --slurpfile b "$b" '
        (. // {}) as $a
        | ($b[0] // {}) as $bj
        | (($a | keys_unsorted // []) - ($bj | keys_unsorted // [])) | .[]
    ' "$a" 2>/dev/null)
    if test (count $unique) -eq 0
        echo subset
    else
        echo "diverged:"(string join ',' -- $unique)
    end
end

# Helper: walk every worktree under a project and fix .claude / CLAUDE.md links.
# When `apply` is "true", performs changes; otherwise prints what would happen.
function __proj_wt_fix_claude_links_for_project --argument-names project_dir apply
    set -l project (basename "$project_dir")
    set -l base_dir "$project_dir/base"

    if not test -d "$base_dir/.git"
        echo "[$project] not new-style (no base/.git), skipping"
        return 0
    end

    echo "[$project]"

    for entry in $project_dir/*
        test -d "$entry"; or continue
        set -l name (basename "$entry")
        test "$name" = base; and continue

        # Verify this is a real worktree (has a .git file pointing into base/.git).
        if not test -f "$entry/.git"
            continue
        end

        for item in .claude CLAUDE.md
            set -l src "$project_dir/$item"
            set -l dst "$entry/$item"

            if not test -e "$src"
                continue
            end

            # Case B: already a symlink → skip silently.
            if test -L "$dst"
                continue
            end

            # Case A: missing → create symlink.
            if not test -e "$dst"
                if test "$apply" = true
                    ln -s "../$item" "$dst"
                    echo "  $name: created symlink $item -> ../$item"
                else
                    echo "  $name: would create symlink $item -> ../$item"
                end
                continue
            end

            # Case C: real file/directory in worktree — inspect.
            if test "$item" = CLAUDE.md
                # Regular file in worktree: never overwrite automatically.
                echo "  $name: $item is a regular file — manual review required (left untouched)"
                continue
            end

            # .claude/ directory: classify contents.
            set -l klass (__proj_wt_classify_claude_dir "$dst")

            if test "$klass" = empty
                if test "$apply" = true
                    rmdir "$dst"
                    and ln -s "../$item" "$dst"
                    and echo "  $name: removed empty $item/ and symlinked to ../$item"
                else
                    echo "  $name: would remove empty $item/ and symlink to ../$item"
                end
                continue
            end

            if test "$klass" = only-settings-local
                set -l wrapper_settings "$src/settings.local.json"
                set -l wt_settings "$dst/settings.local.json"
                set -l verdict subset

                if test -f "$wt_settings" -a -f "$wrapper_settings"
                    set verdict (__proj_wt_settings_subset "$wt_settings" "$wrapper_settings")
                else if test -f "$wt_settings" -a ! -f "$wrapper_settings"
                    # Wrapper has no settings.local.json — worktree's would be lost.
                    set verdict "diverged:wrapper-missing-settings.local.json"
                end

                if test "$verdict" = subset
                    if test "$apply" = true
                        rm -rf "$dst"
                        and ln -s "../$item" "$dst"
                        and echo "  $name: removed (settings.local.json was subset) and symlinked $item"
                    else
                        echo "  $name: would remove $item/ (only settings.local.json, subset of wrapper) and symlink"
                    end
                else
                    set -l unique_keys (string replace 'diverged:' '' -- $verdict)
                    echo "  $name: needs manual merge — settings.local.json has unique entries: $unique_keys"
                    echo "    inspect: diff $wrapper_settings $wt_settings"
                end
                continue
            end

            # has-unexpected:<list>
            set -l extras (string replace 'has-unexpected:' '' -- $klass)
            echo "  $name: skipped — $item/ contains unexpected entries: $extras"
        end
    end
end

function proj --description "Project management: clone repos, cd into projects"
    if not set -q AION_AUTOPOIESEON
        echo "AION_AUTOPOIESEON is not set. Run make work / make personal to configure."
        echo "(See roles/devbox/defaults/main/shell.yml for naming rationale.)"
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
        echo "  proj wt fork <branch>              — fork from current worktree"
        echo "  proj wt sync                       — merge upstream into current worktree"
        echo "  proj wt push                       — push current branch to origin"
        echo "  proj wt ls                         — list worktrees"
        echo "  proj wt status                     — show worktrees with PR status"
        echo "  proj wt rm [-f] <name>              — remove worktree and branch"
        echo "  proj wt clean [--age <days>]      — remove merged + stale (>30d, no unpushed); .wtkeep skips"
        echo "  proj wt fix-claude-links [--apply] [<project>] — migrate existing worktrees to symlinked .claude/ + CLAUDE.md"
        echo "  proj wt <name>                     — cd to worktree"
        echo ""
        echo "  .wtfiles in repo root: list gitignored paths to share with new worktrees"
        echo "    .env               — symlink (default)"
        echo "    link data/fixtures — explicit symlink"
        echo "    copy config/local  — copy instead (for per-worktree divergence)"
        echo "    claude             — link .claude/ and CLAUDE.md (default for new worktrees)"
        echo "    claude copy        — copy .claude/ and CLAUDE.md instead (per-worktree divergence)"
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

            set -l project_dir "$AION_AUTOPOIESEON/$name"
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
            if not test -d "$AION_AUTOPOIESEON"
                echo "No projects directory: $AION_AUTOPOIESEON"
                return 1
            end
            for dir in $AION_AUTOPOIESEON/*/
                basename $dir
            end

        case new
            if test (count $argv) -ne 1
                echo "proj new <name>"
                return 2
            end
            set -l name $argv[1]
            set -l project_dir "$AION_AUTOPOIESEON/$name"
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
            set -l project_dir "$AION_AUTOPOIESEON/$name"

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

            # Refuse if a previous conversion left a staging directory behind.
            # Manual inspection avoids silently clobbering recovery state.
            set -l leftovers
            for d in $project_dir.converting.*
                test -e "$d"; and set -a leftovers $d
            end
            if test (count $leftovers) -gt 0
                echo "Found leftover staging directories from a previous conversion:"
                for d in $leftovers
                    echo "  $d"
                end
                echo "Inspect and recover (or remove) manually, then re-run."
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

            # Do the conversion through a unique staging directory so concurrent
            # conversions don't collide and a crash leaves a recoverable trail.
            set -l staging (mktemp -d "$project_dir.converting.XXXXXX")
            if test -z "$staging"
                echo "Failed to create staging directory beside $project_dir"
                # Roll back preserved files so the project isn't decapitated.
                for f in $preserve_files
                    mv "$tmp_preserve/$f" "$project_dir/"
                end
                rmdir "$tmp_preserve" 2>/dev/null
                return 1
            end
            mv "$project_dir" "$staging/repo"
            mkdir -p "$project_dir"
            mv "$staging/repo" "$project_dir/base"
            rmdir "$staging" 2>/dev/null

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
            set -l rel (string replace "$AION_AUTOPOIESEON/" '' -- $PWD)
            if test "$rel" = "$PWD"
                echo "Not inside AION_AUTOPOIESEON ($AION_AUTOPOIESEON)"
                return 2
            end
            set -l project (string split '/' -- $rel)[1]
            set -l project_dir "$AION_AUTOPOIESEON/$project"
            set -l base_dir "$project_dir/base"

            if not test -d "$base_dir/.git"
                echo "Base repo not found: $base_dir"
                return 2
            end

            __proj_install_hooks "$base_dir"

        case wt
            # `fix-claude-links` is project-agnostic — handle before PWD-based detection.
            if test (count $argv) -ge 1 -a "$argv[1]" = fix-claude-links
                set -e argv[1]
                set -l apply false
                set -l target_project
                for arg in $argv
                    switch $arg
                        case --apply
                            set apply true
                        case '*'
                            set target_project $arg
                    end
                end

                if test -z "$target_project"
                    if not test -d "$AION_AUTOPOIESEON"
                        echo "No projects directory: $AION_AUTOPOIESEON"
                        return 1
                    end
                    if test "$apply" != true
                        echo "(dry-run; pass --apply to actually change files)"
                    end
                    for dir in $AION_AUTOPOIESEON/*/
                        set -l pdir (string trim --right --chars=/ -- "$dir")
                        # Only new-style projects with a wrapper-level .claude/ or CLAUDE.md.
                        test -d "$pdir/base/.git"; or continue
                        if test -d "$pdir/.claude" -o -f "$pdir/CLAUDE.md"
                            __proj_wt_fix_claude_links_for_project "$pdir" $apply
                        end
                    end
                else
                    set -l pdir "$AION_AUTOPOIESEON/$target_project"
                    if not test -d "$pdir"
                        echo "Project not found: $pdir"
                        return 1
                    end
                    if test "$apply" != true
                        echo "(dry-run; pass --apply to actually change files)"
                    end
                    __proj_wt_fix_claude_links_for_project "$pdir" $apply
                end
                return 0
            end

            # Worktree management — detect project from PWD
            set -l rel (string replace "$AION_AUTOPOIESEON/" '' -- $PWD)
            if test "$rel" = "$PWD"
                echo "Not inside AION_AUTOPOIESEON ($AION_AUTOPOIESEON)"
                return 2
            end
            set -l project (string split '/' -- $rel)[1]
            set -l project_dir "$AION_AUTOPOIESEON/$project"
            set -l base_dir "$project_dir/base"

            if not test -d "$base_dir/.git"
                echo "Base repo not found: $base_dir"
                echo "Run 'proj convert $project' to migrate to new layout first."
                return 2
            end

            if test (count $argv) -lt 1
                echo "Usage:"
                echo "  proj wt add <branch> [--from base] — create worktree (tracks remote if exists)"
                echo "  proj wt fork <branch>              — fork from current worktree"
                echo "  proj wt sync                       — merge upstream into current worktree"
                echo "  proj wt push                       — push current branch to origin"
                echo "  proj wt ls                         — list worktrees"
                echo "  proj wt status                     — show worktrees with PR status"
                echo "  proj wt rm [-f] <name>              — remove worktree and branch"
                echo "  proj wt clean [--age <days>]      — remove merged + stale (>30d, no unpushed); .wtkeep skips"
                echo "  proj wt fix-claude-links [--apply] [<project>] — migrate worktrees to symlinked .claude/ + CLAUDE.md"
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

                    # Default base: branch currently checked out in base/
                    if not set -q base_branch[1]
                        set base_branch (git -C "$base_dir" branch --show-current)
                        if test -z "$base_branch"
                            # Detached HEAD — fall back to origin/HEAD or main/master
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
                    # Seed worktree from .wtfiles manifest (or interactive prompt)
                    __proj_wt_copy_shared "$base_dir" "$wt_path"
                    # Inherit wrapper-level .claude/ and CLAUDE.md (symlinks by default).
                    __proj_wt_link_claude "$project_dir" "$base_dir" "$wt_path"
                    and cd "$wt_path"

                case fork
                    if test (count $argv) -lt 1
                        echo "proj wt fork <branch>"
                        return 2
                    end

                    set -l branch $argv[1]
                    set -l source_commit (git rev-parse HEAD 2>/dev/null)
                    if test -z "$source_commit"
                        echo "Cannot resolve HEAD — are you inside a git worktree?"
                        return 1
                    end

                    set -l dir_name (string replace -a '/' '-' -- $branch)
                    set -l wt_path "$project_dir/$dir_name"

                    if test -d "$wt_path"
                        echo "Directory already exists: $wt_path"
                        return 1
                    end

                    git -C "$base_dir" worktree add -b "$branch" "$wt_path" "$source_commit"
                    or return $status

                    echo "Forked from $(git rev-parse --abbrev-ref HEAD 2>/dev/null; or echo $source_commit) → $wt_path"

                    __proj_wt_copy_shared "$base_dir" "$wt_path"
                    __proj_wt_link_claude "$project_dir" "$base_dir" "$wt_path"
                    and cd "$wt_path"

                case sync
                    # Must be inside a worktree (not base/)
                    set -l current_rel (string replace "$project_dir/" '' -- $PWD)
                    if test "$current_rel" = "base" -o "$current_rel" = "$PWD"
                        echo "Run this from inside a worktree, not base/"
                        return 2
                    end

                    # Detect upstream: tracking branch > nearest remote branch by merge-base
                    set -l upstream
                    set -l tracking (git rev-parse --abbrev-ref '@{upstream}' 2>/dev/null)
                    if test -n "$tracking"
                        set upstream (string replace 'origin/' '' -- $tracking)
                    else
                        set -l best_time 0
                        for ref in (git branch -r --list 'origin/main' 'origin/master' 'origin/release-*' 'origin/develop' 2>/dev/null)
                            set ref (string trim -- $ref)
                            set -l mb (git merge-base HEAD "$ref" 2>/dev/null)
                            test -z "$mb"; and continue
                            set -l mb_time (git log -1 --format=%ct "$mb")
                            if test "$mb_time" -gt "$best_time"
                                set best_time $mb_time
                                set upstream (string replace 'origin/' '' -- $ref)
                            end
                        end
                    end
                    if test -z "$upstream"
                        echo "Cannot detect upstream branch. Set tracking with: git branch -u origin/<branch>"
                        return 1
                    end
                    echo "Upstream: origin/$upstream"

                    # Fetch and merge (fetch in worktree so its tracking refs update)
                    echo "Fetching origin/$upstream..."
                    if not git fetch origin "$upstream"
                        echo "Fetch failed"
                        return 1
                    end

                    echo "Merging origin/$upstream into current branch..."
                    git merge "origin/$upstream" --no-edit --no-verify
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
                    # Parse -f/--force flag
                    set -l force false
                    set -l positional
                    for arg in $argv
                        switch $arg
                            case -f --force
                                set force true
                            case '*'
                                set -a positional $arg
                        end
                    end

                    if test (count $positional) -ne 1
                        echo "proj wt rm [-f] <name>"
                        return 2
                    end

                    # Reverse the slash sanitisation applied by `wt add`/`wt fork`:
                    # accept either the on-disk directory name or the original
                    # branch name (e.g. `feature/login` resolves to `feature-login/`).
                    set -l wt_name (string replace -a '/' '-' -- $positional[1])
                    set -l wt_path "$project_dir/$wt_name"

                    if not test -d "$wt_path"
                        echo "Worktree directory not found: $wt_path"
                        return 1
                    end

                    # Resolve the branch checked out in the worktree
                    set -l wt_branch (git -C "$wt_path" branch --show-current 2>/dev/null)

                    # If we're inside the worktree being removed, cd out first
                    if string match -q "$wt_path*" -- $PWD
                        cd "$project_dir"
                    end

                    if test "$force" = true
                        git -C "$base_dir" worktree remove --force "$wt_path"
                    else
                        # Classify dirty entries: "ours" (managed symlinks from
                        # __proj_wt_link_claude / __proj_wt_copy_shared) can be
                        # cleaned silently; anything else blocks removal until
                        # the user commits, stashes, or re-runs with -f.
                        set -l ours_set (__proj_wt_collect_ours "$base_dir")
                        set -l user_dirty
                        set -l our_files

                        for line in (git -C "$wt_path" status --porcelain=v1 -uall 2>/dev/null)
                            set -l code (string sub --length 2 -- "$line")
                            set -l path (string sub --start 4 -- "$line")

                            if test "$code" = '??'
                                set -l is_ours false
                                for ours in $ours_set
                                    if test "$path" = "$ours"; and test -L "$wt_path/$path"
                                        set is_ours true
                                        break
                                    end
                                end
                                if test "$is_ours" = true
                                    set -a our_files $path
                                else
                                    set -a user_dirty $path
                                end
                            else
                                set -a user_dirty "$code $path"
                            end
                        end

                        if test (count $user_dirty) -gt 0
                            echo "Worktree has uncommitted changes:"
                            for p in $user_dirty
                                echo "  $p"
                            end
                            echo "Commit, stash, or run 'wt rm -f $wt_name' to discard."
                            return 1
                        end

                        for p in $our_files
                            rm -f "$wt_path/$p"
                        end

                        git -C "$base_dir" worktree remove "$wt_path"
                    end
                    or return $status

                    # Delete the local branch after removing the worktree
                    if test -n "$wt_branch"
                        if test "$force" = true
                            git -C "$base_dir" branch -D "$wt_branch" 2>/dev/null
                        else
                            git -C "$base_dir" branch -d "$wt_branch" 2>/dev/null
                        end
                        and echo "Deleted branch $wt_branch"
                        or echo "Branch $wt_branch not deleted (not fully merged). Use -f to force."
                    end

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
                    # Default policy: remove worktrees that are (merged) OR
                    # (no commits in last $age days AND no unpushed work).
                    # `--age 0` disables age-based GC. A `.wtkeep` file at
                    # worktree root unconditionally skips the worktree.
                    set -l age 30
                    set -l i 1
                    while test $i -le (count $argv)
                        switch $argv[$i]
                            case --age
                                set age $argv[(math $i + 1)]
                                set i (math $i + 2)
                            case '*'
                                echo "Unknown flag: $argv[$i]"
                                echo "Usage: proj wt clean [--age <days>]"
                                return 2
                        end
                    end
                    if not string match -qr '^\d+$' -- "$age"
                        echo "--age must be a non-negative integer"
                        return 2
                    end

                    if test "$age" -eq 0
                        echo "Cleaning merged worktrees..."
                    else
                        echo "Cleaning merged + stale (>$age days, no unpushed) worktrees..."
                    end

                    set -l removed 0
                    set -l now (date +%s)
                    set -l age_seconds (math "$age * 86400")
                    set -l merged_list (git -C "$base_dir" branch --merged 2>/dev/null | string trim)

                    for line in (git -C "$base_dir" worktree list | tail -n +2)
                        set -l wt (echo $line | awk '{print $1}')
                        test "$wt" = "$base_dir"; and continue

                        if test -e "$wt/.wtkeep"
                            echo "  Skipping (.wtkeep): $wt"
                            continue
                        end

                        set -l br (git -C "$wt" branch --show-current 2>/dev/null)
                        test -z "$br"; and continue

                        set -l reason
                        if contains -- "$br" $merged_list
                            set reason merged
                        else if test "$age" -gt 0
                            set -l last_ts (git -C "$wt" log -1 --format=%ct HEAD 2>/dev/null)
                            if test -n "$last_ts"; and test (math "$now - $last_ts") -gt "$age_seconds"
                                # Require an upstream AND no unpushed commits.
                                # Missing upstream → keep (could be local-only WIP).
                                set -l upstream (git -C "$wt" rev-parse --abbrev-ref '@{u}' 2>/dev/null)
                                if test -n "$upstream"
                                    set -l unpushed (git -C "$wt" rev-list --count '@{u}..HEAD' 2>/dev/null)
                                    if test -n "$unpushed"; and test "$unpushed" -eq 0
                                        set reason "stale ($age+ days, no unpushed)"
                                    end
                                end
                            end
                        end

                        if test -n "$reason"
                            echo "  Removing ($reason): $wt ($br)"
                            git -C "$base_dir" worktree remove "$wt" 2>/dev/null; or true
                            git -C "$base_dir" branch -d "$br" 2>/dev/null; or true
                            set removed (math $removed + 1)
                        end
                    end

                    git -C "$base_dir" worktree prune
                    echo "Done. Removed $removed worktree(s)."

                case '*'
                    # Bare name → cd to worktree directory. Mirror the slash
                    # sanitisation from `wt add` so `wt feature/login` resolves.
                    set -l wt_name (string replace -a '/' '-' -- $wt_cmd)
                    set -l wt_path "$project_dir/$wt_name"
                    if test -d "$wt_path"
                        cd "$wt_path"
                    else
                        echo "Worktree not found: $wt_path"
                        return 1
                    end
            end

        case '*'
            # Bare name → cd shortcut
            set -l target "$AION_AUTOPOIESEON/$cmd"
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
