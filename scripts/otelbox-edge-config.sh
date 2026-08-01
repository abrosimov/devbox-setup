#!/usr/bin/env bash
# Interactive one-time machine-local setup for the durable otelbox edge collector.
# Fills the two values that are NOT tracked in the repo:
#
#   endpoint  — the remote gateway authority (host:port, no https://). Non-secret.
#               Written to the gitignored local overlay
#               roles/devbox/local/.config/otelbox/edge/endpoint.env (source of
#               truth, deployed by Ansible) AND live to ~/.config/otelbox/edge/
#               endpoint.env so the running service picks it up immediately.
#   token     — the Bearer ingestion key. Secret. Stored ONLY in the login
#               keychain slot `otelbox-edge-token`, added with
#               `-T /usr/bin/security` so the wrapper's `security
#               find-generic-password` reads it silently after one "Always Allow".
#
# Consumed by roles/devbox/files/.config/otelbox/edge/otelbox-edge-run (wrapper)
# and edge.yaml (${env:OTELBOX_EDGE_ENDPOINT} / ${env:OTELBOX_EDGE_TOKEN}).
# See README.md § OTLP Telemetry.
#
# Invocation:
#   make otelbox-edge-config                    — prompt for both, upsert
#   ./scripts/otelbox-edge-config.sh --only endpoint
#   ./scripts/otelbox-edge-config.sh --only token
#
# Darwin-only (launchd + login keychain). Non-TTY: refuses to prompt, exits 1.

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "otelbox-edge-config: macOS only (launchd + login keychain)." >&2
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "${SCRIPT_DIR}")"
readonly SCRIPT_DIR REPO_ROOT
readonly OVERLAY_ENV="${REPO_ROOT}/roles/devbox/local/.config/otelbox/edge/endpoint.env"
readonly LIVE_ENV="${HOME}/.config/otelbox/edge/endpoint.env"
readonly TOKEN_SVC="otelbox-edge-token"

_only=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --only)
            _only="${2:-}"
            shift 2
            ;;
        --only=*)
            _only="${1#--only=}"
            shift
            ;;
        -h | --help)
            sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "otelbox-edge-config: unknown argument: $1" >&2
            exit 64
            ;;
    esac
done

case "${_only}" in
    "" | endpoint | token) ;;
    *)
        echo "otelbox-edge-config: --only takes 'endpoint' or 'token', got '${_only}'" >&2
        exit 64
        ;;
esac

_require_tty() {
    if [[ ! -t 0 ]]; then
        echo "otelbox-edge-config: stdin is not a TTY — run interactively." >&2
        exit 1
    fi
}

_set_endpoint() {
    _require_tty
    local endpoint=""
    local attempt
    for attempt in 1 2 3; do
        printf 'Remote gateway endpoint (host:port, no https://): ' >&2
        IFS= read -r endpoint || true
        endpoint="${endpoint## }"
        endpoint="${endpoint%% }"
        if [[ -z "${endpoint}" ]]; then
            echo "  empty input, try again (${attempt}/3)" >&2
            continue
        fi
        if [[ "${endpoint}" == *"://"* ]]; then
            echo "  drop the scheme — give host:port only (e.g. otel.example.com:443)" >&2
            endpoint=""
            continue
        fi
        if [[ "${endpoint}" != *:* ]]; then
            echo "  no port found — expected host:port (e.g. otel.example.com:443)" >&2
            endpoint=""
            continue
        fi
        break
    done
    if [[ -z "${endpoint}" ]]; then
        echo "otelbox-edge-config: giving up on endpoint after 3 attempts" >&2
        exit 1
    fi

    local content="OTELBOX_EDGE_ENDPOINT=${endpoint}"
    mkdir -p "$(dirname "${OVERLAY_ENV}")" "$(dirname "${LIVE_ENV}")"
    printf '%s\n' "${content}" >"${OVERLAY_ENV}"
    printf '%s\n' "${content}" >"${LIVE_ENV}"
    chmod 0644 "${OVERLAY_ENV}" "${LIVE_ENV}"
    echo "otelbox-edge-config: wrote endpoint to overlay + live (${endpoint})" >&2
}

_set_token() {
    _require_tty
    local token=""
    local attempt
    for attempt in 1 2 3; do
        printf 'Bearer ingestion token (input hidden): ' >&2
        IFS= read -rs token || true
        printf '\n' >&2
        if [[ -n "${token}" ]]; then
            break
        fi
        echo "  empty input, try again (${attempt}/3)" >&2
    done
    if [[ -z "${token}" ]]; then
        echo "otelbox-edge-config: giving up on token after 3 attempts" >&2
        exit 1
    fi
    /usr/bin/security add-generic-password \
        -U \
        -a "${USER}" \
        -s "${TOKEN_SVC}" \
        -w "${token}" \
        -T /usr/bin/security \
        "${HOME}/Library/Keychains/login.keychain-db" >/dev/null
    echo "otelbox-edge-config: stored '${TOKEN_SVC}' in login keychain" >&2
}

if [[ -z "${_only}" || "${_only}" == "endpoint" ]]; then
    _set_endpoint
fi
if [[ -z "${_only}" || "${_only}" == "token" ]]; then
    _set_token
fi

echo "otelbox-edge-config: done. Restart the service to apply:" >&2
echo "  launchctl kickstart -k gui/\$(id -u)/local.otelbox-edge" >&2
