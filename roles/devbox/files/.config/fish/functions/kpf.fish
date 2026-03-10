function kpf --description "Port-forward to registered k8s services; data comes from _kpf_registry"
    if test (count $argv) -lt 1
        echo "Usage:"
        echo "  kpf <env> <service>         — port-forward to a registered service"
        echo "  kpf <env> <service> --info   — dry-run: show what would be executed"
        echo "  kpf list                     — show all registered env×service combos"
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
    if test (count $argv) -ge 3; and test "$argv[3]" = "--info"
        set info_only true
    end

    set -l result (_kpf_registry $env $svc)
    if test $status -ne 0
        echo "kpf: unknown combo '$env:$svc'. Run 'kpf list' to see available entries."
        return 1
    end

    set -l parts (string split ' ' -- $result)
    if test (count $parts) -ne 5
        echo "kpf: _kpf_registry returned invalid format (expected: kubeconfig ns pod local_port remote_port)"
        echo "Got: $result"
        return 1
    end

    set -l kubeconfig $parts[1]
    set -l ns $parts[2]
    set -l pod $parts[3]
    set -l local_port $parts[4]
    set -l remote_port $parts[5]

    if not test -f "$kubeconfig"
        echo "kpf: kubeconfig not found: $kubeconfig"
        return 1
    end

    echo "Forwarding localhost:$local_port → pod/$pod:$remote_port (env: $env, ns: $ns)"

    if $info_only
        echo "kubectl -n $ns port-forward pod/$pod $local_port:$remote_port"
        return 0
    end

    env KUBECONFIG=$kubeconfig kubectl -n $ns port-forward pod/$pod $local_port:$remote_port
end
