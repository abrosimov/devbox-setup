#!/usr/bin/env bash
# Post-build smoke check for the OCB-built otelcol-edge binary.
#
# Verifies that every component declared in builder.yaml actually made it into
# the binary, by comparing per-kind counts from the manifest against the
# binary's own `components` output. Counts rather than names, deliberately:
# a component's reported name is its type, not its Go module path, and the two
# do not map mechanically (resourcedetectionprocessor → resource_detection,
# otlpexporter → otlp_grpc, otlpreceiver → otlp). Counts are derivable from both
# sides without a hand-maintained translation table that would rot on every bump.
#
# On top of the counts, two components are asserted by name because they carry
# the invariants the edge exists for: file_storage (durability — the WAL that
# survives outages) and redaction (privacy — credential stripping before export).
#
# Usage: ./otelcol-edge/smoke-check.sh <binary> [builder.yaml]
# Exits non-zero with a per-kind diff on any mismatch.

set -euo pipefail

readonly KINDS="receivers processors exporters extensions connectors"

bin="${1:-}"
manifest="${2:-otelcol-edge/builder.yaml}"

if [[ -z "${bin}" ]]; then
    echo "usage: $0 <binary> [builder.yaml]" >&2
    exit 64
fi
if [[ ! -x "${bin}" ]]; then
    echo "smoke-check: '${bin}' is not an executable" >&2
    exit 66
fi
if [[ ! -f "${manifest}" ]]; then
    echo "smoke-check: '${manifest}' not found" >&2
    exit 66
fi

# Both files are YAML with the component kinds as top-level keys; entries are
# `- gomod:` in the manifest and `- name:` in the binary's output. `kinds` seeds
# every counter to 0 so an entirely missing section reports as 0, not as absent
# (the binary prints `connectors: []` when none are linked).
_count() {
    awk -v kinds="${KINDS}" -v entry="$1" '
        BEGIN {
            split(kinds, k, " ")
            for (i in k) n[k[i]] = 0
        }
        /^[a-z_]+:/ {
            section = $1
            sub(/:.*/, "", section)
            next
        }
        $0 ~ entry {
            if (section in n) n[section]++
        }
        END {
            split(kinds, k, " ")
            for (i = 1; i <= length(k); i++) printf "%s %d\n", k[i], n[k[i]]
        }
    '
}

declared="$(_count '^[[:space:]]*-[[:space:]]*gomod:' <"${manifest}")"
linked="$("${bin}" components | _count '^[[:space:]]*-[[:space:]]*name:')"

failed=0
for kind in ${KINDS}; do
    want="$(printf '%s\n' "${declared}" | awk -v k="${kind}" '$1 == k { print $2 }')"
    got="$(printf '%s\n' "${linked}" | awk -v k="${kind}" '$1 == k { print $2 }')"
    if [[ "${want}" != "${got}" ]]; then
        echo "smoke-check: ${kind}: builder.yaml declares ${want}, binary links ${got}" >&2
        failed=1
    else
        echo "smoke-check: ${kind}: ${got} ✓"
    fi
done

for required in file_storage redaction; do
    if ! "${bin}" components | grep -q "name: ${required}$"; then
        echo "smoke-check: required component '${required}' missing from the binary" >&2
        failed=1
    else
        echo "smoke-check: ${required} present ✓"
    fi
done

if [[ "${failed}" -ne 0 ]]; then
    echo "smoke-check: FAILED — the built binary does not match builder.yaml" >&2
    exit 1
fi

echo "smoke-check: OK"
