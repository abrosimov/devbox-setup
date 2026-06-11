function gctx --description "Switch active gcx (Grafana CLI) context; kubectx-style helper"
    if not command -q gcx
        echo "gctx: gcx is not installed. Run `make personal` or `make work` to install it." >&2
        return 127
    end

    set -l state_dir
    if set -q XDG_STATE_HOME
        set state_dir $XDG_STATE_HOME
    else
        set state_dir $HOME/.local/state
    end
    set -l prev_file $state_dir/gcx-prev

    # No args: fzf picker over contexts; current is marked.
    if test (count $argv) -eq 0
        if not command -q fzf
            echo "gctx: fzf is not installed; pass a context name explicitly." >&2
            return 127
        end

        set -l current (gcx config current-context 2>/dev/null)
        set -l contexts (gcx config list-contexts 2>/dev/null)
        if test -z "$contexts"
            echo "gctx: no contexts found. Run `gcx login <name> --server <url>` first." >&2
            return 1
        end

        set -l selected (printf '%s\n' $contexts | fzf \
            --header="Select gcx context (current: $current)" \
            --preview="gcx --context {} config check 2>&1 | head -30" \
            --preview-window=right:50%:wrap)

        if test -z "$selected"
            return 1
        end

        __gctx_switch_to $selected $current $prev_file
        return $status
    end

    set -l target $argv[1]

    # Toggle: switch to previous context.
    if test "$target" = "-"
        if not test -f $prev_file
            echo "gctx: no previous context recorded." >&2
            return 1
        end
        set target (cat $prev_file)
        if test -z "$target"
            echo "gctx: previous-context file is empty." >&2
            return 1
        end
    end

    set -l current (gcx config current-context 2>/dev/null)
    __gctx_switch_to $target $current $prev_file
end

function __gctx_switch_to --argument-names target current prev_file
    if test "$target" = "$current"
        echo "gctx: already on $target"
        return 0
    end

    if not gcx config use-context $target
        return $status
    end

    if test -n "$current"
        mkdir -p (dirname $prev_file)
        echo $current >$prev_file
    end
    echo "gctx: switched to $target (prev: $current)"
end
