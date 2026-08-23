#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "usage: otelbox-edge-cert-check.sh CERT_FILE KEY_FILE" >&2
    exit 64
fi

cert_file="$1"
key_file="$2"

for path in "${cert_file}" "${key_file}"; do
    if [[ ! -f "${path}" || ! -r "${path}" ]]; then
        echo "otelbox-edge-cert-check: file is missing or unreadable: ${path}" >&2
        exit 78
    fi
done

openssl_bin="$(command -v openssl 2>/dev/null || true)"
if [[ -z "${openssl_bin}" && -x /usr/bin/openssl ]]; then
    openssl_bin=/usr/bin/openssl
fi
if [[ -z "${openssl_bin}" || ! -x "${openssl_bin}" ]]; then
    echo "otelbox-edge-cert-check: no usable openssl" >&2
    exit 69
fi

workdir="$(mktemp -d)"
_cleanup() {
    rm -rf "${workdir}"
}
trap _cleanup EXIT

if ! "${openssl_bin}" x509 -in "${cert_file}" -noout -checkend 0 >/dev/null 2>&1; then
    echo "otelbox-edge-cert-check: certificate is invalid or expired: ${cert_file}" >&2
    exit 78
fi
if ! "${openssl_bin}" x509 -in "${cert_file}" -pubkey -noout >"${workdir}/cert.pub" 2>/dev/null; then
    echo "otelbox-edge-cert-check: cannot read certificate public key: ${cert_file}" >&2
    exit 78
fi
if ! "${openssl_bin}" pkey -in "${key_file}" -pubout >"${workdir}/key.pub" 2>/dev/null; then
    echo "otelbox-edge-cert-check: private key is invalid or encrypted: ${key_file}" >&2
    exit 78
fi
if ! cmp -s "${workdir}/cert.pub" "${workdir}/key.pub"; then
    echo "otelbox-edge-cert-check: certificate and private key do not match" >&2
    exit 78
fi
