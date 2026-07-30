# Tunnel to the private telemetry host and open its browser UIs.
#
# Both UIs (SigNoz, ClickStack) bind loopback on the server and are deliberately
# not published through the public edge, so a forwarded SSH channel is the only
# way in. The public hostname carries authenticated OTLP ingestion only.
#
# Host and ports are machine-local (~/.config/otelbox/tunnel.env) because this
# repository is public — see .config/otelbox/tunnel.env.example.

function otelbox --description "SSH tunnel to the telemetry host + open the SigNoz / ClickStack UIs"
    set -l cmd up
    set -l rest

    if test (count $argv) -ge 1
        set cmd $argv[1]
        set rest $argv[2..-1]
    end

    switch $cmd
        case up ''
            __otelbox_up $rest
        case down stop
            __otelbox_down
        case status
            __otelbox_status
        case signoz
            if not __otelbox_up --no-open
                return 1
            end
            __otelbox_browse signoz
        case clickstack hyperdx
            if not __otelbox_up --no-open
                return 1
            end
            __otelbox_browse clickstack
        case help --help -h
            __otelbox_usage
        case '*'
            echo "otelbox: unknown subcommand '$cmd'" >&2
            __otelbox_usage >&2
            return 2
    end
end

function __otelbox_usage --description "otelbox: print usage"
    echo "Usage:"
    echo "  otelbox [up] [--no-open]  — open the tunnel, then both UIs in the browser"
    echo "  otelbox down              — close the tunnel"
    echo "  otelbox status            — tunnel state and forwarded-port state"
    echo "  otelbox signoz            — ensure the tunnel, open SigNoz only"
    echo "  otelbox clickstack        — ensure the tunnel, open ClickStack only"
    echo ""
    echo "Config: ~/.config/otelbox/tunnel.env"
end

function __otelbox_load_config --description "otelbox: read ~/.config/otelbox/tunnel.env"
    set -g __otelbox_host ""
    set -g __otelbox_signoz_port 18080
    set -g __otelbox_clickstack_port 28080
    set -g __otelbox_socket $HOME/.ssh/otelbox.sock

    set -l config $HOME/.config/otelbox/tunnel.env

    if not test -f $config
        echo "otelbox: $config not found." >&2
        echo "         The real file is machine-local. In devbox-setup, copy" >&2
        echo "           roles/devbox/files/.config/otelbox/tunnel.env.example" >&2
        echo "         to roles/devbox/local/.config/otelbox/tunnel.env," >&2
        echo "         fill in the host, then run 'make local-push'." >&2
        return 1
    end

    while read -l line
        set -l trimmed (string trim -- $line)

        if test -z "$trimmed"; or string match -q '#*' -- $trimmed
            continue
        end

        set -l pair (string split -m 1 '=' -- $trimmed)

        if test (count $pair) -ne 2
            continue
        end

        set -l key (string trim -- $pair[1])
        set -l value (string trim -c ' "\'' -- $pair[2])

        switch $key
            case OTELBOX_TUNNEL_HOST
                set -g __otelbox_host $value
            case OTELBOX_SIGNOZ_PORT
                set -g __otelbox_signoz_port $value
            case OTELBOX_CLICKSTACK_PORT
                set -g __otelbox_clickstack_port $value
        end
    end <$config

    if test -z "$__otelbox_host"
        echo "otelbox: OTELBOX_TUNNEL_HOST is not set in $config" >&2
        return 1
    end
end

function __otelbox_running --description "otelbox: is the control master alive"
    ssh -O check -S $__otelbox_socket $__otelbox_host >/dev/null 2>&1
end

function __otelbox_up --description "otelbox: open the tunnel"
    if not __otelbox_load_config
        return 1
    end

    set -l open_ui true

    for flag in $argv
        switch $flag
            case --no-open
                set open_ui false
            case '*'
                echo "otelbox: unknown flag '$flag'" >&2
                return 2
        end
    end

    if __otelbox_running
        echo "otelbox: tunnel already up ($__otelbox_host)"
    else
        mkdir -p (dirname $__otelbox_socket)

        # -M/-S: a control master makes `otelbox down` a deterministic
        # `ssh -O exit` instead of pattern-matching processes with pkill.
        # ExitOnForwardFailure: fail loudly when a local port is already taken,
        # instead of leaving a live session whose forwards silently never bound.
        ssh -f -N -M -S $__otelbox_socket \
            -o ExitOnForwardFailure=yes \
            -L $__otelbox_signoz_port:127.0.0.1:$__otelbox_signoz_port \
            -L $__otelbox_clickstack_port:127.0.0.1:$__otelbox_clickstack_port \
            $__otelbox_host
        or begin
            echo "otelbox: could not open the tunnel to $__otelbox_host" >&2
            return 1
        end

        echo "otelbox: tunnel up ($__otelbox_host)"
    end

    if $open_ui
        __otelbox_browse signoz
        __otelbox_browse clickstack
    end

    __otelbox_summary
end

function __otelbox_down --description "otelbox: close the tunnel"
    if not __otelbox_load_config
        return 1
    end

    if not __otelbox_running
        echo "otelbox: no tunnel running"
        return 0
    end

    ssh -O exit -S $__otelbox_socket $__otelbox_host >/dev/null 2>&1
    echo "otelbox: tunnel closed ($__otelbox_host)"
end

function __otelbox_status --description "otelbox: report tunnel and port state"
    if not __otelbox_load_config
        return 1
    end

    __otelbox_summary
end

# Printed after every otelbox invocation so the ports, URLs and their live state
# never have to be remembered — `status` is the same table on its own.
function __otelbox_summary --description "otelbox: print what is exposed where"
    set -l tunnel_state down

    if __otelbox_running
        set tunnel_state up
    end

    echo ""
    __otelbox_row tunnel $__otelbox_host $tunnel_state (string replace -- $HOME '~' $__otelbox_socket)
    __otelbox_row SigNoz "http://127.0.0.1:$__otelbox_signoz_port" (__otelbox_port_state $__otelbox_signoz_port) "traces / metrics / logs"
    __otelbox_row ClickStack "http://127.0.0.1:$__otelbox_clickstack_port" (__otelbox_port_state $__otelbox_clickstack_port) "HyperDX: logs / sessions"
    echo ""
    echo "  otelbox status | otelbox down | otelbox signoz | otelbox clickstack"
end

function __otelbox_row --description "otelbox: print one summary line"
    printf "  %-11s %-26s %-14s %s\n" $argv[1] $argv[2] $argv[3] $argv[4]
end

function __otelbox_port_state --description "otelbox: probe one forwarded port"
    if not type -q nc
        echo unknown
        return 0
    end

    if nc -z 127.0.0.1 $argv[1] >/dev/null 2>&1
        echo listening
    else
        echo "not listening"
    end
end

function __otelbox_browse --description "otelbox: open one UI in the browser"
    set -l url

    switch $argv[1]
        case signoz
            set url "http://127.0.0.1:$__otelbox_signoz_port"
        case clickstack
            set url "http://127.0.0.1:$__otelbox_clickstack_port"
        case '*'
            echo "otelbox: nothing to open for '$argv[1]'" >&2
            return 2
    end

    echo "otelbox: opening $argv[1] — $url"

    if type -q open
        open $url
    else if type -q xdg-open
        xdg-open $url
    else
        echo "otelbox: no 'open' or 'xdg-open' — visit $url manually" >&2
    end
end
