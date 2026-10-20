# Trace fixtures

Hand-written protojson lines (`orders.trace.v1.Event`) that exercise `TraceOrders.tla` itself.
They are not recordings of a system. Recordings and counterexamples live in `.runs/` and
`_apalache-out/`, see the `tla-plus` skill §8 for what goes to git.

| File | Expected |
|------|----------|
| `happy-path.jsonl` | accepted |
| `ship-before-pay.jsonl` | rejected at line 2: `Ship` is not enabled for an unpaid customer |
