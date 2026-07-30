#!/usr/bin/env bash
# Liveness smoke for the otelcol-edge collector — run after `make personal`.
# Checks: binary, launchd service, health (:13133), internal metrics (:8888),
# and one OTLP/HTTP round-trip (send a log, confirm the receiver accepted it).
# Exit non-zero on any failure. Darwin-only.
# No set -e/pipefail: every check must run even when a probe curl fails; the
# final exit is driven by the explicit `fail` flag, not the first failing probe.
set -u

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "otelcol-edge-test: macOS only." >&2
    exit 0
fi

fail=0
_ok() { printf '  ok    %s\n' "$1"; }
_bad() {
    printf '  FAIL  %s\n' "$1" >&2
    fail=1
}

accepted_logs() {
    curl -fsS --max-time 3 http://127.0.0.1:8888/metrics 2>/dev/null \
        | awk '/^otelcol_receiver_accepted_log_records/ {s += $NF} END {print s + 0}'
}

bin="${HOME}/.local/bin/otelcol-edge"
if [[ -x "${bin}" ]]; then
    _ok "binary ${bin}"
else
    _bad "binary missing: ${bin} (publish the release, then make personal)"
fi

if info=$(launchctl print "gui/$(id -u)/local.otelcol-edge" 2>/dev/null); then
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
    -d '{"resourceLogs":[{"scopeLogs":[{"logRecords":[{"body":{"stringValue":"otelcol-edge-test"}}]}]}]}' \
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

if [[ "${fail}" -eq 0 ]]; then
    echo "otelcol-edge: all checks passed"
else
    echo "otelcol-edge: FAILED — see above; tail ~/Library/Logs/otelcol-edge.log" >&2
    exit 1
fi
