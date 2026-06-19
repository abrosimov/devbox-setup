# Completions for awsl (AWS SSO login by kaws env)
complete -c awsl -f

function __awsl_envs
    set -l config_file ~/.config/kaws/clusters.yaml
    test -f $config_file; or return
    yq '.envs | keys | .[]' $config_file 2>/dev/null
end

complete -c awsl -n '__fish_use_subcommand' -a '(__awsl_envs)' -d env
