# Grafonnet Patterns

Reference patterns for dashboard construction using the new Grafonnet library.

## Library Setup

### Importing Grafonnet

```jsonnet
// Use the latest generated Grafonnet
local g = import 'github.com/grafana/grafonnet/gen/grafonnet-latest/main.libsonnet';

// Or pin to specific Grafana version
local g = import 'github.com/grafana/grafonnet/gen/grafonnet-v11.0.0/main.libsonnet';

// Common imports
local dashboard = g.dashboard;
local row = g.panel.row;
local timeSeries = g.panel.timeSeries;
local stat = g.panel.stat;
local gauge = g.panel.gauge;
local table = g.panel.table;
local heatmap = g.panel.heatmap;
local logs = g.panel.logs;
local prometheus = g.query.prometheus;
local loki = g.query.loki;
```

### Vendor Dependencies

```bash
# Initialize jsonnet-bundler
jb init

# Install Grafonnet
jb install github.com/grafana/grafonnet/gen/grafonnet-latest@main

# Update dependencies
jb update
```

## Dashboard Structure

### Basic Dashboard

```jsonnet
local g = import 'github.com/grafana/grafonnet/gen/grafonnet-latest/main.libsonnet';

local dashboard = g.dashboard;
local row = g.panel.row;
local timeSeries = g.panel.timeSeries;
local prometheus = g.query.prometheus;

// SANDBOX PREFIX - MANDATORY FOR ALL TEST DASHBOARDS
local title = 'SANDBOX: Service Overview';

dashboard.new(title)
+ dashboard.withUid('sandbox-service-overview')
+ dashboard.withDescription('Overview dashboard for service monitoring')
+ dashboard.withTags(['sandbox', 'service', 'overview'])
+ dashboard.withTimezone('browser')
+ dashboard.withRefresh('30s')
+ dashboard.withEditable(true)
+ dashboard.time.withFrom('now-1h')
+ dashboard.time.withTo('now')
+ dashboard.withPanels([
  // Panels defined here
])
```

### Dashboard with Variables

```jsonnet
local variable = g.dashboard.variable;

dashboard.new('SANDBOX: Multi-Service Dashboard')
+ dashboard.withUid('sandbox-multi-service')
+ dashboard.withVariables([
  // Datasource variable
  variable.datasource.new('datasource', 'prometheus')
  + variable.datasource.withRegex('.*')
  + variable.datasource.generalOptions.withLabel('Data Source'),

  // Query variable
  variable.query.new('namespace')
  + variable.query.withDatasourceFromVariable(variable.datasource.new('datasource', 'prometheus'))
  + variable.query.queryTypes.withLabelValues('namespace', 'kube_pod_info')
  + variable.query.withRefresh('time')  // Refresh on time range change
  + variable.query.selectionOptions.withMulti(true)
  + variable.query.selectionOptions.withIncludeAll(true)
  + variable.query.generalOptions.withLabel('Namespace'),

  // Service variable (depends on namespace)
  variable.query.new('service')
  + variable.query.withDatasourceFromVariable(variable.datasource.new('datasource', 'prometheus'))
  + variable.query.queryTypes.withLabelValues('service', 'up{namespace=~"$namespace"}')
  + variable.query.withRefresh('time')
  + variable.query.selectionOptions.withMulti(true)
  + variable.query.selectionOptions.withIncludeAll(true)
  + variable.query.generalOptions.withLabel('Service'),

  // Interval variable
  variable.interval.new('interval', ['1m', '5m', '10m', '30m', '1h'])
  + variable.interval.withAutoOption(count=30, minInterval='10s')
  + variable.interval.generalOptions.withLabel('Interval'),
])
```

## Panel Types

### Time Series Panel

The most common panel for metrics over time:

```jsonnet
local timeSeries = g.panel.timeSeries;
local prometheus = g.query.prometheus;

local requestRatePanel =
  timeSeries.new('Request Rate')
  + timeSeries.panelOptions.withDescription('HTTP requests per second')
  + timeSeries.queryOptions.withDatasource('prometheus', '$datasource')
  + timeSeries.queryOptions.withTargets([
    prometheus.new('$datasource', 'sum(rate(http_requests_total{namespace="$namespace", service="$service"}[5m])) by (service)')
    + prometheus.withLegendFormat('{{ service }}')
    + prometheus.withInterval('$interval'),
  ])
  + timeSeries.standardOptions.withUnit('reqps')
  + timeSeries.standardOptions.withMin(0)
  + timeSeries.fieldConfig.defaults.custom.withLineWidth(2)
  + timeSeries.fieldConfig.defaults.custom.withFillOpacity(10)
  + timeSeries.fieldConfig.defaults.custom.withShowPoints('never')
  + timeSeries.options.legend.withDisplayMode('table')
  + timeSeries.options.legend.withPlacement('bottom')
  + timeSeries.options.legend.withCalcs(['mean', 'max', 'last'])
  + timeSeries.gridPos.withW(12)
  + timeSeries.gridPos.withH(8);
```

### Stat Panel

For single values with optional sparkline:

```jsonnet
local stat = g.panel.stat;

local errorRateStat =
  stat.new('Error Rate')
  + stat.panelOptions.withDescription('Current error rate percentage')
  + stat.queryOptions.withDatasource('prometheus', '$datasource')
  + stat.queryOptions.withTargets([
    prometheus.new('$datasource', |||
      sum(rate(http_requests_total{status=~"5..", namespace="$namespace"}[5m]))
      /
      sum(rate(http_requests_total{namespace="$namespace"}[5m]))
    |||)
    + prometheus.withLegendFormat('Error Rate'),
  ])
  + stat.standardOptions.withUnit('percentunit')
  + stat.standardOptions.withMin(0)
  + stat.standardOptions.withMax(1)
  + stat.standardOptions.thresholds.withMode('absolute')
  + stat.standardOptions.thresholds.withSteps([
    stat.thresholdStep.withValue(0) + stat.thresholdStep.withColor('green'),
    stat.thresholdStep.withValue(0.01) + stat.thresholdStep.withColor('yellow'),
    stat.thresholdStep.withValue(0.05) + stat.thresholdStep.withColor('red'),
  ])
  + stat.options.withGraphMode('area')
  + stat.options.withTextMode('auto')
  + stat.options.withColorMode('background')
  + stat.gridPos.withW(4)
  + stat.gridPos.withH(4);
```

### Gauge Panel

For values with thresholds and limits:

```jsonnet
local gauge = g.panel.gauge;

local cpuGauge =
  gauge.new('CPU Usage')
  + gauge.queryOptions.withDatasource('prometheus', '$datasource')
  + gauge.queryOptions.withTargets([
    prometheus.new('$datasource', 'avg(rate(container_cpu_usage_seconds_total{namespace="$namespace"}[5m])) * 100')
    + prometheus.withLegendFormat('CPU'),
  ])
  + gauge.standardOptions.withUnit('percent')
  + gauge.standardOptions.withMin(0)
  + gauge.standardOptions.withMax(100)
  + gauge.standardOptions.thresholds.withMode('absolute')
  + gauge.standardOptions.thresholds.withSteps([
    gauge.thresholdStep.withValue(0) + gauge.thresholdStep.withColor('green'),
    gauge.thresholdStep.withValue(70) + gauge.thresholdStep.withColor('yellow'),
    gauge.thresholdStep.withValue(90) + gauge.thresholdStep.withColor('red'),
  ])
  + gauge.options.withShowThresholdLabels(false)
  + gauge.options.withShowThresholdMarkers(true)
  + gauge.gridPos.withW(6)
  + gauge.gridPos.withH(6);
```

### Table Panel

For tabular data:

```jsonnet
local table = g.panel.table;

local podsTable =
  table.new('Pod Status')
  + table.queryOptions.withDatasource('prometheus', '$datasource')
  + table.queryOptions.withTargets([
    prometheus.new('$datasource', 'kube_pod_status_phase{namespace="$namespace"} == 1')
    + prometheus.withFormat('table')
    + prometheus.withInstant(true),
  ])
  + table.queryOptions.withTransformations([
    table.transformation.withId('organize')
    + table.transformation.withOptions({
      excludeByName: {
        Time: true,
        __name__: true,
        job: true,
        instance: true,
      },
      renameByName: {
        pod: 'Pod',
        phase: 'Phase',
        namespace: 'Namespace',
      },
    }),
  ])
  + table.fieldConfig.defaults.custom.withAlign('left')
  + table.options.withShowHeader(true)
  + table.options.footer.withEnablePagination(true)
  + table.gridPos.withW(24)
  + table.gridPos.withH(8);
```

### Heatmap Panel

For distribution visualization:

```jsonnet
local heatmap = g.panel.heatmap;

local latencyHeatmap =
  heatmap.new('Request Latency Distribution')
  + heatmap.queryOptions.withDatasource('prometheus', '$datasource')
  + heatmap.queryOptions.withTargets([
    prometheus.new('$datasource', 'sum(increase(http_request_duration_seconds_bucket{namespace="$namespace"}[$__rate_interval])) by (le)')
    + prometheus.withFormat('heatmap')
    + prometheus.withLegendFormat('{{ le }}'),
  ])
  + heatmap.options.withCalculate(false)  // Data is already bucketed
  + heatmap.options.yAxis.withUnit('s')
  + heatmap.options.color.withScheme('Spectral')
  + heatmap.options.color.withMode('scheme')
  + heatmap.gridPos.withW(12)
  + heatmap.gridPos.withH(8);
```

### Logs Panel

For Loki log viewing:

```jsonnet
local logs = g.panel.logs;
local loki = g.query.loki;

local logsPanel =
  logs.new('Application Logs')
  + logs.queryOptions.withDatasource('loki', '$loki_datasource')
  + logs.queryOptions.withTargets([
    loki.new('$loki_datasource', '{namespace="$namespace", app="$service"} |= "$search"')
    + loki.withLegendFormat(''),
  ])
  + logs.options.withShowTime(true)
  + logs.options.withShowLabels(false)
  + logs.options.withShowCommonLabels(false)
  + logs.options.withWrapLogMessage(true)
  + logs.options.withPrettifyLogMessage(true)
  + logs.options.withEnableLogDetails(true)
  + logs.options.withSortOrder('Descending')
  + logs.gridPos.withW(24)
  + logs.gridPos.withH(10);
```

## Layout Patterns

### Row Organization

```jsonnet
local row = g.panel.row;

local overviewRow =
  row.new('Overview')
  + row.withCollapsed(false);

local detailsRow =
  row.new('Details')
  + row.withCollapsed(true);  // Collapsed by default

// Panels after a row belong to that row
dashboard.new('SANDBOX: Dashboard')
+ dashboard.withPanels([
  // Overview section
  overviewRow
  + row.gridPos.withW(24) + row.gridPos.withH(1) + row.gridPos.withX(0) + row.gridPos.withY(0),

  errorRateStat
  + stat.gridPos.withX(0) + stat.gridPos.withY(1),

  requestRatePanel
  + timeSeries.gridPos.withX(4) + timeSeries.gridPos.withY(1),

  // Details section (collapsed)
  detailsRow
  + row.gridPos.withX(0) + row.gridPos.withY(10),

  podsTable
  + table.gridPos.withX(0) + table.gridPos.withY(11),
])
```

### Grid Positioning

```
Dashboard width = 24 units

+------+------------------+
|  4   |       20         |  Y=0, H=8
+------+------------------+
|          24             |  Y=8, H=8
+-------------------------+
|    12     |     12      |  Y=16, H=8
+-------------------------+

// First row: small stat + wide panel
panel1.gridPos.withX(0) + panel1.gridPos.withY(0) + panel1.gridPos.withW(4) + panel1.gridPos.withH(8)
panel2.gridPos.withX(4) + panel2.gridPos.withY(0) + panel2.gridPos.withW(20) + panel2.gridPos.withH(8)

// Second row: full width
panel3.gridPos.withX(0) + panel3.gridPos.withY(8) + panel3.gridPos.withW(24) + panel3.gridPos.withH(8)

// Third row: two equal panels
panel4.gridPos.withX(0) + panel4.gridPos.withY(16) + panel4.gridPos.withW(12) + panel4.gridPos.withH(8)
panel5.gridPos.withX(12) + panel5.gridPos.withY(16) + panel5.gridPos.withW(12) + panel5.gridPos.withH(8)
```

## Reusable Components

### Panel Factory Functions

```jsonnet
// lib/panels.libsonnet
{
  // RED metric panels
  red:: {
    requestRate(title='Request Rate', service='$service')::
      timeSeries.new(title)
      + timeSeries.queryOptions.withDatasource('prometheus', '$datasource')
      + timeSeries.queryOptions.withTargets([
        prometheus.new('$datasource', 'sum(rate(http_requests_total{service="%s"}[5m]))' % service)
        + prometheus.withLegendFormat('requests/s'),
      ])
      + timeSeries.standardOptions.withUnit('reqps')
      + timeSeries.gridPos.withW(8)
      + timeSeries.gridPos.withH(8),

    errorRate(title='Error Rate', service='$service')::
      timeSeries.new(title)
      + timeSeries.queryOptions.withDatasource('prometheus', '$datasource')
      + timeSeries.queryOptions.withTargets([
        prometheus.new('$datasource', |||
          sum(rate(http_requests_total{service="%s", status=~"5.."}[5m]))
          /
          sum(rate(http_requests_total{service="%s"}[5m]))
        ||| % [service, service])
        + prometheus.withLegendFormat('error rate'),
      ])
      + timeSeries.standardOptions.withUnit('percentunit')
      + timeSeries.standardOptions.thresholds.withSteps([
        { value: 0, color: 'green' },
        { value: 0.01, color: 'yellow' },
        { value: 0.05, color: 'red' },
      ])
      + timeSeries.gridPos.withW(8)
      + timeSeries.gridPos.withH(8),

    latency(title='Latency (p99)', service='$service')::
      timeSeries.new(title)
      + timeSeries.queryOptions.withDatasource('prometheus', '$datasource')
      + timeSeries.queryOptions.withTargets([
        prometheus.new('$datasource', 'histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{service="%s"}[5m])) by (le))' % service)
        + prometheus.withLegendFormat('p99'),
      ])
      + timeSeries.standardOptions.withUnit('s')
      + timeSeries.gridPos.withW(8)
      + timeSeries.gridPos.withH(8),
  },

  // USE metric panels
  use:: {
    cpuUtilization(title='CPU Utilization')::
      gauge.new(title)
      + gauge.queryOptions.withDatasource('prometheus', '$datasource')
      + gauge.queryOptions.withTargets([
        prometheus.new('$datasource', 'avg(rate(container_cpu_usage_seconds_total{namespace="$namespace"}[5m])) * 100'),
      ])
      + gauge.standardOptions.withUnit('percent')
      + gauge.standardOptions.withMin(0)
      + gauge.standardOptions.withMax(100)
      + gauge.gridPos.withW(6)
      + gauge.gridPos.withH(6),

    memoryUtilization(title='Memory Utilization')::
      gauge.new(title)
      + gauge.queryOptions.withDatasource('prometheus', '$datasource')
      + gauge.queryOptions.withTargets([
        prometheus.new('$datasource', 'avg(container_memory_usage_bytes{namespace="$namespace"} / container_spec_memory_limit_bytes{namespace="$namespace"}) * 100'),
      ])
      + gauge.standardOptions.withUnit('percent')
      + gauge.standardOptions.withMin(0)
      + gauge.standardOptions.withMax(100)
      + gauge.gridPos.withW(6)
      + gauge.gridPos.withH(6),
  },
}
```

### Using the Factory

```jsonnet
local panels = import 'lib/panels.libsonnet';

dashboard.new('SANDBOX: Service Dashboard')
+ dashboard.withPanels([
  // RED metrics row
  panels.red.requestRate()
  + timeSeries.gridPos.withX(0) + timeSeries.gridPos.withY(0),

  panels.red.errorRate()
  + timeSeries.gridPos.withX(8) + timeSeries.gridPos.withY(0),

  panels.red.latency()
  + timeSeries.gridPos.withX(16) + timeSeries.gridPos.withY(0),

  // USE metrics row
  panels.use.cpuUtilization()
  + gauge.gridPos.withX(0) + gauge.gridPos.withY(8),

  panels.use.memoryUtilization()
  + gauge.gridPos.withX(6) + gauge.gridPos.withY(8),
])
```

## Common Patterns

### Multi-Query Panel with Overrides

```jsonnet
timeSeries.new('Multiple Metrics')
+ timeSeries.queryOptions.withTargets([
  prometheus.new('$datasource', 'rate(http_requests_total{status="200"}[5m])')
  + prometheus.withLegendFormat('Success')
  + prometheus.withRefId('A'),

  prometheus.new('$datasource', 'rate(http_requests_total{status=~"5.."}[5m])')
  + prometheus.withLegendFormat('Errors')
  + prometheus.withRefId('B'),
])
+ timeSeries.standardOptions.withOverrides([
  {
    matcher: { id: 'byName', options: 'Success' },
    properties: [
      { id: 'color', value: { mode: 'fixed', fixedColor: 'green' } },
    ],
  },
  {
    matcher: { id: 'byName', options: 'Errors' },
    properties: [
      { id: 'color', value: { mode: 'fixed', fixedColor: 'red' } },
      { id: 'custom.fillOpacity', value: 30 },
    ],
  },
])
```

### Annotations

```jsonnet
local annotation = g.dashboard.annotation;

dashboard.new('SANDBOX: Dashboard with Annotations')
+ dashboard.withAnnotations([
  annotation.withName('Deployments')
  + annotation.withDatasource('prometheus', '$datasource')
  + annotation.withExpr('changes(kube_deployment_status_observed_generation{namespace="$namespace"}[1m]) > 0')
  + annotation.withEnable(true)
  + annotation.withIconColor('blue')
  + annotation.withTitleFormat('Deployment')
  + annotation.withTextFormat('{{ deployment }}'),

  annotation.withName('Alerts')
  + annotation.withDatasource('prometheus', '$datasource')
  + annotation.withExpr('ALERTS{alertstate="firing", namespace="$namespace"}')
  + annotation.withEnable(true)
  + annotation.withIconColor('red')
  + annotation.withTitleFormat('Alert: {{ alertname }}'),
])
```

### Links

```jsonnet
dashboard.new('SANDBOX: Dashboard with Links')
+ dashboard.withLinks([
  g.dashboard.link.link.new('Grafana Docs', 'https://grafana.com/docs')
  + g.dashboard.link.link.options.withTargetBlank(true),

  g.dashboard.link.dashboards.new('Related Dashboards')
  + g.dashboard.link.dashboards.options.withTags(['service'])
  + g.dashboard.link.dashboards.options.withAsDropdown(true)
  + g.dashboard.link.dashboards.options.withIncludeVars(true)
  + g.dashboard.link.dashboards.options.withKeepTime(true),
])
```

## Anti-Patterns to Avoid

### DON'T: Hardcode Values

```jsonnet
// BAD
prometheus.new('prometheus', 'rate(http_requests_total{service="api"}[5m])')

// GOOD - use variables
prometheus.new('$datasource', 'rate(http_requests_total{service="$service"}[5m])')
```

### DON'T: Skip Error Handling

```jsonnet
// BAD - division by zero possible
'sum(errors) / sum(requests)'

// GOOD - handle zero denominator
'sum(errors) / (sum(requests) > 0) or vector(0)'
```

### DON'T: Use Unbounded Queries

```jsonnet
// BAD - no time bounds
prometheus.new('$datasource', 'http_requests_total')

// GOOD - use rate with interval
prometheus.new('$datasource', 'rate(http_requests_total[5m])')
```

### DON'T: Forget Units

```jsonnet
// BAD - no unit
timeSeries.new('Latency')

// GOOD - specify unit
timeSeries.new('Latency')
+ timeSeries.standardOptions.withUnit('s')
```

## Validation Checklist

Before generating final JSON:

- [ ] Dashboard has `SANDBOX:` prefix in title
- [ ] UID is unique and prefixed with `sandbox-`
- [ ] All panels have datasource variables (`$datasource`)
- [ ] All queries use appropriate rate/increase functions
- [ ] Units are specified for all numeric panels
- [ ] Thresholds are defined for stat/gauge panels
- [ ] Grid positions don't overlap
- [ ] Variables have refresh settings
- [ ] Legends are configured for readability
