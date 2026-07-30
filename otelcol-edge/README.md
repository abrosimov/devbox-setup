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

## Components (only these 7 are linked in)

| Kind | Component | Repo |
|------|-----------|------|
| receiver | `otlp` | core |
| processor | `memory_limiter`, `batch` | core |
| processor | `resourcedetection`, `redaction` | contrib |
| exporter | `otlp` (gRPC) | core |
| extension | `health_check`, `file_storage` | contrib |

## Release flow

1. Edit `builder.yaml` (component set / version) and, in lockstep, bump
   `devbox_packages.otelcol_edge.version` in
   `roles/devbox/defaults/main/packages.yml`.
2. Push a tag `otelcol-edge-v<version>` (or run the workflow manually). CI
   (`.github/workflows/otelcol-edge.yml`) builds `darwin/arm64` via OCB, smoke-
   checks that `file_storage` + `redaction` are present, and publishes
   `otelcol-edge_darwin_arm64` + `.sha256` to the release.
3. Run `make personal` / `make work`. Ansible downloads the pinned binary,
   deploys the config layers + wrapper + LaunchAgent, and bootstraps the service.

**Ordering matters:** the release must exist before the full run pulls it. If it
does not, the download step warns and the service is skipped (no crash).

## Machine-local setup (once per machine)

- **Endpoint** (non-secret) — via the gitignored local overlay:
  `roles/devbox/local/.config/otelcol-edge/endpoint.env` containing
  `OTELBOX_EDGE_ENDPOINT=otel.example.com:443`. See `endpoint.env.example`.
- **Ingestion key** (secret) — in the login keychain, never on disk:
  `security add-generic-password -U -a "$USER" -s otelbox-edge-token -w '<TOKEN>'`
  (grant "Always Allow" on the first service read).
