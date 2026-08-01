# otelcol-edge

OCB-built durable OpenTelemetry **edge** collector for devbox workstations.
Replaces the former `homebrew-otelbox` tap + `local-telemetry-server` two-tier
setup: no Homebrew, no tap, no separate repo. The collector binary is built in
CI from `builder.yaml`, published as a GitHub release, and installed +
supervised by Ansible (`launchd`).

## What it does

```
local apps → 127.0.0.1:4317 / :4318 (loopback OTLP)
           → memory_limiter → resourcedetection → redaction → batch
           → OTLP/gRPC with file_storage-backed persistent WAL
           → one remote gateway (${env:OTELBOX_EDGE_ENDPOINT})
```

The on-disk `file_storage` queue buffers the workstation→gateway hop across
network outages, gateway restarts, and clean collector restarts. It is delivery
state, not a dead-letter queue or archive (see the pinned upstream
[persistent queue docs](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.156.0/exporter/exporterhelper/README.md#persistent-queue)).

## Components

Two different sets, and the distinction matters:

- **Linked** — everything in `builder.yaml`. Compiled into the binary, available
  to any config, costs binary size only. Currently 41: 18 receivers, 8
  processors, 3 exporters, 7 extensions, 5 connectors.
- **Wired** — what the deployed config layers actually instantiate. Currently 7,
  listed below. The rest of the linked set is dormant until a pipeline
  references it, which needs no rebuild.

| Kind | Component | Repo | Wired in |
|------|-----------|------|----------|
| receiver | `otlp` | core | `base.yaml` |
| processor | `memory_limiter`, `batch` | core | `base.yaml` |
| processor | `resourcedetection`, `redaction` | contrib | `base.yaml` |
| exporter | `otlp` (gRPC) | core | `config.gateway.yaml` |
| extension | `health_check` | contrib | `base.yaml` |
| extension | `file_storage` | contrib | `config.gateway.yaml` |

CI enforces the linked set: `smoke-check.sh` compares per-kind counts from
`builder.yaml` against the built binary's own `components` output, so a dropped
component fails the build rather than shipping a silently thin binary. Counts,
not names — a component reports its type, not its module path, and the two do
not map mechanically (`resourcedetectionprocessor` → `resource_detection`,
`otlpexporter` → `otlp_grpc`).

## Release flow

1. Edit `builder.yaml`. `dist.version` is `<upstream>-custom-<n>`: bump the
   upstream part in lockstep with the `gomod` pins, or bump only `-custom-<n>`
   when the component set changes at the same upstream. CI rejects a mismatch
   between the two. Nothing to bump in
   `roles/devbox/defaults/main/packages.yml` — the task reads `dist.version`
   from this file directly.
2. Merge to master. The push triggers `.github/workflows/otelcol-edge.yml`
   (`on.push.paths: otelcol-edge/builder.yaml`) — **do not cut a tag by hand**,
   there is no tag trigger and pushing one does nothing. CI builds
   `darwin/arm64` via OCB, runs `smoke-check.sh`, and publishes
   `otelcol-edge_darwin_arm64` + `.sha256` to the `otelcol-edge-v<version>`
   release, which it creates. To rebuild an existing version, delete the
   release first, then `gh workflow run otelcol-edge.yml`.

   The OCB toolchain is installed at the **upstream** part of `dist.version`
   only: `-custom-<n>` names our component set and has no upstream tag, so
   `go install ...cmd/builder@v<dist.version>` would 404 (it parses as a valid
   semver pre-release, so the failure surfaces as a missing revision, not a
   syntax error).
3. Run `make personal` / `make work`. Ansible downloads the pinned binary,
   deploys the config layers + wrapper + LaunchAgent, and bootstraps the service.

**Ordering matters:** the release must exist before the full run pulls it. If it
does not, the download step warns and the service is skipped (no crash).

## Machine-local setup (once per machine)

Both values are set interactively by `make otelcol-edge-config` (add
`ONLY=endpoint` / `ONLY=token` to set just one). It needs a TTY. What it writes:

- **Endpoint** (non-secret) — to the gitignored local overlay
  `roles/devbox/local/.config/otelcol-edge/endpoint.env` (source of truth,
  deployed by Ansible) *and* live to `~/.config/otelcol-edge/endpoint.env`, so a
  restart picks it up without a full playbook run. Format:
  `OTELBOX_EDGE_ENDPOINT=otel.example.com:443` — `host:port`, no scheme. See
  `endpoint.env.example`.
- **Ingestion key** (secret) — to the login keychain slot `otelbox-edge-token`,
  never on disk. Added with `-T /usr/bin/security` so the wrapper's
  `find-generic-password` reads it silently after one "Always Allow".

Restart the service to apply either:
`launchctl kickstart -k gui/$(id -u)/local.otelcol-edge`.
Verify with `make otelcol-edge-test`.
