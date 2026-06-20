function _tide_item_fpf_drift
    # Show FPF drift badge when in devbox-setup repo and upstream drift > 0.
    # Background refresh (~weekly TTL) handled by bin/fpf-drift-check itself.

    set -l repo_root (git rev-parse --show-toplevel 2>/dev/null); or return
    test -f "$repo_root/roles/devbox/files/dot_claude/docs/FPF-Spec.md"; or return

    # Fire background refresh; never block the prompt.
    fish -c "$HOME/.claude/bin/fpf-drift-check >/dev/null 2>&1 &" >/dev/null 2>&1 &
    disown 2>/dev/null

    set -l cache_dir (set -q XDG_CACHE_HOME; and echo $XDG_CACHE_HOME; or echo $HOME/.cache)
    set -l state_file $cache_dir/devbox-setup/fpf-drift
    test -f "$state_file"; or return

    set -l drift (cat "$state_file" 2>/dev/null)
    string match -qr '^[0-9]+$' -- $drift; or return
    test $drift -gt 0; or return

    _tide_print_item fpf_drift "FPF Δ$drift"
end
