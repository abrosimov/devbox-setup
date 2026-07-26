function _tide_item_narrative_drift
    # Show Narrative-doc drift badge when in devbox-setup repo and drift > 0.
    # Background refresh is fired by _tide_item_fpf_drift (a single script call
    # refreshes both docs), so this item only reads state — never double-fires.

    set -l repo_root (git rev-parse --show-toplevel 2>/dev/null); or return
    test -f "$repo_root/roles/devbox/files/dot_claude/docs/Narrativization-and-Narrative-Studies-Principles-Framework.md"; or return

    set -l cache_dir (set -q XDG_CACHE_HOME; and echo $XDG_CACHE_HOME; or echo $HOME/.cache)
    set -l state_file $cache_dir/devbox-setup/narrative-drift
    test -f "$state_file"; or return

    set -l drift (cat "$state_file" 2>/dev/null)
    string match -qr '^[0-9]+$' -- $drift; or return
    test $drift -gt 0; or return

    _tide_print_item narrative_drift "NAR Δ$drift"
end
