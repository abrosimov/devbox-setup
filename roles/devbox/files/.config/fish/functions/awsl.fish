function awsl --description "AWS SSO login by kaws env. Usage: awsl [<env>]"
    set -l config_file ~/.config/kaws/clusters.yaml

    if not test -f $config_file
        echo "awsl: $config_file not found" >&2
        return 1
    end

    set -l env
    if test (count $argv) -ge 1
        set env $argv[1]
    else
        set env (yq '.envs | keys | .[]' $config_file | \
            fzf --header="Select env to log in to" --height=40% --reverse)
        if test -z "$env"
            return 1
        end
    end

    set -l profile (env ENV=$env yq '.envs[strenv(ENV)].profile // ""' $config_file)
    if test -z "$profile"
        echo "awsl: env '$env' not found in $config_file" >&2
        echo "Available envs:" >&2
        yq '.envs | keys | .[]' $config_file >&2
        return 1
    end

    aws --profile $profile sso login
end
