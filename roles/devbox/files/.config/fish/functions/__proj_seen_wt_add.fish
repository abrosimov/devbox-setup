function __proj_seen_wt_add
    set -l cmd (commandline -opc)
    test (count $cmd) -ge 3; and test "$cmd[2]" = wt; and test "$cmd[3]" = add
end
