function kitty-save-session --description 'Snapshot focused kitty OS window to ~/.config/kitty/last-session.conf for restore on next launch'
    # Runs under kitty's bundled interpreter, so no system Python is needed. The
    # snapshot logic lives in kitty_session.py because the Cmd+Q kitten reuses it.
    kitty +launch $HOME/.config/kitty/kitty_session.py
end
