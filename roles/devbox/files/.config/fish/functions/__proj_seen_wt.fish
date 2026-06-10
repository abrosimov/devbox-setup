function __proj_seen_wt
    set -l cmd (commandline -opc)
    test (count $cmd) -ge 2; and test "$cmd[2]" = wt
end
