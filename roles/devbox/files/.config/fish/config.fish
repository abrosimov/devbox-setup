if status is-interactive
    # Commands to run in interactive sessions can go here
end

#fish_ssh_agent

test -r '$HOME/.opam/opam-init/init.fish' && source $HOME/.opam/opam-init/init.fish > /dev/null 2> /dev/null; or true
