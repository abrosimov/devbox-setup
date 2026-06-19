# Completions for kaws (multi-cluster AWS+EKS wrapper)
complete -c kaws -f

function __kaws_envs
    set -l config_file ~/.config/kaws/clusters.yaml
    test -f $config_file; or return
    yq '.envs | keys | .[]' $config_file 2>/dev/null
end

# Arg 1: env name (or `list-envs`)
complete -c kaws -n '__fish_use_subcommand' -a '(__kaws_envs)' -d env
complete -c kaws -n '__fish_use_subcommand' -a list-envs -d 'List known envs'

# Arg 2: subcommand (only when arg 1 is a real env, not list-envs)
set -l __kaws_arg2 '__fish_seen_subcommand_from (__kaws_envs); and test (count (commandline -opc)) -eq 2'
complete -c kaws -n "$__kaws_arg2" -a login    -d 'aws sso login for this env'
complete -c kaws -n "$__kaws_arg2" -a whoami   -d 'aws sts get-caller-identity'
complete -c kaws -n "$__kaws_arg2" -a clusters -d 'List EKS clusters in env region'
complete -c kaws -n "$__kaws_arg2" -a refresh  -d 'Regenerate kubeconfig with --profile fix'

# After env + a non-builtin subcommand, delegate to k completions implicitly
# (fish stops here; k.fish has its own completion table when invoked).
