---
aliases:
  - ADR-091 facts (from v01)
---
# ADR-091 review — facts

| Slug | Fact | Reference | Checked | Must-keep | Used by |
|---|---|---|---|---|---|
| `loader-no-retry` | The vendor's bulk-load client does not retry a failed batch unless `retries` is set; its default is 0 | verified in the vendored client: [bulk_client.py:88-97](https://gitlab.com/example/billing/-/blob/3f9c2a7d1e4b5a6c8d9e0f1a2b3c4d5e6f7a8b9c/vendor/bulk_client.py#L88-97); documented: [vendor guide, "Retries"](https://docs.example.com/bulk-load#retries) | 2026-11-24 | yes | `retry-unstated` |
| `landing-overwrite` | A bulk load in "replace" mode, the client's default, overwrites the landing table, so a half-finished night leaves partial data | verified: [bulk_client.py:40-52](https://gitlab.com/example/billing/-/blob/3f9c2a7d1e4b5a6c8d9e0f1a2b3c4d5e6f7a8b9c/vendor/bulk_client.py#L40-52); documented: [vendor guide, "Load modes"](https://docs.example.com/bulk-load#load-modes) | 2026-11-24 | yes | `retry-unstated`, `partial-night` |
| `window-length` | The export window is three hours | [ADR-091, "Decision"](https://wiki.example.com/pages/9191/ADR-091#Decision) | 2026-11-24 | yes | `partial-night` |
