function kpf --description "Port-forward to registered k8s services (kaws-aware; prints Mongo URI)"
    if test (count $argv) -lt 1
        echo "Usage:"
        echo "  kpf <env> <service>              — port-forward to a registered service"
        echo "  kpf <env> <service> --info       — dry-run: show what would be executed"
        echo "  kpf <env> <service> --no-creds   — skip fetching MongoDB credentials"
        echo "  kpf list                          — show all registered env×service combos"
        echo ""
        echo "Registry: define _kpf_registry.fish (see _kpf_registry.fish.example)"
        return 2
    end

    if not functions -q _kpf_registry
        echo "kpf: _kpf_registry function not found."
        echo "Copy _kpf_registry.fish.example to _kpf_registry.fish and fill in your values."
        return 2
    end

    set -l cmd $argv[1]

    if test "$cmd" = list
        echo "Registered services:"
        _kpf_registry
        return $status
    end

    if test (count $argv) -lt 2
        echo "kpf <env> <service>"
        return 2
    end

    set -l env $argv[1]
    set -l svc $argv[2]
    set -l info_only false
    set -l no_creds false
    for flag in $argv[3..-1]
        switch $flag
            case --info
                set info_only true
            case --no-creds
                set no_creds true
            case '*'
                echo "kpf: unknown flag '$flag'" >&2
                return 2
        end
    end

    set -l result (_kpf_registry $env $svc)
    if test $status -ne 0
        echo "kpf: unknown combo '$env:$svc'. Run 'kpf list' to see available entries."
        return 1
    end

    set -l parts (string split ' ' -- $result)
    if test (count $parts) -ne 5
        echo "kpf: _kpf_registry returned invalid format (expected 5 fields: kubeconfig|- ns kind/name local remote)"
        echo "Got: $result"
        return 1
    end

    set -l kubeconfig_field $parts[1]
    set -l ns               $parts[2]
    set -l resource         $parts[3]
    set -l local_port       $parts[4]
    set -l remote_port      $parts[5]

    set -l resource_parts (string split '/' -- $resource)
    if test (count $resource_parts) -ne 2
        echo "kpf: field 3 must be '<kind>/<name>' (e.g. pod/mongodb-0), got: $resource"
        return 1
    end
    set -l kind $resource_parts[1]
    set -l name $resource_parts[2]

    # Backend selection: "-" in field 1 means "resolve via kaws"; anything else is
    # a literal kubeconfig path (legacy direct-kubectl path).
    set -l use_kaws false
    set -l kubeconfig $kubeconfig_field
    if test "$kubeconfig_field" = "-"
        set use_kaws true
        set kubeconfig (env ENV=$env yq '.envs[strenv(ENV)].kubeconfig // ""' ~/.config/kaws/clusters.yaml 2>/dev/null)
        if test -z "$kubeconfig"
            echo "kpf: env '$env' is not defined in ~/.config/kaws/clusters.yaml (registry uses '-' sentinel)" >&2
            return 1
        end
        set kubeconfig (string replace -r '^~' -- "$HOME" $kubeconfig)
    end

    if not $info_only; and not test -f "$kubeconfig"
        echo "kpf: kubeconfig not found: $kubeconfig" >&2
        if $use_kaws
            echo "     Run: kaws $env refresh   (regenerate kubeconfig via aws eks update-kubeconfig)" >&2
        end
        return 1
    end

    # Bitnami MongoDB chart convention: secret `mongodb`, key `mongodb-root-password`, user `root`.
    # Fetch before port-forward starts (kubectl port-forward is blocking).
    set -l uri ""
    if test "$svc" = "mongo"; and not $no_creds
        if $info_only
            set uri "mongodb://root:<REDACTED>@localhost:$local_port/?authSource=admin"
        else
            set -l pw
            if $use_kaws
                set pw (kaws $env raw -n $ns get secret mongodb -o jsonpath='{.data.mongodb-root-password}' | base64 --decode)
            else
                set pw (env KUBECONFIG=$kubeconfig kubectl -n $ns get secret mongodb -o jsonpath='{.data.mongodb-root-password}' | base64 --decode)
            end
            if test -z "$pw"
                echo "kpf: could not read secret mongodb/mongodb-root-password in ns=$ns (continuing without URI)" >&2
            else
                set -l pw_esc (jq -rn --arg s "$pw" '$s | @uri')
                set uri "mongodb://root:$pw_esc@localhost:$local_port/?authSource=admin"
            end
        end
    end

    if test -n "$uri"
        echo $uri
    end

    if $info_only
        if $use_kaws
            echo "kaws $env pf $kind $ns $name $local_port:$remote_port"
        else
            echo "env KUBECONFIG=$kubeconfig kubectl -n $ns port-forward $kind/$name $local_port:$remote_port"
        end
        return 0
    end

    echo "Forwarding localhost:$local_port → $kind/$name:$remote_port (env: $env, ns: $ns)"

    if $use_kaws
        kaws $env pf $kind $ns $name $local_port:$remote_port
    else
        env KUBECONFIG=$kubeconfig kubectl -n $ns port-forward $kind/$name $local_port:$remote_port
    end
end
