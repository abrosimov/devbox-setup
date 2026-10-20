# go-observability examples

Runnable counterparts of the skill's rules; `tests/deploy/test_skill_examples.py` builds and
checks them when `SKILL_EXAMPLES=1` and the tools are present.

| Directory | What | Check |
|-----------|------|-------|
| `dashboards/` | Foundation SDK program rendering `checkout.json` | `go build -o /dev/null . && go run . -o "$(mktemp -d)"` |
| `bootstrap/` | OTel SDK bootstrap and the client_golang equivalent | `go build -o /dev/null . && go vet .` |
| `rules/checkout/` | Nine rules across the three layers, recording rules, promtool tests | `promtool check rules alerts.yaml recording.yaml && promtool test rules tests/alerts_test.yaml` |
