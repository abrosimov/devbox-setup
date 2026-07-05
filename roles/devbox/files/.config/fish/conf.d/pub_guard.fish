# pub_guard.fish — auto-clean stale HTTP(S)_PROXY vars pointing at the local
# `gost` bridge if the bridge is not actually running.
#
# History: earlier versions of `pub on` used `set -Ux` (universal exported),
# which persisted the proxy across reboots. If `gost` did not survive the
# reboot, every subsequent curl/git/gh silently hit a dead 127.0.0.1:8080.
# `pub` itself now uses `-gx`, but this guard cleans up any legacy universal
# left over on machines that ran the old version.
#
# The guard only touches proxies pointing at 127.0.0.1:8080 — an externally
# configured corporate proxy is left alone.

# Only run in interactive shells to keep script/subshell startup cheap and
# to avoid churn during ansible/kitty-launched non-interactive fish invocations.
status --is-interactive; or exit 0

set -l stale
for var in HTTPS_PROXY HTTP_PROXY https_proxy http_proxy
    if set -q -U $var; and string match -q '*127.0.0.1:8080*' -- $$var
        set -a stale $var
    end
end

test (count $stale) -eq 0; and exit 0

# Bridge listens on :8080. If nothing is bound there, the universal vars are
# stale from a previous `pub on` that never got a matching `pub off`.
if not pgrep -f 'gost.*:8080' >/dev/null
    for var in $stale
        set -eU $var
    end
    echo "pub_guard: dropped stale universal proxy vars ("(string join ', ' $stale)") — gost bridge not running. Run `pub on` to re-enable." >&2
end
