# fish_greeting.fish — report an open pub lease at the top of a new shell.
#
# fish calls this only for interactive shells, so it carries no `status
# --is-interactive` guard of its own. It reads ~/.local/state/pub-lease/lease.json
# directly and deliberately never runs `pub-lease status` or `warp-cli`: `status`
# probes the WARP daemon twice before it looks at the lease, which is far too much
# for a line printed on every shell.
function fish_greeting --description "Greeting, plus a line naming the pub lease phase when one exists"
    # Overriding fish's own fish_greeting takes the $fish_greeting variable with it. config.fish
    # empties that variable, but honouring it keeps a machine-local greeting working.
    if set -q fish_greeting[1]
        echo $fish_greeting
    end

    set -l state_dir $PUB_LEASE_STATE_DIR
    test -n "$state_dir"; or set state_dir $HOME/.local/state/pub-lease
    set -l lease "$state_dir/lease.json"
    test -f "$lease"; or return 0

    # The file also exists while restoring, after a failed restore, mid-activation, when the
    # metadata is corrupt, and between expiry and the next reconcile — so its presence is reported
    # as the phase it actually records, never as "the tunnel is on".
    set -l phase (string match -rg '^\s*"phase"\s*:\s*"(activating|active|restoring)",?\s*$' <"$lease")
    if test (count $phase) -ne 1
        echo "pub lease: metadata present but unreadable"
        return 0
    end

    switch $phase[1]
        case activating
            echo "pub lease: activating"
            return 0
        case restoring
            echo "pub lease: restoring the previous WARP state"
            return 0
    end

    set -l expires (string match -rg '^\s*"expires_at"\s*:\s*([0-9]+)(?:\.[0-9]+)?,?\s*$' <"$lease")
    if test (count $expires) -ne 1
        echo "pub lease: metadata present but unreadable"
        return 0
    end

    # The only external command in this file, and the only branch that needs one: fish has no
    # builtin clock. A greeting must never be able to error, so an unreadable one says nothing.
    set -l now (command date +%s 2>/dev/null)
    set -q now[1]; or return 0

    set -l remaining (math "$expires[1] - $now")
    if test $remaining -le 0
        echo "pub lease: expired, awaiting the reconciler"
        return 0
    end
    printf 'pub lease: active, %dh%02dm remaining\n' (math -s0 "floor($remaining / 3600)") (math -s0 "floor($remaining % 3600 / 60)")
end
