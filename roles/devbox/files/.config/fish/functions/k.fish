function k --description "kubectl helper; expects KUBECONFIG to be set by wrapper (kstg/kprd/...)"
    if not set -q KUBECONFIG
        echo "KUBECONFIG is not set. Use a wrapper like: kstg ..., kprd ..."
        return 2
    end

    if test (count $argv) -lt 1
        echo "Usage:"
        echo "  k ctx                                  — show current context and KUBECONFIG"
        echo "  k ns                                   — list all namespaces"
        echo "  k pods <ns> [label-selector]           — list pods"
        echo "  k containers <ns> <pod>                — list containers in pod"
        echo "  k images <ns> <pod>                    — show container images"
        echo "  k ports <ns> <pod>                     — show container ports"
        echo "  k describe <ns> <kind> <name>          — describe resource (pod, svc, deploy, ...)"
        echo "  k events <ns> [--watch]                — show events in namespace"
        echo "  k exec <ns> <pod> [-c container] [cmd] — exec into pod (default: sh)"
        echo "  k logs <ns> <pod> [-c container] [--since 10m] [--tail 200] [-f] [--previous]"
        echo "  k logs-rand <ns> <label-selector> [-c container] [--since 10m] [--tail 200] [-f] [--previous]"
        echo "  k logs-label <ns> <label-selector> [pod-index] [-c container] [--since 10m] [--tail 200] [-f] [--previous]"
        echo "  k pf pod <ns> <pod> <port|local:remote> — port-forward to pod"
        echo "  k pf svc <ns> <svc> <port|local:remote> — port-forward to service"
        echo "  k debug <ns> <pod> [--target container] [--image nicolaka/netshoot]"
        echo "  k raw <any kubectl args...>            — passthrough to kubectl"
        return 2
    end

    set -l cmd $argv[1]
    set -e argv[1]

    switch $cmd
        case ctx
            echo "KUBECONFIG: $KUBECONFIG"
            env KUBECONFIG=$KUBECONFIG kubectl config current-context

        case ns
            env KUBECONFIG=$KUBECONFIG kubectl get namespaces

        case pods
            if test (count $argv) -lt 1
                echo "k pods <ns> [label-selector]"
                return 2
            end
            set -l ns $argv[1]
            set -e argv[1]
            if test (count $argv) -ge 1
                set -l sel $argv[1]
                env KUBECONFIG=$KUBECONFIG kubectl -n $ns get pods -o wide -l $sel
            else
                env KUBECONFIG=$KUBECONFIG kubectl -n $ns get pods -o wide
            end

        case containers
            if test (count $argv) -ne 2
                echo "k containers <ns> <pod>"
                return 2
            end
            set -l ns $argv[1]
            set -l pod $argv[2]
            env KUBECONFIG=$KUBECONFIG kubectl -n $ns get pod $pod -o jsonpath='{range .spec.initContainers[*]}init:{.name}{"\n"}{end}{range .spec.containers[*]}container:{.name}{"\n"}{end}'

        case images
            if test (count $argv) -ne 2
                echo "k images <ns> <pod>"
                return 2
            end
            set -l ns $argv[1]
            set -l pod $argv[2]
            env KUBECONFIG=$KUBECONFIG kubectl -n $ns get pod $pod -o jsonpath='{range .spec.containers[*]}{.name}{": "}{.image}{"\n"}{end}'

        case ports
            if test (count $argv) -ne 2
                echo "k ports <ns> <pod>"
                return 2
            end
            set -l ns $argv[1]
            set -l pod $argv[2]
            env KUBECONFIG=$KUBECONFIG kubectl -n $ns get pod $pod -o jsonpath='{range .spec.containers[*]}{.name}{": "}{range .ports[*]}{.containerPort} {end}{"\n"}{end}'

        case describe
            if test (count $argv) -lt 3
                echo "k describe <ns> <kind> <name>"
                echo "  kind: pod, svc, deploy, sts, ds, cm, secret, ing, pvc, ..."
                return 2
            end
            set -l ns $argv[1]
            set -l kind $argv[2]
            set -l name $argv[3]
            env KUBECONFIG=$KUBECONFIG kubectl -n $ns describe $kind $name

        case events
            if test (count $argv) -lt 1
                echo "k events <ns> [--watch]"
                return 2
            end
            set -l ns $argv[1]
            set -e argv[1]
            set -l watch_flag ""
            if test (count $argv) -ge 1; and test "$argv[1]" = "--watch"
                set watch_flag "--watch"
            end
            if test -n "$watch_flag"
                env KUBECONFIG=$KUBECONFIG kubectl -n $ns get events --sort-by='.lastTimestamp' $watch_flag
            else
                env KUBECONFIG=$KUBECONFIG kubectl -n $ns get events --sort-by='.lastTimestamp'
            end

        case exec
            if test (count $argv) -lt 2
                echo "k exec <ns> <pod> [-c container] [cmd]"
                return 2
            end
            set -l ns $argv[1]
            set -l pod $argv[2]
            set -e argv[1..2]

            set -l container ""
            set -l cmd_to_run sh

            set -l i 1
            while test $i -le (count $argv)
                set -l a $argv[$i]
                switch $a
                    case -c
                        set container $argv[(math $i + 1)]
                        set i (math $i + 2)
                        continue
                    case '*'
                        # Remaining args are the command
                        set cmd_to_run $argv[$i..-1]
                        break
                end
            end

            if test -n "$container"
                env KUBECONFIG=$KUBECONFIG kubectl -n $ns exec -it $pod -c $container -- $cmd_to_run
            else
                env KUBECONFIG=$KUBECONFIG kubectl -n $ns exec -it $pod -- $cmd_to_run
            end

        case logs
            if test (count $argv) -lt 2
                echo "k logs <ns> <pod> [-c container] [--since 10m] [--tail 200] [-f] [--previous]"
                return 2
            end

            set -l ns $argv[1]
            set -l pod $argv[2]
            set -e argv[1..2]

            set -l args
            set -l tail_set false
            set -l i 1
            while test $i -le (count $argv)
                set -l a $argv[$i]
                switch $a
                    case -c
                        set -l c $argv[(math $i + 1)]
                        set args $args -c $c
                        set i (math $i + 2)
                        continue
                    case --since
                        set -l s $argv[(math $i + 1)]
                        set args $args --since=$s
                        set i (math $i + 2)
                        continue
                    case --tail
                        set -l t $argv[(math $i + 1)]
                        set args $args --tail=$t
                        set tail_set true
                        set i (math $i + 2)
                        continue
                    case -f
                        set args $args -f
                        set i (math $i + 1)
                        continue
                    case --previous
                        set args $args --previous
                        set i (math $i + 1)
                        continue
                    case '*'
                        set args $args $a
                        set i (math $i + 1)
                        continue
                end
            end

            # Apply default --tail if not explicitly set
            if not $tail_set
                set args $args --tail=200
            end

            env KUBECONFIG=$KUBECONFIG kubectl -n $ns logs $pod $args

        case logs-rand
            if test (count $argv) -lt 2
                echo "k logs-rand <ns> <label-selector> [-c container] [--since 10m] [--tail 200] [-f] [--previous]"
                return 2
            end

            set -l ns $argv[1]
            set -l sel $argv[2]
            set -e argv[1..2]

            set -l pods (env KUBECONFIG=$KUBECONFIG kubectl -n $ns get pods -l $sel -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')
            set -l pods_list (string split \n -- $pods)
            set -l pods_list (string match -rv '^\s*$' -- $pods_list)

            if test (count $pods_list) -eq 0
                echo "No pods found for selector: $sel in ns: $ns"
                return 1
            end

            set -l idx (random 1 (count $pods_list))
            set -l pod $pods_list[$idx]
            echo "Selected pod: $pod"

            k logs $ns $pod $argv

        case logs-label
            if test (count $argv) -lt 2
                echo "k logs-label <ns> <label-selector> [pod-index] [-c container] [--since 10m] [--tail 200] [-f] [--previous]"
                return 2
            end

            set -l ns $argv[1]
            set -l sel $argv[2]
            set -e argv[1..2]

            set -l pods (env KUBECONFIG=$KUBECONFIG kubectl -n $ns get pods -l $sel -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')
            set -l pods_list (string split \n -- $pods)
            set -l pods_list (string match -rv '^\s*$' -- $pods_list)

            if test (count $pods_list) -eq 0
                echo "No pods found for selector: $sel in ns: $ns"
                return 1
            end

            set -l idx 1
            if test (count $argv) -ge 1
                if string match -qr '^[0-9]+$' -- $argv[1]
                    set idx $argv[1]
                    set -e argv[1]
                end
            end

            if test $idx -lt 1 -o $idx -gt (count $pods_list)
                echo "pod-index out of range. Have "(count $pods_list)" pods:"
                for i in (seq 1 (count $pods_list))
                    echo "$i) $pods_list[$i]"
                end
                return 2
            end

            set -l pod $pods_list[$idx]
            echo "Selected pod: $pod"

            k logs $ns $pod $argv

        case pf
            if test (count $argv) -ne 4
                echo "k pf pod <ns> <pod> <port|local:remote>"
                echo "k pf svc <ns> <svc> <port|local:remote>"
                echo "  single port: auto-assigns local = remote + 10000"
                echo "  explicit:    local:remote uses exact ports"
                return 2
            end

            set -l kind $argv[1]
            set -l ns $argv[2]
            set -l name $argv[3]
            set -l port_arg $argv[4]

            # Parse port argument
            set -l local_port
            set -l remote_port
            if string match -qr '^[0-9]+:[0-9]+$' -- $port_arg
                # Explicit local:remote
                set local_port (string split ':' -- $port_arg)[1]
                set remote_port (string split ':' -- $port_arg)[2]
            else if string match -qr '^[0-9]+$' -- $port_arg
                # Single port: auto-offset
                set remote_port $port_arg
                set local_port (math $remote_port + 10000)
            else
                echo "Invalid port format: $port_arg (use PORT or LOCAL:REMOTE)"
                return 2
            end

            set -l ports "$local_port:$remote_port"

            switch $kind
                case pod
                    echo "Forwarding localhost:$local_port → pod/$name:$remote_port"
                    env KUBECONFIG=$KUBECONFIG kubectl -n $ns port-forward pod/$name $ports
                case svc
                    echo "Forwarding localhost:$local_port → svc/$name:$remote_port"
                    env KUBECONFIG=$KUBECONFIG kubectl -n $ns port-forward svc/$name $ports
                case '*'
                    echo "Unknown kind: $kind (use pod|svc)"
                    return 2
            end

        case debug
            if test (count $argv) -lt 2
                echo "k debug <ns> <pod> [--target container] [--image nicolaka/netshoot]"
                return 2
            end

            set -l ns $argv[1]
            set -l pod $argv[2]
            set -e argv[1..2]

            set -l image nicolaka/netshoot
            set -l target ""

            set -l i 1
            while test $i -le (count $argv)
                set -l a $argv[$i]
                switch $a
                    case --image
                        set image $argv[(math $i + 1)]
                        set i (math $i + 2)
                        continue
                    case --target
                        set target $argv[(math $i + 1)]
                        set i (math $i + 2)
                        continue
                    case '*'
                        set i (math $i + 1)
                        continue
                end
            end

            if test -n "$target"
                env KUBECONFIG=$KUBECONFIG kubectl -n $ns debug -it pod/$pod --image=$image --target=$target -- sh
            else
                env KUBECONFIG=$KUBECONFIG kubectl -n $ns debug -it pod/$pod --image=$image -- sh
            end

        case raw
            env KUBECONFIG=$KUBECONFIG kubectl $argv

        case '*'
            # fallback — allows: k get pods -n ns ... etc
            env KUBECONFIG=$KUBECONFIG kubectl $cmd $argv
    end
end

