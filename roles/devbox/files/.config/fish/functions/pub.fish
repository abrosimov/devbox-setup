function pub --description "WARP proxy toggle for untrusted wifi (HTTP bridge on :8080 -> SOCKS5 on :40000)"
    switch "$argv[1]"
        case on
            warp-cli mode proxy >/dev/null
            warp-cli proxy port 40000 >/dev/null
            warp-cli connect >/dev/null
            sleep 1

            # Bridge fronts WARP's SOCKS listener with HTTP because Claude Code
            # only honours HTTP(S)_PROXY. Bind loopback explicitly -- a bare
            # `http://:8080` listens on all interfaces and exposes the bridge
            # to the untrusted network.
            if not pgrep -f 'gost.*:8080' >/dev/null
                gost -L 'http://127.0.0.1:8080' -F 'socks5://127.0.0.1:40000' >/dev/null 2>&1 &
                disown
                sleep 1
            end

            # Universal exported vars: every fish session and every child
            # process inherits them. Lowercase wins in Claude Code, so set both.
            set -Ux HTTPS_PROXY http://127.0.0.1:8080
            set -Ux HTTP_PROXY http://127.0.0.1:8080
            set -Ux https_proxy http://127.0.0.1:8080
            set -Ux http_proxy http://127.0.0.1:8080

            if curl -s --max-time 5 --proxy http://127.0.0.1:8080 \
                    https://www.cloudflare.com/cdn-cgi/trace | grep -q 'warp=on'
                echo "pub mode ON (warp=on)"
                echo "Restart claude sessions to pick up the proxy."
            else
                echo "WARNING: tunnel did not come up -- check 'pub status' and 'warp-cli status'"
            end
        case off
            set -eU HTTPS_PROXY
            set -eU HTTP_PROXY
            set -eU https_proxy
            set -eU http_proxy
            pkill -f 'gost.*:8080' >/dev/null 2>&1
            warp-cli disconnect >/dev/null
            echo "pub mode OFF"
            echo "Restart claude sessions to drop the proxy."
        case status ''
            warp-cli status
            if pgrep -f 'gost.*:8080' >/dev/null
                echo "bridge: up (http://127.0.0.1:8080 -> socks5://127.0.0.1:40000)"
            else
                echo "bridge: down"
            end
            if set -q HTTPS_PROXY
                echo "HTTPS_PROXY: $HTTPS_PROXY"
            else
                echo "HTTPS_PROXY: (unset)"
            end
        case '*'
            echo "usage: pub {on|off|status}"
    end
end
