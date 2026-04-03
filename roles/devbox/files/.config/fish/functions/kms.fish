function kms --description "Open mongosh on a registered k8s mongo pod"
    if test (count $argv) -lt 1
        echo "Usage:"
        echo "  kms <env>          — open mongosh on the mongo pod"
        echo "  kms <env> --info   — dry-run: show what would be executed"
        echo ""
        echo "Environments: run 'kpf list' to see registered services"
        return 2
    end

    if not functions -q _kpf_registry
        echo "kms: _kpf_registry function not found."
        echo "Copy _kpf_registry.fish.example to _kpf_registry.fish and fill in your values."
        return 2
    end

    set -l env $argv[1]
    set -l info_only false
    if test (count $argv) -ge 2; and test "$argv[2]" = "--info"
        set info_only true
    end

    set -l result (_kpf_registry $env mongo)
    if test $status -ne 0
        echo "kms: no mongo registered for env '$env'. Run 'kpf list' to see available entries."
        return 1
    end

    set -l parts (string split ' ' -- $result)
    set -l kubeconfig $parts[1]
    set -l ns $parts[2]
    set -l pod $parts[3]

    if not test -f "$kubeconfig"
        echo "kms: kubeconfig not found: $kubeconfig"
        return 1
    end

    echo "Opening mongosh on pod/$pod (env: $env, ns: $ns)"

    if $info_only
        echo "KUBECONFIG=$kubeconfig kubectl -n $ns exec -it pod/$pod -- mongosh"
        return 0
    end

    env KUBECONFIG=$kubeconfig kubectl -n $ns exec -it pod/$pod -- mongosh
end
