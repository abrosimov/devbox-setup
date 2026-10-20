// Telemetry bootstrap for a Go service: OpenTelemetry SDK with an OTLP reader
// (to the collector) and a Prometheus reader (scrape endpoint), the semconv
// histogram boundaries as a view, runtime metrics, otelhttp at the edge, and
// the client_golang equivalent for projects on that SDK. Compiles; not wired
// to a real server.
package main

import (
	"context"
	"net/http"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/contrib/instrumentation/runtime"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetricgrpc"
	otelprom "go.opentelemetry.io/otel/exporters/prometheus"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/resource"
)

// Semconv explicit bucket boundaries for http.*.request.duration, rpc and db durations (seconds).
var semconvBuckets = []float64{0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10}

// routeAttr returns the router's route template as http.route; the raw path never becomes a label.
func routeAttr(r *http.Request) []attribute.KeyValue {
	return []attribute.KeyValue{attribute.String("http.route", r.Pattern)}
}

func otelBootstrap(ctx context.Context, mux *http.ServeMux) (http.Handler, error) {
	exp, err := otlpmetricgrpc.New(ctx) // OTEL_EXPORTER_OTLP_ENDPOINT from the environment
	if err != nil {
		return nil, err
	}
	promExp, err := otelprom.New() // registers on prometheus.DefaultRegisterer
	if err != nil {
		return nil, err
	}
	provider := sdkmetric.NewMeterProvider(
		sdkmetric.WithReader(sdkmetric.NewPeriodicReader(exp)),
		sdkmetric.WithReader(promExp),
		sdkmetric.WithResource(resource.Default()), // service.name, service.version from OTEL_RESOURCE_ATTRIBUTES
		sdkmetric.WithView(sdkmetric.NewView(
			sdkmetric.Instrument{Name: "http.server.request.duration"},
			sdkmetric.Stream{Aggregation: sdkmetric.AggregationExplicitBucketHistogram{Boundaries: semconvBuckets}},
		)),
	)
	otel.SetMeterProvider(provider)
	if err := runtime.Start(runtime.WithMinimumReadMemStatsInterval(time.Second)); err != nil {
		return nil, err
	}
	mux.Handle("/metrics", promhttp.Handler())
	return otelhttp.NewHandler(mux, "server", otelhttp.WithMetricAttributesFn(routeAttr)), nil
}

// clientGolangBootstrap is the equivalent for a project already on client_golang:
// the translated Prometheus name, the same buckets, native histograms on top.
func clientGolangBootstrap(reg *prometheus.Registry) *prometheus.HistogramVec {
	return promauto.With(reg).NewHistogramVec(prometheus.HistogramOpts{
		Name:                        "http_server_request_duration_seconds",
		Help:                        "HTTP server request duration.",
		Buckets:                     semconvBuckets,
		NativeHistogramBucketFactor: 1.1,
	}, []string{"http_request_method", "http_route", "http_response_status_code"})
}

// Exporter options for pipelines that already use unsuffixed names.
var _ = []any{otelprom.WithoutUnits, otelprom.WithoutCounterSuffixes, otelprom.WithoutScopeInfo, otelprom.WithoutTargetInfo}

func main() {
	mux := http.NewServeMux()
	handler, err := otelBootstrap(context.Background(), mux)
	if err != nil {
		panic(err)
	}
	_ = clientGolangBootstrap(prometheus.NewRegistry())
	_ = handler
}
