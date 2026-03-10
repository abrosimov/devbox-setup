# Completions for kpf (port-forward registry) function
complete -c kpf -f

# Helper: extract env names from registry
function __kpf_envs
    functions -q _kpf_registry; or return
    _kpf_registry 2>/dev/null | string split \n | string replace -r '\s+.*' ''  | sort -u
end

# Helper: extract service names for a given env
function __kpf_services
    functions -q _kpf_registry; or return
    set -l tokens (commandline -opc)
    if test (count $tokens) -ge 2
        set -l env $tokens[2]
        _kpf_registry 2>/dev/null | string split \n | string match "$env *" | string replace -r '^\S+\s+' '' | sort -u
    end
end

# Subcommands
complete -c kpf -n '__fish_use_subcommand' -a list -d 'Show all registered env x service combos'

# Env names
complete -c kpf -n '__fish_use_subcommand' -a '(__kpf_envs)'

# Service names for selected env
complete -c kpf -n 'not __fish_use_subcommand; and test (count (commandline -opc)) -eq 2' -a '(__kpf_services)'

# --info flag
complete -c kpf -n 'test (count (commandline -opc)) -ge 3' -l info -d 'Dry-run: show what would be executed'
