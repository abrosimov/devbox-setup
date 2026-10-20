# go-observability examples

Runnable counterparts of the snippets in `references/`. `tests/deploy/test_skill_examples.py`
builds and checks them whenever `go` and `promtool` are available and skips otherwise.

| Directory | What | Verified with |
|-----------|------|---------------|
| `dashboards/` | Foundation SDK program: one dashboard (`checkout`), shared `detectorPanel` builder, a Grafana-managed rule group, `-o` renderer | `go build`, `go run . -o out`, SDK `v0.0.21` |
| `bootstrap/` | OpenTelemetry SDK bootstrap (OTLP + Prometheus readers, semconv histogram view, runtime metrics, `otelhttp`) and the `client_golang` equivalent | `go build` |
| `rules/checkout/` | Three alert layers, recording rules, promtool unit tests with firing and non-firing cases | `promtool check rules`, `promtool test rules` (Prometheus 3.x) |

```bash
cd dashboards && go build ./... && go run . -o out && jq empty out/*.json
cd ../bootstrap && go build ./...
cd ../rules/checkout && promtool check rules alerts.yaml recording.yaml && promtool test rules tests/alerts_test.yaml
```
