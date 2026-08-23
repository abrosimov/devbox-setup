#!/usr/bin/env bash
# Interactive one-time machine-local setup for the durable otelbox edge collector.
# Fills the three values that are NOT tracked in the repo:
#
#   endpoint  — the remote gateway authority (host:port, no https://). Non-secret.
#               Written to the gitignored local overlay
#               roles/devbox/local/.config/otelbox/edge/endpoint.env (source of
#               truth, deployed by Ansible) AND live to ~/.config/otelbox/edge/
#               endpoint.env so the running service picks it up immediately.
#   token     — the Bearer ingestion key. The Keychain is authoritative; the
#               collector reads a private header file in the per-user temporary
#               area, which it watches for live rotation.
#   cert      — an optional client-certificate pair for a gateway front end
#               demanding mTLS. Generated here, on this machine: the private key
#               is born locally and never leaves, exactly as the operator's SSH
#               key does not. Both halves go to the gitignored overlay
#               roles/devbox/local/.config/otelbox/edge/client/ (source of truth,
#               deployed by Ansible with modes preserved) AND live to
#               ~/.config/otelbox/edge/client/. Only the PUBLIC half is meant to
#               travel to whoever configures the front end.
#
# Consumed by roles/devbox/files/.config/otelbox/edge/otelbox-edge-run (wrapper)
# and edge.yaml (${env:OTELBOX_UPSTREAM_ENDPOINT} /
# ${env:OTELBOX_UPSTREAM_AUTH_HEADER_FILE} /
# ${env:OTELBOX_UPSTREAM_TLS_CERT_FILE} / ${env:OTELBOX_UPSTREAM_TLS_KEY_FILE}).
# See README.md § OTLP Telemetry.
#
# Invocation:
#   make otelbox-edge-config                    — prompt for endpoint + token
#   make otelbox-edge-config ONLY=cert          — generate the client pair
#   ./scripts/otelbox-edge-config.sh --only endpoint
#   ./scripts/otelbox-edge-config.sh --only token
#   ./scripts/otelbox-edge-config.sh --only cert
#
# `cert` is deliberately NOT part of a bare run: a machine without an mTLS front
# end needs no certificate, and regenerating one invalidates whatever that front
# end already trusts. OTELBOX_CERT_DAYS overrides the 825-day default.
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
readonly OVERLAY_CLIENT_DIR="${REPO_ROOT}/roles/devbox/local/.config/otelbox/edge/client"
readonly LIVE_CLIENT_DIR="${HOME}/.config/otelbox/edge/client"
readonly OVERLAY_CERT="${OVERLAY_CLIENT_DIR}/client.crt"
readonly OVERLAY_KEY="${OVERLAY_CLIENT_DIR}/client.key"
readonly LIVE_CERT="${LIVE_CLIENT_DIR}/client.crt"
readonly LIVE_KEY="${LIVE_CLIENT_DIR}/client.key"
readonly CERT_DAYS="${OTELBOX_CERT_DAYS:-825}"

_workdir=""
_cleanup() {
    if [[ -n "${_workdir}" && -d "${_workdir}" ]]; then
        rm -rf "${_workdir}"
    fi
}
trap _cleanup EXIT

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
            sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "otelbox-edge-config: unknown argument: $1" >&2
            exit 64
            ;;
    esac
done

case "${_only}" in
    "" | endpoint | token | cert) ;;
    *)
        echo "otelbox-edge-config: --only takes 'endpoint', 'token' or 'cert', got '${_only}'" >&2
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
        if [[ ! "${endpoint}" =~ ^[^[:space:]]+:[0-9]+$ ]]; then
            echo "  expected host:numeric-port (e.g. otel.example.com:443)" >&2
            endpoint=""
            continue
        fi
        break
    done
    if [[ -z "${endpoint}" ]]; then
        echo "otelbox-edge-config: giving up on endpoint after 3 attempts" >&2
        exit 1
    fi

    local content="OTELBOX_UPSTREAM_ENDPOINT=${endpoint}"
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
        if [[ "${token}" =~ ^[A-Za-z0-9_-]+$ ]]; then
            break
        fi
        echo "  expected a non-empty [A-Za-z0-9_-] token, try again (${attempt}/3)" >&2
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

    local runtime_root auth_dir auth_file
    runtime_root="$(/usr/bin/getconf DARWIN_USER_TEMP_DIR)"
    auth_dir="${runtime_root%/}/otelbox-edge"
    auth_file="${auth_dir}/upstream-auth-header"
    umask 077
    mkdir -p "${auth_dir}"
    chmod 0700 "${auth_dir}"
    printf 'Bearer %s\n' "${token}" >"${auth_file}"
    echo "otelbox-edge-config: stored '${TOKEN_SVC}' in login keychain" >&2
    echo "otelbox-edge-config: refreshed the private watched header file" >&2
}

_resolve_openssl() {
    local candidate
    candidate="$(command -v openssl 2>/dev/null || true)"
    if [[ -z "${candidate}" ]]; then
        candidate="/usr/bin/openssl"
    fi
    if [[ ! -x "${candidate}" ]]; then
        echo "otelbox-edge-config: no usable openssl (PATH and /usr/bin/openssl)" >&2
        exit 1
    fi
    printf '%s' "${candidate}"
}

# The subject is cosmetic to the protocol — a front end pinning a leaf compares
# the whole certificate — but it is what identifies this machine in the front
# end's logs and in whatever list its operator maintains, so keep it DNS-shaped.
_cert_subject() {
    local host=""
    if [[ -x /usr/sbin/scutil ]]; then
        host="$(/usr/sbin/scutil --get LocalHostName 2>/dev/null || true)"
    fi
    if [[ -z "${host}" ]]; then
        host="$(hostname -s)"
    fi
    host="$(printf '%s' "${host}" | tr -c '[:alnum:]-' '-')"
    host="${host%-}"
    printf 'otelbox-edge-%s' "${host:-unknown}"
}

_set_cert() {
    _require_tty
    local openssl_bin subject fingerprint answer
    openssl_bin="$(_resolve_openssl)"

    if [[ -f "${OVERLAY_CERT}" || -f "${OVERLAY_KEY}" ]]; then
        echo "otelbox-edge-config: a client pair already exists at ${OVERLAY_CLIENT_DIR}" >&2
        echo "  Regenerating invalidates whatever the gateway front end already trusts." >&2
        printf 'Regenerate? [y/N]: ' >&2
        answer=""
        IFS= read -r answer || true
        if [[ ! "${answer}" =~ ^[Yy]$ ]]; then
            echo "otelbox-edge-config: keeping the existing client certificate" >&2
            return 0
        fi
    fi

    subject="$(_cert_subject)"
    _workdir="$(mktemp -d)"
    umask 077

    # Two steps rather than one `req -newkey`: `ecparam -genkey` is the form both
    # OpenSSL 3 and the LibreSSL that ships with macOS accept, so this does not
    # depend on which of the two ends up first on PATH.
    "${openssl_bin}" ecparam -name prime256v1 -genkey -noout -out "${_workdir}/client.key"

    # A config file rather than -addext, for the same portability reason.
    cat >"${_workdir}/openssl.cnf" <<EOF
[req]
distinguished_name = dn
prompt = no

[dn]
CN = ${subject}

[v3_client]
basicConstraints = critical,CA:FALSE
keyUsage = critical,digitalSignature
extendedKeyUsage = clientAuth
subjectAltName = DNS:${subject}
subjectKeyIdentifier = hash
EOF

    "${openssl_bin}" req -new -x509 \
        -key "${_workdir}/client.key" \
        -out "${_workdir}/client.crt" \
        -days "${CERT_DAYS}" \
        -sha256 \
        -config "${_workdir}/openssl.cnf" \
        -extensions v3_client >/dev/null 2>&1

    mkdir -p "${OVERLAY_CLIENT_DIR}" "${LIVE_CLIENT_DIR}"
    # 0700 on both: the overlay directory is what Ansible's filetree copy takes
    # the deployed mode from, so the private half never widens in transit.
    chmod 0700 "${OVERLAY_CLIENT_DIR}" "${LIVE_CLIENT_DIR}"
    install -m 0600 "${_workdir}/client.key" "${OVERLAY_KEY}"
    install -m 0644 "${_workdir}/client.crt" "${OVERLAY_CERT}"
    install -m 0600 "${_workdir}/client.key" "${LIVE_KEY}"
    install -m 0644 "${_workdir}/client.crt" "${LIVE_CERT}"

    fingerprint="$("${openssl_bin}" x509 -in "${OVERLAY_CERT}" -noout -fingerprint -sha256 | sed 's/^.*=//')"
    echo "otelbox-edge-config: generated client certificate CN=${subject}" >&2
    echo "  overlay (source of truth): ${OVERLAY_CERT}" >&2
    echo "  live:                      ${LIVE_CERT}" >&2
    echo "  validity:                  ${CERT_DAYS} days" >&2
    echo "  SHA-256 fingerprint:       ${fingerprint}" >&2
    echo "  Only client.crt is meant to travel; the key stays on this machine." >&2
}

if [[ -z "${_only}" || "${_only}" == "endpoint" ]]; then
    _set_endpoint
fi
if [[ -z "${_only}" || "${_only}" == "token" ]]; then
    _set_token
fi
if [[ "${_only}" == "cert" ]]; then
    _set_cert
fi

if [[ -z "${_only}" || "${_only}" == "endpoint" ]]; then
    echo "otelbox-edge-config: restart the service to apply the endpoint:" >&2
    echo "  launchctl kickstart -k gui/\$(id -u)/local.otelbox-edge" >&2
elif [[ "${_only}" == "cert" ]]; then
    # A collector that started without a pair holds empty cert paths for its
    # lifetime; reload_interval only re-reads paths it was configured with. So
    # the first generation needs a restart and a later rotation does not.
    echo "otelbox-edge-config: restart once so the collector picks the pair up at all:" >&2
    echo "  launchctl kickstart -k gui/\$(id -u)/local.otelbox-edge" >&2
    echo "  Later regenerations are re-read within OTELBOX_UPSTREAM_TLS_RELOAD_INTERVAL (1h)." >&2
else
    echo "otelbox-edge-config: token rotated; the running collector watches the header file." >&2
fi
