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

            # Session-scoped exported vars. Only the current fish session and
            # its children see the proxy — closing the window drops it,
            # eliminating the "forgot to `pub off`" foot-gun where universal
            # vars point at a dead `gost` listener across reboots. Lowercase
            # wins in Claude Code, so set both.
            #
            # Also clear any lingering universal vars from an older `pub on`
            # (they'd otherwise be re-inherited from `fish_variables` on next
            # session start and shadow the -gx here).
            set -eU HTTPS_PROXY 2>/dev/null
            set -eU HTTP_PROXY 2>/dev/null
            set -eU https_proxy 2>/dev/null
            set -eU http_proxy 2>/dev/null

            set -gx HTTPS_PROXY http://127.0.0.1:8080
            set -gx HTTP_PROXY http://127.0.0.1:8080
            set -gx https_proxy http://127.0.0.1:8080
            set -gx http_proxy http://127.0.0.1:8080

            if curl -s --max-time 5 --proxy http://127.0.0.1:8080 \
                    https://www.cloudflare.com/cdn-cgi/trace | grep -q 'warp=on'
                echo "pub mode ON (warp=on)"
                echo "Restart claude sessions to pick up the proxy."
            else
                echo "WARNING: tunnel did not come up -- check 'pub status' and 'warp-cli status'"
            end
        case off
            # Drop both scopes: -g clears the current session's exported var,
            # -U clears any legacy universal set (harmless if empty).
            set -eg HTTPS_PROXY 2>/dev/null
            set -eg HTTP_PROXY 2>/dev/null
            set -eg https_proxy 2>/dev/null
            set -eg http_proxy 2>/dev/null
            set -eU HTTPS_PROXY 2>/dev/null
            set -eU HTTP_PROXY 2>/dev/null
            set -eU https_proxy 2>/dev/null
            set -eU http_proxy 2>/dev/null
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
