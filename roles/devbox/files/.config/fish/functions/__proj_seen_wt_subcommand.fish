function __proj_seen_wt_subcommand
    set -l cmd (commandline -opc)
    test (count $cmd) -ge 3; and test "$cmd[2]" = wt; and contains -- "$cmd[3]" add fork rm ls sync push
end
