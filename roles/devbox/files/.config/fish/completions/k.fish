# Completions for k (kubectl wrapper) function
complete -c k -f

# Subcommands
complete -c k -n '__fish_use_subcommand' -a ctx -d 'Show current context and KUBECONFIG'
complete -c k -n '__fish_use_subcommand' -a ns -d 'List all namespaces'
complete -c k -n '__fish_use_subcommand' -a pods -d 'List pods'
complete -c k -n '__fish_use_subcommand' -a containers -d 'List containers in pod'
complete -c k -n '__fish_use_subcommand' -a images -d 'Show container images'
complete -c k -n '__fish_use_subcommand' -a ports -d 'Show container ports'
complete -c k -n '__fish_use_subcommand' -a describe -d 'Describe resource'
complete -c k -n '__fish_use_subcommand' -a events -d 'Show events in namespace'
complete -c k -n '__fish_use_subcommand' -a exec -d 'Exec into pod'
complete -c k -n '__fish_use_subcommand' -a logs -d 'Show pod logs'
complete -c k -n '__fish_use_subcommand' -a logs-rand -d 'Logs from random pod by label'
complete -c k -n '__fish_use_subcommand' -a logs-label -d 'Logs from pod by label and index'
complete -c k -n '__fish_use_subcommand' -a pf -d 'Port-forward to pod or service'
complete -c k -n '__fish_use_subcommand' -a debug -d 'Debug pod with ephemeral container'
complete -c k -n '__fish_use_subcommand' -a nodes -d 'List nodes'
complete -c k -n '__fish_use_subcommand' -a node -d 'Describe/inspect a node'
complete -c k -n '__fish_use_subcommand' -a raw -d 'Passthrough to kubectl'

# Dynamic namespace completions for subcommands that take <ns> as first arg
function __k_namespaces
    set -q KUBECONFIG; or return
    env KUBECONFIG=$KUBECONFIG kubectl get namespaces -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' 2>/dev/null
end

function __k_pods_in_ns
    set -q KUBECONFIG; or return
    set -l tokens (commandline -opc)
    # tokens: k <subcmd> <ns> ...
    if test (count $tokens) -ge 3
        set -l ns $tokens[3]
        env KUBECONFIG=$KUBECONFIG kubectl -n $ns get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' 2>/dev/null
    end
end

# pods <ns>
complete -c k -n '__fish_seen_subcommand_from pods; and test (count (commandline -opc)) -eq 2' -a '(__k_namespaces)'

# containers/images/ports <ns> <pod>
for sub in containers images ports
    complete -c k -n "__fish_seen_subcommand_from $sub; and test (count (commandline -opc)) -eq 2" -a '(__k_namespaces)'
    complete -c k -n "__fish_seen_subcommand_from $sub; and test (count (commandline -opc)) -eq 3" -a '(__k_pods_in_ns)'
end

# describe <ns> <kind>
complete -c k -n '__fish_seen_subcommand_from describe; and test (count (commandline -opc)) -eq 2' -a '(__k_namespaces)'
complete -c k -n '__fish_seen_subcommand_from describe; and test (count (commandline -opc)) -eq 3' -a 'pod svc deploy sts ds cm secret ing pvc job cronjob'

# exec/logs <ns> <pod>
for sub in exec logs
    complete -c k -n "__fish_seen_subcommand_from $sub; and test (count (commandline -opc)) -eq 2" -a '(__k_namespaces)'
    complete -c k -n "__fish_seen_subcommand_from $sub; and test (count (commandline -opc)) -eq 3" -a '(__k_pods_in_ns)'
end

# logs flags
for sub in logs logs-rand logs-label
    complete -c k -n "__fish_seen_subcommand_from $sub" -l since -d 'Show logs since duration (e.g. 10m)'
    complete -c k -n "__fish_seen_subcommand_from $sub" -l tail -d 'Number of lines to show'
    complete -c k -n "__fish_seen_subcommand_from $sub" -s f -d 'Follow log output'
    complete -c k -n "__fish_seen_subcommand_from $sub" -l previous -d 'Show previous container logs'
    complete -c k -n "__fish_seen_subcommand_from $sub" -s c -d 'Container name'
end

# logs-rand/logs-label <ns>
for sub in logs-rand logs-label
    complete -c k -n "__fish_seen_subcommand_from $sub; and test (count (commandline -opc)) -eq 2" -a '(__k_namespaces)'
end

# pf <pod|svc>
complete -c k -n '__fish_seen_subcommand_from pf; and test (count (commandline -opc)) -eq 2' -a 'pod svc'
complete -c k -n '__fish_seen_subcommand_from pf; and test (count (commandline -opc)) -eq 3' -a '(__k_namespaces)'

# events <ns>
complete -c k -n '__fish_seen_subcommand_from events; and test (count (commandline -opc)) -eq 2' -a '(__k_namespaces)'
complete -c k -n '__fish_seen_subcommand_from events' -l watch -d 'Watch events'

# debug <ns> <pod>
complete -c k -n '__fish_seen_subcommand_from debug; and test (count (commandline -opc)) -eq 2' -a '(__k_namespaces)'
complete -c k -n '__fish_seen_subcommand_from debug; and test (count (commandline -opc)) -eq 3' -a '(__k_pods_in_ns)'
complete -c k -n '__fish_seen_subcommand_from debug' -l target -d 'Target container'
complete -c k -n '__fish_seen_subcommand_from debug' -l image -d 'Debug image (default: nicolaka/netshoot)'

# nodes
complete -c k -n '__fish_seen_subcommand_from nodes' -l top -d 'Show resource usage'

# node <name>
complete -c k -n '__fish_seen_subcommand_from node' -l pods -d 'List pods on node'
complete -c k -n '__fish_seen_subcommand_from node' -l resources -d 'Show node resources'
