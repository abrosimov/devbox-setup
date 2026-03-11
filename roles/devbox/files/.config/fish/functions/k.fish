function k --description "kubectl helper; expects KUBECONFIG to be set by wrapper (kstg/kprd/...)"
    if not set -q KUBECONFIG
        echo "KUBECONFIG is not set. Use a wrapper like: kstg ..., kprd ..."
        return 2
    end

    # Helper: resolve pod name with fuzzy matching
    # - No filter: fzf picker
    # - Filter matches 1 pod: return it
    # - Filter matches multiple: fzf picker with filtered list
    # - Filter matches 0: error
    function __k_resolve_pod --argument-names ns filter
        set -l pods_output (env KUBECONFIG=$KUBECONFIG kubectl -n $ns get pods -o wide 2>/dev/null | tail -n +2)

        if test -z "$filter"
            # No filter - show full fzf picker
            echo $pods_output | \
                fzf --header="Select pod in $ns" \
                    --preview="env KUBECONFIG=$KUBECONFIG kubectl -n $ns describe pod {1} 2>/dev/null | head -40" \
                    --preview-window=right:50%:wrap | awk '{print $1}'
            return
        end

        # Filter provided - grep for matches
        set -l matched (printf '%s\n' $pods_output | grep -i "$filter")
        set -l match_count (printf '%s\n' $matched | grep -c .)

        if test $match_count -eq 0
            echo "No pods matching '$filter' in $ns" >&2
            return 1
        else if test $match_count -eq 1
            # Exactly one match - use it directly
            printf '%s\n' $matched | awk '{print $1}'
        else
            # Multiple matches - fzf picker with filtered list
            printf '%s\n' $matched | \
                fzf --header="Select pod matching '$filter' in $ns" \
                    --preview="env KUBECONFIG=$KUBECONFIG kubectl -n $ns describe pod {1} 2>/dev/null | head -40" \
                    --preview-window=right:50%:wrap | awk '{print $1}'
        end
    end

    # Helper: fzf resource picker with preview
    function __k_pick_resource --argument-names ns kind
        env KUBECONFIG=$KUBECONFIG kubectl -n $ns get $kind 2>/dev/null | tail -n +2 | \
            fzf --header="Select $kind in $ns" \
                --preview="env KUBECONFIG=$KUBECONFIG kubectl -n $ns describe $kind {1} 2>/dev/null | head -40" \
                --preview-window=right:50%:wrap | awk '{print $1}'
    end

    # Helper: fzf helm release picker
    function __k_pick_helm_release --argument-names ns
        env KUBECONFIG=$KUBECONFIG helm list -n $ns 2>/dev/null | tail -n +2 | \
            fzf --header="Select helm release in $ns" \
                --preview="env KUBECONFIG=$KUBECONFIG helm status {1} -n $ns 2>/dev/null | head -40" \
                --preview-window=right:50%:wrap | awk '{print $1}'
    end

    if test (count $argv) -lt 1
        echo "Usage: (use partial name for fuzzy match, omit for fzf picker)"
        echo ""
        echo "Context & Namespaces:"
        echo "  k ctx                                  — show current context and KUBECONFIG"
        echo "  k ns                                   — list all namespaces"
        echo ""
        echo "Resource Listing:"
        echo "  k pods <ns> [filter]                   — list pods (grep filter)"
        echo "  k deploy <ns>                          — list deployments"
        echo "  k sts <ns>                             — list statefulsets"
        echo "  k svc <ns>                             — list services"
        echo "  k ing <ns>                             — list ingresses"
        echo "  k cm <ns>                              — list configmaps"
        echo "  k secret <ns>                          — list secrets"
        echo "  k top <ns>                             — pod resource usage"
        echo ""
        echo "Pod Inspection (fuzzy match or fzf if omitted):"
        echo "  k containers <ns> [filter]             — list containers in pod"
        echo "  k images <ns> [filter]                 — show container images"
        echo "  k ports <ns> [filter]                  — show container ports"
        echo "  k describe <ns> <kind> [name]          — describe resource"
        echo "  k events <ns> [--watch]                — show events in namespace"
        echo ""
        echo "Logs & Exec (fuzzy match or fzf if omitted):"
        echo "  k logs <ns> [filter] [-c container] [--since 10m] [--tail 200] [-f] [--previous]"
        echo "  k logs-rand <ns> <label-selector> ...  — logs from random pod"
        echo "  k logs-label <ns> <label-selector> ... — logs from indexed pod"
        echo "  k exec <ns> [filter] [-c container] [cmd] — exec into pod (default: sh)"
        echo ""
        echo "Port-Forward & Debug (fuzzy match or fzf if omitted):"
        echo "  k pf pod <ns> [filter] <port|local:remote>"
        echo "  k pf svc <ns> [filter] <port|local:remote>"
        echo "  k debug <ns> [filter] [--target container] [--image nicolaka/netshoot]"
        echo ""
        echo "Config Inspection (omit name for fzf picker):"
        echo "  k get-cm <ns> [name]                   — show configmap data"
        echo "  k get-secret <ns> [name] [--decode]    — show secret (optionally decode)"
        echo ""
        echo "Helm (omit <release> for fzf picker):"
        echo "  k helm list <ns>                       — list releases"
        echo "  k helm values <ns> [release]           — get values"
        echo "  k helm history <ns> [release]          — revision history"
        echo "  k helm manifest <ns> [release]         — rendered manifests"
        echo ""
        echo "Operations:"
        echo "  k restart <ns> [deploy]                — rollout restart deployment"
        echo "  k rollout <ns> [deploy]                — rollout status"
        echo ""
        echo "Nodes:"
        echo "  k nodes [--top]                        — list nodes or resource usage"
        echo "  k node <name> [--pods|--resources]     — node details"
        echo ""
        echo "Passthrough:"
        echo "  k raw <any kubectl args...>            — direct kubectl"
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

        case deploy
            if test (count $argv) -lt 1
                echo "k deploy <ns>"
                return 2
            end
            set -l ns $argv[1]
            env KUBECONFIG=$KUBECONFIG kubectl -n $ns get deploy -o wide

        case sts
            if test (count $argv) -lt 1
                echo "k sts <ns>"
                return 2
            end
            set -l ns $argv[1]
            env KUBECONFIG=$KUBECONFIG kubectl -n $ns get sts -o wide

        case svc
            if test (count $argv) -lt 1
                echo "k svc <ns>"
                return 2
            end
            set -l ns $argv[1]
            env KUBECONFIG=$KUBECONFIG kubectl -n $ns get svc -o wide

        case ing
            if test (count $argv) -lt 1
                echo "k ing <ns>"
                return 2
            end
            set -l ns $argv[1]
            env KUBECONFIG=$KUBECONFIG kubectl -n $ns get ing

        case cm
            if test (count $argv) -lt 1
                echo "k cm <ns>"
                return 2
            end
            set -l ns $argv[1]
            env KUBECONFIG=$KUBECONFIG kubectl -n $ns get cm

        case secret
            if test (count $argv) -lt 1
                echo "k secret <ns>"
                return 2
            end
            set -l ns $argv[1]
            env KUBECONFIG=$KUBECONFIG kubectl -n $ns get secret

        case top
            if test (count $argv) -lt 1
                echo "k top <ns>"
                return 2
            end
            set -l ns $argv[1]
            env KUBECONFIG=$KUBECONFIG kubectl -n $ns top pods

        case pods
            if test (count $argv) -lt 1
                echo "k pods <ns> [filter]"
                return 2
            end
            set -l ns $argv[1]
            set -l filter ""
            test (count $argv) -ge 2; and set filter $argv[2]

            set -l output (env KUBECONFIG=$KUBECONFIG kubectl -n $ns get pods -o wide 2>/dev/null)
            if test -z "$filter"
                printf '%s\n' $output
            else
                # Print header + filtered rows
                printf '%s\n' $output | head -1
                printf '%s\n' $output | tail -n +2 | grep -i "$filter"
            end

        case containers
            if test (count $argv) -lt 1
                echo "k containers <ns> [pod-filter]"
                return 2
            end
            set -l ns $argv[1]
            set -l filter ""
            test (count $argv) -ge 2; and set filter $argv[2]

            set -l pod (__k_resolve_pod $ns $filter)
            if test -z "$pod"
                return 1
            end
            test -n "$filter"; and echo "Resolved: $pod"

            env KUBECONFIG=$KUBECONFIG kubectl -n $ns get pod $pod -o jsonpath='{range .spec.initContainers[*]}init:{.name}{"\n"}{end}{range .spec.containers[*]}container:{.name}{"\n"}{end}'

        case images
            if test (count $argv) -lt 1
                echo "k images <ns> [pod-filter]"
                return 2
            end
            set -l ns $argv[1]
            set -l filter ""
            test (count $argv) -ge 2; and set filter $argv[2]

            set -l pod (__k_resolve_pod $ns $filter)
            if test -z "$pod"
                return 1
            end
            test -n "$filter"; and echo "Resolved: $pod"

            env KUBECONFIG=$KUBECONFIG kubectl -n $ns get pod $pod -o jsonpath='{range .spec.containers[*]}{.name}{": "}{.image}{"\n"}{end}'

        case ports
            if test (count $argv) -lt 1
                echo "k ports <ns> [pod-filter]"
                return 2
            end
            set -l ns $argv[1]
            set -l filter ""
            test (count $argv) -ge 2; and set filter $argv[2]

            set -l pod (__k_resolve_pod $ns $filter)
            if test -z "$pod"
                return 1
            end
            test -n "$filter"; and echo "Resolved: $pod"

            env KUBECONFIG=$KUBECONFIG kubectl -n $ns get pod $pod -o jsonpath='{range .spec.containers[*]}{.name}{": "}{range .ports[*]}{.containerPort} {end}{"\n"}{end}'

        case describe
            if test (count $argv) -lt 2
                echo "k describe <ns> <kind> [name]"
                echo "  kind: pod, svc, deploy, sts, ds, cm, secret, ing, pvc, ..."
                return 2
            end
            set -l ns $argv[1]
            set -l kind $argv[2]
            set -l name
            if test (count $argv) -ge 3
                set name $argv[3]
            else
                set name (__k_pick_resource $ns $kind)
                if test -z "$name"
                    return 1
                end
                echo "Selected: $name"
            end
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
            if test (count $argv) -lt 1
                echo "k exec <ns> [pod-filter] [-c container] [cmd]"
                return 2
            end
            set -l ns $argv[1]
            set -e argv[1]

            set -l filter ""
            set -l container ""
            set -l cmd_to_run sh

            # Check if first remaining arg looks like a pod filter (not a flag)
            if test (count $argv) -ge 1; and not string match -q -- '-*' $argv[1]
                set filter $argv[1]
                set -e argv[1]
            end

            set -l pod (__k_resolve_pod $ns $filter)
            if test -z "$pod"
                return 1
            end
            test -n "$filter"; and echo "Resolved: $pod"

            set -l i 1
            while test $i -le (count $argv)
                set -l a $argv[$i]
                switch $a
                    case -c
                        set container $argv[(math $i + 1)]
                        set i (math $i + 2)
                        continue
                    case '*'
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
            if test (count $argv) -lt 1
                echo "k logs <ns> [pod-filter] [-c container] [--since 10m] [--tail 200] [-f] [--previous]"
                return 2
            end

            set -l ns $argv[1]
            set -e argv[1]

            set -l filter ""
            # Check if first remaining arg looks like a pod filter (not a flag)
            if test (count $argv) -ge 1; and not string match -q -- '-*' $argv[1]
                set filter $argv[1]
                set -e argv[1]
            end

            set -l pod (__k_resolve_pod $ns $filter)
            if test -z "$pod"
                return 1
            end
            test -n "$filter"; and echo "Resolved: $pod"

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
            if test (count $argv) -lt 3
                echo "k pf pod <ns> [pod-filter] <port|local:remote>"
                echo "k pf svc <ns> [svc-filter] <port|local:remote>"
                echo "  single port: auto-assigns local = remote + 10000"
                echo "  explicit:    local:remote uses exact ports"
                echo "  omit or use partial name for fuzzy matching"
                return 2
            end

            set -l kind $argv[1]
            set -l ns $argv[2]
            set -e argv[1..2]

            set -l filter ""
            set -l port_arg ""

            # If we have 2 args, it's filter + port; if 1 arg, it's just port (no filter)
            if test (count $argv) -ge 2
                set filter $argv[1]
                set port_arg $argv[2]
            else if test (count $argv) -eq 1
                set port_arg $argv[1]
            else
                echo "k pf $kind <ns> [filter] <port>"
                return 2
            end

            set -l name ""
            switch $kind
                case pod
                    set name (__k_resolve_pod $ns $filter)
                case svc
                    if test -z "$filter"
                        set name (__k_pick_resource $ns svc)
                    else
                        # Simple fuzzy match for services
                        set -l svcs (env KUBECONFIG=$KUBECONFIG kubectl -n $ns get svc -o name 2>/dev/null | sed 's|service/||' | grep -i "$filter")
                        set -l svc_count (printf '%s\n' $svcs | grep -c .)
                        if test $svc_count -eq 0
                            echo "No services matching '$filter' in $ns" >&2
                            return 1
                        else if test $svc_count -eq 1
                            set name $svcs
                        else
                            set name (printf '%s\n' $svcs | fzf --header="Select svc matching '$filter' in $ns")
                        end
                    end
            end

            if test -z "$name"
                return 1
            end
            test -n "$filter"; and echo "Resolved: $name"

            # Parse port argument
            set -l local_port
            set -l remote_port
            if string match -qr '^[0-9]+:[0-9]+$' -- $port_arg
                set local_port (string split ':' -- $port_arg)[1]
                set remote_port (string split ':' -- $port_arg)[2]
            else if string match -qr '^[0-9]+$' -- $port_arg
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
            if test (count $argv) -lt 1
                echo "k debug <ns> [pod-filter] [--target container] [--image nicolaka/netshoot]"
                return 2
            end

            set -l ns $argv[1]
            set -e argv[1]

            set -l filter ""
            # Check if first remaining arg looks like a pod filter (not a flag)
            if test (count $argv) -ge 1; and not string match -q -- '-*' $argv[1]
                set filter $argv[1]
                set -e argv[1]
            end

            set -l pod (__k_resolve_pod $ns $filter)
            if test -z "$pod"
                return 1
            end
            test -n "$filter"; and echo "Resolved: $pod"

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

        case nodes
            set -l show_top false

            set -l i 1
            while test $i -le (count $argv)
                set -l a $argv[$i]
                switch $a
                    case --top
                        set show_top true
                        set i (math $i + 1)
                        continue
                    case '*'
                        echo "k nodes [--top]"
                        return 2
                end
            end

            if test $show_top = true
                env KUBECONFIG=$KUBECONFIG kubectl top nodes
            else
                env KUBECONFIG=$KUBECONFIG kubectl get nodes -o wide
            end

        case node
            if test (count $argv) -lt 1
                echo "k node <name> [--pods|--resources]"
                return 2
            end

            set -l node_name $argv[1]
            set -e argv[1]

            set -l show_pods false
            set -l show_resources false

            set -l i 1
            while test $i -le (count $argv)
                set -l a $argv[$i]
                switch $a
                    case --pods
                        set show_pods true
                        set i (math $i + 1)
                        continue
                    case --resources
                        set show_resources true
                        set i (math $i + 1)
                        continue
                    case '*'
                        echo "k node <name> [--pods|--resources]"
                        return 2
                end
            end

            if test $show_pods = true
                env KUBECONFIG=$KUBECONFIG kubectl get pods --all-namespaces --field-selector spec.nodeName=$node_name -o wide
            else if test $show_resources = true
                env KUBECONFIG=$KUBECONFIG kubectl get node $node_name -o jsonpath='{"\nCapacity:\n  CPU: "}{.status.capacity.cpu}{"\n  Memory: "}{.status.capacity.memory}{"\n\nAllocatable:\n  CPU: "}{.status.allocatable.cpu}{"\n  Memory: "}{.status.allocatable.memory}{"\n"}'
            else
                env KUBECONFIG=$KUBECONFIG kubectl describe node $node_name
            end

        case helm
            if test (count $argv) -lt 2
                echo "k helm list <ns>"
                echo "k helm values <ns> [release]"
                echo "k helm history <ns> [release]"
                echo "k helm manifest <ns> [release]"
                return 2
            end

            set -l subcmd $argv[1]
            set -l ns $argv[2]
            set -e argv[1..2]

            switch $subcmd
                case list
                    env KUBECONFIG=$KUBECONFIG helm list -n $ns
                case values
                    set -l release
                    if test (count $argv) -ge 1
                        set release $argv[1]
                    else
                        set release (__k_pick_helm_release $ns)
                        if test -z "$release"
                            return 1
                        end
                        echo "Selected: $release"
                    end
                    env KUBECONFIG=$KUBECONFIG helm get values $release -n $ns
                case history
                    set -l release
                    if test (count $argv) -ge 1
                        set release $argv[1]
                    else
                        set release (__k_pick_helm_release $ns)
                        if test -z "$release"
                            return 1
                        end
                        echo "Selected: $release"
                    end
                    env KUBECONFIG=$KUBECONFIG helm history $release -n $ns
                case manifest
                    set -l release
                    if test (count $argv) -ge 1
                        set release $argv[1]
                    else
                        set release (__k_pick_helm_release $ns)
                        if test -z "$release"
                            return 1
                        end
                        echo "Selected: $release"
                    end
                    env KUBECONFIG=$KUBECONFIG helm get manifest $release -n $ns
                case '*'
                    echo "Unknown helm subcommand: $subcmd"
                    echo "Use: list, values, history, manifest"
                    return 2
            end

        case restart
            if test (count $argv) -lt 1
                echo "k restart <ns> [deploy]"
                return 2
            end
            set -l ns $argv[1]
            set -l deploy
            if test (count $argv) -ge 2
                set deploy $argv[2]
            else
                set deploy (__k_pick_resource $ns deploy)
                if test -z "$deploy"
                    return 1
                end
                echo "Selected: $deploy"
            end
            env KUBECONFIG=$KUBECONFIG kubectl -n $ns rollout restart deploy/$deploy

        case rollout
            if test (count $argv) -lt 1
                echo "k rollout <ns> [deploy]"
                return 2
            end
            set -l ns $argv[1]
            set -l deploy
            if test (count $argv) -ge 2
                set deploy $argv[2]
            else
                set deploy (__k_pick_resource $ns deploy)
                if test -z "$deploy"
                    return 1
                end
                echo "Selected: $deploy"
            end
            env KUBECONFIG=$KUBECONFIG kubectl -n $ns rollout status deploy/$deploy

        case get-cm
            if test (count $argv) -lt 1
                echo "k get-cm <ns> [name]"
                return 2
            end
            set -l ns $argv[1]
            set -l name
            if test (count $argv) -ge 2
                set name $argv[2]
            else
                set name (__k_pick_resource $ns cm)
                if test -z "$name"
                    return 1
                end
                echo "Selected: $name"
            end
            env KUBECONFIG=$KUBECONFIG kubectl -n $ns get cm $name -o yaml

        case get-secret
            if test (count $argv) -lt 1
                echo "k get-secret <ns> [name] [--decode]"
                return 2
            end
            set -l ns $argv[1]
            set -e argv[1]

            set -l name ""
            set -l decode false

            # Parse arguments
            for a in $argv
                switch $a
                    case --decode
                        set decode true
                    case '*'
                        if test -z "$name"
                            set name $a
                        end
                end
            end

            # If no name, use fzf
            if test -z "$name"
                set name (__k_pick_resource $ns secret)
                if test -z "$name"
                    return 1
                end
                echo "Selected: $name"
            end

            if test $decode = true
                echo "--- Secret: $name (decoded) ---"
                env KUBECONFIG=$KUBECONFIG kubectl -n $ns get secret $name -o json | \
                    jq -r '.data // {} | to_entries[] | "\(.key): \(.value | @base64d)"'
            else
                env KUBECONFIG=$KUBECONFIG kubectl -n $ns get secret $name -o yaml
            end

        case raw
            env KUBECONFIG=$KUBECONFIG kubectl $argv

        case '*'
            # fallback — allows: k get pods -n ns ... etc
            env KUBECONFIG=$KUBECONFIG kubectl $cmd $argv
    end
end

