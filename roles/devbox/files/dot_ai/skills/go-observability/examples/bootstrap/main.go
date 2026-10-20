// Telemetry bootstrap for a Go service. otelBootstrap is the OpenTelemetry
// SDK path (OTLP to the collector plus a Prometheus scrape endpoint);
// clientGolangBootstrap is the equivalent for a project already on
// client_golang. A service uses one of them, never both.
package main

import (
	"context"
	"net/http"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/prometheus/otlptranslator"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/contrib/instrumentation/runtime"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetricgrpc"
	otelprom "go.opentelemetry.io/otel/exporters/prometheus"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/resource"
	"go.opentelemetry.io/otel/semconv/v1.43.0/httpconv"
)

// Semconv explicit bucket boundaries for HTTP and RPC durations, seconds. The
// semconv instruments carry them as advice; set them yourself only on an
// instrument created without one.
var semconvBuckets = []float64{0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10}

func otelBootstrap(ctx context.Context, mux *http.ServeMux) (http.Handler, error) {
	exp, err := otlpmetricgrpc.New(ctx) // OTEL_EXPORTER_OTLP_ENDPOINT from the environment
	if err != nil {
		return nil, err
	}
	// Today's default translation, pinned because the SDK announces a change.
	promExp, err := otelprom.New(otelprom.WithTranslationStrategy(otlptranslator.UnderscoreEscapingWithSuffixes))
	if err != nil {
		return nil, err
	}
	provider := sdkmetric.NewMeterProvider(
		sdkmetric.WithReader(sdkmetric.NewPeriodicReader(exp)),
		sdkmetric.WithReader(promExp),
		sdkmetric.WithResource(resource.Default()), // service.name etc. from OTEL_RESOURCE_ATTRIBUTES
	)
	otel.SetMeterProvider(provider)
	if err := runtime.Start(runtime.WithMinimumReadMemStatsInterval(time.Second)); err != nil {
		return nil, err
	}
	// http.server.request.duration with the semconv buckets and attributes;
	// otelhttp sets http.route from http.Request.Pattern (Go 1.22+ ServeMux).
	if _, err := httpconv.NewServerRequestDuration(otel.Meter("checkout")); err != nil {
		return nil, err
	}
	mux.Handle("/metrics", promhttp.Handler())
	return otelhttp.NewHandler(mux, "server"), nil
}

func clientGolangBootstrap(reg *prometheus.Registry) *prometheus.HistogramVec {
	return promauto.With(reg).NewHistogramVec(prometheus.HistogramOpts{
		Name:                        "http_server_request_duration_seconds",
		Help:                        "HTTP server request duration.",
		Buckets:                     semconvBuckets,
		NativeHistogramBucketFactor: 1.1,
	}, []string{"http_request_method", "http_route", "http_response_status_code"})
}

func main() {
	mux := http.NewServeMux()
	if _, err := otelBootstrap(context.Background(), mux); err != nil {
		panic(err)
	}
}

var _ = clientGolangBootstrap
