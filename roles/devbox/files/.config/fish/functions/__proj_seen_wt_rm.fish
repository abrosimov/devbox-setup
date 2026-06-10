function __proj_seen_wt_rm
    set -l cmd (commandline -opc)
    test (count $cmd) -ge 3; and test "$cmd[2]" = wt; and test "$cmd[3]" = rm
end
