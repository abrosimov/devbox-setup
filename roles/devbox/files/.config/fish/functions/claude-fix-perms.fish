function claude-fix-perms --description "Ensure .claude/settings.local.json has defaultMode: acceptEdits"
    set -l file .claude/settings.local.json

    if not test -f $file
        echo "No $file found — nothing to fix"
        return 0
    end

    if jq -e '.permissions.defaultMode' $file >/dev/null 2>&1
        set -l mode (jq -r '.permissions.defaultMode' $file)
        echo "defaultMode already set: $mode"
        return 0
    end

    jq '.permissions.defaultMode = "acceptEdits"' $file >$file.tmp
    and mv $file.tmp $file
    and echo "Injected defaultMode: acceptEdits into $file"
    or begin
        rm -f $file.tmp
        echo "Failed to update $file"
        return 1
    end
end
