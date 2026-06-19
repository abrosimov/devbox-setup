function kaws --description "Multi-cluster AWS+EKS wrapper. Usage: kaws <env> [subcmd] [args...]"
    set -l config_file ~/.config/kaws/clusters.yaml

    if test (count $argv) -eq 0
        echo "Usage: kaws <env> [subcmd] [args...]"
        echo "       kaws list-envs"
        echo ""
        echo "Subcommands per env:"
        echo "  login       — aws sso login (for the env's profile)"
        echo "  whoami      — aws sts get-caller-identity"
        echo "  clusters    — list EKS clusters in the env's region"
        echo "  refresh     — regenerate kubeconfig + apply --profile fix"
        echo "  <other>     — delegated to k (see `k` for full help)"
        echo ""
        echo "See also: awsl [<env>]  — top-level shortcut for SSO login"
        echo "Config: $config_file"
        return 2
    end

    if test "$argv[1]" = list-envs
        if not test -f $config_file
            echo "kaws: $config_file not found" >&2
            return 1
        end
        yq '.envs | keys | .[]' $config_file
        return 0
    end

    if not test -f $config_file
        echo "kaws: config $config_file not found" >&2
        return 1
    end

    set -l env $argv[1]
    set -e argv[1]

    set -l profile    (env ENV=$env yq '.envs[strenv(ENV)].profile    // ""' $config_file)
    set -l cluster    (env ENV=$env yq '.envs[strenv(ENV)].cluster    // ""' $config_file)
    set -l region     (env ENV=$env yq '.envs[strenv(ENV)].region     // ""' $config_file)
    set -l kubeconfig (env ENV=$env yq '.envs[strenv(ENV)].kubeconfig // ""' $config_file)

    if test -z "$profile"
        echo "kaws: env '$env' not found in $config_file" >&2
        echo "Available envs:" >&2
        yq '.envs | keys | .[]' $config_file >&2
        return 1
    end

    # Expand leading ~ in the kubeconfig path; YAML strings don't auto-expand.
    set kubeconfig (string replace -r '^~' -- "$HOME" $kubeconfig)
    set -lx KUBECONFIG $kubeconfig

    # SSO-bypassing subcommands first: login can't pre-flight (chicken-and-egg),
    # whoami IS the check (its own error is clear enough).
    switch "$argv[1]"
        case login
            aws --profile $profile sso login
            return $status

        case whoami
            aws --profile $profile sts get-caller-identity
            return $status
    end

    # Everything below needs a live SSO session. Without this guard, kubectl's
    # `aws eks get-token` exec-credential plugin blocks 30-120s on expired SSO
    # instead of failing fast. The STS probe is ~250ms on success; on expiry it
    # bails inside the --cli-*-timeout budget.
    if not aws --profile $profile sts get-caller-identity \
            --output text --query Account \
            --cli-connect-timeout 3 --cli-read-timeout 5 \
            >/dev/null 2>&1
        echo "kaws: SSO session for profile '$profile' is missing or expired." >&2
        echo "      Run: awsl $env   (or: kaws $env login)" >&2
        return 1
    end

    switch "$argv[1]"
        case clusters
            aws --profile $profile eks list-clusters --region $region
            return $status

        case refresh
            mkdir -p (dirname $kubeconfig)
            aws --profile $profile eks update-kubeconfig \
                --name $cluster --region $region \
                --alias $env --kubeconfig $kubeconfig
            or return $status
            # aws-cli writes the profile into `env: AWS_PROFILE=...` which loses
            # to any AWS_* env vars in the parent shell. Move it into `args:` so
            # CLI-arg precedence wins. See aws/aws-cli#7794.
            env PROFILE=$profile yq -i '
                .users[].user.exec.args += ["--profile", strenv(PROFILE)]
                | del(.users[].user.exec.env)
            ' $kubeconfig
            echo "Refreshed $kubeconfig (env=$env, profile=$profile, cluster=$cluster)"
            return 0
    end

    k $argv
end
