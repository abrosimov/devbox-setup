# pub_proxy_migration.fish — one-shot removal of the universal HTTP(S)_PROXY
# variables left behind by the retired `gost` bridge, which listened on
# 127.0.0.1:8080. Pub mode now uses WARP `tunnel_only` and sets no proxy at all,
# so those universals only point at a dead endpoint.
#
# Only run in interactive shells to keep script/subshell startup cheap and to
# avoid churn during ansible/kitty-launched non-interactive fish invocations.
status --is-interactive; or exit 0

# One-shot: the migration must never delete a proxy variable the user sets
# deliberately after the upgrade. The universal marker records that the sweep
# has already happened, so from the second shell onwards this file is inert and
# any later 127.0.0.1:8080 proxy is the user's own business.
set -q -U __pub_proxy_migration_v3; and exit 0

set -l legacy_proxy_vars
set -l migration_blocked false
for var in HTTPS_PROXY HTTP_PROXY https_proxy http_proxy
    set -q -U $var; or continue
    # A global shadow means an older `pub on` (or an unrelated exporter) is still
    # driving this shell's proxy: erasing the universal here would not change the
    # live value, yet the marker would record the migration as done and the
    # universal would survive forever. Defer the whole sweep to a later shell
    # that starts without the shadow instead.
    if set -q -g $var
        set migration_blocked true
    # Exact match, not the old pub_guard.fish `*127.0.0.1:8080*` glob: only the
    # value this repo used to write is ours to remove, so an externally
    # configured corporate proxy is never touched.
    else if string match -q 'http://127.0.0.1:8080' -- $$var
        set -a legacy_proxy_vars $var
    end
end

if test (count $legacy_proxy_vars) -gt 0
    for var in $legacy_proxy_vars
        set -eU $var
    end
    echo "pub migration: removed legacy 127.0.0.1:8080 proxy variables" >&2
end

test $migration_blocked = true; and exit 0

# Versioned marker: a later sweep bumps the suffix so it re-runs once on every
# machine, and erases its predecessor so fish_variables does not accumulate dead
# universals. Drop the v2 erase only once no machine can still carry that marker.
set -eU __pub_proxy_migration_v2
set -U __pub_proxy_migration_v3 1
