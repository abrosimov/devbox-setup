package main

import (
	"github.com/grafana/grafana-foundation-sdk/go/alerting"
	"github.com/grafana/grafana-foundation-sdk/go/prometheus"
)

// Grafana-managed rule group; the expressions, labels and annotations follow
// references/alert-rules.md. Reduce (B) and threshold (C) expressions are added
// as in the Grafana provisioning documentation.
var _ = alerting.NewRuleGroupBuilder("checkout").
	FolderUid("observability").
	Interval(60).
	WithRule(alerting.NewRuleBuilder("CheckoutErrorBudgetBurnFast").
		For("2m").
		Labels(map[string]string{"severity": "page", "layer": "product", "maturity": "agreed"}).
		Annotations(map[string]string{"runbook_url": "https://runbooks.example/CheckoutErrorBudgetBurnFast"}).
		Condition("C").
		WithQuery(alerting.NewQueryBuilder("A").DatasourceUid("prom").
			Model(prometheus.NewDataqueryBuilder().Expr(`sli:checkout_errors:ratio_rate1h`))),
	)
