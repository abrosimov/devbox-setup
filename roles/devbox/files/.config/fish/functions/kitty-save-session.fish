function kitty-save-session --description 'Snapshot focused kitty OS window to ~/.config/kitty/last-session.conf for restore on next launch'
    set -l outfile $HOME/.config/kitty/last-session.conf

    # `allow_remote_control yes` must be set in kitty.conf, otherwise `kitty @
    # ls` exits with an error and we'd overwrite the snapshot with garbage.
    set -l raw (kitty @ ls 2>/dev/null)
    if test $status -ne 0
        echo "kitty-save-session: 'kitty @ ls' failed — is allow_remote_control = yes in kitty.conf?" >&2
        return 1
    end

    # Render the first (focused) OS window as a kitty session file. Each tab
    # becomes a `new_tab` block with a `launch` that restores cwd. Running
    # processes are NOT relaunched — only the layout + per-tab cwd survives.
    # This is intentionally minimal (R1); upgrade to tmux/zellij if true
    # per-process persistence becomes a requirement.
    printf '%s\n' $raw | jq -r '
        (.[] | select(.is_focused) // .[0]).tabs[] |
        "new_tab " + (.title // "shell") + "\n" +
        "launch --cwd " + ((.windows[0].cwd // env.HOME) | @sh) + " fish\n"
    ' >$outfile

    set -l count (printf '%s\n' $raw | jq -r '(.[] | select(.is_focused) // .[0]).tabs | length')
    echo "Saved $count tab(s) to $outfile"
end
