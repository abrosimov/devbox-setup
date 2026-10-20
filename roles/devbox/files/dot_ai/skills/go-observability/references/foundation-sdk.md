# Grafana Foundation SDK (Go)

Module `github.com/grafana/grafana-foundation-sdk/go`, packages `dashboard`, `timeseries`, `stat`,
`table`, `prometheus`, `alerting`, `cog`, `common`. The Go module is tagged `v0.0.N` (`v0.0.21`
at the time of writing; `go list -m -versions github.com/grafana/grafana-foundation-sdk/go` lists
them); pin the tag the project already uses, otherwise the newest, and read `go doc` for the builder
signatures of that tag. The code below compiles against `v0.0.21`.

## Program Layout

```
observability/dashboards/
  main.go            # flag -o <dir>; renders every dashboard to <dir>/<uid>.json
  checkout.go        # func checkoutDashboard() *dashboard.DashboardBuilder
  panels.go          # shared builders: redRow, saturationRow, detectorPanel
  out/checkout.json  # committed render; CI diff fails when stale
```

## Dashboard

Full program: `examples/dashboards/` (`main.go`, `alert.go`, `go.mod`); it builds against
`v0.0.21` and renders `checkout.json`. The shape:

```go
package main

import (
    "github.com/grafana/grafana-foundation-sdk/go/cog"
    "github.com/grafana/grafana-foundation-sdk/go/common"
    "github.com/grafana/grafana-foundation-sdk/go/dashboard"
    "github.com/grafana/grafana-foundation-sdk/go/prometheus"
    "github.com/grafana/grafana-foundation-sdk/go/stat"
    "github.com/grafana/grafana-foundation-sdk/go/timeseries"
)

var promDS = dashboard.DataSourceRef{Type: cog.ToPtr("prometheus"), Uid: cog.ToPtr("${datasource}")}

func query(expr, legend string) *prometheus.DataqueryBuilder {
    return prometheus.NewDataqueryBuilder().Expr(expr).LegendFormat(legend)
}

func checkoutDashboard() *dashboard.DashboardBuilder {
    return dashboard.NewDashboardBuilder("Checkout").
        Uid("checkout").
        Tags([]string{"checkout", "generated"}).
        Refresh("30s").
        Time("now-6h", "now").
        Timezone(common.TimeZoneBrowser).
        WithVariable(dashboard.NewDatasourceVariableBuilder("datasource").
            Label("Datasource").Type("prometheus")).
        WithVariable(dashboard.NewQueryVariableBuilder("service").
            Label("Service").Datasource(promDS).
            Query(dashboard.StringOrMap{String: cog.ToPtr(`label_values(target_info, service_name)`)}).
            Refresh(dashboard.VariableRefreshOnDashboardLoad)).
        WithRow(dashboard.NewRowBuilder("Overview")).
        WithPanel(stat.NewPanelBuilder().
            Title("Error budget burn (1h)").
            Datasource(promDS).
            Unit("none").
            Decimals(2).
            Thresholds(dashboard.NewThresholdsConfigBuilder().
                Mode(dashboard.ThresholdsModeAbsolute).
                Steps([]dashboard.Threshold{
                    {Color: "green"},
                    {Color: "orange", Value: cog.ToPtr[float64](1)},
                    {Color: "red", Value: cog.ToPtr[float64](14.4)},
                })).
            WithTarget(query(`sli:checkout_errors:ratio_rate1h / 0.001`, "burn")).
            Height(4).Span(6)).
        WithRow(dashboard.NewRowBuilder("Traffic")).
        WithPanel(timeseries.NewPanelBuilder().
            Title("Requests / s by route").
            Datasource(promDS).
            Unit("reqps").
            WithTarget(query(`sum by (http_route) (rate(http_server_request_duration_seconds_count{service_name="$service"}[5m]))`, "{{http_route}}")).
            Height(8).Span(12)).
        WithPanel(timeseries.NewPanelBuilder().
            Title("p99 latency by route").
            Datasource(promDS).
            Unit("s").
            WithTarget(query(`histogram_quantile(0.99, sum by (le, http_route) (rate(http_server_request_duration_seconds_bucket{service_name="$service"}[5m])))`, "{{http_route}}")).
            Height(8).Span(12))
}
```

Rendering: `main.go` in the example takes `-o <dir>` and writes `<uid>.json` per dashboard with
`json.MarshalIndent`.

`Build()` validates required fields; a build error is a bug in the program, not a warning.

## Shared Builders

Keep the catalogue's structure in code: one builder per row type, parameterised by the catalogue
row, so a dashboard is a list of catalogue ids rather than hand-placed panels.

```go
func detectorPanel(title, metric string) *timeseries.PanelBuilder {
    return timeseries.NewPanelBuilder().
        Title(title).
        Datasource(promDS).
        Unit("short").
        WithTarget(query(`sum by (error_type) (increase(`+metric+`{service_name="$service"}[5m]))`, "{{error_type}}")).
        Height(6).Span(8)
}
```

## Grafana-Managed Alert Rules

When the project uses Grafana alerting rather than Prometheus rules, the `alerting` package builds
rule groups the same way; the expression, labels and annotations follow `alert-rules.md`
unchanged, and the promtool tests still run against a Prometheus-rule rendering of the same
expressions kept next to it, because Grafana has no equivalent unit test.

See `examples/dashboards/alert.go`: `alerting.NewRuleGroupBuilder(...).FolderUid(...).Interval(60)`
with one `alerting.NewRuleBuilder(name)` per rule carrying `For`, `Labels`, `Annotations`,
`Condition("C")` and a `WithQuery(alerting.NewQueryBuilder("A").DatasourceUid(...).Model(
prometheus.NewDataqueryBuilder().Expr(...)))`, plus the reduce (`B`) and threshold (`C`) expressions
as in the Grafana provisioning docs.

## Conventions

- `Uid` is stable and lower-case; the title may change, the uid never does.
- `Tags` include `generated`; a hand-edited dashboard in Grafana with that tag is overwritten by
  the next deploy, and the hand-off says so.
- Every panel: `Unit`, `Datasource(promDS)`, a legend template from the attribute that matters,
  `Height` and `Span` set explicitly.
- Alerting panels link to the runbook via `Links`.
- No panel without a catalogue row; the row id goes in the panel `Description`.
- Validation: `go run ./observability/dashboards -o observability/dashboards/out`, then
  `jq empty` on each file, then `git diff --exit-code observability/dashboards/out` in CI;
  `dashboard-linter lint <file>` when the project installs it.

## Sources

- Grafana Foundation SDK, Go README and reference — https://github.com/grafana/grafana-foundation-sdk/tree/main/go
- Grafana dashboard JSON model — https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/view-dashboard-json-model/
- Grafana-managed alerting provisioning — https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/
- `grafana/dashboard-linter` — https://github.com/grafana/dashboard-linter
