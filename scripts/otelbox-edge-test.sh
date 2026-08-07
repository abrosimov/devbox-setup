#!/usr/bin/env bash
# Liveness smoke for the otelbox edge collector — run after `make personal`.
# Checks the exact binary, service lifecycle, local ingest and delivery signals.
# Exit non-zero on any failure. Darwin-only.
# No set -e/pipefail: every check must run even when a probe curl fails; the
# final exit is driven by the explicit `fail` flag, not the first failing probe.
#
# The delivery check is the local counterpart of the artefact repository's
# TestEdgeToGatewayDelivery. Do not weaken it into a liveness check: it exists
# because a wrong ingestion token once left every other check on this list green
# while the telemetry went nowhere for days.
set -u

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "otelbox-edge-test: macOS only." >&2
    exit 0
fi

fail=0
_ok() { printf '  ok    %s\n' "$1"; }
_bad() {
    printf '  FAIL  %s\n' "$1" >&2
    fail=1
}

sum_metric() {
    curl -fsS --max-time 3 http://127.0.0.1:8888/metrics 2>/dev/null \
        | awk -v pat="$1" '$0 ~ pat {s += $NF} END {printf "%d\n", s}'
}

accepted_logs() { sum_metric '^otelcol_receiver_accepted_log_records'; }

max_queue_percent() {
    curl -fsS --max-time 3 http://127.0.0.1:8888/metrics 2>/dev/null \
        | awk '
            $1 ~ /^otelcol_exporter_queue_capacity\{/ {
                key = $1
                sub(/^otelcol_exporter_queue_capacity/, "", key)
                capacity[key] = $NF
            }
            $1 ~ /^otelcol_exporter_queue_size\{/ {
                key = $1
                sub(/^otelcol_exporter_queue_size/, "", key)
                size[key] = $NF
            }
            END {
                found = 0
                max = 0
                for (key in size) {
                    if (capacity[key] > 0) {
                        found = 1
                        percent = 100 * size[key] / capacity[key]
                        if (percent > max) max = percent
                    }
                }
                if (found) printf "%.0f\n", max
                else print "-1"
            }
        '
}

bin="${HOME}/.local/bin/otelcol-otelbox"
if [[ -x "${bin}" ]] && version=$("${bin}" --version 2>/dev/null) \
    && [[ "${version}" == *"version 2.1.0"* ]]; then
    _ok "binary v2.1.0: ${bin}"
else
    _bad "binary missing or not v2.1.0: ${bin}"
fi

if info=$(launchctl print "gui/$(id -u)/local.otelbox-edge" 2>/dev/null); then
    state=$(printf '%s\n' "${info}" | awk -F'= ' '/state = /{print $2; exit}')
    _ok "service state: ${state:-unknown}"
else
    _bad "service not loaded (launchctl print failed)"
fi

health_ok=0
for _ in 1 2 3 4 5; do
    if curl -fsS --max-time 3 http://127.0.0.1:13133/status >/dev/null 2>&1; then
        health_ok=1
        break
    fi
    sleep 1
done
if [[ "${health_ok}" -eq 1 ]]; then
    _ok "lifecycle health :13133/status"
else
    _bad "lifecycle health :13133/status not responding"
fi

if accepted_logs >/dev/null && curl -fsS --max-time 3 http://127.0.0.1:8888/metrics 2>/dev/null | grep -q '^otelcol_'; then
    _ok "metrics :8888"
else
    _bad "metrics :8888 not serving otelcol_ metrics"
fi

before=$(accepted_logs)
if curl -fsS --max-time 3 -H 'Content-Type: application/json' \
    -d '{"resourceLogs":[{"scopeLogs":[{"logRecords":[{"body":{"stringValue":"otelbox-edge-test"}}]}]}]}' \
    http://127.0.0.1:4318/v1/logs >/dev/null 2>&1; then
    sleep 1
    after=$(accepted_logs)
    if [[ "${after}" -gt "${before}" ]]; then
        _ok "OTLP round-trip: receiver accepted the test log (${before} -> ${after})"
    else
        _bad "receiver_accepted_log_records did not increase (${before} -> ${after})"
    fi
else
    _bad "OTLP/HTTP :4318 rejected the test log"
fi

dropped=$(sum_metric '^otelcol_exporter_send_failed_')
enqueue_failed=$(sum_metric '^otelcol_exporter_enqueue_failed_')
refused=$(sum_metric '^otelcol_receiver_refused_')
queue_percent=$(max_queue_percent)
if [[ "${dropped}" -eq 0 && "${enqueue_failed}" -eq 0 && "${refused}" -eq 0 \
    && "${queue_percent}" -ge 0 && "${queue_percent}" -lt 80 ]]; then
    _ok "gateway delivery: max queue ${queue_percent}%; no send, enqueue or receive failures"
else
    _bad "gateway delivery: send_failed=${dropped}, enqueue_failed=${enqueue_failed}, refused=${refused}, max_queue=${queue_percent}%"
fi

if [[ "${fail}" -eq 0 ]]; then
    echo "otelbox-edge: all checks passed"
else
    echo "otelbox-edge: FAILED — see above; tail ~/Library/Logs/otelbox-edge.log" >&2
    exit 1
fi
