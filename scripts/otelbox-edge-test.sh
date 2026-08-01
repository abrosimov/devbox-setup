#!/usr/bin/env bash
# Liveness smoke for the otelbox edge collector — run after `make personal`.
# Checks: binary, launchd service, health (:13133), internal metrics (:8888),
# one OTLP/HTTP round-trip (send a log, confirm the receiver accepted it), and
# delivery to the remote gateway (no permanently dropped items).
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

bin="${HOME}/.local/bin/otelcol-otelbox"
if [[ -x "${bin}" ]]; then
    _ok "binary ${bin}"
else
    _bad "binary missing: ${bin} (check the pinned version in packages.yml, then make personal)"
fi

if info=$(launchctl print "gui/$(id -u)/local.otelbox-edge" 2>/dev/null); then
    state=$(printf '%s\n' "${info}" | awk -F'= ' '/state = /{print $2; exit}')
    _ok "service state: ${state:-unknown}"
else
    _bad "service not loaded (launchctl print failed)"
fi

# Retry: right after `make personal` the collector may still be binding ports.
health_ok=0
for _ in 1 2 3 4 5; do
    if curl -fsS --max-time 3 http://127.0.0.1:13133/ >/dev/null 2>&1; then
        health_ok=1
        break
    fi
    sleep 1
done
if [[ "${health_ok}" -eq 1 ]]; then
    _ok "health :13133"
else
    _bad "health :13133 not responding"
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

# Delivery to the remote gateway. Everything above only proves the LOCAL half:
# a wrong ingestion token leaves every check green while nothing reaches the
# gateway. send_failed_* counts items the exporter gave up on, and with
# retry_on_failure.max_elapsed_time: 0s only PERMANENT errors (auth, malformed)
# reach it — transient ones retry forever. So any non-zero value means dropped,
# not delayed.
dropped=$(sum_metric '^otelcol_exporter_send_failed_')
queued=$(sum_metric '^otelcol_exporter_queue_size')
if [[ "${dropped}" -eq 0 ]]; then
    _ok "gateway delivery: nothing dropped (queue depth ${queued})"
else
    _bad "gateway delivery: ${dropped} items dropped permanently (queue depth ${queued}); grep 'Exporting failed' ~/Library/Logs/otelbox-edge.log"
fi

if [[ "${fail}" -eq 0 ]]; then
    echo "otelbox-edge: all checks passed"
else
    echo "otelbox-edge: FAILED — see above; tail ~/Library/Logs/otelbox-edge.log" >&2
    exit 1
fi
