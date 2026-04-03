# Completions for kms (kube mongo shell) function
complete -c kms -f

# Helper: extract envs that have mongo registered
function __kms_envs
    functions -q _kpf_registry; or return
    _kpf_registry 2>/dev/null | string split \n | string match '* mongo' | string replace -r '\s+.*' '' | sort -u
end

# Env names
complete -c kms -n '__fish_use_subcommand' -a '(__kms_envs)'

# --info flag
complete -c kms -n 'test (count (commandline -opc)) -ge 2' -l info -d 'Dry-run: show what would be executed'
