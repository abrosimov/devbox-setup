---
aliases:
  - ADR-091 points (from v01)
---
# ADR-091 review — review points

| Slug | Claim about the ADR | ADR section | Facts | Proposal | Deadline | Status by version |
|---|---|---|---|---|---|---|
| `retry-unstated` | The ADR does not say what the loader does when a batch fails | Decision | `loader-no-retry`, `landing-overwrite` | State a retry limit for the loader and set it in the client | before acceptance | v01 adopted |
| `partial-night` | The ADR does not say what Finance sees after a night the loader does not finish | Consequences | `landing-overwrite`, `window-length` | Load into a staging table and switch it in at the end, or state that a partial night is shown | before acceptance | v01 adopted |
