if status is-interactive
    set -g fish_greeting

    if type -q eza
        alias ls 'eza --group-directories-first'
        alias ll 'eza -l --group-directories-first --git'
        alias la 'eza -la --group-directories-first --git'
        alias tree 'eza --tree --level=3'
    end
end

#fish_ssh_agent

test -r "$HOME/.opam/opam-init/init.fish" && source "$HOME/.opam/opam-init/init.fish" >/dev/null 2>/dev/null; or true
