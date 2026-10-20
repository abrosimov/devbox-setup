package main

import (
	"encoding/json"
	"flag"
	"github.com/grafana/grafana-foundation-sdk/go/cog"
	"github.com/grafana/grafana-foundation-sdk/go/common"
	"github.com/grafana/grafana-foundation-sdk/go/dashboard"
	"github.com/grafana/grafana-foundation-sdk/go/prometheus"
	"github.com/grafana/grafana-foundation-sdk/go/stat"
	"github.com/grafana/grafana-foundation-sdk/go/timeseries"
	"log"
	"os"
	"path/filepath"
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

func detectorPanel(title, metric string) *timeseries.PanelBuilder {
	return timeseries.NewPanelBuilder().
		Title(title).
		Datasource(promDS).
		Unit("short").
		WithTarget(query(`sum by (error_type) (increase(`+metric+`{service_name="$service"}[5m]))`, "{{error_type}}")).
		Height(6).Span(8)
}

func main() {
	out := flag.String("o", "out", "output directory")
	flag.Parse()
	if err := os.MkdirAll(*out, 0o755); err != nil {
		log.Fatal(err)
	}
	for _, b := range []*dashboard.DashboardBuilder{checkoutDashboard()} {
		d, err := b.Build()
		if err != nil {
			log.Fatal(err)
		}
		data, _ := json.MarshalIndent(d, "", "  ")
		if err := os.WriteFile(filepath.Join(*out, *d.Uid+".json"), data, 0o644); err != nil {
			log.Fatal(err)
		}
	}
}
