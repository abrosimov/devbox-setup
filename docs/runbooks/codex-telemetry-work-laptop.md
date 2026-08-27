# Codex telemetry check from the work laptop

Use this runbook for one controlled Codex turn and follow the signal from the
work laptop to the local otelbox edge, Caddy, the gateway, and Langfuse. Run it
from the `devbox-setup` checkout on the work laptop.

## What this check proves

There are two related but separate telemetry paths:

```text
Codex native logs and metrics
  -> 127.0.0.1:4317
  -> otelbox edge
  -> Caddy :443 with mTLS
  -> otelbox gateway with a bearer credential
  -> observability backends

Codex Langfuse plugin traces
  -> trusted plugin Stop hook
  -> 127.0.0.1:14318/api/public/otel/v1/traces
  -> otelbox edge, classified as llm
  -> the same Caddy and gateway
  -> Langfuse
```

Important facts:

- `environment = "personal"` is an event tag, not an export permission or an
  on/off switch. Search Langfuse using that environment even on the work
  laptop if that is the applied profile.
- The managed Codex configuration deliberately sets native
  `trace_exporter = "none"`. Native Codex logs and metrics still go to port
  `4317`; Langfuse traces come from the separate plugin.
- The Langfuse plugin sends after a completed Codex turn through its trusted
  `Stop` hook. A long parent turn that has not stopped is not a valid delivery
  test, even if subagents ran during it.
- `make personal` and `make work` run the edge smoke non-fatally. Always run
  `make otelbox-edge-test` explicitly for this diagnosis.

## Safety rules

- Do not paste a Keychain value, bearer header, private key, complete
  `~/.codex/langfuse.json`, certificate PEM, or environment dump into email or
  chat.
- The commands below report only presence, public certificate metadata, safe
  configuration fields, counters, and errors. Review collector logs before
  forwarding them.
- Server commands are intentionally a separate section. Run them only when you
  deliberately choose to inspect the managed host; the laptop-only checks do
  not require SSH.

## 1. Record the test window

```bash
export CODEX_TELEMETRY_CHECK_START="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
printf 'check-start=%s\n' "$CODEX_TELEMETRY_CHECK_START"
codex --version
git status --short --branch
```

Keep the UTC timestamp. It is the correlation point for the laptop, Caddy,
gateway, and Langfuse checks.

## 2. Run the repository-owned edge smoke

```bash
make otelbox-edge-test
```

The expected final line is:

```text
otelbox-edge: all checks passed
```

This proves the pinned binary is present, the LaunchAgent is loaded, health and
self-metrics respond, local OTLP/HTTP accepts a test log, and no exporter send,
enqueue, receiver, or high-queue failure is currently visible. It is the
baseline; the controlled trace below proves the plugin path specifically.

If this step fails, keep the full output and continue with sections 4 and 6.

## 3. Check the effective Codex and plugin configuration

Show only the managed OTel fields:

```bash
rg -n '^\[otel\]|^environment =|^exporter =|^trace_exporter =|^metrics_exporter =' \
  ~/.codex/config.toml
find ~/.codex -maxdepth 1 -name '*.config.toml' -print
```

Expected base values:

```text
[otel]
environment = "personal"        # or the intentionally applied profile
exporter = ...127.0.0.1:4317
trace_exporter = "none"
metrics_exporter = ...127.0.0.1:4317
```

Codex 0.134.0 and later overlays `~/.codex/<name>.config.toml` when launched
with `--profile <name>`. If such a file exists, inspect only its `[otel]`
section and account for any override. Do not treat the word `personal` itself
as the failure.

Check the installed tracing plugin and its safe runtime fields:

```bash
codex plugin list --available --json | \
  jq '.installed[] | select(.pluginId == "tracing@codex-observability-plugin") |
      {pluginId, version, enabled}'

jq '{enabled, base_url, environment, debug, fail_on_error}' \
  ~/.codex/langfuse.json

if [[ -f "$PWD/.codex/langfuse.json" ]]; then
  jq '{enabled, base_url, environment, debug, fail_on_error}' \
    "$PWD/.codex/langfuse.json"
fi

env | rg '^(TRACE_TO_LANGFUSE|LANGFUSE_CODEX_(BASE_URL|ENVIRONMENT|DEBUG|FAIL_ON_ERROR)|LANGFUSE_(BASE_URL|TRACING_ENVIRONMENT))='
```

Expected values are an enabled plugin, base URL
`http://127.0.0.1:14318`, and the intended environment. A project-local
`.codex/langfuse.json` or one of the listed environment variables can override
the user-level file. The command deliberately excludes Langfuse keys.

If `codex plugin list` is unavailable in the installed CLI, open `/plugins` in
Codex and confirm that `tracing@codex-observability-plugin` is installed and
enabled.

Now open `/hooks` in Codex. Review and trust the current `Stop` hook belonging
to `tracing@codex-observability-plugin`. Trust is hash-specific and is not
automated by the devbox playbook.

Check recent normal Stop events and plugin sidecars:

```bash
jq -r 'select(.event == "Stop") | [.timestamp, .event] | @tsv' \
  ~/.codex/state/hook_events.jsonl | tail -10

find ~/.codex/sessions -type f -name '*.langfuse' -mmin -1440 -print | tail -20
```

The universal hook log proves that a normal `Stop` event occurred. It does not
prove that the plugin hook is trusted. A new `.langfuse` sidecar is evidence
that the plugin processed a session, but it is not proof of remote delivery.

## 4. Check the local collector and machine-local inputs

```bash
launchctl print "gui/$(id -u)/local.otelbox-edge" | \
  rg 'state =|pid =|last exit code'

curl -fsS http://127.0.0.1:13133/status

lsof -nP -iTCP:4317 -iTCP:14318 -sTCP:LISTEN
```

Expected: a running LaunchAgent, healthy lifecycle endpoint, and the edge
collector listening on both ports.

Check the endpoint, Keychain slot, and certificate without displaying a
secret:

```bash
test -s ~/.config/otelbox/edge/endpoint.env && echo endpoint-present
awk -F= '/^OTELBOX_UPSTREAM_ENDPOINT=/{print $2}' \
  ~/.config/otelbox/edge/endpoint.env

security find-generic-password -a "$USER" -s otelbox-edge-token \
  >/dev/null && echo token-present

scripts/otelbox-edge-cert-check.sh \
  ~/.config/otelbox/edge/client/client.crt \
  ~/.config/otelbox/edge/client/client.key

openssl x509 -in ~/.config/otelbox/edge/client/client.crt \
  -noout -subject -dates -fingerprint -sha256
```

Expected endpoint: `otel.abrosimov.tech:443`. The certificate check must exit
zero and the certificate must be current. Save its SHA-256 fingerprint for
comparison with the current Caddy client-certificate roster; the fingerprint
is public metadata, but the private key is never copied.

If an input is missing, repair it through the repository-owned workflow rather
than editing generated live files:

```bash
make otelbox-edge-config ONLY=endpoint
make otelbox-edge-config ONLY=token
make otelbox-edge-config ONLY=cert
```

Regenerating the certificate changes the client identity. Do not run
`ONLY=cert` merely as a diagnostic: the new public certificate must first be
added to the Caddy roster and deployed. If the existing certificate and key
pass the check, keep them.

## 5. Send one controlled Langfuse trace

First record the relevant counters:

```bash
curl -fsS http://127.0.0.1:8888/metrics | rg \
  '^otelcol_(receiver_accepted_(spans|log_records|metric_points)|receiver_refused_(spans|log_records|metric_points)|exporter_(sent|send_failed|enqueue_failed)_(spans|log_records|metric_points)|exporter_queue_(size|capacity))'
```

Start a fresh Codex CLI with temporary plugin diagnostics:

```bash
LANGFUSE_CODEX_DEBUG=true LANGFUSE_CODEX_FAIL_ON_ERROR=true codex
```

Send one non-sensitive prompt containing the UTC test timestamp, for example:

```text
Reply only with: telemetry-check-2026-08-31T05:00:00Z
```

Wait for the answer and for the turn to finish. Then end the CLI normally so
the asynchronous native exporter can flush. Do not kill the process. The
temporary environment variables apply only to this CLI process and make a
normally swallowed plugin conversion or flush error visible.

After five to ten seconds, run the counter command again:

```bash
curl -fsS http://127.0.0.1:8888/metrics | rg \
  '^otelcol_(receiver_accepted_(spans|log_records|metric_points)|receiver_refused_(spans|log_records|metric_points)|exporter_(sent|send_failed|enqueue_failed)_(spans|log_records|metric_points)|exporter_queue_(size|capacity))'
```

The strongest laptop-side result is:

- `receiver_accepted_spans` for `receiver="otlp/langfuse_plugins"` increases;
- `exporter_sent_spans` increases;
- refused, send-failed, and enqueue-failed counters do not increase;
- the exporter queue returns to zero or its prior idle value.

An increase in `exporter_sent_spans` means the remote OTLP gateway acknowledged
a span. If other applications are producing spans concurrently, repeat in a
quiet one-minute window before attributing an aggregate delta to this turn.

## 6. Inspect edge errors

```bash
rg -i 'error|warn|retry|auth|tls|certificate|unavailable|timeout|export|queue|refus' \
  ~/Library/Logs/otelbox-edge.log | tail -120
```

Classify the newest errors after `CODEX_TELEMETRY_CHECK_START`:

| Evidence | Likely boundary |
| --- | --- |
| No plugin `receiver_accepted_spans` increase | Codex plugin, hook trust, override, or local port `14318` |
| Accepted spans increase; queue grows or send fails | Edge to Caddy/gateway leg |
| TLS, certificate, or handshake error | Caddy mTLS: missing, expired, mismatched, or untrusted client certificate |
| `Unauthenticated`, authentication failure, or HTTP 401 | Gateway bearer credential mismatch |
| `Unavailable`, DNS, connection refused, or timeout | DNS, corporate network, firewall, Caddy availability, or routing |
| Sent spans increase and queue drains | Caddy and gateway acknowledged delivery; inspect downstream routing and Langfuse filters |

Do not infer a compression problem unless the log explicitly names a codec or
decompression error.

## 7. Prove that the laptop reaches Caddy

This is an optional direct TLS probe from the work laptop. It connects to the
managed public ingress but does not send a bearer credential or telemetry:

```bash
openssl s_client \
  -connect otel.abrosimov.tech:443 \
  -servername otel.abrosimov.tech \
  -alpn h2 \
  -cert ~/.config/otelbox/edge/client/client.crt \
  -key ~/.config/otelbox/edge/client/client.key \
  -verify_return_error </dev/null 2>&1 | \
  rg 'subject=|issuer=|ALPN protocol|Verify return code|alert|error'
```

`Verify return code: 0 (ok)` plus `ALPN protocol: h2` proves DNS, TCP, server
certificate verification, and completion of Caddy's mTLS handshake. It does
not prove gateway bearer authentication; the exporter counters and gateway
logs cover that boundary.

## 8. Correlate Caddy and gateway journals

Run this section on the managed server only when server inspection is
deliberately authorised. Execute it immediately after the controlled turn so a
relative window is sufficient:

```bash
sudo journalctl -u caddy.service --since '20 minutes ago' -o cat | \
  grep -Ei 'otel\.abrosimov\.tech|tls|handshake|certificate|/v1/(traces|logs|metrics)|error'

sudo journalctl --since '20 minutes ago' \
  _SYSTEMD_USER_UNIT=observability-otelbox-gateway.service -o cat | \
  grep -Ei 'auth|unauth|trace|export|queue|retry|langfuse|error|warn'
```

Interpret the pair, not either journal in isolation:

| Caddy | Gateway | Conclusion |
| --- | --- | --- |
| No connection or request in the test window | No event | The request stopped on the laptop, DNS/network path, or before ingress |
| TLS handshake error; no access request | No event | The laptop reached Caddy, but mTLS rejected the client certificate |
| Request is visible | Authentication failure or `Unauthenticated` | Caddy passed the connection; the bearer credential failed at the gateway |
| Request is visible | Gateway accepts and exports the spans | Caddy/gateway reach is proven; continue with downstream/Langfuse checks |
| Request is visible | Gateway queue/retry grows | Gateway accepted ingress but cannot deliver to a downstream backend |

Caddy access logs cannot prove that a failed TLS handshake never happened;
use the direct Caddy service journal for handshake errors.

## 9. Search Langfuse correctly

Search around `CODEX_TELEMETRY_CHECK_START` and use these filters or names:

- environment: `personal` if that is what the live config reported;
- trace names: `Codex Turn` and `Codex Subagent Turn`;
- generation names: `LLM` and `LLM Subagent`;
- service name may appear as `unknown_service:node`;
- use the controlled turn's completion/ingestion window, not only the start of
  a long parent session.

If the edge `exporter_sent_spans` counter increased and the gateway confirmed
an accepted/exported span but Langfuse still shows nothing, the remaining
scope is gateway classification, gateway-to-Langfuse export/WAL, Langfuse
ingestion, or the UI time/environment filters. It is no longer a work-laptop
transport problem.

## Decision checklist

- [ ] `make otelbox-edge-test` passes when run explicitly.
- [ ] Live Codex OTel export points to `127.0.0.1:4317`.
- [ ] Langfuse plugin is enabled and points to `127.0.0.1:14318`.
- [ ] No project file or environment variable overrides the plugin unexpectedly.
- [ ] The current plugin `Stop` hook is trusted in `/hooks`.
- [ ] A controlled turn produces a normal `Stop` event.
- [ ] The collector accepts plugin spans.
- [ ] The collector sends spans and its queue drains.
- [ ] The direct TLS probe completes Caddy mTLS, if run.
- [ ] Caddy and gateway journals agree with the laptop counters, if inspected.
- [ ] Langfuse is searched using the actual environment and test window.

## Safe email summary template

```text
Codex telemetry check
UTC window:
Workstation/profile:
Codex version:

Explicit edge smoke: PASS / FAIL
Plugin installed and enabled: YES / NO
Plugin Stop hook trusted: YES / NO
Latest controlled Stop timestamp:
Local 4317 and 14318 listeners: YES / NO
Endpoint present: YES / NO
Keychain token present: YES / NO
Certificate check: PASS / FAIL
Certificate SHA-256 fingerprint:

Plugin accepted-spans before -> after:
Exporter sent-spans before -> after:
Send/enqueue/refused counters before -> after:
Queue size before -> after:
Newest edge error class:

Caddy TLS probe: PASS / FAIL / NOT RUN
Caddy journal result: REACHED / TLS REJECTED / NO ATTEMPT / NOT CHECKED
Gateway journal result: ACCEPTED / AUTH REJECTED / DOWNSTREAM RETRY / NO EVENT / NOT CHECKED
Langfuse controlled trace: FOUND / NOT FOUND

Narrowest failing boundary:
Next action:
```

Do not attach token values, authentication headers, private keys, PEM files,
complete configuration files, or an unreviewed environment dump.

## Source references

- [OpenAI Advanced Configuration: profiles and observability](https://learn.chatgpt.com/docs/config-file/config-advanced)
- [OpenAI Configuration Reference: `otel.*` keys](https://learn.chatgpt.com/docs/config-file/config-reference)
- [devbox otelbox edge overview](../../README.md#otlp-telemetry-otelbox-edge)
- [edge smoke implementation](../../scripts/otelbox-edge-test.sh)
- [certificate/key validation](../../scripts/otelbox-edge-cert-check.sh)
- [managed Codex configuration](../../roles/devbox/files/dot_codex/config.toml.j2)
- [managed Langfuse plugin configuration](../../roles/devbox/files/dot_codex/langfuse.json.j2)
- [edge collector profile](../../roles/devbox/files/.config/otelbox/edge/edge.yaml)
